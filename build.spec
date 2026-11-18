# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：Cloudy Launcher（CLY）v1.3.9.0（单文件、无控制台窗口）。

磁盘 exe 文件名沿用中文「云朵启动器」命名约定；应用内品牌名已改为 Cloudy Launcher / CLY。
v1.3.9.0 背景音乐使用 QtMultimedia，显式加入 hiddenimports 保证打包不缺模块。
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 内置资源统一放到解压根目录的 resources/ 下，与 resources.py 解析逻辑对应
    datas=[('cloud_launcher/resources/*', 'resources')],
    hiddenimports=[
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PIL', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 合规剔除：Qt 6.12 的 Qt Virtual Keyboard（Qt6VirtualKeyboard.dll 及其 platforminputcontexts
# 插件）是 GPLv3-only / 商业 授权的附加模块，本项目从未使用（只用 Core/Gui/Widgets/
# Multimedia/OpenGLWidgets/Network/Svg），由 PySide6 hook 无条件收集进来。剔除以保证
# 分发包内不携带未使用的 GPL-only 组件，同时减约 170KB。
a.binaries = [b for b in a.binaries if "virtualkeyboard" not in b[0].lower()]
a.datas = [d for d in a.datas if "virtualkeyboard" not in d[0].lower()]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='云朵启动器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='cloud_launcher/resources/app_icon.ico',
)
