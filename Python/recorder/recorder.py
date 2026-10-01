import inspect
import sys
import typing
import uuid

from .archive import Archive
from .utilities import first_where, orelse


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
    self.value = value

  def serialize(self, archive):
    super().serialize(archive)

    # Write the label, if any.
    if self.label is None:
      archive.write_byte(0)
    else:
      archive.write_byte(1)
      archive.write_string(self.label)

    # Write the value of the observation.
    archive.write_object(self.value)

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
    self.positional = positional
    self.named = named

  def serialize(self, archive):
    super().serialize(archive)

    # Write the name of the callee.
    archive.write_string(self.function)

    # Write the number of arguments followed by their values.
    archive.write_unsigned(len(self.positional))
    for a in self.positional:
      archive.write_object(a)

    # Write the number of arguments followed by their values.
    archive.write_unsigned(len(self.named))
    for k, a in sorted(self.named.items()):
      archive.write_string(k)
      archive.write_object(a)

  @classmethod
  def tag(cls):
    return 0x02


class Recorder(object):
  """Instrumentation for tracing the execution of a Python program."""

  def __init__(self, root=None, identifier=None):
    """Creates a new instance."""
    self.identifier = orelse(identifier, uuid.uuid4)
    self.observations = [orelse(root, Recorder.root)]
    self.parent = [0]
    self.active = 0

  def record(self, f):
    """Decorates `f` so that each of its calls is recorded in `self`."""
    def decorated(*args, **kwargs):
      # Get to the first frame outside of this script.
      caller = first_where(inspect.stack(), lambda f: f.filename != __file__)
      callee = f.__qualname__

      # Attach a new call observation to the current trace node.
      call = Call(caller.filename, caller.lineno, callee, args, kwargs)
      self.step_into(call)

      # Apply the decorated function, getting back to the original trace node if it raises.
      try:
        result = f(*args, **kwargs)
      except BaseException:
        self.active = self.parent[self.active]
        raise

      # Get back to the original trace node.
      snap = Snapshot(caller.filename, caller.lineno, callee + ".$result", result)
      self.step_out(snap)
      return result

    return decorated

  def snapshot(self, label, value):
    caller = first_where(inspect.stack(), lambda f: f.filename != __file__)
    self.observe(Snapshot(caller.filename, caller.lineno, label, value))

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
    a = orelse(archive, Archive)

    # Write the trace header, which is a magic number followed by a version number.
    for b in "pmdb":
      a.write_byte(ord(b))
    a.write_byte(1)
    a.write_byte(0)

    # Write the identifier of the trace.
    for b in self.identifier.bytes:
      a.write_byte(b)

    # Write the number of observations followed by their values.
    a.write_unsigned(len(self.observations))
    for o in self.observations:
      a.write(o)

    # Write the mapping from each observation to its parent.
    for p in self.parent:
      a.write_unsigned(p)
    return a

  @staticmethod
  def root():
    caller = inspect.stack()[-1]
    return Call(caller.filename, caller.lineno, "root", [], {})
