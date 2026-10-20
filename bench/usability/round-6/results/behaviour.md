# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 6 | 4/6 | 0 | 35.0 | 14.5 | 5.5 | 0.0 | 17.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.5 | None | None | 20.5 | 1.0 | 0.0 | None | 0.5 |
| haiku | B | 6 | 2/6 | 0 | 63.0 | 15.0 | 6.0 | 0.0 | 5.0 | 0.0 | 0.0 | 24.5 | 1.0 | 1.5 | 1.0 | None | None | 47.0 | 1.5 | 0.0 | None | 9.5 |
| opus | A | 6 | 5/6 | 0 | 5.5 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | None | None | 4 | 1.0 | 0.0 | None | 0.0 |
| opus | B | 6 | 6/6 | 0 | 7.0 | 0.0 | 0.0 | 0.0 | 1.5 | 0.0 | 0.0 | 1.0 | 0.5 | 0.0 | 3.0 | None | None | 7.0 | 0.0 | 0.0 | None | 0.0 |
| sonnet | A | 6 | 5/6 | 0 | 20.5 | 9.5 | 3.5 | 0.0 | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.5 | None | None | 18.0 | 1.0 | 0.0 | None | 0.0 |
| sonnet | B | 6 | 6/6 | 0 | 28.0 | 10.0 | 4.5 | 0.0 | 5.0 | 0.0 | 0.0 | 5.5 | 1.0 | 1.0 | 1.0 | None | None | 25.0 | 1.0 | 0.0 | None | 0.5 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| billing-needle haiku A | ✓ | 44 | 40 | 1 | 0 | None | 2 | python 25, read 12, search 5, edit 1, shell 1 |
| billing-needle haiku B | ✗ | 80 | 78 | 3 | 1 | None | 13 | pmdb 41, read 16, python 14, search 4, edit 3, skill 1, shell 1 |
| billing-needle opus A | ✓ | 7 | 6 | 1 | 0 | None | 1 | shell 3, python 3, edit 1 |
| billing-needle opus B | ✓ | 7 | 6 | 1 | 0 | None | 0 | python 3, shell 2, pmdb 1, edit 1 |
| billing-needle sonnet A | ✓ | 19 | 18 | 1 | 0 | None | 0 | read 8, search 5, python 5, edit 1 |
| billing-needle sonnet B | ✓ | 37 | 34 | 1 | 0 | None | 2 | pmdb 12, read 12, python 6, search 4, skill 1, shell 1, edit 1 |
| bundle-memo haiku A | ✓ | 76 | 20 | 15 | 3 | None | 5 | python 30, read 18, edit 15, search 12, shell 1 |
| bundle-memo haiku B | ✓ | 69 | 40 | 2 | 0 | None | 10 | read 21, search 16, python 15, pmdb 12, edit 2, shell 2, skill 1 |
| bundle-memo opus A | ✓ | 4 | None | 0 | 0 | None | 0 | shell 3, python 1 |
| bundle-memo opus B | ✓ | 5 | None | 0 | 0 | None | 0 | shell 4, python 1 |
| bundle-memo sonnet A | ✓ | 25 | 21 | 1 | 0 | None | 0 | read 11, python 6, shell 5, search 2, edit 1 |
| bundle-memo sonnet B | ✓ | 23 | 20 | 1 | 0 | None | 0 | read 9, python 6, pmdb 4, search 1, skill 1, edit 1, shell 1 |
| hashseed-intermittent haiku A | ✓ | 23 | 18 | 1 | 0 | None | 0 | read 8, python 8, search 5, shell 1, edit 1 |
| hashseed-intermittent haiku B | ✗ | 35 | 29 | 1 | 0 | None | 6 | pmdb 11, read 11, search 7, python 3, skill 1, shell 1, edit 1 |
| hashseed-intermittent opus A | ✓ | 5 | 4 | 1 | 0 | None | 0 | shell 3, edit 1, python 1 |
| hashseed-intermittent opus B | ✓ | 7 | None | 0 | 0 | None | 0 | shell 3, python 2, skill 1, pmdb 1 |
| hashseed-intermittent sonnet A | ✓ | 17 | 12 | 2 | 1 | None | 0 | read 6, search 5, python 3, edit 2, shell 1 |
| hashseed-intermittent sonnet B | ✓ | 20 | 16 | 2 | 1 | None | 0 | read 10, python 3, pmdb 2, edit 2, skill 1, search 1, shell 1 |
| refund-postmortem haiku A | ✗ | 24 | 21 | 1 | 0 | None | 0 | read 17, search 3, python 3, edit 1 |
| refund-postmortem haiku B | ✗ | 74 | 64 | 2 | 0 | None | 13 | pmdb 37, read 20, search 7, python 6, edit 2, skill 1, shell 1 |
| refund-postmortem opus A | ✗ | 11 | 7 | 3 | 2 | None | 0 | shell 6, edit 3, python 2 |
| refund-postmortem opus B | ✓ | 14 | None | 0 | 0 | None | 0 | python 7, shell 3, pmdb 3, skill 1 |
| refund-postmortem sonnet A | ✗ | 31 | 27 | 2 | 1 | None | 0 | read 22, search 4, edit 2, python 2, shell 1 |
| refund-postmortem sonnet B | ✓ | 44 | 37 | 2 | 1 | None | 0 | read 15, python 12, pmdb 8, search 5, edit 2, skill 1, shell 1 |
| shared-tiers haiku A | ✓ | 26 | 19 | 1 | 0 | None | 0 | python 10, read 9, search 6, edit 1 |
| shared-tiers haiku B | ✓ | 29 | 22 | 1 | 0 | None | 5 | read 10, pmdb 8, search 5, python 4, skill 1, edit 1 |
| shared-tiers opus A | ✓ | 6 | 4 | 1 | 0 | None | 0 | shell 4, edit 1, python 1 |
| shared-tiers opus B | ✓ | 4 | None | 0 | 0 | None | 0 | shell 3, python 1 |
| shared-tiers sonnet A | ✓ | 21 | 14 | 1 | 0 | None | 0 | python 10, read 7, search 3, edit 1 |
| shared-tiers sonnet B | ✓ | 25 | 20 | 1 | 0 | None | 1 | search 8, read 6, python 4, pmdb 4, skill 1, edit 1, shell 1 |
| slow-planner haiku A | ✗ | 84 | 51 | 14 | 13 | None | 1 | read 33, python 28, edit 14, search 9 |
| slow-planner haiku B | ✗ | 57 | 54 | 1 | 0 | None | 9 | pmdb 37, read 14, search 2, skill 1, edit 1, python 1, shell 1 |
| slow-planner opus A | ✓ | 5 | 4 | 1 | 0 | None | 0 | shell 3, edit 1, python 1 |
| slow-planner opus B | ✓ | 9 | 8 | 1 | 0 | None | 0 | shell 3, pmdb 3, skill 1, edit 1, python 1 |
| slow-planner sonnet A | ✓ | 20 | 18 | 1 | 0 | None | 0 | read 12, python 6, search 1, edit 1 |
| slow-planner sonnet B | ✓ | 31 | 30 | 1 | 0 | None | 1 | read 10, pmdb 7, search 5, python 4, shell 3, skill 1, edit 1 |
