# Phase 19: App Size & Startup Time Reduction

## Objective
Reduce the frozen Windows build size from ~250 MB and eliminate the current 46–68s one-file cold start by moving to a folder build (`dist\StepShot\StepShot.exe`) that opens fast.

## Interview Decisions (2026-09-10)
These six settled answers from the user interview drive the rest of this document:
- **Audience:** The app is used by the owner and a few colleagues — nobody else.
- **Folder-only:** A plain folder is fine — users run the app straight from it.
- **Fast-open bar:** The app must "open fast" — there is no specific size or startup-time number to hit.
- **Folder-only build:** The build produces only the folder version; the single-EXE (`--onefile`) build is retired.
- **No shortcuts to preserve:** There are no existing shortcuts that have to keep working.
- **Manual zip:** When sharing with colleagues, the user zips `dist\StepShot\` by hand. No auto-zip tooling.

## Root Cause Findings
- **The `collect_all("PySide6")` Trap:** `StepShot.spec` currently calls `collect_all("PySide6")`, which force-bundles the entirety of PySide6. This explicitly bypasses PyInstaller's AST-based `excludes` list, rendering the excludes cosmetic.
- **Unpacked Bundle Bloat:** The unpacked bundle is ~656.7 MB across 3862 files. Massive dead weight includes WebEngine + devtools (340 MB), QML (74 MB), Qt3D (27 MB), Designer (14 MB), Multimedia, etc.
- **App Dependencies:** The app only imports `QtCore`, `QtGui`, `QtWidgets` (plus `QSettings`, `QStyleFactory`) and `PIL.Image`/`PIL.ImageFilter` (for byte manipulation, not I/O).

## Execution Plan
Phase A and Phase B land together as one change. The distribution format was already decided in the interview, so the old "measure Phase A before finalizing Phase B" step is obsolete — measurement happens on the final `--onedir` build.

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
- **Move to `--onedir` as the only distribution method.** A folder-based deployment opens fast because Windows loads the DLLs in place — nothing is unpacked at launch.
- **Sharing is manual.** The user zips `dist\StepShot\` by hand when sharing with colleagues. No auto-zip tooling.

### Phase C: Verification Gate
- Run `pytest` and `pytest -m acceptance`.
- Run the headless smoke test: `$env:QT_QPA_PLATFORM="offscreen"; dist\StepShot\StepShot.exe --smoke-test`.
- **UPX Packing is REJECTED.** Do not use UPX. It breaks Qt6 vtables/relocations, increases cold-start CPU overhead, and triggers antivirus false positives.

## Resolved Design Decisions
1. **`--onedir` vs `--onefile`:** Folder-only. `--onedir` is the only distribution format — the app ships as a folder, which permanently solves the 50-second startup problem.
2. **`opengl32sw.dll`:** We will retain this ~20MB DLL. The stability it provides for enterprise users over RDP or in VMs is worth the space.
3. **Execution Order:** Phase A and Phase B land as one change. The distribution format was already decided in the interview, so "measure Phase A before finalizing Phase B" is obsolete — measurement happens on the final `--onedir` build.
4. **Onefile Build Retired:** There is no build flag and no onefile fallback — the single-EXE build no longer exists.
5. **No Auto-Zip:** Sharing is manual. The user zips `dist\StepShot\` by hand; no auto-zip tooling will be built.
6. **Users:** The owner plus a few colleagues — nobody else.
7. **Success Bar:** The app "opens fast" — there is no hard size or startup-time number to hit.
