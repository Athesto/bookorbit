"""Print the project version."""

import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "pyproject.toml").read_text())

print(config["project"]["version"])
