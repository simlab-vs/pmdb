# How agents worked, by model and arm

Medians per run, from `harness/behaviour.py`. Steps are tool calls. "After solved" counts the steps after the first test run, following an edit, in which the tests passed.

| model | arm | runs | success | wrote tests | steps | read | search | test | python | pdb | record | pmdb | skill | edit | shell | first test run | first record | first edit | edits | rework | after solved | failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | A | 9 | 4/9 | 9 | 37 | 10 | 6 | 9 | 6 | 0 | 0 | 0 | 0 | 3 | 1 | 24 | None | 12 | 3 | 1 | 19 | 2 |
| haiku | B | 9 | 5/9 | 7 | 48 | 9 | 6 | 6 | 6 | 0 | 0 | 0 | 0 | 6 | 2 | 25 | 34 | 8 | 6 | 2 | 14 | 2 |
| opus | A | 9 | 4/9 | 9 | 11 | 3 | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 0 | 9 | None | 6.0 | 2 | 0 | 0.5 | 0 |
| opus | B | 9 | 4/9 | 9 | 12 | 3 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 0 | 8 | None | 7.0 | 2 | 0 | 0.0 | 0 |
| sonnet | A | 9 | 4/9 | 9 | 47 | 12 | 11 | 5 | 3 | 0 | 0 | 0 | 0 | 5 | 0 | 13 | None | 16 | 5 | 2 | 6 | 1 |
| sonnet | B | 9 | 4/9 | 9 | 26 | 8 | 5 | 3 | 1 | 0 | 0 | 0 | 0 | 5 | 0 | 20 | None | 12 | 5 | 2 | 5 | 1 |

## Runs

| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |
|---|---|---|---|---|---|---|---|---|
| ex01-semantica-749b177-hard haiku A | ✗ | 37 | 12 | 5 | 2 | 19 | 2 | read 10, test 9, search 6, python 6, edit 5, shell 1 |
| ex01-semantica-749b177-hard haiku B | ✗ | 25 | 7 | 8 | 2 | 9 | 1 | edit 8, test 6, python 5, read 4, search 1, shell 1 |
| ex01-semantica-749b177-hard opus A | ✗ | 10 | 6 | 1 | 0 | None | 0 | shell 5, python 2, test 2, edit 1 |
| ex01-semantica-749b177-hard opus B | ✗ | 11 | 7 | 1 | 0 | None | 1 | read 3, python 3, test 3, shell 1, edit 1 |
| ex01-semantica-749b177-hard sonnet A | ✗ | 63 | 27 | 9 | 5 | 12 | 2 | read 16, test 14, search 11, edit 9, shell 9, python 4 |
| ex01-semantica-749b177-hard sonnet B | ✗ | 26 | 10 | 5 | 3 | 12 | 1 | test 9, read 8, edit 5, search 2, python 1, shell 1 |
| ex02-beets-ad758c1-hard haiku A | ✗ | 20 | 10 | 3 | 1 | 6 | 0 | search 6, read 5, test 4, edit 3, python 2 |
| ex02-beets-ad758c1-hard haiku B | ✗ | 18 | 6 | 6 | 4 | 6 | 2 | edit 6, test 5, read 4, search 2, shell 1 |
| ex02-beets-ad758c1-hard opus A | ✗ | 11 | 7 | 1 | 0 | 1 | 0 | read 4, search 4, test 2, edit 1 |
| ex02-beets-ad758c1-hard opus B | ✗ | 25 | 18 | 2 | 0 | 2 | 0 | read 10, search 9, test 3, edit 2, python 1 |
| ex02-beets-ad758c1-hard sonnet A | ✗ | 73 | 50 | 8 | 5 | 16 | 5 | read 26, search 25, python 9, edit 8, test 5 |
| ex02-beets-ad758c1-hard sonnet B | ✗ | 80 | 63 | 6 | 1 | 16 | 4 | read 26, search 25, python 15, edit 6, test 5, shell 2, skill 1 |
| ex03-beets-d91df40-hard haiku A | ✓ | 80 | 28 | 7 | 4 | 40 | 10 | read 36, search 24, test 9, edit 7, shell 2, python 2 |
| ex03-beets-d91df40-hard haiku B | ✓ | 71 | 29 | 13 | 11 | 34 | 1 | read 21, search 20, test 14, edit 13, shell 3 |
| ex03-beets-d91df40-hard opus A | ✓ | 14 | None | 0 | 0 | None | 0 | test 4, search 3, read 3, shell 3, python 1 |
| ex03-beets-d91df40-hard opus B | ✓ | 16 | None | 0 | 0 | None | 0 | test 8, read 4, search 3, python 1 |
| ex03-beets-d91df40-hard sonnet A | ✓ | 60 | 16 | 6 | 3 | 7 | 2 | search 27, read 20, edit 6, test 5, shell 1, python 1 |
| ex03-beets-d91df40-hard sonnet B | ✓ | 50 | 19 | 4 | 2 | 5 | 1 | search 29, read 10, test 5, edit 4, shell 1, python 1 |
| ex04-click-0cd28d6-easy haiku A | ✗ | 54 | 25 | 3 | 0 | 24 | 5 | python 17, search 14, read 12, test 7, edit 3, shell 1 |
| ex04-click-0cd28d6-easy haiku B | ✓ | 61 | 4 | 7 | 2 | 9 | 8 | python 25, search 13, read 10, edit 7, test 4, shell 2 |
| ex04-click-0cd28d6-easy opus A | ✗ | 8 | 4 | 3 | 1 | 2 | 0 | edit 3, read 2, test 2, search 1 |
| ex04-click-0cd28d6-easy opus B | ✗ | 7 | 4 | 3 | 1 | 1 | 0 | edit 3, read 2, search 1, test 1 |
| ex04-click-0cd28d6-easy sonnet A | ✗ | 16 | 6 | 4 | 1 | 5 | 1 | edit 4, test 4, search 3, read 3, python 2 |
| ex04-click-0cd28d6-easy sonnet B | ✗ | 17 | 6 | 4 | 1 | 6 | 0 | search 4, read 4, edit 4, test 3, python 2 |
| ex05-seaborn-886c4a2-easy haiku A | ✓ | 73 | 38 | 2 | 0 | 25 | 4 | python 29, read 16, search 14, test 10, edit 2, shell 2 |
| ex05-seaborn-886c4a2-easy haiku B | ✓ | 68 | 33 | 3 | 0 | 15 | 7 | python 22, search 15, read 9, pmdb 6, test 6, shell 5, edit 3, skill 1, record 1 |
| ex05-seaborn-886c4a2-easy opus A | ✓ | 13 | 8 | 2 | 0 | 4 | 0 | search 4, read 3, python 2, edit 2, test 2 |
| ex05-seaborn-886c4a2-easy opus B | ✓ | 17 | 12 | 2 | 0 | 0 | 0 | search 5, python 5, read 4, edit 2, test 1 |
| ex05-seaborn-886c4a2-easy sonnet A | ✓ | 49 | 29 | 2 | 0 | 16 | 3 | read 15, search 13, python 9, test 5, shell 5, edit 2 |
| ex05-seaborn-886c4a2-easy sonnet B | ✓ | 59 | 18 | 5 | 2 | 6 | 4 | read 16, search 15, python 14, shell 6, edit 5, test 3 |
| ex06-semantica-2173308-easy haiku A | ✗ | 32 | 16 | 4 | 3 | 7 | 1 | search 10, read 9, python 6, edit 4, test 3 |
| ex06-semantica-2173308-easy haiku B | ✗ | 76 | 45 | 4 | 1 | 26 | 3 | search 24, read 20, python 18, test 6, edit 4, shell 3, skill 1 |
| ex06-semantica-2173308-easy opus A | ✗ | 14 | 10 | 4 | 2 | 0 | 0 | search 5, edit 4, read 2, shell 1, python 1, test 1 |
| ex06-semantica-2173308-easy opus B | ✗ | 14 | 11 | 2 | 1 | None | 0 | shell 5, search 3, read 2, edit 2, python 1, test 1 |
| ex06-semantica-2173308-easy sonnet A | ✗ | 47 | 27 | 7 | 3 | 5 | 0 | search 16, read 12, python 7, edit 7, test 4, shell 1 |
| ex06-semantica-2173308-easy sonnet B | ✗ | 24 | 14 | 5 | 3 | 4 | 0 | read 8, search 5, edit 5, python 3, test 3 |
| ex07-camel-ba68902-easy haiku A | ✓ | 10 | 4 | 2 | 0 | 1 | 0 | read 4, search 3, edit 2, test 1 |
| ex07-camel-ba68902-easy haiku B | ✓ | 11 | 6 | 3 | 1 | 2 | 0 | search 3, read 3, edit 3, test 2 |
| ex07-camel-ba68902-easy opus A | ✓ | 8 | 4 | 2 | 0 | 0 | 0 | read 3, search 2, edit 2, test 1 |
| ex07-camel-ba68902-easy opus B | ✓ | 8 | 4 | 2 | 0 | 0 | 0 | read 3, search 2, edit 2, test 1 |
| ex07-camel-ba68902-easy sonnet A | ✓ | 7 | 3 | 2 | 0 | 0 | 0 | search 2, read 2, edit 2, test 1 |
| ex07-camel-ba68902-easy sonnet B | ✓ | 9 | 5 | 2 | 0 | 3 | 0 | search 3, read 2, edit 2, test 2 |
| ex08-click-fc5c7f4-easy haiku A | ✓ | 55 | 10 | 4 | 2 | 27 | 4 | python 19, test 13, read 11, search 4, shell 4, edit 4 |
| ex08-click-fc5c7f4-easy haiku B | ✓ | 48 | 8 | 8 | 2 | 18 | 3 | read 11, test 10, python 9, edit 8, search 6, shell 4 |
| ex08-click-fc5c7f4-easy opus A | ✓ | 11 | 6 | 2 | 0 | None | 0 | read 4, python 3, edit 2, search 1, test 1 |
| ex08-click-fc5c7f4-easy opus B | ✓ | 12 | 7 | 3 | 1 | 0 | 0 | test 4, read 3, edit 3, search 1, python 1 |
| ex08-click-fc5c7f4-easy sonnet A | ✓ | 27 | 16 | 5 | 2 | 6 | 0 | read 9, search 5, test 5, edit 5, python 3 |
| ex08-click-fc5c7f4-easy sonnet B | ✓ | 27 | 12 | 5 | 3 | 5 | 1 | read 11, search 5, edit 5, test 5, python 1 |
| ex09-camel-f380bdf-easy haiku A | ✗ | 31 | 9 | 3 | 1 | 19 | 0 | test 12, read 8, search 5, edit 3, shell 2, python 1 |
| ex09-camel-f380bdf-easy haiku B | ✗ | 27 | 11 | 3 | 1 | 14 | 0 | read 9, python 6, test 6, search 3, edit 3 |
| ex09-camel-f380bdf-easy opus A | ✗ | 7 | 4 | 2 | 0 | 0 | 0 | search 2, read 2, edit 2, test 1 |
| ex09-camel-f380bdf-easy opus B | ✗ | 7 | 4 | 2 | 0 | 0 | 0 | search 2, read 2, edit 2, test 1 |
| ex09-camel-f380bdf-easy sonnet A | ✗ | 9 | 4 | 2 | 0 | 0 | 0 | search 3, read 3, edit 2, test 1 |
| ex09-camel-f380bdf-easy sonnet B | ✗ | 8 | 3 | 2 | 0 | 0 | 0 | search 3, read 2, edit 2, test 1 |
