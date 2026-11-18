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

"""v1.3.9.0 个性化外观状态（进程内单例）。

持有玻璃风格三档与背景 / 导航栏七色染色选择，以及 v1.3.9.2 起的苹果动画总开关；
启动时由主窗口从 config.json 灌入，设置页改动后更新并立即触发各面板重绘。
本模块只存状态、不直接碰控件，
frosted_backdrop / background_layer / nav_sidebar / spring_button 在绘制时读取这里的值。
"""
from __future__ import annotations

from .. import constants as C


class AppearanceState:
    """玻璃模式 + 染色键的内存状态。"""

    def __init__(self) -> None:
        self._glass_mode: str = C.GLASS_MODE_FROST
        self._bg_tint: str = C.TINT_NONE
        self._nav_tint: str = C.TINT_NONE
        self._animations_enabled: bool = C.ANIMATIONS_ENABLED_DEFAULT

    # ---- 玻璃模式 ----
    @property
    def glass_mode(self) -> str:
        return self._glass_mode

    def set_glass_mode(self, mode: str) -> None:
        if mode in C.GLASS_MODE_KEYS:
            self._glass_mode = mode

    # ---- 背景染色 ----
    @property
    def bg_tint(self) -> str:
        return self._bg_tint

    def set_bg_tint(self, key: str) -> None:
        if key == C.TINT_NONE or key in C.TINT_COLORS:
            self._bg_tint = key

    def bg_tint_rgba(self) -> tuple[int, int, int, int] | None:
        if self._bg_tint not in C.TINT_COLORS:
            return None
        r, g, b = C.TINT_COLORS[self._bg_tint]
        return (r, g, b, C.TINT_BG_ALPHA)

    # ---- 导航栏染色 ----
    @property
    def nav_tint(self) -> str:
        return self._nav_tint

    def set_nav_tint(self, key: str) -> None:
        if key == C.TINT_NONE or key in C.TINT_COLORS:
            self._nav_tint = key

    def nav_tint_rgba(self) -> tuple[int, int, int, int] | None:
        if self._nav_tint not in C.TINT_COLORS:
            return None
        r, g, b = C.TINT_COLORS[self._nav_tint]
        return (r, g, b, C.TINT_NAV_ALPHA)

    # ---- 苹果动画总开关 ----
    @property
    def animations_enabled(self) -> bool:
        return self._animations_enabled

    def set_animations_enabled(self, enabled: bool) -> None:
        self._animations_enabled = bool(enabled)


# 模块级单例：与 frosted_backdrop.backdrop 同风格，全程序共享一份外观状态。
appearance = AppearanceState()
