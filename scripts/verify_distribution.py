"""Verify that a built wheel contains the runtime package and bundled assets."""

import argparse
import sys
from pathlib import Path
from zipfile import ZipFile

REQUIRED_FILES = (
    "career_ai_core/__init__.py",
    "career_ai_core/agent.py",
    "career_ai_core/ui.py",
    "career_ai_core/assets/styles.css",
    "career_ai_core/assets/voice.js",
    "career_ai_core/i18n/__init__.py",
    "career_ai_core/i18n/en.py",
    "career_ai_core/i18n/es.py",
)


def verify_wheel(wheel: Path) -> None:
    """Raise ValueError when required runtime files are missing or empty."""
    with ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(set(REQUIRED_FILES) - names)
        if missing:
            raise ValueError(f"Wheel is missing required files: {', '.join(missing)}")
        for name in REQUIRED_FILES:
            if not archive.read(name):
                raise ValueError(f"Wheel contains an empty required file: {name}")
        if not any(name.endswith(".dist-info/entry_points.txt") for name in names):
            raise ValueError("Wheel is missing console-script entry points")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="Path to the built .whl file")
    args = parser.parse_args()
    try:
        verify_wheel(args.wheel)
    except (OSError, ValueError) as exc:
        print(f"Distribution verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"Distribution verified: {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
