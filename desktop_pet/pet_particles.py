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

"""云朵桌宠情绪粒子：透明覆盖层，自绘爱心 / 音符 / 问号 / Zzz（仅 PySide6 + 标准库）。

粒子从指定位置（默认角色头顶）生成，向上漂浮并左右轻摆，开头淡入、结尾淡出，
寿命结束自动移除。覆盖层不接收鼠标事件，不影响桌宠交互。

符号全部由 ``QPainter`` 自绘（爱心 / 音符用路径，问号 / Zzz 用粗体文字），
不依赖外部图片。
"""
import math
import random

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QWidget

import pet_constants as P

HEART = "heart"
NOTE = "note"
QUESTION = "question"
ZZZ = "zzz"

_LIFE = {HEART: 1.4, NOTE: 1.6, QUESTION: 1.2, ZZZ: 1.8}
_RISE = 24.0          # 上浮速度（像素/秒）
_SWAY = 3.2           # 左右摆幅（像素）
_SWAY_HZ = 2.0


class ParticleLayer(QWidget):
    """透明粒子覆盖层：铺满父窗口，自管理粒子生命周期。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("particle-layer")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setGeometry(0, 0, P.PET_WINDOW_WIDTH, P.PET_WINDOW_HEIGHT)
        self._particles = []
        self._timer = QTimer(self)
        self._timer.setInterval(P.POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def emit(self, kind, x=None, y=None) -> None:
        """在 (x,y) 发射一个粒子；缺省在角色头顶，位置带少量随机抖动。"""
        if x is None:
            x = P.PET_WINDOW_WIDTH / 2.0
        if y is None:
            y = 26.0
        self._particles.append({
            "kind": kind,
            "x": x + random.uniform(-4.0, 4.0),
            "y": y + random.uniform(-3.0, 3.0),
            "t": 0.0,
            "life": _LIFE[kind],
            "phase": random.uniform(0.0, math.pi * 2.0),
            "scale": random.uniform(0.85, 1.15),
        })
        self.update()

    def heart(self, x=None, y=None) -> None:
        self.emit(HEART, x, y)

    def note(self, x=None, y=None) -> None:
        self.emit(NOTE, x, y)

    def question(self, x=None, y=None) -> None:
        self.emit(QUESTION, x, y)

    def zzz(self, x=None, y=None) -> None:
        self.emit(ZZZ, x, y)

    def clear(self) -> None:
        self._particles = []
        self.update()

    def _tick(self) -> None:
        dt = P.POLL_INTERVAL_MS / 1000.0
        alive = []
        for p in self._particles:
            p["t"] += dt
            if p["t"] < p["life"]:
                alive.append(p)
        self._particles = alive
        self.update()

    # ---------- 绘制 ----------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        for p in self._particles:
            frac = p["t"] / p["life"]
            # 淡入 15%、淡出 30%。
            if frac < 0.15:
                alpha = frac / 0.15
            elif frac > 0.7:
                alpha = max(0.0, (1.0 - frac) / 0.3)
            else:
                alpha = 1.0
            cx = p["x"] + _SWAY * math.sin(
                2.0 * math.pi * _SWAY_HZ * p["t"] + p["phase"])
            cy = p["y"] - _RISE * p["t"]
            painter.save()
            painter.translate(QPointF(cx, cy))
            painter.scale(p["scale"], p["scale"])
            self._draw_one(painter, p["kind"], alpha)
            painter.restore()
        painter.end()

    def _draw_one(self, p, kind, alpha) -> None:
        if kind == HEART:
            self._draw_heart(p, QColor(235, 86, 110, int(255 * alpha)))
        elif kind == NOTE:
            self._draw_note(p, QColor(90, 150, 220, int(255 * alpha)))
        elif kind == QUESTION:
            self._draw_text(p, "?", QColor(120, 130, 150, int(255 * alpha)))
        else:
            self._draw_text(p, "Z", QColor(130, 140, 165, int(255 * alpha)))

    def _draw_heart(self, p, color) -> None:
        s = 6.0
        path = QPainterPath()
        # 经典爱心：两段三次贝塞尔，起点/收点在底部尖角。
        path.moveTo(0, s)
        path.cubicTo(-2.1 * s, 0.25 * s, -1.15 * s, -1.05 * s, 0, -0.35 * s)
        path.cubicTo(1.15 * s, -1.05 * s, 2.1 * s, 0.25 * s, 0, s)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)

    def _draw_note(self, p, color) -> None:
        pen = QPen(color)
        pen.setWidthF(1.8)
        p.setPen(pen)
        # 符干。
        p.drawLine(QPointF(3.5, -7.0), QPointF(3.5, 1.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        # 音符头（椭圆）。
        p.drawEllipse(QPointF(1.2, 1.5), 3.4, 2.5)

    def _draw_text(self, p, text, color) -> None:
        font = QFont()
        font.setBold(True)
        font.setPixelSize(15)
        p.setFont(font)
        p.setPen(color)
        rect = QRectF(-8.0, -10.0, 16.0, 14.0)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
