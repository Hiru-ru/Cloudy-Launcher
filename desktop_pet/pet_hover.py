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

"""云朵桌宠鼠标悬停检测（仅标准库 + PySide6）。

每帧由 ``PetWindow`` 传入全局鼠标位置与帧间隔：鼠标在窗口内静止达到随机的
1~3 秒后，在窗口上方弹出喂食菜单；菜单打开后，鼠标在桌宠窗口或菜单区域内都
保持（允许移动到条目点击），离开这两个区域立即关闭。硬件级微小抖动在
``HOVER_JITTER_PX`` 内不重置。
"""
import math
import random

from PySide6.QtCore import QPoint

import pet_constants as P


class HoverController:
    """驱动悬停计时与喂食菜单显隐。"""

    def __init__(self, window, menu):
        self._window = window
        self._menu = menu
        self._enabled = True
        # 静止基准点；当前位置离它在容差内即视为同一次静止。
        self._anchor = None
        self._hover = 0.0
        self._open = False
        self._trigger = self._roll()

    def _roll(self) -> float:
        return random.uniform(P.HOVER_MENU_MIN_SEC, P.HOVER_MENU_MAX_SEC)

    def set_enabled(self, flag: bool) -> None:
        self._enabled = bool(flag)
        if not self._enabled:
            self.close_menu()
            self._anchor = None

    def is_open(self) -> bool:
        return self._open

    def close_menu(self) -> None:
        """关闭菜单并重置悬停计时（点击条目、鼠标离开时调用）。"""
        if self._open:
            self._menu.hide()
            self._open = False
        self._hover = 0.0
        self._anchor = None
        self._trigger = self._roll()

    def update(self, cursor_pos, dt: float) -> None:
        if not self._enabled:
            return
        pt = QPoint(int(cursor_pos[0]), int(cursor_pos[1]))
        win_rect = self._window.geometry()

        if self._open:
            # 菜单已打开：桌宠窗口或菜单区域内都保持，否则关闭。
            if not (win_rect.contains(pt) or self._menu.frameGeometry().contains(pt)):
                self.close_menu()
            return

        if not win_rect.contains(pt):
            # 未打开且不在窗口内：重置，不累计。
            self._hover = 0.0
            self._anchor = None
            self._trigger = self._roll()
            return

        # 未打开：以基准点 + 容差判定静止；超出容差视为新的静止，重新计时。
        if self._anchor is None:
            self._anchor = cursor_pos
            self._hover = 0.0
            self._trigger = self._roll()
        else:
            dist = math.hypot(cursor_pos[0] - self._anchor[0],
                              cursor_pos[1] - self._anchor[1])
            if dist > P.HOVER_JITTER_PX:
                self._anchor = cursor_pos
                self._hover = 0.0
                self._trigger = self._roll()

        self._hover += dt
        if self._hover >= self._trigger:
            self._open = True
            wolf_visible = self._window.preview.is_wolf_visible()
            self._menu.show_menu(win_rect, wolf_visible=wolf_visible)
