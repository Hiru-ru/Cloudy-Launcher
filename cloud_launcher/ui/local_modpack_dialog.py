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

"""v1.3.22.0 本地整合包拖拽遮罩 + 命名浮层。

全局拖拽导入的两块界面，均为纯 PySide6 + 标准库，不参与父布局、手动定位：

- :class:`DragDropOverlay`：拖文件进窗口时铺满整窗的半透明遮罩，中间虚线框 + 提示
  「松开鼠标，导入整合包」，拖出窗口或放下后隐藏；
- :class:`LocalModpackNameDialog`：放下后让用户确认实例名的磨砂浮层（本地文件无需选
  版本），展示文件名、识别到的格式、MC 版本与加载器；名字实时校验非法字符与重名，
  绝不静默改名。确认发 ``confirmed(alias)``，取消发 ``cancelled``。
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C, game_dirs
from .. import modpack_format as mpf
from .frosted_backdrop import capture_live_backdrop, paint_frosted_panel

_ILLEGAL_CHARS = set('\\/:*?"<>|')

FORMAT_LABELS = {
    mpf.FORMAT_MODRINTH: "Modrinth 整合包 (.mrpack)",
    mpf.FORMAT_CURSEFORGE: "CurseForge 整合包",
    mpf.FORMAT_MULTIMC: "MultiMC / Prism 整合包",
    mpf.FORMAT_MCBBS: "MCBBS 整合包",
    mpf.FORMAT_OFFLINE: "离线完整整合包",
}


# --------------------------------------------------------------------------- #
# 拖拽遮罩
# --------------------------------------------------------------------------- #
class DragDropOverlay(QWidget):
    """铺满主窗口的拖拽提示遮罩（自绘，半透明 + 虚线框）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("dragDropOverlay")
        self._resolving = False
        self.hide()

    def show_overlay(self) -> None:
        self._resolving = False
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.update()

    def show_resolving(self) -> None:
        """放下后保持遮罩，切换为「正在解析」提示。"""
        self._resolving = True
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 整窗一层深色半透明压暗，让后方页面退后。
        painter.fillRect(self.rect(), QColor(28, 42, 56, 118))

        margin = 22
        box = self.rect().adjusted(margin, margin, -margin, -margin)
        radius = 22.0
        path = QPainterPath()
        path.addRoundedRect(box, radius, radius)

        if not self._resolving:
            # 虚线高亮框（白色偏亮）。
            pen = QPen(QColor(255, 255, 255, 228))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            pen.setDashPattern([10, 7])
            painter.setPen(pen)
            painter.fillPath(path, QColor(255, 255, 255, 26))
            painter.drawPath(path)

            painter.setPen(QColor(255, 255, 255, 245))
            font = painter.font()
            font.setPointSize(17)
            painter.setFont(font)
            title_rect = box.adjusted(0, -box.height() * 0.12, 0, -box.height() * 0.12)
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignBottom,
                             "松开鼠标，导入整合包")

            sub_font = painter.font()
            sub_font.setPointSize(11)
            painter.setFont(sub_font)
            painter.setPen(QColor(255, 255, 255, 190))
            sub_rect = box.adjusted(0, box.height() * 0.06, 0, box.height() * 0.06)
            painter.drawText(sub_rect, Qt.AlignHCenter | Qt.AlignTop,
                             "支持 Modrinth / CurseForge / MultiMC / MCBBS / 离线包")
        else:
            painter.setPen(QColor(255, 255, 255, 245))
            font = painter.font()
            font.setPointSize(16)
            painter.setFont(font)
            painter.drawText(box, Qt.AlignCenter, "正在解析整合包…")
        painter.end()


