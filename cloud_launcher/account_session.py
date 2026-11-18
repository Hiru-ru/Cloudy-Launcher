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

"""当前账号会话状态（进程内存态；刷新令牌与公开身份由 AccountStore 持久化）。

会话口径（1.2.3.0 起）：正版登录成功后，档案进入本内存对象供界面即时使用；刷新令牌
与公开身份同时由 ``AccountStore`` 写入 ``yd/account.json``，供下次启动静默恢复。短期
访问令牌只存内存、不落盘。点「离线」或「退出登录」清空本内存会话，并由个人页调用
``AccountStore.clear()`` 删除本地账号文件；离线昵称、离线皮肤、游玩统计、窗口位置等
既有持久化字段仍由 ``ConfigStore`` 负责，本模块不参与写盘。
"""


class AccountSession:
    """单账号内存会话：离线 ↔ 正版互斥切换，退出登录即清空正版凭据。"""

    MODE_OFFLINE = "offline"
    MODE_MICROSOFT = "microsoft"

    def __init__(self) -> None:
        self._mode = self.MODE_OFFLINE
        self._profile: dict | None = None

    # ---- 状态读取 ----
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_microsoft(self) -> bool:
        return self._mode == self.MODE_MICROSOFT and self._profile is not None

    @property
    def profile(self) -> dict | None:
        return self._profile

    @property
    def name(self) -> str:
        return self._profile.get("name", "") if self._profile else ""

    @property
    def uuid(self) -> str:
        return self._profile.get("uuid", "") if self._profile else ""

    @property
    def skin_url(self) -> str | None:
        return self._profile.get("skin_url") if self._profile else None

    @property
    def slim(self) -> bool:
        return bool(self._profile.get("slim")) if self._profile else False

    @property
    def mc_access_token(self) -> str:
        return self._profile.get("mc_access_token", "") if self._profile else ""

    @property
    def refresh_token(self) -> str:
        return self._profile.get("refresh_token", "") if self._profile else ""

    # ---- 状态变更 ----
    def set_microsoft(self, profile: dict) -> None:
        """登录成功后写入正版档案，切换到正版模式。"""
        self._profile = dict(profile)
        self._mode = self.MODE_MICROSOFT

    def switch_offline(self) -> None:
        """切回离线：清空全部正版凭据与内存令牌，不触碰 config 中的离线昵称。"""
        self._profile = None
        self._mode = self.MODE_OFFLINE
