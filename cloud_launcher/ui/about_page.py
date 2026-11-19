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

"""About page: brand strip + feedback card + release notes + acknowledgements.

按手绘线框上下四块：

1. 顶部品牌横条卡：左侧 Logo，右侧名称与版本号；Logo / 名称的显隐仍跟随
   设置页个性化开关（:mod:`brand`），版本号始终展示。
2. 「问题反馈」卡：写明作者反馈 QQ（:data:`constants.AUTHOR_QQ`），号码可
   鼠标选中复制，遇到问题或 Bug 可加此号联系作者。
3. 下方「本版本介绍」卡：逐条列出 :data:`constants.ABOUT_RELEASE_NOTES`。
4. 底部「致谢」卡：以小字号列出 :data:`constants.ACK_NOTES`，感谢 DeepSeek
   大模型与 DeepSeek 团队，并标注机器翻译免责。

品牌名 / 版本号沿用英文口径；介绍正文为中文。纯 PySide6 + 标准库。
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import brand
from .. import constants as C
from .card_widget import Card


class AboutPage(QWidget):
    """上下两块的关于页：品牌横条（Logo / 名称 / 版本）+ 本版本介绍。"""

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self.setObjectName("about-page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_widget = QWidget()
        list_widget.setObjectName("settingsList")
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(12)

        self._build_brand_card()
        self._build_feedback_card()
        self._build_notes_card()
        self._build_ack_card()
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

        self.refresh_brand(config)

    # ------------------------------------------------------------------ #
    # 卡片构建
    # ------------------------------------------------------------------ #
    def _build_brand_card(self) -> None:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setAlignment(Qt.AlignVCenter)

        self._logo = QLabel()
        self._logo.setAlignment(Qt.AlignCenter)
        self._logo.setFixedSize(64, 64)
        row.addWidget(self._logo)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        self._name = QLabel()
        self._name.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {C.COLOR_TEXT};"
        )
        text_col.addWidget(self._name)

        self._version = QLabel(C.ABOUT_VERSION_LABEL)
        self._version.setStyleSheet(
            f"font-size: 13px; color: {C.COLOR_TEXT_LIGHT};"
        )
        text_col.addWidget(self._version)

        row.addLayout(text_col)
        row.addStretch(1)
        card.add_layout(row)
        self._list_layout.addWidget(card)

    def _build_feedback_card(self) -> None:
        card = Card("问题反馈")

        tip = QLabel("使用中遇到任何问题或 Bug，都可以加作者 QQ 联系反馈。")
        tip.setWordWrap(True)
        tip.setProperty("fieldLabel", True)
        card.add_widget(tip)

        qq_row = QHBoxLayout()
        qq_row.setSpacing(8)
        qq_caption = QLabel("作者 QQ：")
        qq_caption.setProperty("fieldLabel", True)
        qq_row.addWidget(qq_caption)

        self._qq = QLabel(C.AUTHOR_QQ)
        self._qq.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {C.COLOR_TEXT};"
        )
        self._qq.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._qq.setCursor(Qt.IBeamCursor)
        qq_row.addWidget(self._qq)
        qq_row.addStretch(1)
        card.add_layout(qq_row)

        self._list_layout.addWidget(card)

    def _build_notes_card(self) -> None:
        card = Card("本版本介绍")
        self._note_labels: list[QLabel] = []
        for item in C.ABOUT_RELEASE_NOTES:
            lab = QLabel("• " + item)
            lab.setWordWrap(True)
            lab.setProperty("fieldLabel", True)
            card.add_widget(lab)
            self._note_labels.append(lab)
        self._list_layout.addWidget(card)

    def _build_ack_card(self) -> None:
        """小字体致谢卡：小云 AI 所用模型与开源团队，字号小于正文，低调列出。"""
        card = Card(C.ACK_TITLE)
        for item in C.ACK_NOTES:
            lab = QLabel(item)
            lab.setWordWrap(True)
            lab.setStyleSheet(
                f"font-size: 11px; color: {C.COLOR_TEXT_LIGHT}; "
                "background: transparent;"
            )
            card.add_widget(lab)
        self._list_layout.addWidget(card)

    # ------------------------------------------------------------------ #
    # 品牌回填
    # ------------------------------------------------------------------ #
    def refresh_brand(self, config) -> None:
        """按 config 重建关于页 logo 与名字，并按显隐开关隐藏对应元素。"""
        self._config = config
        pix = QPixmap(brand.logo_path(config))
        if not pix.isNull():
            self._logo.setPixmap(
                pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self._name.setText(brand.full_name(config))
        self._logo.setVisible(brand.logo_visible(config))
        self._name.setVisible(brand.name_visible(config))
