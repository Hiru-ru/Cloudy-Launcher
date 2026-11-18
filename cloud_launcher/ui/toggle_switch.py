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

"""自绘 iOS 风格滑块开关（仅 PySide6）。

主题里没有现成的滑块（QCheckBox 是方形勾选），因此本组件自绘：圆角轨道 + 白色圆钮，
开启时轨道为主色、圆钮滑到右侧，关闭时轨道为灰色、圆钮在左侧；圆钮位置与轨道颜色
随 ``QPropertyAnimation`` 平滑过渡。点击即切换并发出 ``toggled`` 信号。
"""
from PySide6.QtCore import Property, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from .. import constants as C

_TRACK_W = 42
_TRACK_H = 25
_MARGIN = 2
_OFF_COLOR = QColor("#c2c8d0")
_ON_COLOR = QColor(C.COLOR_PRIMARY)


class ToggleSwitch(QWidget):
    """iOS 滑块：setChecked/isChecked + toggled 信号。"""

    toggled = Signal(bool)

    def __init__(self, checked: bool = True, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._knob = 1.0 if self._checked else 0.0
        self.setFixedSize(_TRACK_W, _TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)

    def _get_knob(self) -> float:
        return self._knob

    def _set_knob(self, value: float) -> None:
        self._knob = float(value)
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        self._animate()
        self.toggled.emit(value)

    def _animate(self) -> None:
        target = 1.0 if self._checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.setChecked(not self._checked)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = _TRACK_H / 2.0

        # 轨道颜色随圆钮位置在灰→主色间插值。
        k = self._knob
        track = QColor(
            int(_OFF_COLOR.red() + (_ON_COLOR.red() - _OFF_COLOR.red()) * k),
            int(_OFF_COLOR.green() + (_ON_COLOR.green() - _OFF_COLOR.green()) * k),
            int(_OFF_COLOR.blue() + (_ON_COLOR.blue() - _OFF_COLOR.blue()) * k),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(0, 0, _TRACK_W, _TRACK_H, radius, radius)

        # 白色圆钮：沿轨道滑动。
        knob_d = _TRACK_H - 2 * _MARGIN
        x = _MARGIN + (_TRACK_W - _TRACK_H) * self._knob
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(round(x)), _MARGIN, knob_d, knob_d)
        painter.end()
