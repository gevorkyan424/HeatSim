# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\assets', 'assets'), ('C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\data', 'data'), ('C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\i18n', 'i18n'), ('C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\VERSION', 'VERSION'), ('C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\Лицензионное_соглашение.txt', 'Лицензионное_соглашение.txt')],
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
    name='HeatSim',
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
    icon=['C:\\Users\\ruben\\OneDrive\\Documents\\Projects\\Python\\HeatSim\\assets\\icon.ico'],
)
