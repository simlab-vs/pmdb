#!/usr/bin/env python3
"""Build a quill site.

Usage: python3 build.py SITE_DIR [--out OUT_DIR] [-v]
"""

import argparse
import logging
import sys

from quill.builder import BuildError, build
from quill.config import ConfigError
from quill.content import ContentError
from quill.plugins import PluginError
from quill.templates import TemplateError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a quill site.")
    parser.add_argument("site", help="site directory (containing site.ini)")
    parser.add_argument("--out", default="public", help="output directory (default: public)")
    parser.add_argument("--no-clean", action="store_true", help="don't empty the output directory first")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debugging information")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        build(args.site, args.out, clean=not args.no_clean)
    except (BuildError, ConfigError, ContentError, PluginError, TemplateError) as error:
        logging.getLogger("quill").error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
