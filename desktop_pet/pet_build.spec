# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：云朵桌宠（Cloudy Pet）独立 APP（单文件、无控制台）。

在 ``desktop_pet`` 目录下运行 PyInstaller；桌宠与启动器解耦，仅依赖
Core/Gui/Widgets/OpenGL/OpenGLWidgets，不包含多媒体、网络等无关模块。
"""

block_cipher = None

a = Analysis(
    ['pet_main.py'],
    pathex=[],
    binaries=[],
    # 内置兜底皮肤与图标放到解压根目录 resources/，与 pet_constants.resource_path 对应
    datas=[('resources/*', 'resources')],
    hiddenimports=[
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PIL', 'numpy', 'scipy',
              'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
              'PySide6.QtNetwork'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 合规剔除未使用的 Qt Virtual Keyboard（GPL-only 附加模块），与启动器 spec 口径一致。
a.binaries = [b for b in a.binaries if "virtualkeyboard" not in b[0].lower()]
a.datas = [d for d in a.datas if "virtualkeyboard" not in d[0].lower()]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='云朵桌宠',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='resources/app_icon.ico',
)
