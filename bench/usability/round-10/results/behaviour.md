# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | C | 6 | 2/6 | 0 | 50.0 | 16.5 | 4.5 | 0.0 | 16.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 6.5 | 1.5 | None | None | 4.0 | 6.5 | 2.0 | None | 1.5 |
| opus | C | 6 | 6/6 | 0 | 9.5 | 0.0 | 0.0 | 0.0 | 6.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 | 3.0 | None | None | 7 | 0.5 | 0.0 | None | 0.0 |
| sonnet | C | 6 | 6/6 | 0 | 38.5 | 15.0 | 2.5 | 0.0 | 15.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 | 1.5 | None | None | 16.0 | 3.0 | 1.0 | None | 0.5 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku C | ✓ | 27 | 4 | 7 | 0 | None | 2 | read 9, python 8, edit 7, shell 2, search 1 |
| card-ledger-queue haiku C | ✓ | 49 | 6 | 15 | 1 | None | 2 | read 16, edit 15, python 15, search 3 |
| card-ledger-queue opus C | ✓ | 9 | 7 | 2 | 1 | None | 0 | python 4, shell 3, edit 2 |
| card-ledger-queue opus C | ✓ | 10 | None | 0 | 0 | None | 0 | python 7, shell 3 |
| card-ledger-queue sonnet C | ✓ | 35 | 18 | 4 | 2 | None | 2 | read 16, python 11, edit 4, search 2, shell 2 |
| card-ledger-queue sonnet C | ✓ | 40 | 22 | 3 | 1 | None | 1 | read 20, python 13, shell 3, edit 3, search 1 |
| payroll-postmortem haiku C | ✗ | 60 | 4 | 6 | 3 | None | 0 | read 25, python 14, search 12, edit 6, shell 2, pmdb 1 |
| payroll-postmortem haiku C | ✗ | 71 | 4 | 6 | 3 | None | 2 | python 33, read 18, search 12, edit 6, shell 2 |
| payroll-postmortem opus C | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 3, python 3, pmdb 1, edit 1 |
| payroll-postmortem opus C | ✓ | 9 | 7 | 1 | 0 | None | 0 | python 5, shell 3, edit 1 |
| payroll-postmortem sonnet C | ✓ | 37 | 14 | 2 | 0 | None | 0 | python 17, read 12, search 6, edit 2 |
| payroll-postmortem sonnet C | ✓ | 33 | 15 | 2 | 0 | None | 1 | read 14, python 14, search 3, edit 2 |
| refund-postmortem haiku C | ✗ | 51 | 4 | 6 | 3 | None | 1 | python 27, read 13, edit 6, search 4, shell 1 |
| refund-postmortem haiku C | ✗ | 47 | 8 | 8 | 1 | None | 1 | read 17, python 17, edit 8, search 5 |
| refund-postmortem opus C | ✓ | 13 | None | 0 | 0 | None | 0 | python 8, shell 5 |
| refund-postmortem opus C | ✓ | 12 | None | 0 | 0 | None | 0 | python 8, shell 4 |
| refund-postmortem sonnet C | ✓ | 48 | 11 | 3 | 1 | None | 0 | python 25, read 14, search 5, edit 3, shell 1 |
| refund-postmortem sonnet C | ✓ | 55 | 17 | 5 | 1 | None | 0 | python 29, read 17, edit 5, search 2, shell 2 |
