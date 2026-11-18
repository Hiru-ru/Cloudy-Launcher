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

"""自绘胶囊加载进度条。

背景：QProgressBar 原生 ``::chunk`` 子控件在 Qt 样式表下只画矩形填充段，
``border-radius`` 对填充端头不生效（A/B 对照实测：去 margin、去边框、加大圆角均无效），
导致进度到 40% 时填充右端是垂直方头、填满 100% 时整条被矩形填充盖住轨道圆角、
两端露直角，看起来仍是长条矩形。

本控件继承 QProgressBar，完整保留 ``setRange / setValue / setFormat / text()`` 等
对外接口，仅重写 ``paintEvent``：轨道与填充都用 ``QPainterPath`` 圆角矩形绘制，
半径严格等于内容高度一半（正半圆胶囊），任意进度比例与填满状态下两端都是圆弧；
配色沿用 constants 既有通透玻璃数值，不引入新依赖、不改布局与信号。
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import QProgressBar

# 轨道 / 填充颜色数值（与 constants 中 QSS rgba 字符串一一对应，alpha 取 0-255）
_TRACK = QColor(255, 255, 255, 44)
_TRACK_BORDER = QColor(190, 222, 238, 34)
_CHUNK_LEFT = QColor(170, 216, 238, 110)
_CHUNK_RIGHT = QColor(130, 192, 224, 96)
_TEXT = QColor(0x2B, 0x47, 0x59)

_BAR_HEIGHT = 18
_BORDER = 1.0


class CapsuleProgressBar(QProgressBar):
    """两端正半圆胶囊形态的通透玻璃进度条（自绘，原生 chunk 不参与绘制）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_BAR_HEIGHT)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignCenter)
        # 关闭原生背景与边框绘制，轨道 / 填充全部由 paintEvent 自绘，避免 QSS 轨道
        # 与自绘图层叠加；该本地表只作用于本控件自身，不影响兄弟控件。
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 内容区：四周各留 _BORDER 描边余量
        inner = QRectF(self.rect()).adjusted(_BORDER, _BORDER, -_BORDER, -_BORDER)
        radius = inner.height() / 2.0

        # ---- 轨道胶囊底 ----
        track_path = QPainterPath()
        track_path.addRoundedRect(inner, radius, radius)
        painter.fillPath(track_path, _TRACK)
        pen = painter.pen()
        pen.setColor(_TRACK_BORDER)
        pen.setWidthF(_BORDER)
        painter.setPen(pen)
        painter.strokePath(track_path, pen)

        # ---- 填充胶囊（任意比例端头均为圆弧）----
        span = self.maximum() - self.minimum()
        fraction = 0.0
        if span > 0:
            fraction = (self.value() - self.minimum()) / span
        fraction = max(0.0, min(1.0, fraction))

        if fraction > 0.0:
            fill_w = inner.width() * fraction
            fill_rect = QRectF(inner.left(), inner.top(), fill_w, inner.height())
            chunk_path = QPainterPath()
            chunk_path.addRoundedRect(fill_rect, radius, radius)

            gradient = QLinearGradient(inner.left(), 0, inner.right(), 0)
            gradient.setColorAt(0.0, _CHUNK_LEFT)
            gradient.setColorAt(1.0, _CHUNK_RIGHT)
            painter.fillPath(chunk_path, gradient)

        # ---- 居中文字（self.text() 已处理 format 中的 %p / %v）----
        painter.setPen(_TEXT)
        font = QFont(self.font())
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

        painter.end()
