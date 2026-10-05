"""The sandbox of round 5: no network, except a relay to the Claude API for Claude Code.

Every command runs in the bubblewrap sandbox of `pmdbbench.sandbox` without its `--share-net`, so
the sandbox has its own network namespace with only a loopback interface. Claude Code reaches the
API through a relay:
- on the host, `socat UNIX-LISTEN:<root>/api.sock,fork TCP:api.anthropic.com:443` (one per run,
  started before and terminated after it, by `relay`);
- the socket is bound into the sandbox at `/run/api.sock`;
- in the sandbox, `socat TCP-LISTEN:8443,bind=127.0.0.1,fork UNIX-CONNECT:/run/api.sock` is started
  before the command, `/etc/hosts` maps `api.anthropic.com` to 127.0.0.1, and Claude Code is
  given `ANTHROPIC_BASE_URL=https://api.anthropic.com:8443`, so TLS still verifies the API's
  certificate end to end.
Commands that don't need the API (the harness's test runs and recordings) run without the relay.
stdin is /dev/null.
"""

import contextlib
import os
import shutil
import subprocess
import time
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
from pmdbbench import sandbox

SOCAT = os.path.realpath(shutil.which("socat"))
SOCKET_NAME = "api.sock"
SOCKET_IN_SANDBOX = "/run/api.sock"
PORT = 8443
API_HOST = "api.anthropic.com"
BASE_URL = f"https://{API_HOST}:{PORT}"
HOSTS = f"127.0.0.1 localhost {API_HOST}\n::1 localhost\n"

# Started in the sandbox before the command: the inner end of the relay (its log discarded, so
# that it doesn't mix with the transcript), then a wait until it listens (port 8443 is 20FB in /proc/net/tcp), then the command itself.
INNER = (f"{SOCAT} TCP-LISTEN:{PORT},bind=127.0.0.1,reuseaddr,fork "
         f"UNIX-CONNECT:{SOCKET_IN_SANDBOX} </dev/null >/dev/null 2>&1 & "
         "for i in $(seq 100); do grep -q ':20FB ' /proc/net/tcp && break; sleep 0.05; done; "
         'exec "$@"')


def prepare_etc(root):
  """Writes the sandbox's minimal /etc into `root / "etc"`, with the API mapped to the loopback."""
  etc = sandbox.prepare_etc(Path(root))
  (etc / "hosts").write_text(HOSTS)
  return etc


def command(root, argv, opt=None, env=None, binds=(), api=False):
  """Returns the bwrap command line running `argv` in the sandbox rooted at `root`, without
  network. `binds` are extra `(source, destination)` read-only binds. With `api`, the command can
  reach the Claude API through the relay, which `relay(root)` must be running."""
  root = Path(root)
  environment = dict(env or {})
  if api:
    environment["ANTHROPIC_BASE_URL"] = BASE_URL
    argv = [sandbox.SHELL, "-c", INNER, "relay", *argv]
  args = sandbox.command(root, argv, opt=opt, env=environment)
  args.remove("--share-net")  # `--unshare-all` then unshares the network too
  extra = []
  for source, destination in binds:
    extra += ["--ro-bind", str(source), destination]
  if api:
    extra += ["--bind", str(root / SOCKET_NAME), SOCKET_IN_SANDBOX]
  i = args.index("--chdir")
  return args[:i] + extra + args[i:]


@contextlib.contextmanager
def relay(root):
  """Runs the host's end of the relay for the sandbox rooted at `root` while the block runs.

  socat is started in `root` with a relative socket path, since a socket's absolute path may not
  exceed 107 bytes."""
  root = Path(root)
  socket = root / SOCKET_NAME
  socket.unlink(missing_ok=True)
  process = subprocess.Popen([SOCAT, f"UNIX-LISTEN:{SOCKET_NAME},fork", f"TCP:{API_HOST}:443"],
                             cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
  try:
    deadline = time.time() + 10
    while not socket.exists():
      if process.poll() is not None or time.time() > deadline:
        raise RuntimeError(f"the API relay didn't start (exit {process.poll()})")
      time.sleep(0.02)
    yield socket
  finally:
    process.terminate()
    try:
      process.wait(timeout=10)
    except subprocess.TimeoutExpired:
      process.kill()
      process.wait()
    socket.unlink(missing_ok=True)


def run(root, argv, opt=None, env=None, binds=(), api=False, **kwargs):
  """Runs `argv` in the sandbox (with the relay if `api`), stdin from /dev/null."""
  args = command(root, argv, opt=opt, env=env, binds=binds, api=api)
  with relay(root) if api else contextlib.nullcontext():
    return subprocess.run(args, stdin=subprocess.DEVNULL, **kwargs)
