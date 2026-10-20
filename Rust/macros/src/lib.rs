//! Procedural macros of `pmdb-recorder`, which documents them.

use proc_macro::TokenStream;
use proc_macro2::{Span, TokenStream as Tokens};
use quote::{format_ident, quote};
use std::collections::HashSet;
use syn::spanned::Spanned;
use syn::{
  Data, DeriveInput, Error, Expr, Fields, FnArg, Ident, ItemFn, LitStr, Pat, PatIdent, Path,
  ReturnType, parse_macro_input, parse_quote,
};

#[proc_macro_attribute]
pub fn record(attr: TokenStream, item: TokenStream) -> TokenStream {
  let mut options = RecordOptions::default();
  let parser = syn::meta::parser(|meta| {
    if meta.path.is_ident("recorder") {
      options.recorder = Some(meta.value()?.parse()?);
      Ok(())
    } else if meta.path.is_ident("name") {
      options.name = Some(meta.value()?.parse()?);
      Ok(())
    } else {
      Err(meta.error("expected `recorder` or `name`"))
    }
  });
  parse_macro_input!(attr with parser);
  let f = parse_macro_input!(item as ItemFn);
  instrument(f, options)
    .unwrap_or_else(Error::into_compile_error)
    .into()
}

#[derive(Default)]
struct RecordOptions {
  recorder: Option<Expr>,
  name: Option<LitStr>,
}

