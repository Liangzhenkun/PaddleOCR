# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []


def should_keep(entry):
    src = Path(entry[0]).as_posix().lower()
    if "/paddle/include/" in src:
        return False
    if src.endswith("/paddle/base/libpaddle.lib"):
        return False
    return True

for package_name in ("paddle", "paddleocr", "paddlex", "fitz", "PIL"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    datas += [entry for entry in pkg_datas if should_keep(entry)]
    binaries += [entry for entry in pkg_binaries if should_keep(entry)]
    hiddenimports += pkg_hiddenimports


a = Analysis(
    ["ocr_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaddleOCRDesktopTool",
    icon="assets/app_icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PaddleOCRDesktopTool",
)
