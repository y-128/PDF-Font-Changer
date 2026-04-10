# -*- mode: python ; coding: utf-8 -*-
"""
PDF Font Changer - Linux Build Specification
PyInstaller spec file for building Linux standalone executable

ビルド方法:
    cd Release
    pyinstaller linux_build.spec

注意: OCR機能（ndlocr-lite）を含むため、最終バイナリは 300MB 以上になります。
"""

import sys
import os
from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_all, collect_submodules

# プロジェクトルートディレクトリ（このファイルから2階層上）
project_root = os.path.abspath(os.path.join(SPECPATH, '..'))

# 必要なソースファイル
source_files = [
    os.path.join(project_root, 'main.py'),
    os.path.join(project_root, 'pdf_processor.py'),
    os.path.join(project_root, 'ocr_processor.py'),
    os.path.join(project_root, 'font_scanner.py'),
]

# アセットファイル
assets_folder = os.path.join(project_root, 'assets')
icon_file = os.path.join(assets_folder, 'icon.png')

# ─── ndlocr-lite モデル・設定ファイルの収集 ───
_spec_ocr = importlib.util.find_spec("ocr")
_ndlocr_site = Path(_spec_ocr.origin).parent if (_spec_ocr and _spec_ocr.origin) else None

ndlocr_datas = []
ndlocr_hiddenimports = []
if _ndlocr_site:
    _model_dir = _ndlocr_site / "model"
    _config_dir = _ndlocr_site / "config"
    if _model_dir.exists():
        ndlocr_datas.append((str(_model_dir), "model"))
    if _config_dir.exists():
        ndlocr_datas.append((str(_config_dir), "config"))
    ndlocr_hiddenimports = [
        "ocr", "deim", "parseq", "ndl_parser",
        "config", "config.ops",
        "yaml",
    ] + collect_submodules("reading_order")

# ─── onnxruntime / opencv ネイティブライブラリの収集 ───
try:
    ort_datas, ort_binaries, ort_hiddenimports = collect_all("onnxruntime")
except Exception:
    ort_datas, ort_binaries, ort_hiddenimports = [], [], []

try:
    cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")
except Exception:
    cv2_datas, cv2_binaries, cv2_hiddenimports = [], [], []

# ─── tkinterdnd2（ドラッグ&ドロップ）の収集 ───
try:
    dnd_datas, dnd_binaries, dnd_hiddenimports = collect_all("tkinterdnd2")
except Exception:
    dnd_datas, dnd_binaries, dnd_hiddenimports = [], [], []

# ─── Analysis ───
a = Analysis(
    source_files,
    pathex=[project_root],
    binaries=[] + ort_binaries + cv2_binaries + dnd_binaries,
    datas=[
        (assets_folder, "assets"),
        (os.path.join(project_root, "LICENSE"), "."),
    ] + ndlocr_datas + ort_datas + cv2_datas + dnd_datas,
    hiddenimports=[
        "PIL._tkinter_finder",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
        "numpy",
        "tkinterdnd2",
    ] + ndlocr_hiddenimports + ort_hiddenimports + cv2_hiddenimports + dnd_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF Font Changer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
