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

"""云朵桌宠困倦 / 睡眠行为链（仅 PySide6 + 标准库）。

鼠标持续静止（空闲）时累计空闲时长：达到 ``SLEEP_DROWSY_SEC`` 先打哈欠、冒泡
「好困啊…」，继续静止到 ``SLEEP_FALL_SEC`` 后蜷缩入睡（渲染组件进入睡眠姿态，
头顶由粒子组件冒 Zzz）；鼠标一动立即醒来并复位计时。

睡眠状态由渲染组件 ``set_sleeping`` 承载，本控制器只负责时序与状态切换。
"""
import pet_actions as A
import pet_constants as P


class SleepController:
    """根据持续空闲时长驱动 打哈欠 → 入睡 → 醒来。"""

    def __init__(self, preview, say, on_sleep_change=None):
        self._preview = preview
        self._say = say
        self._on_sleep_change = on_sleep_change
        self._enabled = True
        self._idle_time = 0.0
        self._yawned = False
        self._sleeping = False

    def set_enabled(self, flag: bool) -> None:
        self._enabled = bool(flag)
        if not self._enabled:
            self.reset()

    def reset(self) -> None:
        self._idle_time = 0.0
        self._yawned = False
        if self._sleeping:
            self._preview.set_sleeping(False)
        self._sleeping = False

    def is_sleeping(self) -> bool:
        return self._sleeping

    def on_activity(self) -> None:
        """鼠标活动：立即醒来并复位困倦计时。"""
        self._idle_time = 0.0
        self._yawned = False
        if self._sleeping:
            self._sleeping = False
            self._preview.set_sleeping(False)
            if self._on_sleep_change is not None:
                self._on_sleep_change(False)

    def update(self, dt: float) -> None:
        if not self._enabled or self._sleeping:
            return
        # 动作播放中（含打哈欠）不推进入睡判定，但保留已累计的空闲时间。
        self._idle_time += dt

        if self._idle_time >= P.SLEEP_DROWSY_SEC and not self._yawned:
            self._yawned = True
            self._say("好困啊…")
            if not self._preview.is_acting():
                self._preview.trigger_action(A.YAWN)

        if self._idle_time >= P.SLEEP_FALL_SEC:
            self._sleeping = True
            # 入睡时停止可能在播的动作，进入睡眠姿态。
            self._preview.stop_action()
            self._preview.set_sleeping(True)
            if self._on_sleep_change is not None:
                self._on_sleep_change(True)
