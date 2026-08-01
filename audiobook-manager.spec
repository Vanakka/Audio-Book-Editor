# PyInstaller spec: one-folder build into dist/AudioBook-Manager/
# Source code in the project root is never modified or overwritten.

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH)

pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")
multimedia_datas, multimedia_binaries, multimedia_hidden = collect_all("PySide6.QtMultimedia")

resource_datas = [(str(project_root / "resources"), "resources")]

hiddenimports = (
    pyside6_hidden
    + multimedia_hidden
    + collect_submodules("mutagen")
    + collect_submodules("openpyxl")
    + [
        "bs4",
        "PIL",
        "requests",
        "core",
        "core.app_paths",
        "core.chapters",
        "core.config",
        "core.logging_config",
        "core.media_tools",
        "core.metadata",
        "core.models",
        "core.scanner",
        "core.renamer",
        "core.libation_import",
        "core.cache_keys",
        "scrapers",
        "scrapers.audible",
        "scrapers.audible_api",
        "scrapers.google_books",
        "scrapers.openlibrary",
        "scrapers.goodreads",
        "scrapers.cover_downloader",
        "scrapers.cover_search",
        "scrapers.http",
        "scrapers.matching",
        "scrapers.base",
        "ui",
        "ui.main_window",
        "ui.detail_panel",
        "ui.detail.widgets",
        "ui.detail.details_tab",
        "ui.detail.cover_tab",
        "ui.detail.files_tab",
        "ui.detail.chapters_tab",
        "ui.workers",
        "ui.styles",
        "ui.library_panel",
        "ui.fetch_dialog",
        "ui.batch_dialog",
        "ui.rename_dialog",
        "ui.settings_dialog",
        "ui.sort_dialog",
        "ui.cover_widget",
    ]
)

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=pyside6_binaries + multimedia_binaries,
    datas=pyside6_datas + multimedia_datas + resource_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AudioBook Manager",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AudioBook-Manager",
)