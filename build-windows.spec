# -*- mode: python ; coding: utf-8 -*-
import os
import offline_folium

# Dynamically find the offline_folium package directory
offline_folium_dir = os.path.dirname(offline_folium.__file__)
print(offline_folium_dir)

datas = [
    ('icon.png', '.'),
    ('C:\\hostedtoolcache\\windows\\Python\\3.13.7\\x64\\Lib\\site-packages\\offline_folium', 'offline_folium')
]

a = Analysis(
    ['netseedf.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name='NetSeeDF',
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
    icon='icon.png'
)