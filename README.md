# pmdbg

`pmdbg` is a language-agnostic "post-mortem" debugger.
It provides users with a holistic view of a program's behavior and lets them identify interesting events using queries rather than careful step-by-step forward execution.

Unlike a traditional live debugger, a post-mortem debugger operates on the traces of a program's execution, after that program has finished running.
This approach is related but different from [time-travel debugging](https://en.wikipedia.org/wiki/Time_travel_debugging), which extends traditional debugging with the ability to go back to a previous state.

## Description

In the context of this project, a trace is not a sequence of statements having been visited but rather a collection of *observations* about the program's execution.
These observations are structured into a tree whose nodes correspond to call frames.
That is, each child of a node is an observation that happened within the frame of the corresponding function.

`pmdbg` is a language-agnostic but it requires a way to instrument the program under study to generate a trace of its execution(s).
A library for instrumenting Python programs is currently available.

To illustrate, consider the following Python program:

```python
import pmdgb

@pmdgb.main.record
def factorial(n):
  return 1 if n < 2 else n * factorial(n - 1)

if __name__ == "__main__":
  n = pmdgb.main.run(factorial, 3)
  print(n)  # Prints 6

  with open("factorial.trace", "wb") as f:
    archive = pmdgb.main.serialize()
    f.write(archive.buffer)
```

The decorator on `factorial` indicates that calls to this function should be traced.
The call to `pmdgb.main.run` records the evaluation of `factorial(3)` in a trace that is then serialized and saved on disk.

The serialized trace contains the following tree:

```
pmdbg --show factorial.trace
* call root():
├─* call factorial(3):
│ ├─* call factorial(2):
│ │ ├─* call factorial(1):
│ │ └─* snap factorial.$result = 1
│ └─* snap factorial.$result = 2
└─* snap factorial.$result = 3
```

Queries:

```
select snap under:strict (factorial(%x) where %x > 2)
%0 = <x results>

show %0

select * under factorial(_)
%1 = <x results>

select call factorial(%x) where %x > 2
%2 = <x results>

select snap x from *
%3 = <x results>
select snap y after %3
```

Idea: debug a runtime system dealing with memory (e.g., mvs-calculus).