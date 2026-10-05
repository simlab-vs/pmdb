# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | trace | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 3 | 1/3 | 0 | 32 | 16 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | None | None | 22 | 2 | 1 | None | 1 |
| haiku | F | 3 | 1/3 | 0 | 65 | 25 | 6 | 0 | 17 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | None | None | 8 | 6 | 2 | None | 2 |
| haiku | P | 3 | 0/3 | 0 | 75 | 13 | 4 | 0 | 1 | 30 | 0 | 0 | 0 | 0 | 4 | 0 | None | None | 48.5 | 4 | 2 | None | 11 |
| haiku | Q | 3 | 1/3 | 0 | 75 | 18 | 4 | 0 | 27 | 0 | 0 | 0 | 13 | 0 | 2 | 1 | None | None | 63 | 2 | 1 | None | 4 |
| opus | A | 3 | 2/3 | 0 | 9 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | None | None | 8 | 0 | 0 | None | 0 |
| opus | F | 3 | 3/3 | 0 | 15 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | None | None | 7 | 0 | 0 | None | 0 |
| opus | P | 3 | 3/3 | 0 | 8 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | None | None | 9 | 0 | 0 | None | 1 |
| opus | Q | 3 | 3/3 | 0 | 9 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 4 | 0 | 1 | 3 | None | None | 6.5 | 1 | 0 | None | 0 |
| sonnet | A | 3 | 2/3 | 0 | 30 | 20 | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 23 | None | 25 | 2 | 1 | None | 0 |
| sonnet | F | 3 | 3/3 | 0 | 48 | 16 | 2 | 0 | 23 | 0 | 0 | 0 | 0 | 0 | 3 | 1 | 47 | None | 17 | 3 | 1 | None | 0 |
| sonnet | P | 3 | 3/3 | 0 | 42 | 18 | 3 | 0 | 1 | 17 | 0 | 0 | 0 | 0 | 2 | 0 | None | None | 32 | 2 | 1 | None | 1 |
| sonnet | Q | 3 | 3/3 | 0 | 35 | 14 | 2 | 0 | 10 | 0 | 0 | 0 | 6 | 0 | 2 | 1 | None | None | 26 | 2 | 1 | None | 0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| card-ledger-queue haiku A | ✓ | 32 | 24 | 2 | 1 | None | 1 | read 20, search 4, python 4, edit 2, shell 2 |
| card-ledger-queue haiku F | ✓ | 54 | 4 | 18 | 3 | None | 1 | edit 18, python 17, read 16, search 3 |
| card-ledger-queue haiku P | ✗ | 76 | None | 0 | 0 | None | 18 | trace 64, read 8, search 4 |
| card-ledger-queue haiku Q | ✗ | 75 | 72 | 1 | 0 | None | 6 | python 27, pmdb 26, read 17, search 2, shell 2, edit 1 |
| card-ledger-queue opus A | ✓ | 5 | None | 0 | 0 | None | 0 | shell 4, python 1 |
| card-ledger-queue opus F | ✓ | 16 | None | 0 | 0 | None | 2 | python 7, shell 4, pmdb 4, read 1 |
| card-ledger-queue opus P | ✓ | 8 | None | 0 | 0 | None | 1 | shell 3, python 3, trace 2 |
| card-ledger-queue opus Q | ✓ | 8 | 6 | 2 | 1 | None | 0 | pmdb 4, edit 2, shell 1, python 1 |
| card-ledger-queue sonnet A | ✓ | 18 | 15 | 2 | 1 | None | 0 | read 13, python 2, edit 2, search 1 |
| card-ledger-queue sonnet F | ✓ | 35 | 18 | 3 | 1 | None | 0 | read 16, python 13, edit 3, search 2, shell 1 |
| card-ledger-queue sonnet P | ✓ | 35 | 31 | 2 | 1 | None | 1 | read 20, trace 9, search 2, edit 2, shell 1, python 1 |
| card-ledger-queue sonnet Q | ✓ | 28 | 22 | 2 | 1 | None | 1 | read 9, python 8, pmdb 6, search 2, edit 2, shell 1 |
| payroll-postmortem haiku A | ✗ | 33 | 22 | 3 | 2 | None | 1 | read 16, python 7, search 6, edit 3, shell 1 |
| payroll-postmortem haiku F | ✗ | 67 | 9 | 6 | 2 | None | 2 | read 28, search 16, python 16, edit 6, shell 1 |
| payroll-postmortem haiku P | ✗ | 75 | 59 | 9 | 7 | None | 11 | trace 30, read 25, search 9, edit 9, python 1, shell 1 |
| payroll-postmortem haiku Q | ✓ | 44 | 39 | 2 | 1 | None | 4 | read 18, pmdb 13, python 6, search 4, edit 2, shell 1 |
| payroll-postmortem opus A | ✓ | 9 | 8 | 1 | 0 | None | 0 | shell 6, python 2, edit 1 |
| payroll-postmortem opus F | ✓ | 8 | 7 | 1 | 0 | None | 0 | shell 4, python 3, edit 1 |
| payroll-postmortem opus P | ✓ | 10 | 9 | 1 | 0 | None | 2 | shell 3, trace 3, python 3, edit 1 |
| payroll-postmortem opus Q | ✓ | 9 | 7 | 1 | 0 | None | 0 | pmdb 4, shell 3, edit 1, python 1 |
| payroll-postmortem sonnet A | ✓ | 31 | 26 | 2 | 1 | None | 0 | read 20, python 5, search 3, edit 2, test 1 |
| payroll-postmortem sonnet F | ✓ | 48 | 16 | 3 | 1 | None | 0 | python 23, read 18, edit 3, search 2, shell 1, test 1 |
| payroll-postmortem sonnet P | ✓ | 42 | 32 | 1 | 0 | None | 2 | read 18, trace 17, search 4, python 2, edit 1 |
| payroll-postmortem sonnet Q | ✓ | 35 | 26 | 1 | 0 | None | 0 | read 14, python 10, pmdb 5, search 4, edit 1, shell 1 |
| refund-postmortem haiku A | ✗ | 23 | 20 | 1 | 0 | None | 0 | read 16, search 4, python 2, edit 1 |
| refund-postmortem haiku F | ✗ | 65 | 8 | 6 | 2 | None | 2 | python 28, read 25, search 6, edit 6 |
| refund-postmortem haiku P | ✗ | 47 | 38 | 4 | 2 | None | 1 | trace 27, read 13, edit 4, search 2, python 1 |
| refund-postmortem haiku Q | ✗ | 78 | 63 | 8 | 6 | None | 4 | python 33, read 25, edit 8, pmdb 7, search 5 |
| refund-postmortem opus A | ✗ | 11 | None | 0 | 0 | None | 0 | read 4, shell 3, python 3, search 1 |
| refund-postmortem opus F | ✓ | 15 | None | 0 | 0 | None | 0 | python 10, shell 5 |
| refund-postmortem opus P | ✓ | 7 | None | 0 | 0 | None | 0 | trace 6, shell 1 |
| refund-postmortem opus Q | ✓ | 12 | None | 0 | 0 | None | 0 | pmdb 5, python 4, shell 3 |
| refund-postmortem sonnet A | ✗ | 30 | 25 | 2 | 0 | None | 1 | read 23, search 4, edit 2, python 1 |
| refund-postmortem sonnet F | ✓ | 56 | 17 | 3 | 1 | None | 1 | python 34, read 16, edit 3, shell 2, search 1 |
| refund-postmortem sonnet P | ✓ | 50 | 44 | 2 | 1 | None | 0 | trace 27, read 17, search 3, edit 2, python 1 |
| refund-postmortem sonnet Q | ✓ | 59 | 35 | 4 | 3 | None | 0 | python 27, read 17, pmdb 8, edit 4, search 2, shell 1 |
