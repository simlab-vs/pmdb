# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | D | 6 | 1/6 | 0 | 68.0 | 21.0 | 6.0 | 0.0 | 17.0 | 0.0 | 0.0 | 0.0 | 16.0 | 0.0 | 2.5 | 1.0 | None | None | 53.0 | 2.5 | 1.5 | None | 4.0 |
| opus | D | 6 | 6/6 | 0 | 10.5 | 0.0 | 0.0 | 0.0 | 3.5 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 | 1.0 | 2.0 | None | None | 8.5 | 1.0 | 0.0 | None | 0.0 |
| sonnet | D | 6 | 6/6 | 0 | 44.5 | 14.5 | 3.0 | 0.0 | 18.5 | 0.0 | 0.0 | 0.0 | 6.5 | 0.0 | 2.0 | 1.0 | None | None | 37.0 | 2.0 | 0.5 | None | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku D | ✗ | 79 | 74 | 2 | 1 | None | 12 | pmdb 32, read 21, python 15, search 9, edit 2 |
| card-ledger-queue haiku D | ✗ | 67 | 54 | 7 | 5 | None | 4 | read 21, pmdb 20, python 12, edit 7, search 6, shell 1 |
| card-ledger-queue opus D | ✓ | 8 | None | 0 | 0 | None | 1 | python 4, pmdb 3, shell 1 |
| card-ledger-queue opus D | ✓ | 10 | 8 | 2 | 1 | None | 0 | pmdb 3, python 3, shell 2, edit 2 |
| card-ledger-queue sonnet D | ✓ | 33 | 24 | 2 | 1 | None | 0 | read 12, python 12, pmdb 4, search 3, edit 2 |
| card-ledger-queue sonnet D | ✓ | 24 | 19 | 2 | 1 | None | 0 | read 11, python 5, pmdb 4, edit 2, search 1, shell 1 |
| payroll-postmortem haiku D | ✓ | 50 | 39 | 1 | 0 | None | 5 | pmdb 17, read 17, python 8, search 6, edit 1, shell 1 |
| payroll-postmortem haiku D | ✗ | 80 | 53 | 4 | 3 | None | 4 | python 34, read 23, pmdb 9, search 7, edit 4, shell 3 |
| payroll-postmortem opus D | ✓ | 9 | 7 | 1 | 0 | None | 1 | pmdb 4, shell 2, python 2, edit 1 |
| payroll-postmortem opus D | ✓ | 11 | 9 | 1 | 0 | None | 0 | pmdb 4, python 4, shell 2, edit 1 |
| payroll-postmortem sonnet D | ✓ | 34 | 29 | 1 | 0 | None | 0 | read 14, python 8, pmdb 7, search 3, edit 1, shell 1 |
| payroll-postmortem sonnet D | ✓ | 66 | 63 | 1 | 0 | None | 0 | python 34, read 20, pmdb 6, search 3, shell 2, edit 1 |
| refund-postmortem haiku D | ✗ | 69 | 45 | 3 | 2 | None | 4 | python 31, read 15, pmdb 15, search 5, edit 3 |
| refund-postmortem haiku D | ✗ | 58 | 53 | 1 | 0 | None | 3 | read 21, python 19, pmdb 11, search 5, edit 1, shell 1 |
| refund-postmortem opus D | ✓ | 14 | 10 | 4 | 3 | None | 0 | pmdb 5, edit 4, python 3, shell 2 |
| refund-postmortem opus D | ✓ | 13 | None | 0 | 0 | None | 0 | python 6, pmdb 5, shell 2 |
| refund-postmortem sonnet D | ✓ | 68 | 50 | 2 | 0 | None | 0 | python 38, read 20, pmdb 7, edit 2, search 1 |
| refund-postmortem sonnet D | ✓ | 55 | 45 | 4 | 1 | None | 1 | python 25, read 15, pmdb 7, edit 4, search 3, shell 1 |
