# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | steps | read | search | test | python | pdb | pmdb | skill | edit | shell | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 10 | 9/10 | 20.0 | 8.0 | 4.0 | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 14 | 1.0 | 0.0 | 4 | 2.0 |
| haiku | B | 10 | 10/10 | 27.0 | 6.0 | 6.0 | 6.0 | 0.0 | 0.0 | 4.5 | 1.0 | 2.0 | 0.0 | 12.5 | 2.0 | 0.0 | 5 | 3.5 |
| opus | A | 10 | 10/10 | 5.5 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 4.5 | 1.0 | 0.0 | 0.0 | 0.0 |
| opus | B | 10 | 10/10 | 5.5 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.5 | 4.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| sonnet | A | 10 | 10/10 | 15.0 | 3.0 | 5.5 | 3.5 | 0.5 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 11.0 | 1.0 | 0.0 | 1.0 | 0.5 |
| sonnet | B | 10 | 10/10 | 18.0 | 3.5 | 4.5 | 3.5 | 0.0 | 0.0 | 0.0 | 0.5 | 1.0 | 0.0 | 14.0 | 1.0 | 0.0 | 1.0 | 0.0 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| ex01-beets-d91df40-hard haiku A | ✓ | 29 | 15 | 5 | 4 | 9 | 4 | read 10, test 7, search 6, edit 5, shell 1 |
| ex01-beets-d91df40-hard haiku B | ✓ | 38 | 8 | 2 | 0 | 7 | 3 | read 14, search 12, test 6, pmdb 2, edit 2, skill 1, shell 1 |
| ex01-beets-d91df40-hard opus A | ✓ | 10 | None | 0 | 0 | None | 0 | read 4, test 3, search 2, shell 1 |
| ex01-beets-d91df40-hard opus B | ✓ | 13 | None | 0 | 0 | None | 0 | shell 6, test 4, read 2, python 1 |
| ex01-beets-d91df40-hard sonnet A | ✓ | 16 | 13 | 2 | 1 | 1 | 1 | search 7, test 4, read 3, edit 2 |
| ex01-beets-d91df40-hard sonnet B | ✓ | 29 | 26 | 2 | 1 | 1 | 0 | search 8, pmdb 8, read 7, test 3, edit 2, skill 1 |
| ex02-click-3bb230d-easy haiku A | ✓ | 17 | 14 | 1 | 0 | 2 | 2 | python 5, search 4, test 4, read 3, edit 1 |
| ex02-click-3bb230d-easy haiku B | ✓ | 28 | 23 | 1 | 0 | 4 | 5 | pmdb 9, test 7, search 5, read 5, skill 1, edit 1 |
| ex02-click-3bb230d-easy opus A | ✓ | 5 | 4 | 1 | 0 | 0 | 0 | test 2, shell 2, edit 1 |
| ex02-click-3bb230d-easy opus B | ✓ | 6 | 4 | 1 | 0 | 1 | 0 | shell 3, test 2, edit 1 |
| ex02-click-3bb230d-easy sonnet A | ✓ | 12 | 10 | 1 | 0 | 1 | 0 | search 5, test 3, read 2, python 1, edit 1 |
| ex02-click-3bb230d-easy sonnet B | ✓ | 16 | 14 | 1 | 0 | 1 | 0 | search 4, read 4, test 3, python 3, shell 1, edit 1 |
| ex03-pipx-d94a615-easy haiku A | ✗ | 60 | None | 0 | 0 | None | 8 | search 19, read 17, python 14, test 10 |
| ex03-pipx-d94a615-easy haiku B | ✓ | 27 | 9 | 1 | 0 | None | 2 | search 7, test 6, read 5, pmdb 4, python 3, skill 1, edit 1 |
| ex03-pipx-d94a615-easy opus A | ✓ | 11 | 5 | 1 | 0 | 0 | 1 | test 5, shell 5, edit 1 |
| ex03-pipx-d94a615-easy opus B | ✓ | 5 | 4 | 1 | 0 | 0 | 0 | shell 2, test 2, edit 1 |
| ex03-pipx-d94a615-easy sonnet A | ✓ | 45 | 43 | 1 | 0 | 1 | 3 | test 14, python 10, read 9, search 8, pdb 2, shell 1, edit 1 |
| ex03-pipx-d94a615-easy sonnet B | ✓ | 30 | 14 | 1 | 0 | 1 | 0 | test 9, search 7, read 4, shell 4, pmdb 3, skill 1, edit 1, python 1 |
| ex04-semantica-749b177-easy haiku A | ✓ | 9 | 6 | 1 | 0 | 2 | 1 | test 4, read 3, search 1, edit 1 |
| ex04-semantica-749b177-easy haiku B | ✓ | 17 | 11 | 2 | 1 | 5 | 2 | pmdb 5, read 4, test 4, edit 2, search 1, skill 1 |
| ex04-semantica-749b177-easy opus A | ✓ | 5 | 4 | 1 | 0 | 0 | 0 | test 2, shell 2, edit 1 |
| ex04-semantica-749b177-easy opus B | ✓ | 5 | 4 | 1 | 0 | 0 | 0 | test 2, shell 2, edit 1 |
| ex04-semantica-749b177-easy sonnet A | ✓ | 8 | 6 | 1 | 0 | 1 | 0 | test 3, read 3, search 1, edit 1 |
| ex04-semantica-749b177-easy sonnet B | ✓ | 9 | 7 | 1 | 0 | 1 | 0 | read 3, test 3, search 2, edit 1 |
| ex05-seaborn-886c4a2-easy haiku A | ✓ | 34 | 23 | 1 | 0 | 10 | 3 | read 15, search 10, test 7, edit 1, shell 1 |
| ex05-seaborn-886c4a2-easy haiku B | ✓ | 44 | 33 | 1 | 0 | 10 | 5 | read 15, pmdb 12, test 9, search 6, skill 1, edit 1 |
| ex05-seaborn-886c4a2-easy opus A | ✓ | 14 | 11 | 1 | 0 | None | 0 | search 3, read 3, shell 3, test 2, python 2, edit 1 |
| ex05-seaborn-886c4a2-easy opus B | ✓ | 20 | 15 | 1 | 0 | 3 | 0 | shell 9, test 3, search 2, read 2, skill 1, pmdb 1, python 1, edit 1 |
| ex05-seaborn-886c4a2-easy sonnet A | ✓ | 43 | 29 | 2 | 1 | 8 | 2 | search 11, read 11, python 10, shell 5, test 4, edit 2 |
| ex05-seaborn-886c4a2-easy sonnet B | ✓ | 34 | 18 | 1 | 0 | 15 | 1 | read 11, test 8, search 8, shell 6, edit 1 |
| ex06-needle-c11ccba-easy haiku A | ✓ | 14 | 8 | 2 | 1 | 5 | 2 | test 5, read 4, search 3, edit 2 |
| ex06-needle-c11ccba-easy haiku B | ✓ | 25 | 16 | 2 | 1 | 8 | 3 | search 7, test 6, read 4, pmdb 4, edit 2, skill 1, python 1 |
| ex06-needle-c11ccba-easy opus A | ✓ | 6 | 5 | 1 | 0 | 0 | 0 | shell 3, test 2, edit 1 |
| ex06-needle-c11ccba-easy opus B | ✓ | 6 | 5 | 1 | 0 | 0 | 0 | shell 3, test 2, edit 1 |
| ex06-needle-c11ccba-easy sonnet A | ✓ | 17 | 8 | 2 | 1 | 8 | 1 | test 7, search 5, read 2, edit 2, python 1 |
| ex06-needle-c11ccba-easy sonnet B | ✓ | 18 | 14 | 1 | 0 | 3 | 1 | search 10, test 5, read 2, edit 1 |
| ex07-Gymnasium-5b2b0e5-easy haiku A | ✓ | 15 | 7 | 2 | 1 | 5 | 2 | test 7, search 3, read 3, edit 2 |
| ex07-Gymnasium-5b2b0e5-easy haiku B | ✓ | 21 | 13 | 2 | 1 | 5 | 2 | test 7, pmdb 6, read 3, search 2, edit 2, skill 1 |
| ex07-Gymnasium-5b2b0e5-easy opus A | ✓ | 4 | 3 | 1 | 0 | 0 | 0 | test 2, shell 1, edit 1 |
| ex07-Gymnasium-5b2b0e5-easy opus B | ✓ | 3 | 2 | 1 | 0 | 0 | 0 | shell 1, edit 1, test 1 |
| ex07-Gymnasium-5b2b0e5-easy sonnet A | ✓ | 9 | 7 | 1 | 0 | 1 | 0 | test 3, search 3, read 2, edit 1 |
| ex07-Gymnasium-5b2b0e5-easy sonnet B | ✓ | 10 | 7 | 1 | 0 | 2 | 0 | test 4, read 3, skill 1, search 1, edit 1 |
| ex08-beets-96b2b9d-easy haiku A | ✓ | 19 | 14 | 1 | 0 | 4 | 1 | read 7, test 6, search 4, python 1, edit 1 |
| ex08-beets-96b2b9d-easy haiku B | ✓ | 23 | 8 | 2 | 0 | 5 | 4 | read 7, test 5, search 4, pmdb 3, edit 2, skill 1, shell 1 |
| ex08-beets-96b2b9d-easy opus A | ✓ | 3 | None | 0 | 0 | None | 0 | test 2, shell 1 |
| ex08-beets-96b2b9d-easy opus B | ✓ | 5 | None | 0 | 0 | None | 0 | read 3, test 2 |
| ex08-beets-96b2b9d-easy sonnet A | ✓ | 14 | 12 | 1 | 0 | 1 | 0 | search 6, read 4, test 3, edit 1 |
| ex08-beets-96b2b9d-easy sonnet B | ✓ | 18 | 16 | 1 | 0 | 1 | 2 | search 5, pmdb 5, test 3, read 3, skill 1, edit 1 |
| ex09-click-fc5c7f4-easy haiku A | ✓ | 22 | 18 | 1 | 0 | 3 | 1 | read 11, search 6, test 4, edit 1 |
| ex09-click-fc5c7f4-easy haiku B | ✓ | 27 | 23 | 1 | 0 | 3 | 5 | search 9, read 8, test 4, pmdb 3, skill 1, python 1, edit 1 |
| ex09-click-fc5c7f4-easy opus A | ✓ | 4 | 3 | 1 | 0 | 0 | 0 | test 2, shell 1, edit 1 |
| ex09-click-fc5c7f4-easy opus B | ✓ | 4 | 3 | 1 | 0 | 0 | 0 | test 2, read 1, edit 1 |
| ex09-click-fc5c7f4-easy sonnet A | ✓ | 6 | 4 | 1 | 0 | 1 | 0 | test 3, search 1, read 1, edit 1 |
| ex09-click-fc5c7f4-easy sonnet B | ✓ | 7 | 5 | 1 | 0 | 1 | 0 | test 3, read 2, search 1, edit 1 |
| ex10-pipx-84eaad3-easy haiku A | ✓ | 21 | 12 | 1 | 0 | 3 | 0 | read 9, test 5, search 3, shell 2, edit 1, python 1 |
| ex10-pipx-84eaad3-easy haiku B | ✓ | 48 | 12 | 3 | 1 | 8 | 4 | read 13, pmdb 11, test 11, search 6, edit 3, shell 2, skill 1, python 1 |
| ex10-pipx-84eaad3-easy opus A | ✓ | 17 | 13 | 1 | 0 | None | 1 | shell 7, test 5, python 3, search 1, edit 1 |
| ex10-pipx-84eaad3-easy opus B | ✓ | 10 | 9 | 1 | 0 | 0 | 0 | shell 5, test 2, skill 1, pmdb 1, edit 1 |
| ex10-pipx-84eaad3-easy sonnet A | ✓ | 36 | 32 | 2 | 1 | 2 | 2 | test 11, search 10, read 9, shell 3, edit 2, python 1 |
| ex10-pipx-84eaad3-easy sonnet B | ✓ | 18 | 11 | 1 | 0 | 0 | 1 | read 5, test 4, pmdb 3, shell 3, skill 1, search 1, edit 1 |
