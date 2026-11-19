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

"""设置页「AI」标签：导入独立小云 AI 程序并说明用途。

两张局部磨砂卡片：

1. 小云 AI 程序：通过文件选择导入小云 AI .exe 或其 .zip 发布包（复制到 ``CLY/ai``），
   未导入不可在版本设置中使用 AI 翻译；可移除或重新导入；
2. 功能说明：解释离线本地翻译、入口位置与机器翻译免责声明。

文件对话框只负责取路径，核心导入动作拆成独立方法以便离屏回归直接调用。
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import ai_controller as ac
from .. import constants as C
from .card_widget import Card


class AiSettingsPage(QWidget):
    """小云 AI 设置页（独立程序导入 + 说明）。"""

    def __init__(self, config, host, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ai-settings-page")
        self._config = config
        self._host = host

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

        self._build_app_section()
        self._build_about_section()
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # 卡片 1：小云 AI 程序导入
    # ------------------------------------------------------------------
    def _build_app_section(self) -> None:
        card = Card("小云 AI 程序")
        self._app_status = QLabel()
        self._app_status.setProperty("hintLabel", True)
        self._app_status.setWordWrap(True)
        card.add_widget(self._app_status)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._import_btn = QPushButton("导入小云 AI")
        self._import_btn.setProperty("ghostAction", True)
        self._import_btn.setCursor(Qt.PointingHandCursor)
        self._import_btn.clicked.connect(self._on_choose_app)
        self._remove_btn = QPushButton("移除")
        self._remove_btn.setProperty("ghostAction", True)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.clicked.connect(self._on_remove_app)
        layout.addWidget(self._import_btn)
        layout.addWidget(self._remove_btn)
        layout.addStretch(1)
        card.add_widget(row)
        self._list_layout.addWidget(card)

    def _on_choose_app(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, "选择小云 AI 程序", "", "小云 AI 程序 (*.exe *.zip)")
        if src:
            self.import_app(src)

    def import_app(self, src: str) -> bool:
        """核心导入动作：复制/解压到固定路径并写 config；成功返回 True。"""
        try:
            path = ac.import_ai_app(src)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Cloudy Launcher", f"小云 AI 导入失败：{exc}")
            return False
        self._config.ai_app_path = path
        self._config.save()
        self.refresh()
        return True

    def _on_remove_app(self) -> None:
        try:
            ac.remove_ai_app()
        except OSError as exc:
            QMessageBox.warning(self, "Cloudy Launcher",
                                f"小云 AI 仍被占用，移除失败：{exc}")
            return
        self._config.ai_app_path = ""
        self._config.save()
        self.refresh()

    # ------------------------------------------------------------------
    # 卡片 2：功能说明
    # ------------------------------------------------------------------
    def _build_about_section(self) -> None:
        card = Card("功能说明")
        text = QLabel(
            "· 小云 AI 是独立的本地翻译程序，使用本地 DeepSeek 模型，离线运行、"
            "不上传任何数据。\n"
            "· 用途：把当前版本的 mod、材质包、整合包中的英文语言文件翻译成简体中文，"
            "并生成可在游戏内启用的汉化资源包；已有中文的条目会自动跳过。\n"
            "· 入口：打开「版本设置 → 高级功能 → AI 翻译」，仅处理当前版本。\n"
            "· 必须先在本页导入小云 AI，否则无法翻译。\n"
            "· " + C.TRANSLATION_DISCLAIMER)
        text.setWordWrap(True)
        card.add_widget(text)
        self._list_layout.addWidget(card)

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        path = self._config.ai_app_path
        if path and os.path.isfile(path):
            self._app_status.setText("已导入：" + os.path.basename(path))
            self._remove_btn.setEnabled(True)
        else:
            self._app_status.setText("尚未导入小云 AI 程序，请先导入后再使用 AI 翻译。")
            self._remove_btn.setEnabled(False)

    def shutdown(self) -> None:
        """启动器退出：小云 AI 为按需拉起，无常驻进程，这里仅保留接口。"""
        return
