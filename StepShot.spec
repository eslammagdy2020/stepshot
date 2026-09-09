# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for StepShot — single-file Windows GUI executable."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = Path(SPECPATH)

pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")
pillow_datas, pillow_binaries, pillow_hidden = collect_all("PIL")

# Trim unused Qt modules to keep the one-file EXE smaller.
excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtQuick3D",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtStateMachine",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
]

hiddenimports = [
    "keyboard",
    "ui",
    "ui.main_window",
    "ui.toolbar",
    "ui.canvas",
    "ui.theme",
    "ui.graphics_items",
    "ui.region_selector",
    "ui.resize_handles",
    "ui.icon_factory",
    "ui.annotation_adapters",
    "services",
    "services.screenshot_service",
    "services.export_service",
    "services.clipboard_service",
    "services.image_effects",
    "services.settings_service",
    "models",
    "models.step_marker",
    "models.document_history",
    "models.screenshot_inventory",
    "tools",
    "tools.arrow_tool",
    "tools.rectangle_tool",
    "tools.blur_tool",
    "tools.handlers",
    "tools.handlers.arrow",
    "tools.handlers.base",
    "tools.handlers.blur",
    "tools.handlers.context",
    "tools.handlers.crop",
    "tools.handlers.highlight",
    "tools.handlers.pen",
    "tools.handlers.rectangle",
    "tools.handlers.step",
    "tools.handlers.text",
    "tools.highlight_tool",
    "tools.pen_tool",
    "tools.step_tool",
    "tools.text_tool",
    *pyside6_hidden,
    *pillow_hidden,
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=pyside6_binaries + pillow_binaries,
    datas=pyside6_datas + pillow_datas + [(str(project_root / "assets"), "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="StepShot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.ico"),
)

