"""Guards the Phase 19 slimmed spec and onedir build layout."""

from __future__ import annotations

from pathlib import Path

import build

ROOT = Path(__file__).resolve().parents[2]
SPEC_TEXT = (ROOT / "StepShot.spec").read_text(encoding="utf-8")


def test_spec_drops_collect_all():
    """collect_all force-bundles whole packages and bypasses the excludes list."""
    assert "collect_all" not in SPEC_TEXT


def test_spec_builds_onedir():
    """The onedir layout is the only distribution format for Phase 19+."""
    assert "COLLECT(" in SPEC_TEXT
    assert "exclude_binaries=True" in SPEC_TEXT


def test_spec_keep_list_names_essential_qt_binaries():
    """The keep-list must guard the plugin DLLs the app and smoke test load."""
    for name in (
        "qwindows.dll",
        "qwindowsvistastyle.dll",
        "qjpeg.dll",
        "qico.dll",
        "opengl32sw.dll",
    ):
        assert name in SPEC_TEXT


def test_spec_rejects_upx():
    """UPX breaks Qt6 vtables and triggers antivirus false positives."""
    assert "upx=True" not in SPEC_TEXT


def test_build_dist_exe_targets_onedir_executable():
    assert build.DIST_EXE == ROOT / "dist" / "StepShot" / "StepShot.exe"
