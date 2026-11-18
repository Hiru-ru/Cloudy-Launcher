# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Cloudy Pet / 云朵桌宠
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

"""云朵桌宠喂食菜单（自绘独立弹出窗，仅 PySide6）。

鼠标悬停静止到阈值后，在桌宠窗口上方弹出圆角白卡片。菜单分「喂自己」与「喂小狗」
两组：狼可见时才显示喂狗条目（骨头 / 生肉）。点击条目通过 ``on_pick(target, food_id)``
把目标与食物 id 交给 ``PetWindow``。独立窗口定位，不被桌宠小窗裁剪。
"""
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

import pet_constants as P

# 喂自己（桌宠角色）条目：(id, 文案, 图标相对 resources 的路径)。
SELF_ITEMS = [
    ("beef", "喂牛排", "items/cooked_beef.png"),
    ("porkchop", "喂猪排", "items/cooked_porkchop.png"),
]
# 喂小狗（驯服狼）条目。
WOLF_ITEMS = [
    ("bone", "喂狗骨头", "items/bone.png"),
    ("raw_beef", "喂狗生肉", "items/raw_beef.png"),
    ("raw_porkchop", "喂狗生排", "items/raw_porkchop.png"),
]

_RADIUS = 9
_CARD_W = 118
_ROW_H = 27
_HEADER_H = 18
_PAD = 5
_ICON = 18
_GAP = 6


class FeedMenu(QWidget):
    """圆角喂食菜单独立窗，支持分组、悬停高亮与点击选择。"""

    def __init__(self, on_pick):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # on_pick(target, food_id)：target 为 "self" 或 "wolf"。
        self._on_pick = on_pick
        self._hover = -1
        self._rows = []          # 扁平行：("header",文案) 或 ("item",id,文案,图标,target)
        self._icons = {}
        font = QFont()
        font.setPixelSize(13)
        self._font = font
        hfont = QFont()
        hfont.setPixelSize(11)
        hfont.setBold(True)
        self._hfont = hfont
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.hide()

    # ---------- 条目构建 ----------
    def _build_rows(self, wolf_visible: bool) -> None:
        rows = [("header", "喂自己")]
        for fid, label, icon in SELF_ITEMS:
            rows.append(("item", fid, label, icon, "self"))
        if wolf_visible:
            rows.append(("header", "喂小狗"))
            for fid, label, icon in WOLF_ITEMS:
                rows.append(("item", fid, label, icon, "wolf"))
            # 摸小狗：无食物图标的动作条目。
            rows.append(("item", "pet_dog", "摸小狗", None, "pet"))
        self._rows = rows
        self._icons = {}
        for kind, *rest in rows:
            if kind != "item":
                continue
            fid, _label, icon, _target = rest
            if icon is None:
                continue
            pix = QPixmap(P.resource_path(icon))
            self._icons[fid] = pix.scaled(
                _ICON, _ICON, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation)
        height = _PAD
        for kind, *_ in rows:
            height += _HEADER_H if kind == "header" else _ROW_H
        height += _PAD
        self.setFixedSize(_CARD_W, height)

    # ---------- 对外 ----------
    def show_menu(self, win_geom, wolf_visible=False) -> None:
        self._hover = -1
        self._build_rows(wolf_visible)
        # 水平居中对齐桌宠窗口；优先放上方，上方空间不足则放下方。
        x = win_geom.center().x() - self.width() // 2
        screen = QApplication.primaryScreen().availableGeometry()
        top_y = win_geom.top() - self.height() - _GAP
        if top_y < screen.top():
            top_y = win_geom.bottom() + _GAP
        self.move(x, top_y)
        self.show()
        self.raise_()

    # ---------- 行几何 ----------
    def _row_top(self, index: int) -> int:
        top = _PAD
        for i in range(index):
            kind = self._rows[i][0]
            top += _HEADER_H if kind == "header" else _ROW_H
        return top

    def _row_rect(self, index: int) -> QRectF:
        kind = self._rows[index][0]
        h = _HEADER_H if kind == "header" else _ROW_H
        return QRectF(2, self._row_top(index), self.width() - 4, h - 2)

    def _index_at(self, pos: QPoint) -> int:
        for i in range(len(self._rows)):
            if self._rows[i][0] != "item":
                continue
            if self._row_rect(i).contains(pos):
                return i
        return -1

    # ---------- 鼠标 ----------
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        idx = self._index_at(event.position())
        if idx != self._hover:
            self._hover = idx
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        idx = self._index_at(event.position())
        if idx >= 0:
            _kind, fid, _label, _icon, target = self._rows[idx]
            self._on_pick(target, fid)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    # ---------- 绘制 ----------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), _RADIUS, _RADIUS)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 245))
        painter.drawPath(path)

        for i, row in enumerate(self._rows):
            kind = row[0]
            rect = self._row_rect(i)
            if kind == "header":
                painter.setFont(self._hfont)
                painter.setPen(QColor("#8a919c"))
                painter.drawText(
                    QRectF(rect.left() + 5, rect.top(), rect.width(), rect.height()),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, row[1])
                continue
            _kind, fid, label, _icon, target = row
            if i == self._hover:
                painter.setBrush(QColor(64, 132, 246, 38))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 7, 7)
            icon = self._icons.get(fid)
            text_x = rect.left() + 6
            if icon is not None:
                iy = int(rect.top() + (rect.height() - _ICON) / 2)
                painter.drawPixmap(int(rect.left() + 6), iy, icon)
                text_x = rect.left() + 6 + _ICON + 6
            painter.setFont(self._font)
            painter.setPen(QColor("#2f3542"))
            text_rect = QRectF(text_x, rect.top(),
                               rect.right() - text_x - 4, rect.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter
                             | Qt.AlignmentFlag.AlignLeft, label)

        # 整体细描边。
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(0, 0, 0, 38))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), _RADIUS, _RADIUS)
