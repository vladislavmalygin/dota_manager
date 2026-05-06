# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None

# Windows only: collect Kivy native DLL dependencies
KIVY_DEPS = []
if sys.platform == 'win32':
    try:
        from kivy_deps import sdl2, glew, angle
        KIVY_DEPS = sdl2.dep_bins + glew.dep_bins + angle.dep_bins
    except ImportError:
        try:
            from kivy_deps import sdl2, glew
            KIVY_DEPS = sdl2.dep_bins + glew.dep_bins
        except ImportError:
            pass

a = Analysis(
    ['manager/dota_manager.py'],
    pathex=['manager'],          # all .py in manager/ auto-discovered
    binaries=[],
    datas=[
        # Assets (non-Python files)
        ('manager/images',           'images'),
        ('manager/start_database.db', '.'),
        # Kivy resources (fonts, shaders, etc.)
        ('manager/logic',            'logic'),
        ('manager/ingame_interface', 'ingame_interface'),
    ],
    hiddenimports=[
        # Kivy internals not always auto-detected
        'kivy.core.window.window_sdl2',
        'kivy.core.text.text_sdl2',
        'kivy.core.text.text_pil',
        'kivy.core.image.img_sdl2',
        'kivy.core.image.img_pil',
        'kivy.core.audio.audio_sdl2',
        'kivy.core.clipboard.clipboard_sdl2',
        'kivy.core.spelling',
        'kivy.graphics.cgl_backend.cgl_glew',   # Windows
        'kivy.graphics.cgl_backend.cgl_mock',
        'kivy.uix.behaviors',
        'kivy.uix.behaviors.button',
        'kivy.uix.recycleview',
        'kivy.uix.recycleview.views',
        'PIL._tkinter_finder',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test', 'xmlrpc', 'doctest'],
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
    name='dota_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *([Tree(p) for p in KIVY_DEPS] if KIVY_DEPS else []),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dota_manager',
)
