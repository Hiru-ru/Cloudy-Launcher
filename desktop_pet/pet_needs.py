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

"""云朵桌宠饥饿值（仅 PySide6 + 标准库）。

饥饿值随时间下降；降到阈值时先通过 ``say`` 冒泡「我饿了」，再自动触发吃东西动作；
EAT 动作结束后回满。鼠标打断会中止动作，但饥饿值仍低，之后会再次尝试。
"""
import pet_actions as A
import pet_constants as P


class HungerController:
    def __init__(self, preview, say):
        self._preview = preview
        self._say = say
        self._enabled = True
        self.hunger = P.HUNGER_MAX
        self._announced = False
        # 上一帧是否处于 EAT，用于检测“刚吃完”的边沿。
        self._was_eating = False

    def set_enabled(self, flag: bool) -> None:
        self._enabled = bool(flag)
        if not self._enabled:
            self.reset()

    def reset(self) -> None:
        self.hunger = P.HUNGER_MAX
        self._announced = False
        self._was_eating = False

    def update(self, dt: float) -> None:
        if not self._enabled:
            return
        now_eating = self._preview._action_id == A.EAT
        prev_eating = self._was_eating
        self._was_eating = now_eating

        # 随时间下降。
        if self.hunger > 0.0:
            self.hunger = max(0.0, self.hunger - P.HUNGER_DRAIN_PER_SEC * dt)

        # 低饥饿：每轮冒泡喊一次。
        if self.hunger <= P.HUNGER_LOW and not self._announced:
            self._say("我饿了")
            self._announced = True

        if not self._announced:
            return

        # 动作进行中（吃东西或被其他动作占用）：等待，不抢触发。
        if self._preview.is_acting():
            return

        if prev_eating and not now_eating:
            # EAT 刚结束：回满，本轮饥饿闭环。
            self.hunger = P.HUNGER_RESTORE
            self._announced = False
        else:
            # 喊饿后空闲：自动吃东西。
            self._preview.trigger_action(A.EAT)
