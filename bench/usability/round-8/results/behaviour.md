# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 10 | 5/10 | 0 | 30.0 | 16.5 | 6.0 | 0.0 | 3.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.5 | None | None | 24.0 | 1.0 | 0.0 | None | 1.5 |
| haiku | B | 10 | 6/10 | 0 | 48.0 | 13.0 | 4.0 | 0.0 | 14.0 | 0.0 | 0.0 | 6.0 | 1.0 | 2.5 | 0.0 | None | None | 37.5 | 2.5 | 1.0 | None | 4.5 |
| opus | A | 10 | 8/10 | 0 | 6.0 | 0.0 | 0.0 | 0.0 | 1.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | None | None | 5.0 | 1.0 | 0.0 | None | 0.0 |
| opus | B | 10 | 10/10 | 0 | 11.5 | 0.0 | 0.0 | 0.0 | 4.5 | 0.0 | 0.0 | 1.0 | 1.0 | 1.0 | 2.5 | None | 7.0 | 7.5 | 1.0 | 0.0 | None | 1.0 |
| sonnet | A | 10 | 8/10 | 0 | 30.5 | 19.0 | 3.5 | 0.0 | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.5 | 1.0 | None | None | 27.5 | 1.5 | 0.0 | None | 0.0 |
| sonnet | B | 10 | 10/10 | 0 | 30.5 | 13.5 | 3.0 | 0.0 | 8.5 | 0.0 | 0.0 | 2.0 | 1.0 | 1.5 | 0.0 | None | None | 23.5 | 1.5 | 0.5 | None | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku A | ✗ | 30 | 23 | 5 | 3 | None | 1 | read 17, search 5, edit 5, python 3 |
| card-ledger-queue haiku A | ✓ | 18 | 13 | 1 | 0 | None | 0 | read 8, search 7, python 2, edit 1 |
| card-ledger-queue haiku B | ✗ | 39 | 36 | 1 | 0 | None | 2 | read 16, python 14, search 6, skill 1, pmdb 1, edit 1 |
| card-ledger-queue haiku B | ✓ | 57 | 44 | 12 | 10 | None | 5 | python 20, edit 12, pmdb 9, read 9, search 5, skill 1, bash 1 |
| card-ledger-queue opus A | ✓ | 9 | 7 | 2 | 1 | None | 0 | shell 6, edit 2, python 1 |
| card-ledger-queue opus A | ✓ | 9 | 7 | 2 | 1 | None | 0 | shell 5, python 2, edit 2 |
| card-ledger-queue opus B | ✓ | 11 | 9 | 2 | 1 | None | 1 | python 5, shell 2, edit 2, skill 1, pmdb 1 |
| card-ledger-queue opus B | ✓ | 14 | 12 | 2 | 1 | None | 2 | python 4, pmdb 3, shell 2, edit 2, skill 1, record 1, read 1 |
| card-ledger-queue sonnet A | ✓ | 20 | 17 | 2 | 1 | None | 0 | read 13, search 3, edit 2, python 2 |
| card-ledger-queue sonnet A | ✓ | 26 | 23 | 2 | 1 | None | 0 | read 19, search 2, python 2, edit 2, shell 1 |
| card-ledger-queue sonnet B | ✓ | 25 | 22 | 2 | 1 | None | 0 | read 12, python 6, search 2, pmdb 2, edit 2, skill 1 |
| card-ledger-queue sonnet B | ✓ | 31 | 25 | 2 | 1 | None | 0 | read 14, python 10, search 2, pmdb 2, edit 2, skill 1 |
| payroll-postmortem haiku A | ✗ | 49 | 41 | 5 | 4 | None | 1 | read 24, search 12, python 7, edit 5, shell 1 |
| payroll-postmortem haiku A | ✗ | 38 | 33 | 2 | 1 | None | 2 | read 23, search 6, python 5, shell 2, edit 2 |
| payroll-postmortem haiku B | ✓ | 80 | 56 | 11 | 8 | None | 8 | pmdb 30, read 20, python 11, edit 11, search 7, skill 1 |
| payroll-postmortem haiku B | ✗ | 67 | 50 | 12 | 11 | None | 1 | python 23, read 17, search 12, edit 12, skill 1, pmdb 1, shell 1 |
| payroll-postmortem opus A | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 5, edit 1, python 1 |
| payroll-postmortem opus A | ✓ | 6 | None | 0 | 0 | None | 1 | shell 4, python 2 |
| payroll-postmortem opus B | ✓ | 10 | 9 | 1 | 0 | None | 0 | python 4, shell 3, skill 1, pmdb 1, edit 1 |
| payroll-postmortem opus B | ✓ | 15 | 13 | 1 | 0 | None | 2 | python 6, shell 5, skill 1, record 1, search 1, edit 1 |
| payroll-postmortem sonnet A | ✓ | 47 | 33 | 3 | 1 | None | 0 | read 23, python 12, search 7, edit 3, shell 2 |
| payroll-postmortem sonnet A | ✓ | 30 | 28 | 1 | 0 | None | 0 | read 22, search 4, python 3, edit 1 |
| payroll-postmortem sonnet B | ✓ | 40 | 32 | 1 | 0 | None | 2 | python 19, read 16, skill 1, search 1, pmdb 1, shell 1, edit 1 |
| payroll-postmortem sonnet B | ✓ | 55 | 49 | 2 | 1 | None | 2 | python 26, read 22, search 3, edit 2, skill 1, pmdb 1 |
| points-expiry haiku A | ✓ | 12 | 11 | 1 | 0 | None | 0 | read 7, search 4, edit 1 |
| points-expiry haiku A | ✓ | 25 | 17 | 1 | 0 | None | 2 | read 13, search 6, python 4, edit 1, shell 1 |
| points-expiry haiku B | ✓ | 36 | 30 | 1 | 0 | None | 4 | python 14, read 9, pmdb 7, search 4, skill 1, edit 1 |
| points-expiry haiku B | ✓ | 30 | 24 | 1 | 0 | None | 12 | pmdb 11, read 8, search 4, python 4, skill 1, edit 1, shell 1 |
| points-expiry opus A | ✓ | 5 | 4 | 1 | 0 | None | 0 | shell 4, edit 1 |
| points-expiry opus A | ✓ | 5 | 5 | 1 | 0 | None | 0 | shell 4, edit 1 |
| points-expiry opus B | ✓ | 7 | 5 | 1 | 0 | None | 1 | shell 2, python 2, skill 1, pmdb 1, edit 1 |
| points-expiry opus B | ✓ | 8 | 5 | 1 | 0 | None | 1 | shell 2, python 2, skill 1, pmdb 1, edit 1, record 1 |
| points-expiry sonnet A | ✓ | 15 | 14 | 1 | 0 | None | 0 | read 10, search 3, edit 1, python 1 |
| points-expiry sonnet A | ✓ | 17 | 16 | 1 | 0 | None | 0 | read 13, search 2, edit 1, python 1 |
| points-expiry sonnet B | ✓ | 18 | 16 | 1 | 0 | None | 0 | read 9, search 3, pmdb 3, skill 1, edit 1, python 1 |
| points-expiry sonnet B | ✓ | 16 | 15 | 1 | 0 | None | 0 | read 7, search 4, python 2, skill 1, pmdb 1, edit 1 |
| refund-postmortem haiku A | ✗ | 23 | 23 | 1 | 0 | None | 0 | read 16, search 6, edit 1 |
| refund-postmortem haiku A | ✗ | 30 | 25 | 1 | 0 | None | 2 | read 21, search 5, python 2, shell 1, edit 1 |
| refund-postmortem haiku B | ✗ | 62 | 39 | 8 | 6 | None | 3 | python 31, read 16, edit 8, search 3, pmdb 3, skill 1 |
| refund-postmortem haiku B | ✗ | 65 | 58 | 1 | 0 | None | 4 | python 41, read 17, pmdb 3, search 2, skill 1, edit 1 |
| refund-postmortem opus A | ✗ | 8 | 5 | 2 | 1 | None | 0 | read 2, edit 2, python 2, search 1, shell 1 |
| refund-postmortem opus A | ✗ | 6 | None | 0 | 0 | None | 0 | read 3, python 2, search 1 |
| refund-postmortem opus B | ✓ | 14 | None | 0 | 0 | None | 0 | python 9, pmdb 2, skill 1, shell 1, read 1 |
| refund-postmortem opus B | ✓ | 16 | None | 0 | 0 | None | 2 | python 8, pmdb 3, shell 3, skill 1, record 1 |
| refund-postmortem sonnet A | ✗ | 32 | 29 | 2 | 1 | None | 0 | read 23, search 5, edit 2, shell 1, python 1 |
| refund-postmortem sonnet A | ✗ | 32 | 28 | 2 | 0 | None | 0 | read 22, search 3, python 3, shell 2, edit 2 |
| refund-postmortem sonnet B | ✓ | 43 | 37 | 4 | 1 | None | 0 | read 16, python 15, edit 4, search 3, pmdb 3, skill 1, shell 1 |
| refund-postmortem sonnet B | ✓ | 51 | 47 | 2 | 1 | None | 1 | python 30, read 14, search 3, edit 2, skill 1, pmdb 1 |
| stock-allocation haiku A | ✓ | 38 | 37 | 1 | 0 | None | 3 | read 16, python 14, search 7, edit 1 |
| stock-allocation haiku A | ✓ | 52 | 41 | 1 | 0 | None | 2 | read 25, python 13, search 11, shell 2, edit 1 |
| stock-allocation haiku B | ✓ | 31 | 20 | 4 | 2 | None | 8 | read 10, pmdb 8, edit 4, search 3, python 3, shell 2, skill 1 |
| stock-allocation haiku B | ✓ | 28 | 21 | 1 | 0 | None | 6 | python 11, read 8, pmdb 5, search 2, skill 1, edit 1 |
| stock-allocation opus A | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 3, python 2, edit 1 |
| stock-allocation opus A | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| stock-allocation opus B | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 3, pmdb 2, skill 1, edit 1 |
| stock-allocation opus B | ✓ | 12 | 5 | 1 | 0 | None | 1 | python 5, shell 4, skill 1, pmdb 1, edit 1 |
| stock-allocation sonnet A | ✓ | 31 | 27 | 1 | 0 | None | 0 | read 18, search 6, python 5, edit 1, shell 1 |
| stock-allocation sonnet A | ✓ | 38 | 30 | 1 | 0 | None | 0 | read 19, python 9, search 7, shell 2, edit 1 |
| stock-allocation sonnet B | ✓ | 30 | 18 | 1 | 0 | None | 0 | read 13, python 7, search 5, pmdb 3, skill 1, edit 1 |
| stock-allocation sonnet B | ✓ | 18 | 16 | 1 | 0 | None | 0 | read 9, search 3, pmdb 3, skill 1, edit 1, python 1 |
