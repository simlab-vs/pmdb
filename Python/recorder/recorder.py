import functools
import inspect
import sys
import typing
import uuid

from .archive import Archive, describe
from .utilities import orelse


def encode(value) -> bytes:
  """Returns the serialization of `value` in its current state."""
  archive = Archive()
  archive.write_object(value)
  return bytes(archive.buffer)


class Observation(object):
  """A record of an event that occurred during the execution of a program."""

  def __init__(self, source_file: str, line_number: int):
    self.source_file = source_file
    self.line_number = line_number

  def serialize(self, archive):
    # The file and line number of the caller.
    archive.write_byte(self.tag())
    archive.write_string(self.source_file)
    archive.write_unsigned(self.line_number)

  @classmethod
  def tag(cls):
    """Returns a tag identifying the type of this observation."""
    raise NotImplementedError()


class Snapshot(Observation):
  """A record of an expression having been evaluated."""

  def __init__(
    self, source_file: str, line_number: int, label: typing.Optional[str], value: object
  ):
    super().__init__(source_file, line_number)
    self.label = label

    # Values are encoded right away because they might be mutated later.
    self.value = encode(value)

  def serialize(self, archive):
    super().serialize(archive)

    # Write the label, if any.
    if self.label is None:
      archive.write_byte(0)
    else:
      archive.write_byte(1)
      archive.write_string(self.label)

    # Write the value of the observation.
    archive.write_bytes(self.value)

  @classmethod
  def tag(cls):
    return 0x01


class Call(Observation):
  """A record of a function application."""

  def __init__(
    self, source_file: str, line_number: int, function: str, positional: list, named: dict
  ):
    super().__init__(source_file, line_number)
    self.function = function

    # Arguments are encoded right away because they might be mutated during the call.
    self.positional = [encode(a) for a in positional]
    self.named = {k: encode(a) for k, a in named.items()}

  def serialize(self, archive):
    super().serialize(archive)

    # Write the name of the callee.
    archive.write_string(self.function)

    # Write the number of arguments followed by their values.
    archive.write_unsigned(len(self.positional))
    for a in self.positional:
      archive.write_bytes(a)

    # Write the number of arguments followed by their values.
    archive.write_unsigned(len(self.named))
    for k, a in sorted(self.named.items()):
      archive.write_string(k)
      archive.write_bytes(a)

  @classmethod
  def tag(cls):
    return 0x02


class NamedCall(Call):
  """A record of a function application, with the names of the parameters receiving the
  positional arguments and the location of the function's definition."""

  def __init__(
    self, source_file: str, line_number: int, function: str, definition: tuple,
    positional: list, named: dict
  ):
    # `positional` is a list of pairs of a parameter name and an argument; an argument collected
    # by a parameter `*rest` is named `*rest`.
    super().__init__(source_file, line_number, function, [a for _, a in positional], named)
    self.names = [k for k, _ in positional]
    self.definition = definition

  def serialize(self, archive):
    archive.write_byte(self.tag())
    archive.write_string(self.source_file)
    archive.write_unsigned(self.line_number)
    archive.write_string(self.function)

    # Write where the function is defined.
    archive.write_string(self.definition[0])
    archive.write_unsigned(self.definition[1])

    # Write the number of positional arguments followed by their names and values.
    archive.write_unsigned(len(self.positional))
    for k, a in zip(self.names, self.positional):
      archive.write_string(k)
      archive.write_bytes(a)

    # Write the number of named arguments followed by their names and values.
    archive.write_unsigned(len(self.named))
    for k, a in sorted(self.named.items()):
      archive.write_string(k)
      archive.write_bytes(a)

  @classmethod
  def tag(cls):
    return 0x04


class Outcome(Observation):
  """A record of the value a call returned or the exception it raised, which refers to the call
  explicitly (unlike a snap labeled `<function>.$result`), so that it needn't follow the call
  immediately (e.g., for a generator suspended in between)."""

  def __init__(self, source_file: str, line_number: int, call: int, raised: bool, value: object):
    super().__init__(source_file, line_number)
    self.call = call
    self.raised = raised
    self.value = encode(value)

  def serialize(self, archive):
    super().serialize(archive)
    archive.write_unsigned(self.call)
    archive.write_byte(int(self.raised))
    archive.write_bytes(self.value)

  @classmethod
  def tag(cls):
    return 0x03


def write_trace(identifier, observations, parents, archive=None):
  """Returns `archive` (or a new archive) after writing the trace of `observations`, where the
  parent of the `i`-th observation is the `parents[i]`-th."""
  a = orelse(archive, Archive)

  # Write the trace header, which is a magic number followed by a version number.
  a.write_bytes(b"pmdb")
  a.write_byte(1)
  a.write_byte(0)

  # Write the identifier of the trace.
  a.write_bytes(identifier.bytes)

  # Write the number of observations followed by their values.
  a.write_unsigned(len(observations))
  for o in observations:
    a.write(o)

  # Write the mapping from each observation to its parent.
  for p in parents:
    a.write_unsigned(p)
  return a


class Driven(object):
  """An awaitable running a generator, as `Recorder.drive` returns."""

  def __init__(self, generator):
    self.generator = generator

  def __await__(self):
    return self.generator


