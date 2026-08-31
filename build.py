#!/usr/bin/env python3
"""Build StepShot as a standalone Windows executable using PyInstaller."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_FILE = ROOT / "StepShot.spec"
DIST_EXE = ROOT / "dist" / "StepShot.exe"


def build(*, clean: bool = True) -> Path:
    if not SPEC_FILE.is_file():
        raise FileNotFoundError(f"Spec file not found: {SPEC_FILE}")

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is not installed. Run:\n"
            "  pip install -r requirements-build.txt"
        ) from exc

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
    ]
    if clean:
        command.append("--clean")

    print("Running:", " ".join(command))
    subprocess.check_call(command, cwd=ROOT)

    if not DIST_EXE.is_file():
        raise RuntimeError(f"Build finished but executable was not found: {DIST_EXE}")

    size_mb = DIST_EXE.stat().st_size / (1024 * 1024)
    print(f"Success: {DIST_EXE} ({size_mb:.1f} MB)")
    return DIST_EXE


def main() -> int:
    parser = argparse.ArgumentParser(description="Build StepShot.exe with PyInstaller")
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip PyInstaller --clean (faster incremental builds)",
    )
    args = parser.parse_args()

    try:
        build(clean=not args.no_clean)
    except subprocess.CalledProcessError as exc:
        print(f"Build failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    except (FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
