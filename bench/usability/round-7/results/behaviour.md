# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 10 | 5/10 | 0 | 27.5 | 15.5 | 5.5 | 0.0 | 4.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | None | None | 21.5 | 1.0 | 0.0 | None | 1.0 |
| haiku | B | 10 | 6/10 | 0 | 47.0 | 13.5 | 4.5 | 0.0 | 5.0 | 0.0 | 0.0 | 11.5 | 1.0 | 1.0 | 1.0 | None | None | 29 | 1.0 | 0.0 | None | 4.5 |
| opus | A | 10 | 8/10 | 0 | 7.5 | 0.0 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.5 | None | None | 5.5 | 1.0 | 0.0 | None | 0.0 |
| opus | B | 10 | 10/10 | 0 | 10.5 | 0.0 | 0.0 | 0.0 | 2.5 | 0.0 | 0.0 | 3.0 | 1.0 | 1.0 | 2.0 | None | None | 8 | 1.0 | 0.0 | None | 0.0 |
| sonnet | A | 10 | 8/10 | 0 | 27.0 | 19.0 | 4.0 | 0.0 | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | None | None | 23.5 | 1.0 | 0.0 | None | 0.0 |
| sonnet | B | 10 | 10/10 | 0 | 34.0 | 14.0 | 2.5 | 0.0 | 9.5 | 0.0 | 0.0 | 5.5 | 1.0 | 1.0 | 0.0 | None | None | 27.5 | 1.0 | 0.0 | None | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku A | ✗ | 25 | 21 | 1 | 0 | None | 1 | read 16, search 5, shell 2, edit 1, python 1 |
| card-ledger-queue haiku A | ✓ | 19 | 15 | 1 | 0 | None | 1 | read 12, python 4, search 2, edit 1 |
| card-ledger-queue haiku B | ✗ | 64 | 57 | 5 | 4 | None | 13 | pmdb 36, read 16, edit 5, python 3, search 2, skill 1, shell 1 |
| card-ledger-queue haiku B | ✗ | 80 | None | 0 | 0 | None | 10 | pmdb 41, python 22, read 14, search 2, skill 1 |
| card-ledger-queue opus A | ✓ | 8 | 6 | 2 | 1 | None | 0 | shell 4, python 2, edit 2 |
| card-ledger-queue opus A | ✓ | 4 | None | 0 | 0 | None | 0 | shell 3, python 1 |
| card-ledger-queue opus B | ✓ | 12 | 10 | 2 | 1 | None | 0 | pmdb 3, python 3, read 2, edit 2, skill 1, search 1 |
| card-ledger-queue opus B | ✓ | 9 | None | 0 | 0 | None | 0 | python 4, pmdb 3, skill 1, shell 1 |
| card-ledger-queue sonnet A | ✓ | 27 | 24 | 2 | 1 | None | 0 | read 21, search 3, edit 2, python 1 |
| card-ledger-queue sonnet A | ✓ | 24 | 21 | 2 | 1 | None | 0 | read 18, search 2, edit 2, python 2 |
| card-ledger-queue sonnet B | ✓ | 34 | 24 | 2 | 1 | None | 0 | read 13, python 10, pmdb 4, search 2, edit 2, shell 2, skill 1 |
| card-ledger-queue sonnet B | ✓ | 23 | 18 | 2 | 1 | None | 0 | read 9, pmdb 5, python 5, edit 2, search 1, skill 1 |
| payroll-postmortem haiku A | ✗ | 65 | 52 | 5 | 3 | None | 2 | read 27, search 18, python 13, edit 5, shell 2 |
| payroll-postmortem haiku A | ✗ | 78 | 62 | 5 | 3 | None | 3 | read 30, python 24, search 18, edit 5, shell 1 |
| payroll-postmortem haiku B | ✓ | 63 | 48 | 1 | 0 | None | 5 | python 29, read 19, pmdb 9, search 4, skill 1, edit 1 |
| payroll-postmortem haiku B | ✓ | 36 | 19 | 2 | 0 | None | 4 | read 14, search 7, pmdb 7, python 4, edit 2, skill 1, shell 1 |
| payroll-postmortem opus A | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 5, edit 1, python 1 |
| payroll-postmortem opus A | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 5, python 2, edit 1 |
| payroll-postmortem opus B | ✓ | 10 | 9 | 1 | 0 | None | 0 | shell 3, python 3, pmdb 2, skill 1, edit 1 |
| payroll-postmortem opus B | ✓ | 13 | 9 | 1 | 0 | None | 0 | pmdb 6, shell 3, python 2, skill 1, edit 1 |
| payroll-postmortem sonnet A | ✓ | 37 | 35 | 1 | 0 | None | 0 | read 23, python 9, search 3, shell 1, edit 1 |
| payroll-postmortem sonnet A | ✓ | 44 | 40 | 1 | 0 | None | 0 | read 26, python 12, search 4, edit 1, shell 1 |
| payroll-postmortem sonnet B | ✓ | 46 | 35 | 1 | 0 | None | 0 | python 17, read 16, pmdb 6, search 3, shell 2, skill 1, edit 1 |
| payroll-postmortem sonnet B | ✓ | 36 | 33 | 1 | 0 | None | 1 | read 17, python 12, pmdb 3, skill 1, search 1, shell 1, edit 1 |
| points-expiry haiku A | ✓ | 19 | 17 | 1 | 0 | None | 1 | read 10, search 6, python 2, edit 1 |
| points-expiry haiku A | ✓ | 21 | 16 | 1 | 0 | None | 0 | read 13, search 5, python 2, edit 1 |
| points-expiry haiku B | ✓ | 30 | 29 | 1 | 0 | None | 1 | read 12, python 7, pmdb 6, search 3, skill 1, edit 1 |
| points-expiry haiku B | ✗ | 33 | 28 | 1 | 0 | None | 10 | pmdb 12, read 10, search 6, python 2, skill 1, edit 1, shell 1 |
| points-expiry opus A | ✓ | 5 | 4 | 1 | 0 | None | 0 | shell 3, edit 1, python 1 |
| points-expiry opus A | ✓ | 4 | 4 | 1 | 0 | None | 0 | shell 3, edit 1 |
| points-expiry opus B | ✓ | 11 | 8 | 1 | 0 | None | 1 | pmdb 5, shell 3, skill 1, edit 1, python 1 |
| points-expiry opus B | ✓ | 7 | 7 | 1 | 0 | None | 1 | pmdb 3, shell 2, skill 1, edit 1 |
| points-expiry sonnet A | ✓ | 12 | 12 | 1 | 0 | None | 0 | read 9, search 2, edit 1 |
| points-expiry sonnet A | ✓ | 16 | 14 | 1 | 0 | None | 0 | read 10, search 4, edit 1, python 1 |
| points-expiry sonnet B | ✓ | 31 | 30 | 1 | 0 | None | 4 | pmdb 11, search 8, read 8, python 2, skill 1, edit 1 |
| points-expiry sonnet B | ✓ | 27 | 25 | 1 | 0 | None | 2 | read 15, pmdb 6, search 3, skill 1, edit 1, python 1 |
| refund-postmortem haiku A | ✗ | 22 | 21 | 1 | 0 | None | 0 | read 15, search 5, python 1, edit 1 |
| refund-postmortem haiku A | ✗ | 30 | 26 | 1 | 0 | None | 1 | read 18, python 5, search 4, shell 2, edit 1 |
| refund-postmortem haiku B | ✗ | 63 | 43 | 1 | 0 | None | 1 | pmdb 43, read 13, search 5, edit 1, python 1 |
| refund-postmortem haiku B | ✓ | 52 | 46 | 3 | 1 | None | 3 | python 26, read 12, pmdb 5, search 4, edit 3, skill 1, shell 1 |
| refund-postmortem opus A | ✗ | 5 | None | 0 | 0 | None | 0 | read 2, python 2, search 1 |
| refund-postmortem opus A | ✗ | 9 | 6 | 3 | 2 | None | 0 | python 3, edit 3, shell 2, search 1 |
| refund-postmortem opus B | ✓ | 16 | None | 0 | 0 | None | 0 | pmdb 7, python 6, shell 2, skill 1 |
| refund-postmortem opus B | ✓ | 14 | None | 0 | 0 | None | 1 | pmdb 5, python 5, shell 3, skill 1 |
| refund-postmortem sonnet A | ✗ | 30 | 26 | 2 | 1 | None | 0 | read 20, search 5, python 3, edit 2 |
| refund-postmortem sonnet A | ✗ | 27 | 26 | 1 | 0 | None | 0 | read 20, search 5, edit 1, python 1 |
| refund-postmortem sonnet B | ✓ | 48 | 39 | 4 | 1 | None | 0 | read 18, python 18, pmdb 5, edit 4, search 2, skill 1 |
| refund-postmortem sonnet B | ✓ | 52 | 40 | 4 | 3 | None | 1 | read 15, python 15, pmdb 9, search 7, edit 4, skill 1, shell 1 |
| stock-allocation haiku A | ✓ | 38 | 34 | 1 | 0 | None | 2 | read 18, search 10, python 8, edit 1, shell 1 |
| stock-allocation haiku A | ✓ | 31 | 22 | 1 | 0 | None | 2 | read 15, search 9, python 5, edit 1, shell 1 |
| stock-allocation haiku B | ✓ | 42 | 27 | 1 | 0 | None | 4 | read 14, pmdb 12, search 7, python 6, skill 1, edit 1, shell 1 |
| stock-allocation haiku B | ✓ | 33 | 22 | 1 | 0 | None | 5 | read 11, pmdb 11, search 5, python 3, skill 1, edit 1, shell 1 |
| stock-allocation opus A | ✓ | 8 | 5 | 1 | 0 | None | 1 | shell 5, python 2, edit 1 |
| stock-allocation opus A | ✓ | 8 | 5 | 1 | 0 | None | 0 | shell 5, python 2, edit 1 |
| stock-allocation opus B | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 2, skill 1, pmdb 1, edit 1, python 1 |
| stock-allocation opus B | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 2, skill 1, pmdb 1, edit 1, python 1 |
| stock-allocation sonnet A | ✓ | 29 | 23 | 1 | 0 | None | 0 | read 13, python 10, search 5, edit 1 |
| stock-allocation sonnet A | ✓ | 27 | 22 | 1 | 0 | None | 0 | read 14, python 7, search 4, edit 1, shell 1 |
| stock-allocation sonnet B | ✓ | 34 | 21 | 1 | 0 | None | 0 | read 13, python 9, pmdb 7, search 3, skill 1, edit 1 |
| stock-allocation sonnet B | ✓ | 19 | 18 | 1 | 0 | None | 0 | read 11, pmdb 4, skill 1, search 1, edit 1, python 1 |
