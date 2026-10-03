# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 10 | 5/10 | 0 | 22.5 | 15.5 | 5.0 | 0.0 | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.5 | None | None | 20.0 | 1.0 | 0.0 | None | 1.0 |
| haiku | B | 10 | 4/10 | 0 | 47.0 | 11.5 | 4.0 | 0.0 | 1.0 | 21.5 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | 0.0 | None | None | 29.5 | 1.0 | 0.0 | None | 4.5 |
| opus | A | 10 | 8/10 | 0 | 7.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | None | None | 5.5 | 1.0 | 0.0 | None | 0.0 |
| opus | B | 10 | 10/10 | 0 | 10.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.0 | 0.0 | 0.0 | 1.0 | 1.0 | 1.0 | 2.0 | None | None | 7 | 1.0 | 0.0 | None | 0.0 |
| sonnet | A | 10 | 8/10 | 0 | 30.0 | 19.0 | 4.0 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | None | None | 25.0 | 1.0 | 0.0 | None | 0.0 |
| sonnet | B | 10 | 8/10 | 0 | 33.0 | 13.0 | 2.0 | 0.0 | 1.5 | 12.5 | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | 0.5 | None | None | 27.5 | 1.0 | 0.0 | None | 0.5 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku A | ✗ | 18 | 15 | 2 | 1 | None | 0 | read 11, search 5, edit 2 |
| card-ledger-queue haiku A | ✓ | 22 | 16 | 1 | 0 | None | 1 | read 14, search 4, python 2, edit 1, shell 1 |
| card-ledger-queue haiku B | ✗ | 80 | None | 0 | 0 | None | 9 | trace 67, read 10, search 3 |
| card-ledger-queue haiku B | ✗ | 80 | None | 0 | 0 | None | 4 | trace 65, read 13, skill 1, search 1 |
| card-ledger-queue opus A | ✓ | 9 | 7 | 2 | 1 | None | 0 | shell 6, edit 2, python 1 |
| card-ledger-queue opus A | ✓ | 7 | 5 | 2 | 1 | None | 0 | shell 3, python 2, edit 2 |
| card-ledger-queue opus B | ✓ | 11 | 8 | 2 | 1 | None | 0 | trace 6, edit 2, skill 1, pmdb 1, shell 1 |
| card-ledger-queue opus B | ✓ | 10 | 8 | 2 | 1 | None | 0 | trace 4, shell 3, edit 2, skill 1 |
| card-ledger-queue sonnet A | ✓ | 30 | 21 | 2 | 1 | None | 0 | read 20, python 5, search 2, edit 2, shell 1 |
| card-ledger-queue sonnet A | ✓ | 23 | 17 | 2 | 1 | None | 0 | read 18, edit 2, search 1, python 1, shell 1 |
| card-ledger-queue sonnet B | ✓ | 37 | 32 | 2 | 1 | None | 0 | trace 18, read 11, search 2, edit 2, python 2, skill 1, shell 1 |
| card-ledger-queue sonnet B | ✗ | 48 | 46 | 1 | 0 | None | 0 | read 21, trace 18, search 5, python 2, skill 1, edit 1 |
| payroll-postmortem haiku A | ✗ | 51 | 22 | 10 | 8 | None | 3 | read 25, edit 10, python 9, search 6, shell 1 |
| payroll-postmortem haiku A | ✗ | 80 | 65 | 10 | 8 | None | 3 | read 29, python 23, search 17, edit 10, shell 1 |
| payroll-postmortem haiku B | ✗ | 41 | 34 | 1 | 0 | None | 5 | trace 19, read 13, search 4, python 4, edit 1 |
| payroll-postmortem haiku B | ✗ | 65 | 50 | 6 | 5 | None | 6 | trace 24, read 21, search 7, edit 6, python 5, skill 1, shell 1 |
| payroll-postmortem opus A | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 5, edit 1, python 1 |
| payroll-postmortem opus A | ✓ | 10 | 8 | 1 | 0 | None | 0 | shell 8, edit 1, python 1 |
| payroll-postmortem opus B | ✓ | 10 | 8 | 1 | 0 | None | 2 | trace 5, shell 2, skill 1, pmdb 1, edit 1 |
| payroll-postmortem opus B | ✓ | 7 | 6 | 1 | 0 | None | 0 | shell 2, trace 2, skill 1, pmdb 1, edit 1 |
| payroll-postmortem sonnet A | ✓ | 32 | 26 | 1 | 0 | None | 0 | read 20, python 7, search 3, edit 1, shell 1 |
| payroll-postmortem sonnet A | ✓ | 32 | 27 | 1 | 0 | None | 0 | read 21, python 6, search 4, edit 1 |
| payroll-postmortem sonnet B | ✓ | 40 | 38 | 1 | 0 | None | 3 | read 20, trace 14, search 2, skill 1, shell 1, edit 1, python 1 |
| payroll-postmortem sonnet B | ✓ | 29 | 23 | 1 | 0 | None | 2 | read 13, trace 11, search 2, skill 1, edit 1, python 1 |
| points-expiry haiku A | ✓ | 17 | 13 | 1 | 0 | None | 1 | read 8, search 5, python 2, edit 1, shell 1 |
| points-expiry haiku A | ✓ | 19 | 16 | 1 | 0 | None | 0 | read 11, search 4, python 3, edit 1 |
| points-expiry haiku B | ✓ | 28 | 25 | 1 | 0 | None | 4 | trace 11, read 8, search 6, python 1, edit 1, shell 1 |
| points-expiry haiku B | ✓ | 23 | 18 | 1 | 0 | None | 3 | trace 12, read 6, search 2, skill 1, edit 1, shell 1 |
| points-expiry opus A | ✓ | 6 | 4 | 1 | 0 | None | 1 | shell 4, edit 1, python 1 |
| points-expiry opus A | ✓ | 5 | 4 | 1 | 0 | None | 1 | shell 3, edit 1, python 1 |
| points-expiry opus B | ✓ | 7 | 7 | 1 | 0 | None | 0 | shell 2, trace 2, skill 1, pmdb 1, edit 1 |
| points-expiry opus B | ✓ | 8 | 6 | 1 | 0 | None | 1 | trace 3, shell 2, skill 1, pmdb 1, edit 1 |
| points-expiry sonnet A | ✓ | 15 | 15 | 1 | 0 | None | 0 | read 12, search 2, edit 1 |
| points-expiry sonnet A | ✓ | 20 | 18 | 1 | 0 | None | 0 | read 14, search 4, edit 1, python 1 |
| points-expiry sonnet B | ✓ | 22 | 19 | 1 | 0 | None | 1 | read 10, trace 7, search 2, skill 1, edit 1, python 1 |
| points-expiry sonnet B | ✓ | 22 | 19 | 1 | 0 | None | 2 | read 13, trace 5, search 2, skill 1, edit 1 |
| refund-postmortem haiku A | ✗ | 19 | 18 | 1 | 0 | None | 0 | read 16, search 2, edit 1 |
| refund-postmortem haiku A | ✗ | 23 | 22 | 1 | 0 | None | 0 | read 17, search 5, edit 1 |
| refund-postmortem haiku B | ✗ | 53 | 40 | 3 | 2 | None | 4 | trace 29, read 15, search 4, edit 3, skill 1, python 1 |
| refund-postmortem haiku B | ✗ | 58 | 41 | 1 | 0 | None | 8 | trace 36, read 15, search 4, skill 1, edit 1, python 1 |
| refund-postmortem opus A | ✗ | 8 | 6 | 1 | 0 | None | 0 | shell 3, python 3, search 1, edit 1 |
| refund-postmortem opus A | ✗ | 11 | 7 | 3 | 2 | None | 0 | search 3, read 3, edit 3, python 2 |
| refund-postmortem opus B | ✓ | 9 | None | 0 | 0 | None | 1 | trace 6, skill 1, pmdb 1, shell 1 |
| refund-postmortem opus B | ✓ | 21 | 9 | 6 | 5 | None | 0 | trace 8, edit 6, shell 4, skill 1, read 1, python 1 |
| refund-postmortem sonnet A | ✗ | 33 | 29 | 2 | 1 | None | 0 | read 21, search 7, python 2, edit 2, shell 1 |
| refund-postmortem sonnet A | ✗ | 30 | 24 | 2 | 1 | None | 0 | read 21, search 4, edit 2, python 2, shell 1 |
| refund-postmortem sonnet B | ✓ | 47 | 39 | 5 | 1 | None | 0 | trace 22, read 16, edit 5, skill 1, search 1, python 1, shell 1 |
| refund-postmortem sonnet B | ✗ | 70 | 62 | 3 | 2 | None | 1 | trace 41, read 18, search 3, python 3, edit 3, skill 1, shell 1 |
| stock-allocation haiku A | ✓ | 47 | 38 | 1 | 0 | None | 5 | read 20, search 14, python 9, shell 3, edit 1 |
| stock-allocation haiku A | ✓ | 32 | 23 | 1 | 0 | None | 1 | read 15, python 10, search 6, edit 1 |
| stock-allocation haiku B | ✓ | 22 | 16 | 1 | 0 | None | 1 | trace 9, read 6, search 4, skill 1, edit 1, python 1 |
| stock-allocation haiku B | ✓ | 32 | 23 | 1 | 0 | None | 5 | trace 13, read 10, search 6, python 2, edit 1 |
| stock-allocation opus A | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| stock-allocation opus A | ✓ | 6 | 5 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| stock-allocation opus B | ✓ | 11 | 5 | 1 | 0 | None | 2 | trace 6, shell 3, skill 1, edit 1 |
| stock-allocation opus B | ✓ | 10 | 6 | 1 | 0 | None | 0 | trace 5, shell 3, skill 1, edit 1 |
| stock-allocation sonnet A | ✓ | 32 | 29 | 1 | 0 | None | 0 | read 18, python 8, search 4, edit 1, shell 1 |
| stock-allocation sonnet A | ✓ | 27 | 26 | 1 | 0 | None | 0 | read 17, search 5, python 4, edit 1 |
| stock-allocation sonnet B | ✓ | 22 | 21 | 1 | 0 | None | 0 | read 9, trace 5, search 3, python 2, skill 1, shell 1, edit 1 |
| stock-allocation sonnet B | ✓ | 23 | 22 | 1 | 0 | None | 0 | read 10, trace 5, search 4, python 2, skill 1, edit 1 |
