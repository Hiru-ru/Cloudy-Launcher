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

"""v1.3.9.3 品牌（logo / 名字）解析。

品牌区两个开关是**显隐**语义（不是改写）：
- Logo 开关关闭 = 整个隐藏 Logo；名字开关关闭 = 隐藏名字。
- 自定义 Logo / 名字是独立的「替换内容」：导入 Logo、填写名字后替换内置内容，
  显隐仍由两个开关控制。

侧栏品牌区、关于页、窗口标题都从本模块取当前 logo 路径、显示名与显隐状态，保证口径一致。

- 网络标识 ``APP_UA_NAME`` 不在这里出现，永远保持纯 ASCII、不随显示名改动。
- 自定义 logo 存放在 app 同级 ``yd/`` 目录，config 里只存文件名；文件缺失时
  自动回退内置 logo，不报错。
"""
from __future__ import annotations

import os
import shutil

from . import constants as C
from .resources import data_dir, resource_path


def custom_logo_exists(config) -> bool:
    filename = config.get("custom_logo")
    if not filename:
        return False
    path = os.path.join(data_dir(), filename)
    return os.path.isfile(path)


def custom_logo_path(config) -> str:
    return os.path.join(data_dir(), config.get("custom_logo", ""))


def logo_visible(config) -> bool:
    """Logo 开关：关闭即整个隐藏 Logo。"""
    return bool(config.get("logo_visible", C.LOGO_VISIBLE_DEFAULT))


def name_visible(config) -> bool:
    """名字开关：关闭即隐藏名字。"""
    return bool(config.get("name_visible", C.NAME_VISIBLE_DEFAULT))


def _custom_name(config) -> str:
    return str(config.get("custom_name", "") or "").strip()


def logo_path(config) -> str:
    """当前应使用的 logo 绝对路径（自定义或内置）；显隐由消费方控制。"""
    if custom_logo_exists(config):
        return custom_logo_path(config)
    return resource_path("cloud_logo.png")


def short_name(config) -> str:
    """侧栏品牌区显示名（默认 APP_NAME）。"""
    return _custom_name(config) or C.APP_NAME


def full_name(config) -> str:
    """关于页显示名（默认 APP_FULL_NAME）。"""
    return _custom_name(config) or C.APP_FULL_NAME


def window_title(config) -> str:
    """窗口标题：名字隐藏时回退默认标题，不显示自定义名字。"""
    if name_visible(config) and _custom_name(config):
        return _custom_name(config)
    return C.APP_DISPLAY_NAME


def custom_logo_dir() -> str:
    """自定义 logo 所在目录（v1.3.10.0 起直接平铺在 CLY 数据目录）。"""
    return data_dir()


def import_custom_logo(src_path: str) -> str:
    """导入自定义 logo 到 yd/custom_logo.<ext>（替换旧文件），返回存入 config 的文件名。

    Raises:
        ValueError: 源文件不存在 / 格式不支持 / 图片无法打开。
    """
    from PySide6.QtGui import QPixmap  # 延迟导入，保持模块轻量

    if not os.path.isfile(src_path):
        raise ValueError("源文件不存在")
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in C.WALLPAPER_EXTS:
        raise ValueError("不支持的图片格式")
    if QPixmap(src_path).isNull():
        raise ValueError("图片文件已损坏，无法打开")

    directory = custom_logo_dir()
    os.makedirs(directory, exist_ok=True)
    # 清掉旧的 custom_logo.*，只保留当前一份。
    for name in os.listdir(directory):
        if (
            os.path.splitext(name)[0] == C.CUSTOM_LOGO_BASENAME
            and os.path.splitext(name)[1].lower() in C.WALLPAPER_EXTS
        ):
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                pass
    filename = f"{C.CUSTOM_LOGO_BASENAME}{ext}"
    shutil.copy2(src_path, os.path.join(directory, filename))
    return filename
