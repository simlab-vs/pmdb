## result pattern and binding (works)

In the trace of `15-ex01-invoicing-rare-B-sonnet`:

```
$ pmdb /work/report.pmdb <<'EOF'
select coupon_reductions(lines, subtotals, code) where code == "BIG50"
show $0
EOF
$0 = <1 element(s) in 1 trace(s)>
/work/billing.py:109: call coupon_reductions([{category: food, quantity: 10, sku: SKU-146, unit_price: 4}, {category: clothing, quantity: 1, sku: SKU-222, unit_price: 12}], [40, 12], BIG50) -> [0, 0]
   107 |   region = order["region"]
   108 |   subtotals = [line_subtotal(l) for l in lines]
>  109 |   reductions = coupon_reductions(lines, subtotals, order.get("coupon"))
   110 |   nets = [s - r for s, r in zip(subtotals, reductions)]
   111 |   taxes = [line_tax(l, n, region) for l, n in zip(lines, nets)]
[exit 0]
```

## show $1 after one select

In the trace of `10-ex02-invoicing-subtle-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select spread(*, *)
show $1
EOF
$0 = <2 element(s) in 1 trace(s)>
error: undefined symbol '$1'
[exit 1]
```

## show query

In the trace of `23-ex01-invoicing-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select spread(...)
show query
EOF
$0 = <0 element(s) in 0 trace(s)>
error: expected variable
[exit 1]
```

## show --query

In the trace of `34-ex03-calc-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(...)
show --query
EOF
$0 = <7685 element(s) in 1 trace(s)>
error: expected variable
[exit 1]
```

## pipe inside the heredoc

In the trace of `18-ex07-routes-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select fastest_route(...) -> r where r.len() > 0
show $0 | head -40
EOF
$0 = <6 element(s) in 1 trace(s)>
error: expected end of command, found '| head -40'
[exit 1]
```

## two variadic positional patterns

In the trace of `34-ex03-calc-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(*, _, *)
EOF
$0 = <0 element(s) in 0 trace(s)>
[exit 0]
```

## evaluate arity

In the trace of `34-ex03-calc-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(_, _)
select evaluate(_)
select evaluate(_, *)
EOF
$0 = <0 element(s) in 0 trace(s)>
$1 = <7 element(s) in 1 trace(s)>
$2 = <7685 element(s) in 1 trace(s)>
[exit 0]
```

## SQL-like query

In the trace of `34-ex03-calc-rare-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select /evaluate/ from calls where args[1] like "%%"
EOF
error: expected 'select'
[exit 1]
```

## calls that raised

In the trace of `26-ex09-scheduler-crash-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select /subtract/(...) raised
EOF
error: expected end of command, found 'raised'
[exit 1]
```

## regex for one function's exception

In the trace of `26-ex09-scheduler-crash-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select /subtract/.*\$exception/
EOF
error: expected end of command, found '.*\$exception/'
[exit 1]
```

## same, written as one regex (works)

In the trace of `26-ex09-scheduler-crash-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select /subtract\.\$exception/
EOF
$0 = <1 element(s) in 1 trace(s)>
[exit 0]
```

## comparison with mixed result types

In the trace of `30-ex04-calc-subtle-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(...) -> r where r == -4
EOF
error: cannot apply == on values of type 'object' and 'integer'
[exit 1]
```

## literal result pattern (works)

In the trace of `30-ex04-calc-subtle-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(...) -> -4
EOF
$0 = <4 element(s) in 1 trace(s)>
[exit 0]
```

## bare names are variables

In the trace of `33-ex08-routes-subtle-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select turn_penalty(S, W) -> p
select turn_penalty("S", "W") -> p
EOF
$0 = <227 element(s) in 1 trace(s)>
$1 = <12 element(s) in 1 trace(s)>
[exit 0]
```

## what the object results are

In the trace of `30-ex04-calc-subtle-B-haiku`:

```
$ pmdb /work/report.pmdb <<'EOF'
select evaluate(...) -> r where r == none
select evaluate(...)
EOF
$0 = <0 element(s) in 0 trace(s)>
$1 = <1081 element(s) in 1 trace(s)>
[exit 0]
```

