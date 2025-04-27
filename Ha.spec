# -*- mode: python ; coding: utf-8 -*-

systemBinaries = []
import os
ostype = os.environ.get('OSTYPE', 'None')
if ostype == 'darwin':
    pass
elif ostype == 'linux':
    from pathlib import Path
    sofile = Path('/usr/lib64/gtk-3.0/modules/libxapp-gtk3-module.so')
    if sofile.is_file():
        systemBinaries.append(('/usr/lib64/gtk-3.0/modules/libxapp-gtk3-module.so', '.'))
    endif
else:
    print('WHOOPS - Unrecognized or nonexistent OSTYPE')


a = Analysis(
    ['Hauntimator.py'],
    pathex=[],
    binaries=systemBinaries,
    datas=[
        ('docs/*.md', 'docs'),
        ('docs/images/*.png', 'docs/images'),
        ('plugins', 'plugins'),
        ('Hauntimator.dist-info/METADATA', 'Hauntimator.dist-info'),
        ('joysticking.dist-info/METADATA', 'joysticking.dist-info'),
    ],
    hiddenimports=['pocketsphinx', 'pygame', 'serial'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['commlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Hauntimator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Hauntimator',
)
