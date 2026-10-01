# pmdb

`pmdb` is a "post-mortem" debugger: instead of stepping through a running program, you record a trace of the program's execution and then query that trace.

## Recording a trace

```
pmdb-record -o trace.pmdb main.py input.json
```

`pmdb-record` runs a Python script and records every call to the functions and methods defined in the Python files of the script's directory, without modifying those files.
The trace is written when the program exits, even if it raises an exception.

A trace is a tree of *observations*:

- a **call** records a call to a function, with the values of its arguments when the call started and the location of the call site;
- a **snap** records a value with a label. Each call is followed by a snap labeled `<function>.$result` holding its return value, or `<function>.$exception` holding a table with the `type` and `message` of the exception it raised.

The children of a call are the observations that happened during that call.
`None` is recorded as `none`, lists and tuples as arrays, dictionaries with string keys as tables, and other objects are shown as `<object>`.

## Running pmdb

```
pmdb --show trace.pmdb                      # print the whole trace as a tree
pmdb trace.pmdb -e 'select f(x) where x > 1' -e 'show $0'
pmdb trace.pmdb                             # interactive session (reads commands from standard input)
```

Commands:

- `select <query>` runs a query (described below) and assigns its result to the next variable `$0`, `$1`, ...;
- `show $N` prints the observations in `$N` with an excerpt of the source code around each of them;
- `show variables` lists the variables that have been defined;
- `load <path> as $name` loads another trace;
- `exit` ends the session.

With `-e`, `pmdb` runs the given commands in order and exits; each query also lists the observations it selects.
It stops at the first command that fails.

