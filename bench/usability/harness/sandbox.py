"""Runs commands in a bubblewrap sandbox that exposes only what an agent is meant to see.

The sandbox contains a read-only /nix store, a minimal /etc, a fresh home directory, the writable
/work directory and, optionally, a read-only /opt/pmdb. All namespaces but the network are
unshared, since Claude Code needs to reach the API.
"""

import os
import shutil
from pathlib import Path


def store_dir(command):
  """Returns the Nix store `bin` directory providing `command` on the host."""
  return str(Path(os.path.realpath(shutil.which(command))).parent)


TOOLS = ["python3", "bash", "grep", "sed", "find", "diff", "awk", "ls", "less", "file", "claude"]
TOOL_DIRS = []
for t in TOOLS:
  if shutil.which(t) and store_dir(t) not in TOOL_DIRS:
    TOOL_DIRS.append(store_dir(t))
CA_BUNDLE = os.path.realpath("/etc/ssl/certs/ca-certificates.crt")
SHELL = os.path.join(store_dir("bash"), "bash")


def prepare_etc(root):
  """Writes a minimal /etc into `root / "etc"`."""
  etc = root / "etc"
  (etc / "ssl" / "certs").mkdir(parents=True, exist_ok=True)
  (etc / "passwd").write_text(f"agent:x:1000:100:agent:/home/agent:{SHELL}\n")
  (etc / "group").write_text("users:x:100:\n")
  (etc / "hosts").write_text("127.0.0.1 localhost\n::1 localhost\n")
  (etc / "resolv.conf").write_text(Path("/etc/resolv.conf").read_text())
  (etc / "nsswitch.conf").write_text("hosts: files dns\npasswd: files\ngroup: files\n")
  link = etc / "ssl" / "certs" / "ca-certificates.crt"
  if not link.is_symlink():
    link.symlink_to(CA_BUNDLE)
  return etc


def command(root, argv, opt=None, env=None):
  """Returns the bwrap command line running `argv` in the sandbox rooted at `root`.

  `root` contains `etc`, `home` and `work`; `opt` is mounted at /opt/pmdb if given.
  """
  path = ([] if opt is None else ["/opt/pmdb/bin"]) + TOOL_DIRS
  environment = {
    "PATH": ":".join(path),
    "HOME": "/home/agent", "USER": "agent", "LOGNAME": "agent", "SHELL": SHELL,
    "TERM": "dumb", "LANG": "C.UTF-8",
    "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
    "DISABLE_AUTOUPDATER": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
  }
  environment.update(env or {})

  args = [
    "bwrap", "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
    "--hostname", "sandbox", "--uid", "1000", "--gid", "100",
    "--ro-bind", "/nix", "/nix",
    "--ro-bind", str(root / "etc"), "/etc",
    "--symlink", os.path.realpath("/bin/sh"), "/bin/sh",
    "--symlink", os.path.realpath("/usr/bin/env"), "/usr/bin/env",
    "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
    "--bind", str(root / "home"), "/home/agent",
    "--bind", str(root / "work"), "/work",
  ]
  if opt is not None:
    args += ["--ro-bind", str(opt), "/opt/pmdb"]
  args += ["--chdir", "/work", "--clearenv"]
  for k, v in environment.items():
    args += ["--setenv", k, v]
  return args + ["--"] + list(argv)
