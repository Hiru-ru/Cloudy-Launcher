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

"""左侧导航栏：品牌区 + 启动 / 下载 / 设置 / 打包 / 关于 五项导航。

v1.2.5.1：按 PCL 式参考骨架重构为五项竖排导航。未选中项为「图标 + 文字」，
选中项隐藏图标、只保留文字（加粗高亮）；页面切换通过 ``navigateRequested`` 信号
把导航 key 发给主窗口。栏片背景与卡片一致，由 paintEvent 在圆角矩形内做片内局部
磨砂（只模糊栏片正后方那一小块壁纸），再叠三段白玻璃高光与细亮边；栏片之外的
壁纸保持清晰。不调用本地 setStyleSheet，避免切断全局表中后代控件的属性选择器规则。

归属口径：「启动」导航对应个人页 ProfilePage（3D 预览、昵称、账号、开始游戏）；
「下载」导航对应参考图标签 + 卡片骨架；设置 / 打包 / 关于为占位页。
"""
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from .. import brand
from .. import constants as C
from ..resources import resource_path
from .appearance import appearance
from .frosted_backdrop import paint_frosted_panel
from .spring_button import SpringPushButton

_SIDEBAR_RADIUS = 22.0

# 导航项顺序、key、显示文字与内嵌图标文件名（resources/icons/<name>.png）。
NAV_ITEMS = (
    ("launch", "启动", "launch"),
    ("download", "下载", "download"),
    ("settings", "设置", "settings"),
    ("package", "打包", "package"),
    ("about", "关于", "about"),
)


class NavItem(SpringPushButton):
    """单个导航项：内部图标标签 + 文字标签；选中时隐藏图标、只留文字。"""

    def __init__(self, key: str, text: str, icon_name: str, parent=None) -> None:
        super().__init__("", parent)
        self.nav_key = key
        self.setProperty("navItem", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(12)

        self.icon_label = QLabel()
        pix = QPixmap(resource_path(f"icons/{icon_name}.png"))
        if not pix.isNull():
            self.icon_label.setPixmap(
                pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        row.addWidget(self.icon_label)

        self.text_label = QLabel(text)
        self.text_label.setProperty("navText", True)
        row.addWidget(self.text_label)
        row.addStretch(1)

    def set_active(self, active: bool) -> None:
        """切换选中态：隐藏图标只留文字；刷新按钮与文字标签的属性样式。"""
        self.setProperty("navActive", active)
        self.text_label.setProperty("navActive", active)
        self.icon_label.setVisible(not active)
        for widget in (self, self.text_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


class NavSidebar(QFrame):
    """五导航左侧栏；主窗口通过 ``navigateRequested`` 接收 key 并切换页面栈。"""

    navigateRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(172)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 16, 14, 16)
        root.setSpacing(10)

        self._build_brand(root)
        root.addSpacing(10)

        self._items: dict[str, NavItem] = {}
        for key, text, icon_name in NAV_ITEMS:
            item = NavItem(key, text, icon_name)
            item.clicked.connect(lambda _=False, k=key: self.navigateRequested.emit(k))
            self._items[key] = item
            root.addWidget(item)

        root.addStretch(1)

        # 默认选中「启动」。
        self.set_active("launch")

    def set_active(self, key: str) -> None:
        for item_key, item in self._items.items():
            item.set_active(item_key == key)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        paint_frosted_panel(
            painter,
            self,
            _SIDEBAR_RADIUS,
            C.COLOR_SIDEBAR_TOP_RGBA,
            C.COLOR_SIDEBAR_MID_RGBA,
            C.COLOR_SIDEBAR_BOTTOM_RGBA,
            C.COLOR_SIDEBAR_BORDER_RGBA,
        )
        # v1.3.9.0：导航栏七色染色（普通档下同样叠色）。
        # v1.3.9.3：染色裁剪到与磨砂面板一致的 22px 圆角路径，避免 fillRect 方角盖住圆角。
        tint = appearance.nav_tint_rgba()
        if tint is not None:
            clip = QPainterPath()
            inner = QRectF(self.rect()).adjusted(0.0, 0.0, -1.0, -1.0)
            clip.addRoundedRect(inner, _SIDEBAR_RADIUS, _SIDEBAR_RADIUS)
            painter.fillPath(clip, QColor(*tint))
        painter.end()

    def refresh_brand(self, config) -> None:
        """按 config 重建品牌区 logo 与名字，并按显隐开关整体隐藏对应元素。"""
        pix = QPixmap(brand.logo_path(config))
        if not pix.isNull():
            self._brand_logo.setPixmap(
                pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self._brand_name.setText(brand.short_name(config))
        self._brand_logo.setVisible(brand.logo_visible(config))
        self._brand_name.setVisible(brand.name_visible(config))

    def _build_brand(self, root: QVBoxLayout) -> None:
        """品牌区：LOGO + 名字（默认 CLY，可在设置页改写）；版本号只在关于页展示。"""
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        self._brand_logo = QLabel()
        pix = QPixmap(resource_path("cloud_logo.png"))
        if not pix.isNull():
            self._brand_logo.setPixmap(
                pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        brand_row.addWidget(self._brand_logo)

        self._brand_name = QLabel(C.APP_NAME)
        self._brand_name.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {C.COLOR_TEXT};"
        )
        brand_row.addWidget(self._brand_name)
        brand_row.addStretch(1)

        root.addLayout(brand_row)
