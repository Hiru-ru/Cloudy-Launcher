# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Cloudy Launcher (CLY) / 云朵启动器
# Copyright (C) 2026 小鱼
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""资源路径解析：同时兼容源码运行与 PyInstaller 打包后的 onefile 环境。"""
import os
import sys


def app_base_dir() -> str:
    """应用运行时所在目录。

    - 打包后：exe 所在目录（便于定位便携数据目录）
    - 源码运行：工程根目录（cloud_launcher 的上一级）
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    """应用数据根目录（v1.3.10.0 起统一为 ``<app 目录>/CLY``，不保证已创建）。

    运行期数据（config.json、music、wallpaper、账号、缓存、自定义 logo）平铺在该
    目录下，不再散落在 app 目录或使用 yd 子目录。唯独 ``.minecraft`` 游戏目录不进
    CLY，v1.3.10.1 起保留在 ``<app 目录>/.minecraft``（见 ``game_dirs.minecraft_root``）。
    """
    from . import constants as C
    return os.path.join(app_base_dir(), C.DATA_DIR_NAME)


def resource_path(relative: str) -> str:
    """返回打包内置资源的绝对路径。

    PyInstaller onefile 解压目录为 sys._MEIPASS；源码运行时基于本包目录。
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "resources", relative)
