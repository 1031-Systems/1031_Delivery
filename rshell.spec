# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/john/QtProjects/.venv/bin/rshell'],
    pathex=[],
    binaries=[],
    datas=[
        ('/home/john/QtProjects/.venv/lib64/python3.9/site-packages/rshell', 'rshell'),
        ('/home/john/QtProjects/.venv/lib64/python3.9/site-packages/rshell-0.0.31-py3.9.egg-info', 'rshell-0.0.31-py3.9.egg-info'),
    ],
    hiddenimports=['serial', 'serial.tools', 'serial.tools.list_ports', 'rlcompleter'],
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
    a.binaries,
    a.datas,
    [],
    name='rshell',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
