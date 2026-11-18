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

"""云朵桌宠头顶对话气泡（自绘 QWidget，仅 PySide6）。

圆角白气泡 + 底部小三角，淡入、停留、淡出；尺寸随文字自适应，绝对定位在
角色头顶。由 ``PetWindow`` 调用 ``show_text`` 触发（如「我饿了」）。
"""
from PySide6.QtCore import (
    QPointF, QPropertyAnimation, QRectF, QTimer, Qt,
)
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPolygonF,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

# 气泡在窗口内的水平安全边距与顶部位置（像素）。
_MARGIN = 3
_TOP = 2
_PAD_X = 9
_PAD_Y = 6
_RADIUS = 9
_TAIL_W = 11
_TAIL_H = 7
_FADE_MS = 180


class SpeechBubble(QWidget):
    """带小三角的对话气泡，支持淡入淡出与定时消失。"""

    def __init__(self, parent, window_width: int):
        super().__init__(parent)
        self._window_width = window_width
        self._text = ""
        font = QFont()
        font.setPixelSize(13)
        font.setBold(True)
        self._font = font

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

        # 透明度效果 + 两个独立的淡入 / 淡出动画，避免 finished 信号重复连接。
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(_FADE_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(_FADE_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self.hide)

        # 停留计时：到点开始淡出。
        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.timeout.connect(self._begin_fade_out)

    # ---------- 对外 ----------
    def show_text(self, text: str, hold_ms: int = 2000) -> None:
        self._text = text
        self._resize_to_text()
        self._reposition()
        self._hold.stop()
        self._fade_out.stop()
        self.show()
        self.raise_()
        self._fade_in.stop()
        self._fade_in.start()
        self._hold.start(hold_ms)

    def hide_now(self) -> None:
        """立即隐藏（鼠标一动打断时调用）。"""
        self._hold.stop()
        self._fade_in.stop()
        self._fade_out.stop()
        self._effect.setOpacity(0.0)
        self.hide()

    # ---------- 尺寸与定位 ----------
    def _resize_to_text(self) -> None:
        metrics = QFontMetrics(self._font)
        text_w = metrics.horizontalAdvance(self._text)
        text_h = metrics.height()
        max_w = self._window_width - 2 * _MARGIN
        w = min(max_w, text_w + 2 * _PAD_X)
        h = text_h + 2 * _PAD_Y + _TAIL_H
        self.setFixedSize(w, h)

    def _reposition(self) -> None:
        x = max(_MARGIN, (self._window_width - self.width()) // 2)
        self.move(x, _TOP)

    def _begin_fade_out(self) -> None:
        self._fade_in.stop()
        self._fade_out.stop()
        self._fade_out.start()

    # ---------- 绘制 ----------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body_h = self.height() - _TAIL_H

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), body_h), _RADIUS, _RADIUS)
        cx = self.width() / 2.0
        tail = QPolygonF([
            QPointF(cx - _TAIL_W / 2, body_h - 0.5),
            QPointF(cx + _TAIL_W / 2, body_h - 0.5),
            QPointF(cx, body_h + _TAIL_H),
        ])
        path.addPolygon(tail)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 243))
        painter.drawPath(path)
        # 细描边，让气泡在浅色背景上也有轮廓。
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(0, 0, 0, 38))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), body_h), _RADIUS, _RADIUS)

        painter.setPen(QColor("#2f3542"))
        painter.setFont(self._font)
        painter.drawText(QRectF(0, 0, self.width(), body_h),
                         Qt.AlignmentFlag.AlignCenter, self._text)
