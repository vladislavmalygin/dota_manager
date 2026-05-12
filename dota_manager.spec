# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['manager/dota_manager.py'],
    pathex=['manager'],
    binaries=[],
    datas=[
        ('manager/images',            'images'),
        ('manager/music',             'music'),
        ('manager/start_database.db', '.'),
        ('manager/logic',             'logic'),
        ('manager/ingame_interface',  'ingame_interface'),
    ],
    hiddenimports=[
        'kivy.core.window.window_sdl2',
        'kivy.core.window.window_pygame',
        'kivy.core.text.text_pil',
        'kivy.core.text.text_sdl2',
        'kivy.core.image.img_pil',
        'kivy.core.image.img_sdl2',
        'kivy.core.image.img_pygame',
        'kivy.core.audio.audio_sdl2',
        'kivy.core.audio.audio_pygame',
        'kivy.core.clipboard.clipboard_sdl2',
        'kivy.core.clipboard.clipboard_xclip',
        'kivy.graphics.cgl_backend.cgl_gl',
        'kivy.graphics.cgl_backend.cgl_mock',
        'kivy.uix.behaviors',
        'kivy.uix.behaviors.button',
        'kivy.uix.recycleview',
        'kivy.uix.recycleview.views',
        'PIL._imaging',
        'PIL.Image',
        'sqlite3',
        '_sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test', 'xmlrpc', 'doctest',
              'email', 'html', 'http', 'urllib', 'xml'],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dota_manager',
)