class Recorder(object):
  """Instrumentation for tracing the execution of a Python program."""

  def __init__(self, root=None, identifier=None):
    """Creates a new instance."""
    self.identifier = orelse(identifier, uuid.uuid4)
    self.observations = [orelse(root, Recorder.root)]
    self.parent = [0]
    self.active = 0

    # The number of observations being created. Calls made while values are encoded (e.g., to
    # `__repr__`, `__pmdb__`, or a property read by `isinstance`) aren't recorded, since recording
    # them would encode the same values again.
    self.encoding = 0

  def record(self, f):
    """Decorates `f` so that each of its calls is recorded in `self`.

    The decorated function is of the same kind as `f`. The call of a generator function or of a
    coroutine function is recorded when it starts running, with the value it returns or the
    exception it raises as its outcome; calls made while it is suspended aren't nested in it.
    Asynchronous generator functions are returned undecorated.
    """
    if inspect.isasyncgenfunction(f):
      return f

    if inspect.isgeneratorfunction(f):
      @functools.wraps(f)
      def generator(*args, **kwargs):
        if self.encoding:
          return (yield from f(*args, **kwargs))
        return (yield from self.drive(f, args, kwargs, lambda g: g))
      return generator

    if inspect.iscoroutinefunction(f):
      @functools.wraps(f)
      async def coroutine(*args, **kwargs):
        if self.encoding:
          return await f(*args, **kwargs)
        return await Driven(self.drive(f, args, kwargs, lambda c: c.__await__()))
      return coroutine

    @functools.wraps(f)
    def decorated(*args, **kwargs):
      if self.encoding:
        return f(*args, **kwargs)
      caller = Recorder.caller()
      call = self.enter(caller, f, args, kwargs)
      try:
        result = f(*args, **kwargs)
      except BaseException as e:
        self.leave(caller, call, raised=e)
        raise
      self.leave(caller, call, returned=result)
      return result

    return decorated

  def enter(self, caller, f, args, kwargs):
    """Records the start of a call to `f` made at the frame `caller` and makes it the active
    observation, returning the name under which it is recorded."""
    callee = f.__qualname__
    call = self.encoded(Call, caller.f_code.co_filename, caller.f_lineno, callee, args, kwargs)
    self.step_into(call)
    return callee

  def leave(self, caller, callee, **outcome):
    """Records the outcome of the active call to `callee`, made at the frame `caller`: the value
    it `returned`, or the exception it `raised`."""
    if "raised" in outcome:
      e = outcome["raised"]
      value = self.encoded(lambda: {"type": type(e).__qualname__, "message": describe(e, str)})
      label = callee + ".$exception"
    else:
      value, label = outcome["returned"], callee + ".$result"
    self.step_out(
      self.encoded(Snapshot, caller.f_code.co_filename, caller.f_lineno, label, value))

  def drive(self, f, args, kwargs, iterator):
    """Runs the generator `iterator(f(*args, **kwargs))`, recording the call to `f`, and returns
    its value.

    The call is the active observation while the generator runs, and its parent while it is
    suspended, so that calls made by the generator's consumer aren't nested in it.
    """
    caller = Recorder.caller()
    callee = self.enter(caller, f, args, kwargs)
    index = self.active
    parent = self.parent[index]
    try:
      g = iterator(f(*args, **kwargs))
    except BaseException as e:
      self.leave(caller, callee, raised=e)
      raise
    send, value = True, None
    while True:
      self.active = index
      try:
        item = g.send(value) if send else g.throw(value)
      except StopIteration as stop:
        self.leave(caller, callee, returned=stop.value)
        return stop.value
      except BaseException as e:
        self.leave(caller, callee, raised=e)
        raise
      self.active = parent
      try:
        send, value = True, (yield item)
      except GeneratorExit:
        g.close()
        raise
      except BaseException as e:
        send, value = False, e

  def snapshot(self, label, value):
    caller = Recorder.caller()
    self.observe(self.encoded(Snapshot, caller.f_code.co_filename, caller.f_lineno, label, value))

  def encoded(self, make, *args):
    """Returns `make(*args)`, which encodes values, without recording the calls it makes."""
    self.encoding += 1
    try:
      return make(*args)
    finally:
      self.encoding -= 1

  def run(self, f, *args, **kwargs):
    return f(*args, **kwargs)

  def observe(self, snap: Snapshot):
    self.observations.append(snap)
    self.parent.append(self.active)

  def step_into(self, call: Call):
    self.observations.append(call)
    self.parent.append(self.active)
    self.active = len(self.observations) - 1

  def step_out(self, result: Snapshot):
    assert self.active != 0, "cannot pop the root"
    self.active = self.parent[self.active]
    self.observe(result)

  def serialize(self, archive=None):
    return write_trace(self.identifier, self.observations, self.parent, archive)

  @staticmethod
  def caller():
    """Returns the innermost frame outside of this script."""
    # `sys._getframe` is used rather than `inspect.stack`, which builds descriptions of all frames
    # in the stack and reads their source, making each recorded call cost O(depth).
    frame = sys._getframe(1)
    while frame.f_code.co_filename == __file__:
      frame = frame.f_back
    return frame

  @staticmethod
  def root():
    frame = sys._getframe(0)
    while frame.f_back is not None:
      frame = frame.f_back
    return Call(frame.f_code.co_filename, frame.f_lineno, "root", [], {})
