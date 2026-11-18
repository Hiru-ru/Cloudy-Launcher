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

"""v1.3.11.0 整合包「选版本 + 命名」玻璃浮层。

点整合包卡片「下载」后，先在后台拉到该整合包的 ``.mrpack`` 版本列表，再由本浮层让
用户：

1. 选一个整合包版本（单选，标注整合包版本号、对应 MC 版本、加载器、文件大小）；
2. 自定义实例名称——留空则用整合包自己的名字（项目标题）作为默认名；
3. 名字实时校验：含 Windows 非法字符，或与已有实例重名（``alias_exists``），
   确认按钮直接禁用并给出原因，**绝不静默改名**，必须用户自己改到可用为止。

不参与父布局，由 :meth:`reposition` 手动定位居中。为与现有 :class:`ContentVersionPicker`
观感统一，外层与各子控件复用同一套 QSS 对象名，命名输入用现成的 ``customNameField``。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C, game_dirs
from .frosted_backdrop import capture_live_backdrop, paint_frosted_panel

_MAX_LIST = 200
# Windows 目录名非法字符。
_ILLEGAL_CHARS = set('\\/:*?"<>|')


def _format_size(value: int) -> str:
    if value >= 1_048_576:
        return f"{value / 1_048_576:.1f}MB"
    if value >= 1024:
        return f"{value / 1024:.0f}KB"
    return f"{value}B"


class ModpackInstallDialog(QFrame):
    """整合包版本选择 + 命名浮层；确认后发 ``(选中版本, 最终别名)``。"""

    cancelled = Signal()
    confirmed = Signal(object, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # 与 ContentVersionPicker 同款自绘磨砂底板（不再依赖 WA_StyledBackground/QSS）。
        self.setObjectName("contentVersionPicker")
        self.hide()

        self._versions: list[dict] = []
        self._default_name = ""
        # 弹出前抓到的父控件真实背景：无壁纸时也能把后方密集卡片柔化压住，不做白板。
        self._live_ref = None
        self._live_clear = None
        self._live_blur = None
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("选择版本并命名")
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

        self._subtitle = QLabel("")
        self._subtitle.setObjectName("contentPickerSubtitle")
        self._subtitle.setFixedHeight(18)
        root.addWidget(self._subtitle)

        # 版本列表：滚动条 AlwaysOff，滚轮仍可滚。
        self._scroll = QScrollArea()
        self._scroll.setObjectName("contentPickerScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)

        self._list_host = QWidget()
        self._list_host.setObjectName("contentPickerList")
        self._list_host.setAutoFillBackground(False)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._scroll.setWidget(self._list_host)
        root.addWidget(self._scroll, 0)

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

        self._hint = QLabel("")
        self._hint.setObjectName("contentPickerFooter")
        self._hint.setWordWrap(True)
        self._hint.setFixedHeight(28)
        root.addWidget(self._hint)

        # 错误提示固定占位，避免显隐时界面跳动。
        self._error = QLabel("")
        self._error.setObjectName("modpackError")
        self._error.setWordWrap(True)
        self._error.setFixedHeight(18)
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

        self._group.buttonClicked.connect(lambda _b: self._refresh())

    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        # 自绘局部磨砂，随外观设置在磨砂/通透/普通三档间切换。
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        live = None
        if self._live_clear is not None and self._live_ref is not None:
            live = (self._live_clear, self._live_blur, self._live_ref)
        paint_frosted_panel(
            painter,
            self,
            18.0,
            C.COLOR_GLASS_TOP_RGBA,
            C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA,
            C.COLOR_CARD_BORDER_RGBA,
            live=live,
        )
        painter.end()

    # ------------------------------------------------------------------ #
    def open_for(self, item: dict, versions: list[dict]) -> None:
        """按项目与版本列表铺开浮层，重置命名与校验状态。"""
        self._default_name = str(item.get("title") or "").strip()
        self._versions = list(versions)
        self._build_versions()
        self._name_input.clear()
        self._name_input.setPlaceholderText(
            "留空则默认命名为：%s" % (self._default_name or "整合包"))
        self._subtitle.setText(str(item.get("title", "")))
        self._hint.setText(
            "可自定义实例名称；留空就用整合包自己的名字。名字与已有实例重名时不能用。")
        self._error.setText("")
        self._error.hide()
        self.reposition()
        # 自身显示前抓取父控件真实渲染（此刻本浮层仍隐藏，不会被抓进去），作为磨砂底板。
        self._live_ref = self.parentWidget()
        self._live_clear, self._live_blur = capture_live_backdrop(self._live_ref)
        self.show()
        self.raise_()
        self._refresh()

    def _build_versions(self) -> None:
        while self._list_layout.count():
            old = self._list_layout.takeAt(0)
            w = old.widget()
            if w is not None:
                w.deleteLater()
        for version in self._versions:
            mc = version.get("game_versions") or []
            mc_text = "/".join(mc[:2]) if mc else "版本未知"
            loaders = version.get("loaders") or []
            loader_text = "、".join(loaders) if loaders else "原版"
            number = version.get("version_number") or version.get("version_id") or "?"
            label = "%s　·　MC %s　·　%s　·　%s" % (
                number, mc_text, loader_text,
                _format_size(int(version.get("size") or 0)))
            btn = QPushButton(label)
            btn.setProperty("versionOption", True)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            self._group.addButton(btn)
            self._list_layout.addWidget(btn)
        if self._group.buttons():
            self._group.buttons()[0].setChecked(True)
        self._list_layout.addStretch(1)

    def reposition(self) -> None:
        """父控件内居中；高度按固定非列表预算 + 列表高度计算。"""
        parent = self.parentWidget()
        if parent is None:
            return
        count = max(1, len(self._versions))
        list_h = min(_MAX_LIST, count * 42)
        self._scroll.setFixedHeight(list_h)
        height = 240 + list_h
        width = max(340, min(460, parent.width() - 48))
        height = min(height, max(240, parent.height() - 24))
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
            return False, ("名称不能包含 \\ / : * ? \" < > | 这些字符，请改一个。")
        if game_dirs.alias_exists(name):
            return False, ("名字「%s」已被占用，这个名字不能用，请换一个。" % name)
        return True, ""

    def _refresh(self) -> None:
        ok, message = self._validate()
        has_selection = self._group.checkedButton() is not None
        if message:
            self._error.setText(message)
            self._error.show()
        else:
            self._error.setText("")
            self._error.hide()
        self._ok_btn.setEnabled(ok and has_selection)

    def _on_cancel(self) -> None:
        self.hide()
        self.cancelled.emit()

    def _on_ok(self) -> None:
        ok, _message = self._validate()
        checked = self._group.checkedButton()
        if not ok or checked is None:
            return
        index = self._group.buttons().index(checked)
        chosen = self._versions[index]
        alias = self._effective_name()
        self.hide()
        self.confirmed.emit(chosen, alias)
