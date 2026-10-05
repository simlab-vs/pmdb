# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 6 | 1/6 | 0 | 34.5 | 19.0 | 4.5 | 0.0 | 11.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.5 | 0.0 | None | None | 26.0 | 1.5 | 0.0 | None | 1.0 |
| haiku | F | 6 | 1/6 | 0 | 33.0 | 11.5 | 3.5 | 0.0 | 12.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 4.5 | 0.0 | None | None | 4.0 | 4.5 | 1.0 | None | 1.0 |
| haiku | P | 6 | 1/6 | 0 | 42.0 | 13.5 | 3.0 | 0.0 | 4.0 | 18.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | None | None | 28 | 1.0 | 0.0 | None | 3.5 |
| haiku | Q | 6 | 1/6 | 0 | 37.0 | 13.5 | 2.0 | 0.0 | 4.0 | 0.0 | 0.0 | 0.0 | 13.5 | 0.0 | 1.0 | 0.0 | None | None | 32.0 | 1.0 | 0.0 | None | 3.0 |
| opus | A | 6 | 5/6 | 0 | 8.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 6.0 | None | None | 8 | 1.0 | 0.0 | None | 0.0 |
| opus | F | 6 | 5/6 | 0 | 7.5 | 0.0 | 0.0 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | None | None | 7 | 1.0 | 0.0 | None | 0.0 |
| opus | P | 6 | 5/6 | 0 | 8.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | None | None | 7.0 | 1.0 | 0.0 | None | 0.0 |
| opus | Q | 6 | 5/6 | 0 | 9.5 | 0.0 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 3.5 | 0.0 | 1.0 | 3.5 | None | None | 7 | 1.0 | 0.0 | None | 0.0 |
| sonnet | A | 6 | 3/6 | 0 | 36.0 | 20.5 | 4.5 | 0.0 | 9.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.5 | 0.5 | None | None | 27.5 | 1.5 | 0.0 | None | 0.0 |
| sonnet | F | 6 | 4/6 | 0 | 47.0 | 18.5 | 4.5 | 0.0 | 20.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.5 | 3.0 | None | None | 9.0 | 2.5 | 0.5 | None | 0.0 |
| sonnet | P | 6 | 5/6 | 0 | 43.0 | 20.5 | 4.0 | 0.0 | 2.0 | 11.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.5 | 1.0 | None | None | 37.5 | 1.5 | 0.5 | None | 0.0 |
| sonnet | Q | 6 | 5/6 | 0 | 42.5 | 21.0 | 3.5 | 0.0 | 6.5 | 0.0 | 0.0 | 0.0 | 9.5 | 0.0 | 1.5 | 0.5 | None | None | 39.0 | 1.5 | 0.0 | None | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| billing-postmortem haiku A | ✗ | 48 | 43 | 2 | 0 | None | 1 | read 22, python 12, search 11, edit 2, pdb 1 |
| billing-postmortem haiku F | ✗ | 29 | 3 | 3 | 1 | None | 3 | python 14, read 7, search 3, edit 3, shell 2 |
| billing-postmortem haiku P | ✗ | 53 | 52 | 1 | 0 | None | 6 | trace 26, read 16, python 7, search 3, edit 1 |
| billing-postmortem haiku Q | ✗ | 48 | 41 | 3 | 2 | None | 4 | pmdb 16, read 15, python 7, search 5, edit 3, shell 2 |
| billing-postmortem opus A | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| billing-postmortem opus F | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 4, python 3, edit 1 |
| billing-postmortem opus P | ✓ | 8 | 6 | 1 | 0 | None | 0 | shell 3, trace 2, python 2, edit 1 |
| billing-postmortem opus Q | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 4, pmdb 2, edit 1, python 1 |
| billing-postmortem sonnet A | ✓ | 41 | 28 | 2 | 0 | None | 0 | read 15, python 14, search 6, shell 4, edit 2 |
| billing-postmortem sonnet F | ✓ | 27 | 8 | 2 | 0 | None | 0 | read 10, python 9, search 3, shell 3, edit 2 |
| billing-postmortem sonnet P | ✓ | 19 | 16 | 1 | 0 | None | 0 | trace 7, read 6, search 3, pmdb 1, shell 1, edit 1 |
| billing-postmortem sonnet Q | ✓ | 31 | 29 | 1 | 0 | None | 0 | read 14, pmdb 6, python 5, search 3, shell 2, edit 1 |
| card-ledger-queue haiku A | ✗ | 28 | 25 | 1 | 0 | None | 1 | python 13, read 10, search 4, edit 1 |
| card-ledger-queue haiku F | ✗ | 20 | 5 | 4 | 0 | None | 1 | read 7, python 5, search 4, edit 4 |
| card-ledger-queue haiku P | ✗ | 18 | 17 | 1 | 0 | None | 3 | trace 11, read 5, search 1, edit 1 |
| card-ledger-queue haiku Q | ✗ | 26 | 23 | 1 | 0 | None | 1 | read 12, pmdb 10, search 2, edit 1, python 1 |
| card-ledger-queue opus A | ✓ | 7 | None | 0 | 0 | None | 0 | shell 6, python 1 |
| card-ledger-queue opus F | ✓ | 7 | 6 | 1 | 0 | None | 0 | python 3, shell 2, pmdb 1, edit 1 |
| card-ledger-queue opus P | ✓ | 9 | 8 | 1 | 0 | None | 0 | trace 5, shell 3, edit 1 |
| card-ledger-queue opus Q | ✓ | 12 | 10 | 1 | 0 | None | 0 | pmdb 4, shell 4, python 3, edit 1 |
| card-ledger-queue sonnet A | ✗ | 31 | 24 | 3 | 0 | None | 0 | read 21, python 4, search 3, edit 3 |
| card-ledger-queue sonnet F | ✓ | 63 | 7 | 3 | 1 | None | 0 | python 27, read 22, search 8, shell 3, edit 3 |
| card-ledger-queue sonnet P | ✓ | 41 | 38 | 2 | 1 | None | 0 | read 20, trace 13, search 4, edit 2, shell 1, python 1 |
| card-ledger-queue sonnet Q | ✓ | 52 | 48 | 2 | 1 | None | 0 | read 21, pmdb 16, python 8, search 4, edit 2, shell 1 |
| payroll-postmortem haiku A | ✗ | 46 | 41 | 3 | 2 | None | 2 | read 23, python 12, search 6, edit 3, shell 1, bash 1 |
| payroll-postmortem haiku F | ✗ | 54 | 4 | 10 | 3 | None | 1 | read 29, edit 10, python 10, search 5 |
| payroll-postmortem haiku P | ✗ | 75 | 62 | 5 | 3 | None | 6 | read 27, trace 25, python 9, search 7, edit 5, shell 2 |
| payroll-postmortem haiku Q | ✗ | 77 | 51 | 18 | 16 | None | 5 | pmdb 23, read 22, edit 18, python 9, search 5 |
| payroll-postmortem opus A | ✓ | 9 | 8 | 1 | 0 | None | 0 | shell 6, python 2, edit 1 |
| payroll-postmortem opus F | ✓ | 9 | 8 | 1 | 0 | None | 0 | python 4, shell 3, read 1, edit 1 |
| payroll-postmortem opus P | ✓ | 10 | 9 | 1 | 0 | None | 0 | shell 5, trace 4, edit 1 |
| payroll-postmortem opus Q | ✓ | 11 | 9 | 1 | 0 | None | 0 | shell 4, pmdb 3, python 3, edit 1 |
| payroll-postmortem sonnet A | ✗ | 65 | 50 | 2 | 0 | None | 1 | read 26, python 24, search 12, edit 2, shell 1 |
| payroll-postmortem sonnet F | ✗ | 60 | 6 | 2 | 0 | None | 0 | python 26, read 24, search 5, shell 3, edit 2 |
| payroll-postmortem sonnet P | ✓ | 45 | 37 | 2 | 1 | None | 1 | read 23, trace 9, python 5, search 4, edit 2, pmdb 1, shell 1 |
| payroll-postmortem sonnet Q | ✓ | 63 | 53 | 2 | 0 | None | 1 | read 23, python 19, pmdb 12, search 7, edit 2 |
| points-expiry haiku A | ✗ | 41 | 19 | 12 | 11 | None | 1 | read 20, edit 12, python 7, search 2 |
| points-expiry haiku F | ✗ | 37 | 4 | 6 | 1 | None | 0 | python 18, read 11, edit 6, search 2 |
| points-expiry haiku P | ✗ | 64 | None | 0 | 0 | None | 2 | trace 23, read 18, python 16, search 7 |
| points-expiry haiku Q | ✗ | 55 | 52 | 1 | 0 | None | 4 | pmdb 26, read 17, python 7, search 2, shell 2, edit 1 |
| points-expiry opus A | ✓ | 6 | 4 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| points-expiry opus F | ✓ | 7 | 7 | 1 | 0 | None | 0 | shell 4, python 2, edit 1 |
| points-expiry opus P | ✓ | 5 | 5 | 1 | 0 | None | 0 | trace 3, shell 1, edit 1 |
| points-expiry opus Q | ✓ | 7 | 7 | 1 | 0 | None | 0 | pmdb 4, shell 2, edit 1 |
| points-expiry sonnet A | ✓ | 28 | 27 | 1 | 0 | None | 0 | read 20, python 5, search 2, edit 1 |
| points-expiry sonnet F | ✓ | 42 | 20 | 2 | 0 | None | 0 | read 18, python 17, search 5, edit 2 |
| points-expiry sonnet P | ✓ | 54 | 52 | 1 | 0 | None | 0 | read 21, trace 20, search 6, python 4, shell 2, edit 1 |
| points-expiry sonnet Q | ✓ | 34 | 32 | 1 | 0 | None | 0 | read 23, python 5, pmdb 3, search 2, edit 1 |
| refund-postmortem haiku A | ✗ | 25 | 21 | 1 | 0 | None | 0 | read 10, python 10, search 4, edit 1 |
| refund-postmortem haiku F | ✗ | 51 | 4 | 2 | 0 | None | 1 | python 35, read 12, search 2, edit 2 |
| refund-postmortem haiku P | ✗ | 29 | 21 | 5 | 4 | None | 1 | trace 12, read 8, edit 5, search 3, python 1 |
| refund-postmortem haiku Q | ✗ | 21 | 20 | 1 | 0 | None | 2 | read 9, pmdb 9, search 2, edit 1 |
| refund-postmortem opus A | ✗ | 11 | 10 | 1 | 0 | None | 1 | shell 7, python 2, search 1, edit 1 |
| refund-postmortem opus F | ✗ | 14 | None | 0 | 0 | None | 0 | python 8, shell 5, search 1 |
| refund-postmortem opus P | ✗ | 21 | 19 | 2 | 1 | None | 1 | trace 16, shell 3, edit 2 |
| refund-postmortem opus Q | ✗ | 16 | None | 0 | 0 | None | 0 | pmdb 7, python 6, shell 3 |
| refund-postmortem sonnet A | ✗ | 43 | 41 | 1 | 0 | None | 4 | read 22, python 13, search 6, shell 1, edit 1 |
| refund-postmortem sonnet F | ✗ | 36 | 10 | 3 | 1 | None | 0 | python 19, shell 6, search 4, read 4, edit 3 |
| refund-postmortem sonnet P | ✗ | 46 | 43 | 2 | 1 | None | 0 | read 21, trace 18, search 4, edit 2, python 1 |
| refund-postmortem sonnet Q | ✗ | 50 | 46 | 2 | 1 | None | 0 | read 21, pmdb 12, python 9, search 6, edit 2 |
| stock-allocation haiku A | ✓ | 28 | 27 | 1 | 0 | None | 0 | read 18, search 5, python 4, edit 1 |
| stock-allocation haiku F | ✓ | 28 | 4 | 5 | 1 | None | 0 | read 14, edit 5, search 4, python 4, shell 1 |
| stock-allocation haiku P | ✓ | 31 | 28 | 1 | 0 | None | 4 | trace 14, read 11, search 3, edit 1, python 1, shell 1 |
| stock-allocation haiku Q | ✓ | 19 | 18 | 1 | 0 | None | 1 | pmdb 11, read 5, search 2, edit 1 |
| stock-allocation opus A | ✓ | 9 | 8 | 1 | 0 | None | 0 | shell 7, edit 1, python 1 |
| stock-allocation opus F | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 4, python 2, edit 1 |
| stock-allocation opus P | ✓ | 6 | 5 | 1 | 0 | None | 0 | trace 4, shell 1, edit 1 |
| stock-allocation opus Q | ✓ | 6 | 5 | 1 | 0 | None | 0 | pmdb 2, shell 2, edit 1, python 1 |
| stock-allocation sonnet A | ✓ | 26 | 25 | 1 | 0 | None | 0 | read 18, python 5, search 2, edit 1 |
| stock-allocation sonnet F | ✓ | 52 | 21 | 4 | 1 | None | 1 | python 22, read 19, edit 4, shell 4, search 3 |
| stock-allocation sonnet P | ✓ | 26 | 15 | 1 | 0 | None | 2 | read 10, trace 9, python 3, shell 2, search 1, edit 1 |
| stock-allocation sonnet Q | ✓ | 35 | 27 | 1 | 0 | None | 0 | read 17, pmdb 7, python 4, search 3, shell 3, edit 1 |
