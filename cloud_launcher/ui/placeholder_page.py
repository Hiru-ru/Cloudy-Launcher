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

"""v1.2.5.1 通用占位页：设置 / 打包 / 关于 三个导航本轮只摆空骨架。

本轮按用户口径「先把展示图骨架搭好，功能后续慢慢加」：这三个页面不接真实功能，
只在透明页面中央放置标题与一句浅色提示；后续接入对应模块时替换本页内容即可。
启动导航挂载 ``profile_page.py`` 个人页、下载导航挂载 ``download_page.py`` 骨架页，
均不在本占位页范围。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .. import constants as C


class PlaceholderPage(QWidget):
    """透明底居中占位页：标题 + 后续开放提示。"""

    def __init__(self, title: str, hint: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("placeholder-page")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch(1)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setProperty("pageTitle", True)
        root.addWidget(title_label)

        hint_label = QLabel(hint)
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setWordWrap(True)
        hint_label.setProperty("hintLabel", True)
        root.addWidget(hint_label)

        root.addStretch(1)