# --------------------------------------------------------------------------- #
# 命名浮层
# --------------------------------------------------------------------------- #
class LocalModpackNameDialog(QFrame):
    """本地整合包命名浮层；确认后发最终别名。"""

    cancelled = Signal()
    confirmed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contentVersionPicker")
        self.hide()

        self._default_name = ""
        self._live_ref = None
        self._live_clear = None
        self._live_blur = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(9)

        title_row = QHBoxLayout()
        title = QLabel("导入整合包")
        title.setObjectName("contentPickerTitle")
        title.setFixedHeight(22)
        title_row.addWidget(title, 1)
        self._close = QPushButton("✕")
        self._close.setObjectName("contentPickerClose")
        self._close.setFixedSize(24, 24)
        self._close.setCursor(Qt.PointingHandCursor)
        self._close.clicked.connect(self._on_cancel)
        title_row.addWidget(self._close, 0, Qt.AlignTop)
        root.addLayout(title_row)

        self._file_label = QLabel("")
        self._file_label.setObjectName("contentPickerSubtitle")
        self._file_label.setWordWrap(True)
        root.addWidget(self._file_label)

        self._info_label = QLabel("")
        self._info_label.setObjectName("contentPickerFooter")
        self._info_label.setWordWrap(True)
        self._info_label.setFixedHeight(38)
        root.addWidget(self._info_label)

        name_caption = QLabel("实例名称")
        name_caption.setObjectName("contentPickerSubtitle")
        name_caption.setFixedHeight(18)
        root.addWidget(name_caption)

        self._name_input = QLineEdit()
        self._name_input.setObjectName("customNameField")
        self._name_input.setFixedHeight(38)
        self._name_input.setClearButtonEnabled(True)
        self._name_input.textChanged.connect(lambda _t: self._refresh())
        root.addWidget(self._name_input)

        self._error = QLabel("")
        self._error.setObjectName("modpackError")
        self._error.setWordWrap(True)
        self._error.setFixedHeight(20)
        self._error.hide()
        root.addWidget(self._error)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("contentPickerCancel")
        self._cancel_btn.setFixedSize(72, 32)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        self._ok_btn = QPushButton("开始安装")
        self._ok_btn.setObjectName("contentPickerOk")
        self._ok_btn.setFixedSize(96, 32)
        self._ok_btn.setCursor(Qt.PointingHandCursor)
        self._ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(self._ok_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        live = None
        if self._live_clear is not None and self._live_ref is not None:
            live = (self._live_clear, self._live_blur, self._live_ref)
        paint_frosted_panel(
            painter, self, 18.0,
            C.COLOR_GLASS_TOP_RGBA, C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA, C.COLOR_CARD_BORDER_RGBA,
            live=live)
        painter.end()

    # ------------------------------------------------------------------ #
    def open_for(self, path: str, plan: mpf.ModpackPlan) -> None:
        """按文件与已解析计划铺开浮层，预填默认名并校验。"""
        self._default_name = str(plan.suggested_name or "").strip()
        self._file_label.setText("文件：%s" % os.path.basename(path))
        fmt_text = FORMAT_LABELS.get(plan.format, plan.format)
        if plan.mc_version:
            loader_text = C.LOADER_LABELS.get(plan.loader_key, plan.loader_key)
            if plan.loader_version:
                loader_text = "%s %s" % (loader_text, plan.loader_version)
            info = "%s　·　MC %s　·　%s" % (
                fmt_text, plan.mc_version, loader_text)
        else:
            info = "%s　·　版本与加载器将按包内目录推断" % fmt_text
        self._info_label.setText(info)

        self._name_input.clear()
        self._name_input.setPlaceholderText(
            "留空则默认命名为：%s" % (self._default_name or "整合包"))
        self._error.setText("")
        self._error.hide()
        self.reposition()
        self._live_ref = self.parentWidget()
        self._live_clear, self._live_blur = capture_live_backdrop(self._live_ref)
        self.show()
        self.raise_()
        self._refresh()
        self._name_input.setFocus()

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        width = max(360, min(460, parent.width() - 48))
        height = 268
        x = max(6, (parent.width() - width) // 2)
        y = max(6, (parent.height() - height) // 2)
        self.setGeometry(x, y, width, height)

    # ------------------------------------------------------------------ #
    def _effective_name(self) -> str:
        text = self._name_input.text().strip()
        return text or self._default_name

    def _validate(self) -> tuple[bool, str]:
        name = self._effective_name()
        if not name:
            return False, ""
        illegal = sorted({ch for ch in name if ch in _ILLEGAL_CHARS})
        if illegal:
            return False, "名称不能包含 \\ / : * ? \" < > | 这些字符，请改一个。"
        if game_dirs.alias_exists(name):
            return False, "名字「%s」已被占用，这个名字不能用，请换一个。" % name
        return True, ""

    def _refresh(self) -> None:
        ok, message = self._validate()
        if message:
            self._error.setText(message)
            self._error.show()
        else:
            self._error.setText("")
            self._error.hide()
        self._ok_btn.setEnabled(ok)

    def _on_cancel(self) -> None:
        self.hide()
        self.cancelled.emit()

    def _on_ok(self) -> None:
        ok, _message = self._validate()
        if not ok:
            return
        alias = self._effective_name()
        self.hide()
        self.confirmed.emit(alias)
