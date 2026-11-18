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

"""通用苹果风局部磨砂圆角卡片。

v1.2.4.1：卡片背景不再由 QSS 三段白渐变直接画在整张（那只是半透明白片、压在全屏模糊
底色上）。改为重写 paintEvent，在卡片圆角矩形内只截取正后方一小块清晰壁纸做片内局部
柔化，再叠三段白玻璃高光与细亮边；卡片之外的壁纸保持清晰。模糊被严格限制在卡片矩形内。

卡片不调用本地 setStyleSheet（避免祖先本地表切断后代控件全局属性选择器规则），背景 /
边框 / 圆角全部由 paintEvent 自绘；内部文字、输入框、按钮、GL 预览等子控件仍由 Qt 在
本层之后独立绘制，不被柔化。
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from .. import constants as C
from .frosted_backdrop import paint_frosted_panel

_CARD_RADIUS = 20.0


class Card(QFrame):
    """可复用的局部磨砂圆角卡片：可选标题，内部内容通过 body_layout 放置。"""

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        # 独立顶层弹窗内的卡片需以主窗口为坐标基准；None 时用自身 window()。
        self._reference_window = None
        # 模态弹窗弹出前抓到的父窗口真实背景（清晰/模糊/基准）；None 时回退壁纸缓存。
        self._live = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(8)

        self._title_label: QLabel | None = None
        if title:
            self._title_label = QLabel(title)
            self._title_label.setProperty("cardTitle", True)
            root.addWidget(self._title_label)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(10)
        root.addLayout(self.body_layout)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 圆角矩形内：片内局部磨砂壁纸块 -> 三段白玻璃高光 -> 细亮边。
        paint_frosted_panel(
            painter,
            self,
            _CARD_RADIUS,
            C.COLOR_GLASS_TOP_RGBA,
            C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA,
            C.COLOR_CARD_BORDER_RGBA,
            reference_window=self._reference_window,
            live=self._live,
        )
        painter.end()

    def set_reference_window(self, window) -> None:
        """指定磨砂采样的坐标基准（独立顶层弹窗传主窗口）。"""
        self._reference_window = window

    def set_live_backdrop(self, clear_pix, blur_pix, reference_widget) -> None:
        """注入弹出前抓到的父窗口真实背景，供模态卡片做真正的背景模糊。"""
        if clear_pix is None or reference_widget is None:
            self._live = None
        else:
            self._live = (clear_pix, blur_pix, reference_widget)

    def set_title(self, text: str) -> None:
        if self._title_label is None:
            self._title_label = QLabel(text)
            self._title_label.setProperty("cardTitle", True)
            self.layout().insertWidget(0, self._title_label)
        else:
            self._title_label.setText(text)

    @property
    def body(self) -> QVBoxLayout:
        return self.body_layout

    def add_widget(self, widget) -> None:
        self.body_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.body_layout.addLayout(layout)
