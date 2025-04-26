# -*- mode: python ; coding: utf-8 -*-

# Find the needed rshell packages within the virtual environment
import os
venv = os.environ.get('VIRTUAL_ENV', '.')
import re
import sys
localdatas = []
for path in sys.path:
    m = re.match('(' + venv + '/lib.*site-packages)', path)
    if m is not None:
        for rpath in os.listdir(m.group(1)):
            if rpath.find('rshell') == 0:
                localdatas.append((m.group(1) + '/' + rpath, rpath))
        break
        
a = Analysis(
    [venv + '/bin/rshell'],
    pathex=[],
    binaries=[],
    datas = localdatas,
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
