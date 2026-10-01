# Reproduced pmdb attempts

## result of a call (pilot)

```
$ pmdb report.pmdb -e 'select merge(_).$result'
error: multiple commands should be separated by a newline
[exit 1]
```

## label written as documented

```
$ pmdb report.pmdb -e 'select merge.$result'
error: multiple commands should be separated by a newline
[exit 1]
```

## working form

```
$ pmdb report.pmdb -e 'select /merge\.\$result/'
$0 = <9 element(s) in 1 trace(s)>
/work/availability.py:17: snap merge.$result = [[1005, 1005], [3480, 3525], [4995, 4995], [5040, 5070], [6360, 6405], [6420, 6435], [6690, 6735], [7800, 7845], [7920, 7950], [9240, 9285]]
/work/availability.py:17: snap merge.$result = [[1005, 1005], [3480, 3525], [4995, 4995], [5040, 5070], [6360, 6405], [6420, 6435], [6690, 6735], [7800, 7845], [7920, 7950], [9240, 9285]]
/work/availability.py:17: snap merge.$result = [[915, 960], [1050, 1110], [1905, 1995], [2435, 2435], [3495, 3540], [3840, 3870], [4796, 4875], [5310, 5310], [6180, 6225], [6720, 6750], [7665, 7755], [8130, 8190], [9600, 9630]]
/work/availability.py:17: snap merge.$result = [[915, 960], [1050, 1110], [1905, 1995], [2435, 2435], [3495, 3540], [3840, 3870], [4796, 4875], [5310, 5310], [6180, 6225], [6720, 6750], [7665, 7755], [8130, 8190], [9600, 9630]]
/work/availability.py:17: snap merge.$result = [[555, 675], [900, 960], [2190, 2280], [5799, 5799], [6450, 6480], [7890, 7920], [9330, 9360]]
... (4 more lines)
[exit 0]
```

## show of calls has no results

```
$ pmdb report.pmdb -e 'select spread(*)' -e 'show $0' | grep -c result
0
[exit 0]
```

## regex closed early

```
$ pmdb report.pmdb -e 'select /utilization/\.\$result/'
error: multiple commands should be separated by a newline
[exit 1]
```

## regex closed early

```
$ pmdb report.pmdb -e "select /fastest_route/.*result/"
error: multiple commands should be separated by a newline
[exit 1]
```

## double-quoted shell: \$ becomes $ (an anchor)

```
$ pmdb report.pmdb -e "select /fastest_route.*\$result/ where true"
$0 = <0 element(s) in 0 trace(s)>
[exit 0]
```

## same regex, single-quoted

```
$ pmdb report.pmdb -e 'select /fastest_route.*\$result/'
$0 = <6 element(s) in 1 trace(s)>
/work/main.py:15: snap fastest_route.$result = [332, [E0, Avenue E, E1, Road 1, D1, Road 1, C1, Road 1, B1, Road 1, A1, Avenue A, A0]]
/work/main.py:15: snap fastest_route.$result = [217, [F3, Avenue F, F2, Avenue F, F1, Avenue F, F0, Road 0, E0]]
/work/main.py:15: snap fastest_route.$result = [127, [D2, Road 2, E2, Road 2, F2]]
/work/main.py:15: snap fastest_route.$result = [331, [F1, Road 1, E1, Road 1, D1, Road 1, C1, Road 1, B1, Road 1, A1, Avenue A, A2, Avenue A, A3]]
/work/main.py:15: snap fastest_route.$result = [276, [C0, Road 0, D0, Avenue D, D1, Avenue D, D2, Avenue D, D3, Avenue D, D4]]
/work/main.py:15: snap fastest_route.$result = [237, [E4, Road 4, D4, Avenue D, D3, Avenue D, D2, Road 2, C2]]
[exit 0]
```

## literal values as argument patterns

```
$ pmdb report.pmdb -e 'select spread(5000, [3597610, 33068])'
error: expected identifier
[exit 1]
```

## single-quoted string literal

```
$ pmdb report.pmdb -e "select coupon_reductions(lines, subtotals, code) where code == 'BIG50'"
error: expected expression
[exit 1]
```

## double-quoted string literal

```
$ pmdb report.pmdb -e 'select coupon_reductions(lines, subtotals, code) where code == "BIG50"'
$0 = <1 element(s) in 1 trace(s)>
/work/billing.py:109: call coupon_reductions([{category: food, quantity: 10, sku: SKU-146, unit_price: 4}, {category: clothing, quantity: 1, sku: SKU-222, unit_price: 12}], [40, 12], BIG50)
[exit 0]
```

## name not bound by ...

```
$ pmdb report.pmdb -e 'select coupon_reductions(...) where code == "BIG50"'
error: undefined symbol 'code'
[exit 1]
```

## `and` instead of `&&`

```
$ pmdb report.pmdb -e 'select fastest_route(n, s, t) where s == "B2" and t == "A0"'
error: multiple commands should be separated by a newline
[exit 1]
```

## working form

