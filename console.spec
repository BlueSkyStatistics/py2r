# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import site
from PyInstaller.utils.hooks import collect_all
from pathlib import Path


datas = []
binaries = []
hidden_imports = []

if sys.platform == 'win32':
    binaries += [
        (r"C:\\Windows\\SysWOW64\\msvcp140.dll", "."),
    	(r"C:\\Windows\\SysWOW64\\ucrtbase.dll", ".")
    ]
else:
    sys.path.insert(0, Path().absolute())

def collect_package(package_name: str):
    global datas
    global binaries
    global hidden_imports

    d, b, h, *_ = collect_all(package_name)
    datas += d
    binaries += b
    hidden_imports += h

#collect_package('py2r')
#collect_package('rpy2')
#collect_package('rpy2.robjects')
#collect_package('dulwich')
#collect_package('paramiko')
#collect_package('certifi')
collect_package('urllib3')
#collect_package('cryptography')
#collect_package('six')
#collect_package('astunparse')
#collect_package('logging')

print(f'{datas=}')
print(f'{binaries=}')
print(f'{hidden_imports=}')

block_cipher = None

pathex = site.getsitepackages()
pathex.append(Path().absolute())
a = Analysis(['console.py'],
             pathex=pathex,
             binaries=binaries,
             datas=datas,
             hiddenimports=hidden_imports,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RConsole',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RConsole'
)
