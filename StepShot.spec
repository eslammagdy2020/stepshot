# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for StepShot — onedir Windows GUI build (dist/StepShot/StepShot.exe)."""

from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH)

# Belt-and-braces module excludes; the built-in PyInstaller hooks collect only
# what the imports in main.py and its first-party hiddenimports reference, and
# the post-Analysis filter below strips any remaining bloat from the TOCs.
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
]


def _normalize(dest_name):
    return dest_name.replace("\\", "/").lower()


# Keep-list: checked first. Anything matching is never stripped, even when a
# bloat pattern below would also match it. Covers the Qt plugin folders the app
# needs (platforms incl. qwindows.dll/qoffscreen.dll, styles, imageformats
# incl. qjpeg.dll/qico.dll, iconengines), the software GL fallback for RDP/VM
# users, the core Qt/shiboken6/Python/VC runtime DLLs, and the app assets.
_KEEP_SUBSTRINGS = (
    "qwindows.dll",
    "qwindowsvistastyle.dll",
    "qjpeg.dll",
    "qico.dll",
    "opengl32sw.dll",
    "qt6core.dll",
    "qt6gui.dll",
    "qt6widgets.dll",
    "qt6svg.dll",
    "pyside6.abi3.dll",
    "shiboken6",
    "python3",
    "vcruntime",
    "msvcp",
    "concrt",
    "vcomp",
    "vcamp",
    "vccorlib",
    "ucrtbase",
)

_KEEP_SEGMENTS = (
    "platforms",
    "styles",
    "imageformats",
    "iconengines",
    "assets",
)

# Bloat patterns, checked only after the keep-list.
_STRIP_SUBSTRINGS = (
    "qt6webengine",
    "qt6qml",
    "qt6quick",
    "qt63d",
    "qt6designer",
    "qt6multimedia",
    "qt6network",
    "qt6sql",
    "qt6pdf",
    "qt6charts",
    "qt6datavisualization",
    "qt6graphs",
    "qt6bluetooth",
    "qt6sensors",
    "qt6serialport",
    "qt6positioning",
    "qt6location",
    "qt6remoteobjects",
    "qt6scxml",
    "qt6statemachine",
    "qt6websockets",
    "qt6test",
    "qt6xml",
    "qt6opengl",
    "qt6dbus",
    "qt6networkauth",
    "qt6nfc",
    "qt6spatialaudio",
    "virtualkeyboard",
)

# The tls, networkinformation and generic plugin folders only exist for
# QtNetwork/touch support; their DLLs link Qt6Network.dll, so they are dead
# weight once that module is stripped.
_STRIP_SEGMENTS = (
    "translations",
    "typesystems",
    "qml",
    "tls",
    "networkinformation",
    "generic",
)

# PySide6 extension modules the app actually imports.
_PYSIDE6_KEEP_PYD = ("qtcore.pyd", "qtgui.pyd", "qtwidgets.pyd")


def _keep_entry(dest_name):
    normalized = _normalize(dest_name)
    if any(pattern in normalized for pattern in _KEEP_SUBSTRINGS):
        return True
    return any(segment in _KEEP_SEGMENTS for segment in normalized.split("/"))


def _strip_entry(dest_name):
    normalized = _normalize(dest_name)
    if any(pattern in normalized for pattern in _STRIP_SUBSTRINGS):
        return True
    if any(segment in _STRIP_SEGMENTS for segment in normalized.split("/")):
        return True
    if normalized.endswith(".qm"):
        return True
    segments = normalized.split("/")
    return (
        len(segments) > 1
        and "pyside6" in segments[:-1]
        and segments[-1].endswith(".pyd")
        and segments[-1] not in _PYSIDE6_KEEP_PYD
    )


def _filter_toc(toc, label):
    kept = []
    stripped = []
    for entry in toc:
        dest_name = _normalize(entry[0])
        if _keep_entry(entry[0]) or not _strip_entry(entry[0]):
            kept.append(entry)
        else:
            stripped.append(dest_name)
    if stripped:
        print(f"StepShot.spec: stripped {len(stripped)} {label} entries:")
        for dest_name in stripped:
            print(f"  - {dest_name}")
    return kept


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "assets"), "assets")],
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

a.binaries = _filter_toc(a.binaries, "binary")
a.datas = _filter_toc(a.datas, "data")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StepShot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StepShot",
)
