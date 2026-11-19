"""Print the project version, independently of the current directory."""

import tomllib
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    print(config["project"]["version"])


if __name__ == "__main__":
    main()