/// Returns `f` instrumented so that its calls are recorded.
fn instrument(mut f: ItemFn, options: RecordOptions) -> syn::Result<Tokens> {
  if let Some(t) = f.sig.asyncness {
    return Err(Error::new(t.span(), "`async` functions can't be recorded"));
  }
  if let Some(t) = f.sig.constness {
    return Err(Error::new(t.span(), "`const` functions can't be recorded"));
  }
  if let Some(abi) = &f.sig.abi {
    return Err(Error::new(
      abi.span(),
      "functions with an explicit ABI can't be recorded",
    ));
  }

  // Name the parameters bound by patterns other than identifiers, which are bound in the body.
  let mut arguments = Vec::new();
  let mut bindings = Vec::new();
  for (i, input) in f.sig.inputs.iter_mut().enumerate() {
    match input {
      FnArg::Receiver(_) => arguments.push(quote!(self)),
      FnArg::Typed(p) => match &*p.pat {
        Pat::Ident(PatIdent {
          by_ref: None,
          subpat: None,
          ident,
          ..
        }) => arguments.push(quote!(#ident)),
        _ => {
          let name = format_ident!("__pmdb_argument{i}");
          let pattern = std::mem::replace(&mut *p.pat, parse_quote!(#name));
          bindings.push(quote!(let #pattern = #name;));
          arguments.push(quote!(#name))
        }
      },
    }
  }

  let recorder = match options.recorder {
    Some(e) => quote!(#e),
    None => quote!(::pmdb_recorder::main()),
  };
  let name = match options.name {
    Some(n) => quote!(#n),
    None => quote!({
      // The name is computed once, from the type name of an item nested in the function.
      fn __pmdb_marker() {}
      static NAME: ::std::sync::OnceLock<::std::string::String> = ::std::sync::OnceLock::new();
      NAME.get_or_init(|| {
        ::pmdb_recorder::__private::qualified_name(
          ::std::any::type_name_of_val(&__pmdb_marker),
          ::std::module_path!(),
        )
      })
    }),
  };

  // Annotate the closure wrapping the body with the return type of the function so that `?` and
  // `return` in the body are typed the same way, unless that type can't be written there.
  let output = match &f.sig.output {
    ReturnType::Type(_, t) if !quote!(#t).to_string().contains("impl") => quote!(-> #t),
    _ => quote!(),
  };

  let block = &f.block;
  let body = quote!({
    let __pmdb_recorder: &::pmdb_recorder::Recorder = #recorder;
    let __pmdb_frame = {
      #[allow(unused_imports)]
      use ::pmdb_recorder::__private::probe::*;
      ::pmdb_recorder::__private::Frame::enter(
        __pmdb_recorder,
        ::core::panic::Location::caller(),
        ::std::env!("CARGO_MANIFEST_DIR"),
        #name,
        ::std::vec![#(::pmdb_recorder::__private::encode(
          |w| (&Probe(&#arguments)).__pmdb_record(w)),)*])
    };
    let __pmdb_outcome = ::std::panic::catch_unwind(::std::panic::AssertUnwindSafe(
      || #output { #(#bindings)* #block }));
    match __pmdb_outcome {
      ::std::result::Result::Ok(__pmdb_result) => {
        #[allow(unused_imports)]
        use ::pmdb_recorder::__private::probe::*;
        __pmdb_frame.result(::pmdb_recorder::__private::encode(
          |w| (&Probe(&__pmdb_result)).__pmdb_record(w)));
        __pmdb_result
      }
      ::std::result::Result::Err(__pmdb_payload) => {
        __pmdb_frame.panic(&*__pmdb_payload);
        ::std::panic::resume_unwind(__pmdb_payload)
      }
    }
  });

  f.attrs.push(parse_quote!(#[track_caller]));
  *f.block = syn::parse2(body)?;
  Ok(quote!(#f))
}

#[proc_macro_derive(Record, attributes(pmdb))]
pub fn derive_record(input: TokenStream) -> TokenStream {
  let input = parse_macro_input!(input as DeriveInput);
  derive(input)
    .unwrap_or_else(Error::into_compile_error)
    .into()
}

/// The options of a field or variant.
#[derive(Default)]
struct MemberOptions {
  skip: bool,
  rename: Option<String>,
  with: Option<Path>,
}

impl MemberOptions {
  fn parse(attrs: &[syn::Attribute]) -> syn::Result<Self> {
    let mut options = Self::default();
    for a in attrs.iter().filter(|a| a.path().is_ident("pmdb")) {
      a.parse_nested_meta(|meta| {
        if meta.path.is_ident("skip") {
          options.skip = true;
        } else if meta.path.is_ident("rename") {
          options.rename = Some(meta.value()?.parse::<LitStr>()?.value());
        } else if meta.path.is_ident("with") {
          options.with = Some(meta.value()?.parse()?);
        } else {
          return Err(meta.error("expected `skip`, `rename`, or `with`"));
        }
        Ok(())
      })?;
    }
    Ok(options)
  }
}

/// A field to record.
struct Field {
  /// The key of the field in a table.
  key: String,

  /// An expression denoting a reference to the value of the field.
  access: Tokens,

  /// The function recording the field, if not the default.
  with: Option<Path>,
}

impl Field {
  /// Returns an expression recording `self` to the writer `w`.
  fn write(&self, w: Tokens) -> Tokens {
    let access = &self.access;
    match &self.with {
      Some(p) => quote!(#p(#access, #w)),
      None => quote!((&Probe(#access)).__pmdb_record(#w)),
    }
  }
}

/// Returns the fields of `fields` that are recorded and the pattern binding all fields, which
/// are accessed by `access` if `bind` is false.
fn collect(
  fields: &Fields, bind: bool, access: impl Fn(Tokens) -> Tokens,
) -> syn::Result<(Vec<Field>, Tokens)> {
  let mut result = Vec::new();
  let mut keys = HashSet::new();
  let mut pattern = Vec::new();
  for (i, f) in fields.iter().enumerate() {
    let options = MemberOptions::parse(&f.attrs)?;
    // Bindings are prefixed so as to not shadow the writers of the generated code.
    let member = match &f.ident {
      Some(n) => quote!(#n),
      None => {
        let i = syn::Index::from(i);
        quote!(#i)
      }
    };
    let binding = format_ident!("__pmdb_field{}", i);
    pattern.push(quote!(#member: #binding));
    if options.skip {
      continue;
    }

    let key = options.rename.unwrap_or_else(|| {
      f.ident
        .as_ref()
        .map_or(i.to_string(), |n| n.unraw().to_string())
    });
    if !keys.insert(key.clone()) {
      return Err(Error::new(f.span(), format!("duplicate key '{key}'")));
    }
    let access = if bind {
      quote!(#binding)
    } else {
      access(member)
    };
    result.push(Field {
      key,
      access,
      with: options.with,
    });
  }
  Ok((result, quote!({ #(#pattern,)* })))
}

/// Returns an expression recording `fields` to the writer `w` as a table, starting with the
/// entries in `prefix`.
fn table(fields: &[Field], prefix: Tokens, prefix_count: usize) -> Tokens {
  let count = fields.len() + prefix_count;
  let writes = fields.iter().map(|f| {
    let key = &f.key;
    f.write(quote!(t.entry(#key)))
  });
  quote!({
    let mut t = w.table(#count);
    #prefix
    #(#writes;)*
  })
}

/// Returns an expression recording `fields` to the writer `w` as an array.
fn array(fields: &[Field]) -> Tokens {
  let count = fields.len();
  let writes = fields.iter().map(|f| f.write(quote!(a.element())));
  quote!({
    let mut a = w.array(#count);
    #(#writes;)*
  })
}

fn derive(input: DeriveInput) -> syn::Result<Tokens> {
  let name = &input.ident;
  let type_name = name.unraw().to_string();

  let body = match &input.data {
    Data::Struct(s) => {
      let (fields, _) = collect(&s.fields, false, |m| quote!(&self.#m))?;
      match &s.fields {
        Fields::Named(_) => table(&fields, quote!(), 0),
        Fields::Unnamed(_) => array(&fields),
        Fields::Unit => quote!(w.string(#type_name)),
      }
    }

    Data::Enum(e) => {
      let mut arms = Vec::new();
      let fieldless = e.variants.iter().all(|v| matches!(v.fields, Fields::Unit));
      let mut names = HashSet::new();
      for v in &e.variants {
        let options = MemberOptions::parse(&v.attrs)?;
        if options.skip || options.with.is_some() {
          return Err(Error::new(v.span(), "variants only accept `rename`"));
        }
        let variant = &v.ident;
        let label = options
          .rename
          .unwrap_or_else(|| variant.unraw().to_string());
        if !names.insert(label.clone()) {
          return Err(Error::new(
            v.span(),
            format!("duplicate variant name '{label}'"),
          ));
        }

        let (fields, pattern) = collect(&v.fields, true, |m| m)?;
        if fields.iter().any(|f| f.key == "$variant") {
          return Err(Error::new(v.span(), "the key '$variant' is reserved"));
        }
        let write = if fieldless {
          quote!(w.string(#label))
        } else {
          table(
            &fields,
            quote!(t.entry(::pmdb_recorder::VARIANT_KEY).string(#label);),
            1,
          )
        };
        arms.push(quote!(#[allow(unused_variables)] Self::#variant #pattern => #write));
      }
      quote!(match self { #(#arms,)* })
    }

    Data::Union(u) => {
      return Err(Error::new(
        u.union_token.span,
        "unions can't derive `Record`",
      ));
    }
  };

  // Require type parameters to implement `Record` so that the values of fields mentioning them
  // are recorded with their implementation rather than a fallback.
  let mut generics = input.generics.clone();
  for p in generics.type_params_mut() {
    p.bounds.push(parse_quote!(::pmdb_recorder::Record));
  }
  let (impl_generics, type_generics, where_clause) = generics.split_for_impl();

  Ok(quote! {
    #[automatically_derived]
    impl #impl_generics ::pmdb_recorder::Record for #name #type_generics #where_clause {
      fn record(&self, w: ::pmdb_recorder::ValueWriter<'_>) {
        #[allow(unused_imports)]
        use ::pmdb_recorder::__private::probe::*;
        #body
      }
    }
  })
}

trait Unraw {
  /// Returns `self` without the `r#` prefix of raw identifiers.
  fn unraw(&self) -> Ident;
}

impl Unraw for Ident {
  fn unraw(&self) -> Ident {
    let s = self.to_string();
    match s.strip_prefix("r#") {
      Some(t) => Ident::new(t, Span::call_site()),
      None => self.clone(),
    }
  }
}