```
$ pmdb report.pmdb -e 'select fastest_route(n, s, t) where s == "B2" && t == "A0"'
$0 = <1 element(s) in 1 trace(s)>
/work/main.py:15: call fastest_route(<object>, B2, A0)
[exit 0]
```

## intended literals, arity 2 of 3

```
$ pmdb report.pmdb -e 'select fastest_route(E0, A0)'
$0 = <0 element(s) in 0 trace(s)>
[exit 0]
```

## names are variables, not strings

```
$ pmdb report.pmdb -e 'select fastest_route(_, E0, A0)'
$0 = <6 element(s) in 1 trace(s)>
/work/main.py:15: call fastest_route(<object>, E0, A0)
/work/main.py:15: call fastest_route(<object>, F3, E0)
/work/main.py:15: call fastest_route(<object>, D2, F2)
/work/main.py:15: call fastest_route(<object>, F1, A3)
/work/main.py:15: call fastest_route(<object>, C0, D4)
/work/main.py:15: call fastest_route(<object>, E4, C2)
[exit 0]
```

## `_` in a where clause

```
$ pmdb report.pmdb -e 'select subtract(_, _) where _'
error: expected expression
[exit 1]
```

## `_` in a where clause

```
$ pmdb report.pmdb -e 'select utilization(_) where _ != none'
error: expected expression
[exit 1]
```

## `$` as a pattern

```
$ pmdb report.pmdb -e 'select utilization($)'
error: expected identifier
[exit 1]
```

## `call(name, ...)` form

```
$ pmdb report.pmdb -e "select call('parse', _) where _ > 0"
error: expected identifier
[exit 1]
```

## variable as an argument pattern

```
$ pmdb report.pmdb -e 'select fastest_route($0)'
error: expected identifier
[exit 1]
```

## `from *`

```
$ pmdb report.pmdb -e 'select spread(*) from * where true'
error: expected 'select'
[exit 1]
```

## subquery without select

```
$ pmdb report.pmdb -e 'select /coupon_reductions.*\$result/ from coupon_reductions(...)'
error: expected 'select'
[exit 1]
```

## subquery with select

```
$ pmdb report.pmdb -e 'select /coupon_reductions.*\$result/ from select coupon_reductions(...)'
$0 = <0 element(s) in 0 trace(s)>
[exit 0]
```

## property of a table argument

```
$ pmdb report.pmdb -e 'select invoice(o) where o.coupon == "BIG50"'
error: undefined property 'coupon'
[exit 1]
```

## calls made inside the selected call

```
$ pmdb report.pmdb -e 'select invoice(o) where o.id == "0-4"' -e 'select line_subtotal(l) from $0'
$0 = <1 element(s) in 1 trace(s)>
/work/main.py:14: call invoice({coupon: BIG50, currency: EUR, id: 0-4, lines: [{category: food, quantity: 10, sku: SKU-146, unit_price: 4}, {category: clothing, quantity: 1, sku: SKU-222, unit_price: 12}], region: north})
$1 = <0 element(s) in 0 trace(s)>
[exit 0]
```

## from keeps only the selected observations

```
$ pmdb report.pmdb -e 'select line_subtotal(l)' -e 'select line_subtotal(l) from $0' | grep '\$'
$0 = <18 element(s) in 1 trace(s)>
$1 = <18 element(s) in 1 trace(s)>
[exit 0]
```

## variable from an earlier invocation

```
$ pmdb report.pmdb -e 'show $0'
error: undefined symbol '$0'
[exit 1]
```

## commands piped with |

```
$ echo 'select spread(*) | show $0' | pmdb report.pmdb
error: multiple commands should be separated by a newline
(pmdb) (pmdb) [exit 0]
```

## REPL fed from stdin

```
$ printf 'select merge(_)\nshow $0\n' | pmdb report.pmdb | head -4
(pmdb) $0 = <9 element(s) in 1 trace(s)>
(pmdb) /work/availability.py:17: call merge([[6690, 6735], [975, 1005], [4950, 4995], [6420, 6435], [3480, 3525], [4920, 4965], [6360, 6405], [7800, 7845], [9240, 9285], [4965, 4995], [945, 1005], [5040, 5070], [7920, 7950]])
    15 |   for b in bookings:
    16 |     intervals.extend(expand(b))
[exit 0]
```

## --show after the trace

```
$ pmdb report.pmdb --show | head -3
Error: Missing value for '--show <show>'
Help:  --show <show>  Show the contents of the trace stored in the specified file and exit.
Usage: driver [--show <show>] [--export-xml <export-xml>] [<inputs> ...] [--execute <execute> ...]
  See 'driver --help' for more information.
[exit 64]
```

## size of --show

```
$ pmdb --show report.pmdb | wc -l
382
[exit 0]
```

## size of show for 30 calls

```
$ pmdb report.pmdb -e 'select subtract(...)' -e 'show $0' | wc -l
211
[exit 0]
```

## objects shown as <object>

```
$ pmdb report.pmdb -e 'select fastest_route(*)' | head -2
$0 = <6 element(s) in 1 trace(s)>
/work/main.py:15: call fastest_route(<object>, E0, A0)
[exit 0]
```

