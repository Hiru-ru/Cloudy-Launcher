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

"""云朵桌宠空闲检测与随机事件调度（仅标准库）。

每帧由 ``PetWindow`` 传入当前全局鼠标位置与帧间隔；鼠标静止达到
``IDLE_THRESHOLD_SEC`` 后进入空闲，按随机间隔从动作清单里挑动作播放，
鼠标一动立即停止动作、回到正常状态。
"""
import random

import pet_actions as A
import pet_constants as P


class IdleController:
    """根据鼠标静止时间驱动随机动作；鼠标移动立即打断。"""

    def __init__(self, preview, on_activity=None):
        self._preview = preview
        self._on_activity = on_activity
        self._enabled = True
        self._last_pos = None
        self._idle = 0.0
        # 距下一个随机动作的倒计时（只计动作之外的额外间隔）。
        self._cooldown = 0.0

    def set_enabled(self, flag: bool) -> None:
        self._enabled = bool(flag)
        if not self._enabled:
            self.reset()

    def reset(self) -> None:
        self._idle = 0.0
        self._cooldown = 0.0
        self._last_pos = None

    def is_idle(self) -> bool:
        return self._idle >= P.IDLE_THRESHOLD_SEC

    def update(self, cursor_pos, dt: float) -> None:
        if not self._enabled:
            return
        # 鼠标位置变化即视为用户活动：复位空闲，若在表演立即停止。
        if self._last_pos is not None and cursor_pos != self._last_pos:
            if self._preview.is_acting():
                self._preview.stop_action()
            self._idle = 0.0
            self._cooldown = 0.0
            if self._on_activity is not None:
                self._on_activity()
        else:
            self._idle += dt
        self._last_pos = cursor_pos

        if self._idle < P.IDLE_THRESHOLD_SEC or self._preview.is_acting():
            return
        # 已进入空闲且当前无动作：倒计时到点随机挑一个动作。
        self._cooldown -= dt
        if self._cooldown <= 0.0:
            action_id = random.choice(A.ACTION_IDS)
            self._preview.trigger_action(action_id)
            self._cooldown = random.uniform(P.IDLE_GAP_MIN, P.IDLE_GAP_MAX)
