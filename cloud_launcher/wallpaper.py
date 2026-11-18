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

"""外部自定义壁纸加载（v1.2.4.0）。

壁纸**不打进 exe、也不进入源码 zip**：启动时在 exe 同级外部目录 ``wallpaper/`` 按固定
优先级读取受支持图片；目录缺失、文件损坏、格式不支持或被用户手动删除时，静默返回
``(None, 0.0)``，主窗口回退到默认蓝白渐变背景，不弹窗、不抛异常、不崩溃。

以后接入任意自定义壁纸：把图片覆盖到 ``wallpaper/wallpaper.png``（或目录内任一受支持
图片）即可，无需改程序、无需重新打包。主 ``config.json`` 不新增任何壁纸字段。
"""
import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from . import constants as C
from .resources import data_dir


def wallpaper_dir() -> str:
    """CLY 数据目录下的壁纸目录绝对路径（v1.3.10.0 起）。"""
    return os.path.join(data_dir(), C.WALLPAPER_DIR_NAME)


def _candidate_paths() -> list[str]:
    """按固定优先级返回候选壁纸路径；目录存在时再兜底扫描其余受支持图片。"""
    directory = wallpaper_dir()
    paths = [os.path.join(directory, name) for name in C.WALLPAPER_CANDIDATES]
    if os.path.isdir(directory):
        others: list[str] = []
        try:
            entries = os.listdir(directory)
        except OSError:
            entries = []
        for fn in entries:
            ext = os.path.splitext(fn)[1].lower()
            if ext in C.WALLPAPER_EXTS and fn not in C.WALLPAPER_CANDIDATES:
                others.append(os.path.join(directory, fn))
        others.sort()
        paths.extend(others)
    return paths


def average_brightness(pixmap: QPixmap) -> float:
    """采样整图平均亮度，归一化到 0（全黑）~1（全白）；空图返回 0。"""
    if pixmap.isNull():
        return 0.0
    small = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    image = small.toImage()
    total = image.width() * image.height()
    if total <= 0:
        return 0.0
    red = green = blue = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            red += color.red()
            green += color.green()
            blue += color.blue()
    red /= total
    green /= total
    blue /= total
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return max(0.0, min(1.0, luminance / 255.0))


def load_wallpaper() -> tuple[QPixmap | None, float]:
    """加载外部壁纸。

    :return: ``(pixmap, brightness)``；无可用壁纸时返回 ``(None, 0.0)``。
    任何读取 / 解析异常都被吞掉并回退，保证启动器在壁纸被删、损坏或目录缺失时正常运行。
    """
    try:
        for path in _candidate_paths():
            if not os.path.isfile(path):
                continue
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap, average_brightness(pixmap)
    except Exception:  # 壁纸属于外部可替换资源，任何异常都不允许拖垮主窗口
        return None, 0.0
    return None, 0.0


# ---------------------------------------------------------------------------
# v1.3.9.0：壁纸导入与选择（设置页个性化）。
# ---------------------------------------------------------------------------
def list_wallpapers() -> list[str]:
    """列出 wallpaper/ 目录下所有受支持图片的文件名（按修改时间倒序）。"""
    directory = wallpaper_dir()
    if not os.path.isdir(directory):
        return []
    entries: list[tuple[float, str]] = []
    try:
        names = os.listdir(directory)
    except OSError:
        names = []
    for name in names:
        if os.path.splitext(name)[1].lower() not in C.WALLPAPER_EXTS:
            continue
        full = os.path.join(directory, name)
        if os.path.isfile(full):
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                mtime = 0.0
            entries.append((mtime, name))
    entries.sort(reverse=True)
    return [name for _, name in entries]


def _unique_target(directory: str, filename: str) -> str:
    """目标目录已存在同名文件时追加序号，返回不冲突的文件名。"""
    stem, ext = os.path.splitext(filename)
    candidate = filename
    index = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{stem}_{index}{ext}"
        index += 1
    return candidate


def import_wallpaper(src_path: str) -> str:
    """把外部图片复制进 wallpaper/ 目录，返回新文件名。

    Raises:
        ValueError: 源文件不存在 / 扩展名不支持 / 图片无法打开。
    """
    if not os.path.isfile(src_path):
        raise ValueError("源文件不存在")
    if os.path.splitext(src_path)[1].lower() not in C.WALLPAPER_EXTS:
        raise ValueError("不支持的图片格式")
    probe = QPixmap(src_path)  # 先确认图片能被 Qt 打开，避免坏文件进目录。
    if probe.isNull():
        raise ValueError("图片文件已损坏，无法打开")

    # v1.3.9.2：自定义壁纸最多三个，UI 之外再加一道兜底。
    if len(list_wallpapers()) >= C.WALLPAPER_MAX_COUNT:
        raise ValueError("最多导入三个壁纸")

    directory = wallpaper_dir()
    os.makedirs(directory, exist_ok=True)
    target_name = _unique_target(directory, os.path.basename(src_path))
    shutil.copy2(src_path, os.path.join(directory, target_name))
    return target_name


def load_named_wallpaper(filename: str) -> tuple[QPixmap | None, float]:
    """按文件名加载 wallpaper/ 目录下的指定壁纸（拒绝目录穿越）。"""
    if not filename or os.path.basename(filename) != filename:
        return None, 0.0
    path = os.path.join(wallpaper_dir(), filename)
    if not os.path.isfile(path):
        return None, 0.0
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None, 0.0
    return pixmap, average_brightness(pixmap)


def load_selected_wallpaper(config) -> tuple[QPixmap | None, float]:
    """按 config 的 wallpaper_file 加载壁纸。

    v1.3.9.2：默认档（default）即空白——返回 ``(None, 0.0)``，
    由主窗口回退内置蓝白渐变，不再扫描 wallpaper/ 目录；
    显式选中的自定义壁纸缺失 / 损坏时同样回退空白。
    """
    selected = config.get("wallpaper_file", C.WALLPAPER_DEFAULT_KEY)
    if selected and selected != C.WALLPAPER_DEFAULT_KEY:
        pixmap, brightness = load_named_wallpaper(selected)
        if pixmap is not None:
            return pixmap, brightness
    return None, 0.0
