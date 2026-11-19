"""Only publish stable SemVer tags that match the project version."""

import os
import re
import tomllib
from pathlib import Path


def main():
    tag = os.environ.get("GITHUB_REF_NAME", "")
    version = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    )["project"]["version"]
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise SystemExit(f"Invalid release tag: {tag!r}; expected vX.Y.Z")
    if tag != f"v{version}":
        raise SystemExit(f"Tag {tag} does not match project version {version}")
    print(f"Release tag verified: {tag}")


if __name__ == "__main__":
    main()
