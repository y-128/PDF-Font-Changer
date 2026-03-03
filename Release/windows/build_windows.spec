# -*- mode: python ; coding: utf-8 -*-
"""
PDF Font Changer - Windows Build Specification
PyInstaller spec file for building Windows standalone executable
"""

import sys
import os

# プロジェクトルートディレクトリ（このファイルから2階層上）
project_root = os.path.abspath(os.path.join(SPECPATH, '..', '..'))

# 必要なソースファイル
source_files = [
    os.path.join(project_root, 'main.py'),
    os.path.join(project_root, 'pdf_processor.py'),
    os.path.join(project_root, 'font_scanner.py'),
]

# アセットファイル（assetsフォルダ）
assets_folder = os.path.join(project_root, 'assets')
icon_file = os.path.join(assets_folder, 'icon.png')

a = Analysis(
    source_files,
    pathex=[project_root],
    binaries=[],
    datas=[
        (assets_folder, 'assets'),  # assets フォルダを同梱
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
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
    console=False,  # GUIアプリなのでコンソールを表示しない
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.exists(icon_file) else None,
)
