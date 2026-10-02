"""Prompts given to agents. Both arms share everything except `TOOLS`."""

TASK = """\
A user reported a problem with the Python program in /work. They ran

    python3 main.py {input}

and the output does not match what they expected. The expected output is in \
/work/expected_output.txt.

{tools}

Find the root cause of the problem and fix it with a minimal change to the source code. Do not \
modify {input} or expected_output.txt. When you are done, end your reply with a line of the form

RESULT: {{"file": "<file you fixed>", "function": "<function you fixed>", "cause": "<one sentence>"}}
"""

TOOLS = {
  "A": "Python 3 is installed, including pdb.",
  "B": "Python 3 is installed, including pdb. pmdb, a trace-query debugger, is also installed, "
       "with a skill describing how to use it, and a trace of the failing run has already been "
       "recorded to /work/report.pmdb.",
}

FEEDBACK = """\
The task is over, thank you. We are studying how debugging tools help with tasks like the one \
you just did, and would like your honest feedback about this session. There are no right answers; \
specific, critical feedback is the most useful.

Reply with only a JSON object (no code fence) with these fields:
- "approach": how you found the bug, in 2-4 sentences;
- "key_step": the single step or piece of information that revealed the bug;
- "wasted_effort": what took time without helping, or "" if nothing;
- "confidence": your confidence that your fix is correct, from 1 (low) to 5 (high);
- "used_pmdb": true if you ran pmdb or pmdb-record, false otherwise (false if it was not available);
- "pmdb_usefulness": from 1 (useless) to 5 (essential), or null if you did not use pmdb;
- "pmdb_problems": a list of concrete problems you had with pmdb or its documentation (confusing \
syntax, errors, missing or misleading documentation, surprising output), or [];
- "pmdb_wishes": a list of features or changes that would have made pmdb more useful here, or [];
- "other_wishes": a list of other tools or information that would have made this task faster, or [].
"""


def task(arm, input_name):
  return TASK.format(input=input_name, tools=TOOLS[arm])
