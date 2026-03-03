# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
from PyInstaller.utils.hooks import copy_metadata

# Metadata needed by Streamlit and other libraries
datas = []
datas += copy_metadata('streamlit')
datas += copy_metadata('plotly')
datas += copy_metadata('pandas')
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('packaging')
datas += copy_metadata('altair')
datas += copy_metadata('jsonschema')

# Explicitly mapping project files into the bundle
datas += [
    ('lecat/dashboard', 'lecat/dashboard'),
    ('lecat/data/schema.sql', 'lecat/data'),
    ('lecat/config.yaml', 'lecat'),
    ('lecat_plugins', 'lecat_plugins'),
]

# Hidden imports that pyinstaller might miss but streamlit needs
hiddenimports = [
    'streamlit',
    'altair',
    'plotly',
    'pandas',
    'sqlite3',
    'lecat',
    'lecat.data_loader',
    'lecat.repository',
    'lecat.evaluator',
    'lecat.parser',
    'lecat.lexer',
    'lecat.std_lib',
    'lecat.indicators',
    'lecat.dynamic_registry',
    'lecat.plugin_loader',
    'lecat.context',
    'lecat.dashboard.app',
]

a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LECAT_Trader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to True to see terminal output/errors
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
    upx=True,
    upx_exclude=[],
    name='LECAT_Trader',
)
