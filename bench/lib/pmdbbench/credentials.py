"""The credentials with which agents run on the user's Claude subscription."""

from pathlib import Path

TOKEN_FILE = Path.home() / ".config" / "pmdb-study" / "oauth-token"


def token():
  return TOKEN_FILE.read_text().strip()
