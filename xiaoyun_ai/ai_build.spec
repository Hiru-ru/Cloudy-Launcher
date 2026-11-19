# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：小云 AI（Xiaoyun AI）独立程序（单文件、无控制台）。

在 ``xiaoyun_ai`` 目录下运行 PyInstaller；小云 AI 与启动器解耦，仅依赖
QtWidgets/QtCore/QtGui 与 Python 标准库，不包含 OpenGL、多媒体、网络等无关模块。

v1.1.0 起把本地模型与 llama.cpp 引擎一并内置（bundled/ 目录，构建前放入、不进
git/源码包），做到开箱即用、无需手动选择模型：
- 模型打包到解压根目录 ``models/model.gguf``；
- 引擎运行时（llama-server.exe 及同目录 DLL）打包到 ``llama/``。
"""
import glob
import os

block_cipher = None

try:
    _spec_dir = SPECPATH  # PyInstaller 注入的 spec 所在目录
except NameError:
    _spec_dir = os.path.abspath(os.getcwd())

_bundled = os.path.join(_spec_dir, "bundled")
_extra_datas = []
_model = os.path.join(_bundled, "models", "model.gguf")
if os.path.isfile(_model):
    _extra_datas.append((_model, "models"))
for _f in sorted(glob.glob(os.path.join(_bundled, "llama", "*"))):
    if os.path.isfile(_f):
        _extra_datas.append((_f, "llama"))

a = Analysis(
    ['ai_main.py'],
    pathex=[],
    binaries=[],
    # 图标等资源放到解压根目录 resources/，模型与引擎分别放 models/、llama/。
    datas=[('resources/*', 'resources')] + _extra_datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PIL', 'numpy', 'scipy',
              'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
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
    name='小云AI',
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
