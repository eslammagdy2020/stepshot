# Phase 19: App Size & Startup Time Reduction

## Objective
Reduce the frozen Windows build (`dist\StepShot.exe`) size from ~250 MB and improve the current 46–68s one-file cold startup time. 

## Root Cause Findings
- **The `collect_all("PySide6")` Trap:** `StepShot.spec` currently calls `collect_all("PySide6")`, which force-bundles the entirety of PySide6. This explicitly bypasses PyInstaller's AST-based `excludes` list, rendering the excludes cosmetic.
- **Unpacked Bundle Bloat:** The unpacked bundle is ~656.7 MB across 3862 files. Massive dead weight includes WebEngine + devtools (340 MB), QML (74 MB), Qt3D (27 MB), Designer (14 MB), Multimedia, etc.
- **App Dependencies:** The app only imports `QtCore`, `QtGui`, `QtWidgets` (plus `QSettings`, `QStyleFactory`) and `PIL.Image`/`PIL.ImageFilter` (for byte manipulation, not I/O).

## Execution Plan

### Phase A: Slim the Spec File (Core Reduction)
Instead of relying on `excludes` or `collect_all`, implement post-Analysis filtering directly in `StepShot.spec`:
1. **Drop `collect_all("PySide6")` and `collect_all("PIL")`.**
2. **Filter `a.binaries` and `a.datas` via list comprehensions:** Strip out libraries and folders matching known bloat (e.g., `Qt6WebEngine`, `Qt6Qml`, `Qt63D`, `Qt6Designer`, `Qt6Multimedia`, `Qt6Network`, `Qt6Sql`, `Qt6Pdf`).
3. **Preserve Essential Qt Plugins:** Ensure the filters explicitly *keep*:
   - `plugins/platforms/qwindows.dll`
   - `plugins/styles/qwindowsvistastyle.dll`
   - `plugins/imageformats/qjpeg.dll`
   - `plugins/imageformats/qico.dll`
4. **Preserve Fallback Rendering:** Keep `opengl32sw.dll` (Software GL Fallback) as insurance for RDP/VM users without hardware acceleration.

### Phase B: Distribution Format (Startup Speed)
The ~50s startup time is dominated by PyInstaller unpacking 650MB of DLLs into `%TEMP%` on every launch.
- **Move to `--onedir` as the primary distribution method.** A folder-based deployment launches instantly (< 2s) because Windows loads the DLLs in place.
- We will retain the ability to build a `--onefile` executable (perhaps via a build flag) for users who strictly demand a single EXE, but with the slimmed spec from Phase A, its startup time will be drastically reduced (estimated ~5-10s instead of 50s).

### Phase C: Verification Gate
- Run `pytest` and `pytest -m acceptance`.
- Run the headless smoke test: `$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot.exe --smoke-test` (or against the `--onedir` executable).
- **UPX Packing is REJECTED.** Do not use UPX. It breaks Qt6 vtables/relocations, increases cold-start CPU overhead, and triggers antivirus false positives.

## Resolved Design Decisions
1. **`--onedir` vs `--onefile`:** We will shift to `--onedir` (which can be distributed as a `.zip` or simple installer) to solve the 50-second startup time permanently.
2. **`opengl32sw.dll`:** We will retain this ~20MB DLL. The stability it provides for enterprise users over RDP or in VMs is worth the space.
3. **Execution Order:** Phase A (Slimming the Spec) will be executed *first* to measure the true size reduction before finalizing the distribution format changes in Phase B.
