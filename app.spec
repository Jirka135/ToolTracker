# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),  # Ensure you have your templates directory added
        ('C:\\Users\\Jirka\\anaconda3\\envs\\tooltracker\\Lib\\site-packages\\pyzbar\\libiconv.dll', '.'),  # Corrected line
        ('C:\\Users\\Jirka\\anaconda3\\envs\\tooltracker\\Lib\\site-packages\\pyzbar\\libzbar-64.dll', '.'),  # Add the path to your libzbar-64.dll file
    ],
    hiddenimports=['pysqlite2', 'MySQLdb', 'psycopg2'],
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
    name='app',
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
    icon='dist/ikona.ico',
)
