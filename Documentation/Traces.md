# Traces

`pmdb` traces can be stored using either a binary or human-readable format.
The former is optimized to minimize space and parsing time.
The latter can be used for debugging or to help with the developement of new features.

The human-readable format is based on XML.
A schema definition is provided.
A binary trace can be converted to XML with `pmdb --export-xml <trace>`, which prints the XML document to the standard output.

## Structure of a trace

Both binary and human-readable traces have the same overall structure.
In essense, a trace is a tree whose nodes are observations, i.e., calls and snaps.
The parenthood relationship in that tree roughly mirrors the call stack of program: the descendants of a node *n* are the observations that occurred within the call frame of *n*.

Each observation is associated with a line in a source file, describing where in the program's sources the observation occurred.
A snap additionaly contains a recorded value with an optional label.
A call additionally contains the name of the function being called, the arguments passed to that function, and a list of observation that occurred during the call.

The outcome of a call is recorded as the snap that immediately follows it, under the same parent.
That snap is labeled `<function>.$result` and holds the returned value if the call returned, or is labeled `<function>.$exception` and holds a table with the `type` and the `message` of the exception if the call raised one, where `<function>` is the name of the function being called.
`pmdb` shows such snaps as the outcomes of the calls they follow (e.g., `call f(3) -> 6`), and matches them against the result patterns of queries (e.g., `f(x) -> r`).
The recorders for Python and Rust record the outcome of every call they record.

### Values

`pmdb` supports 9 types of values to record snaps and call arguments, namely:

1. the absence of a value (e.g., `None` in Python or `null` in JavaScript),
2. Booleans,
3. integers,
4. floating-point numbers,
5. character strings,
6. arrays (i.e., ordered collection of values),
7. tables (i.e., mappings from strings to values),
8. functions, represented by their names, and
9. arbitrary objects, represented as raw sequence of bytes.

`pmdb` internally represents integers using 64 signed bits and floating-point numbers using the double-precision format of IEEE 754 (aka `double` in most programming languages).
This particular choice has a couple of noteworthy consequences:

- One cannot load integer values that are not representable as a two's complement 64-bit integer.
- The semantics of where clauses depend on the specifics of these representations. For example, computing `x + 1` in a context where `x` is equal to `0xff` will result in `0x100` even if the value of `x` was recorded from a program manipulating bytes.

One should store values as objects in situations where a finer control is necessary.
For example, one can store a 128 bit integer as a raw sequence of 16 bytes.

## XML representation

A trace can be stored as an XML document, as described by the schema definition provided together with this documentation.

The root of a trace document is a `pmdb:trace` element which must contain a single `pmdb:observations` element.
The latter contains a sequence of observations, which are represented either by `pmdb:snap` or `pmdb:call` elements, for snaps and calls, respectively.
The location of an observation is encoded as an attribute.

A `pmdb:snap` element must contain exactly one `pmdb:value` element.
The label of the snap is optionally encoded as an attribute.
For example, the following element describes a snap recoding the value `42` labeled by `a`.

```xml
<pmdb:snap location="/foo/bar.py:1" label="a">
  <pmdb:value>
    <pmdb:integer>42</pmdb:integer>
  </pmdb:value>
</pmdb:snap>
```

A `pmdb:call` element contains a `pmdb:function` element representing the name of the function being called, followed by a `pmdb:arguments` element containing a sequence of `pmdb:value` elements representing each argument.
The label of named arguments is expressed as an attribute on the `pmdb:value` element.
Finally, a `pmdb:call` element can contain at most one `pmdb:observations` representing the observations that occurred within the call.
The following illustrate with an observation recording `f(42, pi = 42)`.

```xml
<pmdb:call location="/foo/bar.py:3">
  <pmdb:function>f</pmdb:function>
  <pmdb:arguments>
    <pmdb:value>
      <pmdb:integer>42</pmdb:integer>
    </pmdb:value>
    <pmdb:value label="pi">
      <pmdb:float>3.14</pmdb:float>
    </pmdb:value>
  </pmdb:arguments>
  <pmdb:observations>
    ...
  </pmdb:observations>
</pmdb:call>
```

A value is expressed by a `pmdb:value` tag containing a single element representing its contents.
There is one element per type of value supported by `pmdb`.
Payloads are written in plain text, Booleans being written `true` or `false`, except for arrays which are sequences of values, tables which are sequence of labeled values, and objects whose contents are written using a base64 enoding.
For example, the following describes an array containing an integer and an object.

```xml
<pmdb:array>
  <pmdb:value>
    <pmdb:integer>42</pmdb:integer>
  </pmdb:value>
  <pmdb:value>
    <pmdb:object>SGVsbG8sIHdvcmxkIQ==</pmdb:object>
  </pmdb:value>
</pmdb:array>
```

Note that the value of an object uses base64 encoding.
