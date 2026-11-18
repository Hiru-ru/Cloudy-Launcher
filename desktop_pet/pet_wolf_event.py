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

"""云朵桌宠小狗随机进场/退场（仅标准库）。

进入空闲（鼠标静止到阈值）后，在随机延迟内让驯服狼走路进场陪伴；陪伴一段随机
时间后自动退场。用户正在操作（非空闲）时不进场；鼠标活动会重新计时，避免
刚回到桌宠就被打断。狼可见时由 ``PetPreview`` 负责走路/摇尾/被喂动画。
"""
import random

import pet_constants as P


class WolfEventController:
    """根据空闲状态驱动小狗随机进场与退场。"""

    def __init__(self, preview):
        self._preview = preview
        self._enabled = True
        self._enter_cd = self._roll_enter()
        self._stay_left = 0.0

    def _roll_enter(self) -> float:
        return random.uniform(P.WOLF_ENTER_DELAY_MIN, P.WOLF_ENTER_DELAY_MAX)

    def _roll_stay(self) -> float:
        return random.uniform(P.WOLF_STAY_MIN, P.WOLF_STAY_MAX)

    def set_enabled(self, flag: bool) -> None:
        self._enabled = bool(flag)

    def on_activity(self) -> None:
        """用户活动：狼不在时重置进场计时；狼在则继续陪伴（不强制退场）。"""
        if not self._preview.is_wolf_visible():
            self._enter_cd = self._roll_enter()

    def update(self, is_idle: bool, dt: float) -> None:
        if not self._enabled:
            return
        if self._preview.is_wolf_visible():
            # 走路进场期间不退场；进场结束静止后才开始计陪伴时间。
            if self._preview._wolf_walking:
                return
            self._stay_left -= dt
            if self._stay_left <= 0.0:
                self._preview.hide_wolf()
                self._enter_cd = self._roll_enter()
            return
        # 狼不在：仅在空闲时累计进场倒计时，非空闲则重置。
        if not is_idle:
            self._enter_cd = self._roll_enter()
            return
        self._enter_cd -= dt
        if self._enter_cd <= 0.0:
            self._preview.show_wolf()
            self._stay_left = self._roll_stay()
