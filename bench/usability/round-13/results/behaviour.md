# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 6 | 4/6 | 0 | 24.0 | 17.0 | 5.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | None | None | 22.0 | 1.0 | 0.0 | None | 0.0 |
| haiku | F | 6 | 2/6 | 0 | 39.0 | 12.0 | 4.5 | 0.0 | 9.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 6.5 | 1.0 | None | None | 5.5 | 6.5 | 3.5 | None | 1.5 |
| haiku | P | 6 | 3/6 | 0 | 41.0 | 12.0 | 3.5 | 0.0 | 1.0 | 25.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | None | None | 37.0 | 1.0 | 0.0 | None | 3.0 |
| haiku | Q | 6 | 3/6 | 0 | 42.0 | 12.5 | 4.5 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 | 13.5 | 0.0 | 1.0 | 1.0 | None | None | 41.0 | 1.0 | 0.0 | None | 4.0 |
| opus | A | 6 | 5/6 | 0 | 7.0 | 0.0 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | None | None | 5.5 | 1.0 | 0.0 | None | 0.0 |
| opus | F | 6 | 6/6 | 0 | 8.0 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | None | None | 7 | 1.0 | 0.0 | None | 0.0 |
| opus | P | 6 | 6/6 | 0 | 8.0 | 0.0 | 0.0 | 0.0 | 0.5 | 3.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | None | None | 5 | 1.0 | 0.0 | None | 0.0 |
| opus | Q | 6 | 6/6 | 0 | 9.0 | 0.0 | 0.0 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 | 3.0 | 0.0 | 1.0 | 2.5 | None | None | 5 | 1.0 | 0.0 | None | 0.0 |
| sonnet | A | 6 | 5/6 | 0 | 26.5 | 17.0 | 2.5 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | None | None | 22.0 | 1.0 | 0.0 | None | 0.0 |
| sonnet | F | 6 | 6/6 | 0 | 30.5 | 14.0 | 3.0 | 0.0 | 10.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.0 | 1.0 | None | None | 17.5 | 2.0 | 0.0 | None | 0.0 |
| sonnet | P | 6 | 6/6 | 0 | 23.5 | 11.0 | 3.0 | 0.0 | 1.0 | 9.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | None | None | 21.0 | 1.0 | 0.0 | None | 0.5 |
| sonnet | Q | 6 | 6/6 | 0 | 27.0 | 12.0 | 2.0 | 0.0 | 5.0 | 0.0 | 0.0 | 0.0 | 4.5 | 0.0 | 1.5 | 0.0 | 30 | None | 22.5 | 1.5 | 0.5 | None | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| billing-postmortem haiku A | ✗ | 16 | 15 | 1 | 0 | None | 0 | read 9, search 4, python 2, edit 1 |
| billing-postmortem haiku F | ✗ | 27 | 5 | 5 | 1 | None | 2 | read 12, search 5, edit 5, python 4, shell 1 |
| billing-postmortem haiku P | ✓ | 45 | 37 | 1 | 0 | None | 3 | trace 27, read 13, search 2, python 2, edit 1 |
| billing-postmortem haiku Q | ✗ | 37 | 35 | 1 | 0 | None | 3 | pmdb 23, read 11, search 1, edit 1, shell 1 |
| billing-postmortem opus A | ✓ | 5 | None | 0 | 0 | None | 0 | shell 3, python 2 |
| billing-postmortem opus F | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 3, python 2, edit 1 |
| billing-postmortem opus P | ✓ | 6 | 5 | 1 | 0 | None | 0 | trace 3, shell 2, edit 1 |
| billing-postmortem opus Q | ✓ | 6 | 5 | 1 | 0 | None | 0 | pmdb 2, shell 2, edit 1, python 1 |
| billing-postmortem sonnet A | ✓ | 18 | 17 | 1 | 0 | None | 0 | read 14, search 1, shell 1, edit 1, python 1 |
| billing-postmortem sonnet F | ✓ | 27 | 17 | 2 | 0 | None | 0 | read 14, python 9, edit 2, search 1, shell 1 |
| billing-postmortem sonnet P | ✓ | 25 | 22 | 1 | 0 | None | 0 | read 10, trace 9, search 3, shell 1, edit 1, python 1 |
| billing-postmortem sonnet Q | ✓ | 23 | 22 | 1 | 0 | None | 0 | read 12, pmdb 5, python 4, search 1, edit 1 |
| card-ledger-queue haiku A | ✓ | 19 | 18 | 1 | 0 | None | 0 | read 15, search 3, edit 1 |
| card-ledger-queue haiku F | ✗ | 51 | 4 | 17 | 8 | None | 1 | python 18, edit 17, read 12, search 3, shell 1 |
| card-ledger-queue haiku P | ✗ | 37 | 37 | 1 | 0 | None | 3 | trace 24, read 9, search 3, edit 1 |
| card-ledger-queue haiku Q | ✗ | 47 | 47 | 1 | 0 | None | 5 | pmdb 23, read 13, search 5, python 5, edit 1 |
| card-ledger-queue opus A | ✓ | 7 | 5 | 2 | 1 | None | 0 | shell 4, edit 2, python 1 |
| card-ledger-queue opus F | ✓ | 9 | 7 | 2 | 1 | None | 0 | python 5, shell 2, edit 2 |
| card-ledger-queue opus P | ✓ | 8 | 6 | 2 | 1 | None | 0 | trace 4, edit 2, pmdb 1, shell 1 |
| card-ledger-queue opus Q | ✓ | 12 | 12 | 1 | 0 | None | 0 | python 5, pmdb 3, shell 3, edit 1 |
| card-ledger-queue sonnet A | ✓ | 22 | 19 | 2 | 1 | None | 0 | read 16, search 2, edit 2, shell 1, python 1 |
| card-ledger-queue sonnet F | ✓ | 35 | 21 | 3 | 1 | None | 0 | read 19, python 11, edit 3, search 1, shell 1 |
| card-ledger-queue sonnet P | ✓ | 21 | 20 | 1 | 0 | None | 1 | read 9, trace 9, search 1, edit 1, python 1 |
| card-ledger-queue sonnet Q | ✓ | 29 | 23 | 2 | 1 | None | 2 | read 12, pmdb 7, python 6, search 2, edit 2 |
| payroll-postmortem haiku A | ✓ | 45 | 32 | 1 | 0 | None | 0 | read 26, python 9, search 7, shell 2, edit 1 |
| payroll-postmortem haiku F | ✗ | 59 | 6 | 16 | 7 | None | 1 | read 24, edit 16, search 9, python 8, shell 2 |
| payroll-postmortem haiku P | ✗ | 80 | 80 | 1 | 0 | None | 3 | trace 56, read 17, search 5, python 1, edit 1 |
| payroll-postmortem haiku Q | ✓ | 79 | 69 | 6 | 5 | None | 7 | read 37, python 16, pmdb 14, edit 6, search 4, shell 2 |
| payroll-postmortem opus A | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 5, python 2, edit 1 |
| payroll-postmortem opus F | ✓ | 10 | 9 | 1 | 0 | None | 0 | python 6, shell 3, edit 1 |
| payroll-postmortem opus P | ✓ | 8 | 6 | 1 | 0 | None | 1 | shell 4, trace 2, edit 1, python 1 |
| payroll-postmortem opus Q | ✓ | 11 | 8 | 1 | 0 | None | 1 | python 4, pmdb 3, shell 3, edit 1 |
| payroll-postmortem sonnet A | ✓ | 35 | 31 | 1 | 0 | None | 0 | read 22, python 9, shell 2, search 1, edit 1 |
| payroll-postmortem sonnet F | ✓ | 34 | 15 | 2 | 0 | None | 0 | read 14, python 14, search 3, edit 2, shell 1 |
| payroll-postmortem sonnet P | ✓ | 38 | 34 | 1 | 0 | None | 1 | trace 17, read 14, search 5, edit 1, python 1 |
| payroll-postmortem sonnet Q | ✓ | 31 | 27 | 2 | 1 | None | 1 | read 13, python 8, pmdb 5, search 2, edit 2, test 1 |
| points-expiry haiku A | ✓ | 12 | 12 | 1 | 0 | None | 0 | read 7, search 4, edit 1 |
| points-expiry haiku F | ✓ | 38 | 7 | 8 | 5 | None | 2 | read 11, python 11, edit 8, search 6, pmdb 1, shell 1 |
| points-expiry haiku P | ✓ | 32 | 22 | 1 | 0 | None | 7 | trace 13, read 12, search 4, edit 1, python 1, shell 1 |
| points-expiry haiku Q | ✓ | 25 | 24 | 1 | 0 | None | 2 | read 11, pmdb 9, search 4, edit 1 |
| points-expiry opus A | ✓ | 6 | 4 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| points-expiry opus F | ✓ | 7 | 7 | 1 | 0 | None | 1 | python 3, shell 2, pmdb 1, edit 1 |
| points-expiry opus P | ✓ | 6 | 5 | 1 | 0 | None | 0 | trace 3, shell 2, edit 1 |
| points-expiry opus Q | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 3, pmdb 2, edit 1 |
| points-expiry sonnet A | ✓ | 17 | 15 | 1 | 0 | None | 0 | read 11, search 3, python 2, edit 1 |
| points-expiry sonnet F | ✓ | 26 | 13 | 2 | 0 | None | 0 | read 12, python 7, search 5, edit 2 |
| points-expiry sonnet P | ✓ | 17 | 15 | 1 | 0 | None | 0 | read 8, trace 4, search 3, edit 1, python 1 |
| points-expiry sonnet Q | ✓ | 20 | 16 | 1 | 0 | None | 0 | read 12, pmdb 4, search 2, edit 1, python 1 |
| refund-postmortem haiku A | ✗ | 29 | 26 | 1 | 0 | None | 2 | read 22, search 6, edit 1 |
| refund-postmortem haiku F | ✗ | 29 | 2 | 5 | 2 | None | 3 | read 12, python 8, edit 5, search 3, shell 1 |
| refund-postmortem haiku P | ✗ | 57 | 54 | 2 | 0 | None | 2 | trace 37, read 12, search 6, edit 2 |
| refund-postmortem haiku Q | ✗ | 62 | 50 | 4 | 3 | None | 8 | python 24, read 13, pmdb 13, search 6, edit 4, shell 2 |
| refund-postmortem opus A | ✗ | 8 | None | 0 | 0 | None | 0 | read 3, search 2, python 2, shell 1 |
| refund-postmortem opus F | ✓ | 13 | None | 0 | 0 | None | 0 | python 7, shell 4, search 1, read 1 |
| refund-postmortem opus P | ✓ | 12 | None | 0 | 0 | None | 0 | trace 8, shell 2, python 2 |
| refund-postmortem opus Q | ✓ | 13 | None | 0 | 0 | None | 0 | python 6, pmdb 5, shell 2 |
| refund-postmortem sonnet A | ✗ | 31 | 25 | 2 | 1 | None | 0 | read 20, search 4, python 4, edit 2, shell 1 |
| refund-postmortem sonnet F | ✓ | 63 | 18 | 4 | 0 | None | 0 | python 39, read 16, edit 4, search 3, shell 1 |
| refund-postmortem sonnet P | ✓ | 83 | 76 | 4 | 3 | None | 0 | trace 55, read 21, edit 4, python 2, search 1 |
| refund-postmortem sonnet Q | ✓ | 50 | 39 | 3 | 2 | None | 0 | python 26, read 13, pmdb 4, search 3, edit 3, shell 1 |
| stock-allocation haiku A | ✓ | 43 | 32 | 1 | 0 | None | 5 | read 19, python 11, search 10, shell 2, edit 1 |
| stock-allocation haiku F | ✓ | 40 | 38 | 1 | 0 | None | 1 | python 21, read 14, search 4, edit 1 |
| stock-allocation haiku P | ✓ | 23 | 19 | 1 | 0 | None | 2 | read 12, trace 7, search 2, edit 1, python 1 |
| stock-allocation haiku Q | ✓ | 28 | 16 | 1 | 0 | None | 3 | read 12, pmdb 8, search 5, edit 1, python 1, shell 1 |
| stock-allocation opus A | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 4, python 2, edit 1 |
| stock-allocation opus F | ✓ | 7 | 6 | 1 | 0 | None | 1 | shell 3, python 3, edit 1 |
| stock-allocation opus P | ✓ | 9 | 5 | 1 | 0 | None | 0 | trace 4, shell 3, edit 1, python 1 |
| stock-allocation opus Q | ✓ | 7 | 5 | 1 | 0 | None | 0 | pmdb 3, python 2, shell 1, edit 1 |
| stock-allocation sonnet A | ✓ | 35 | 29 | 1 | 0 | None | 0 | read 18, python 9, search 5, shell 2, edit 1 |
| stock-allocation sonnet F | ✓ | 27 | 20 | 2 | 0 | None | 0 | read 14, python 6, search 5, edit 2 |
| stock-allocation sonnet P | ✓ | 22 | 19 | 1 | 0 | None | 1 | read 12, search 4, trace 4, edit 1, python 1 |
| stock-allocation sonnet Q | ✓ | 25 | 17 | 1 | 0 | None | 0 | read 12, search 5, pmdb 4, python 3, edit 1 |
