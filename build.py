#!/usr/bin/env python3
"""Build StepShot as a Windows onedir build (dist/StepShot/StepShot.exe) using PyInstaller."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_FILE = ROOT / "StepShot.spec"
DIST_DIR = ROOT / "dist" / "StepShot"
DIST_EXE = DIST_DIR / "StepShot.exe"


def _dist_folder_stats() -> tuple[float, int]:
    files = [path for path in DIST_DIR.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    return total_bytes / (1024 * 1024), len(files)


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

    exe_mb = DIST_EXE.stat().st_size / (1024 * 1024)
    folder_mb, file_count = _dist_folder_stats()
    print(f"Success: {DIST_EXE} ({exe_mb:.1f} MB)")
    print(f"Success: {DIST_DIR} ({folder_mb:.1f} MB, {file_count} files)")
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
