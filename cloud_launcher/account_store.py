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

"""正版账号凭据本地持久化：exe 同级 ``yd/account.json``（明文 JSON，对标 PCL2 本地账号文件）。

与 ``ConfigStore`` 分工：

- ``ConfigStore`` / ``config.json``：离线昵称、离线角色、游玩统计、窗口位置等本地设置；
- ``AccountStore`` / ``yd/account.json``：正版登录后的**刷新令牌**与公开身份
  （``refresh_token``、``name``、``uuid``、``skin_url``、``slim``）。

短期会话令牌（微软 / Xbox / XSTS / Minecraft ``access_token`` 与 ``expires_at``）**不落盘**：
寿命短、重启基本已过期，启动时由本地 ``refresh_token`` 静默换新整条会话，没有保存价值。

安全口径（1.2.3.0 起）：``refresh_token`` 明文保存在本机独立目录、与离线配置分离；点
「离线」或「退出登录」立即删除本账号文件；令牌只用于本启动器静默续期，不上传任何服务器。
``refresh_token`` 被吊销、超过不活跃期限或静默续期失败时，本文件被清除并回到离线，需要
重新走一次设备码授权。
"""
import json
import os
import threading

from .resources import data_dir


ACCOUNT_DIRNAME = "yd"  # 历史目录名（v1.3.10.0 起账号文件平铺到 CLY，不再使用 yd）
ACCOUNT_FILENAME = "account.json"

# 允许落盘的字段白名单；短期 access_token / expires_at 一律不写入磁盘。
_PERSIST_KEYS = ("refresh_token", "name", "uuid", "skin_url", "slim")


class AccountStore:
    """线程安全的正版账号文件读写器（独立于离线 ``config.json``）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dir = data_dir()
        self._path = os.path.join(self._dir, ACCOUNT_FILENAME)

    @property
    def path(self) -> str:
        """账号文件绝对路径。"""
        return self._path

    def save(self, profile: dict) -> None:
        """把刷新令牌与公开身份写入账号文件；短期会话令牌不落盘。

        传入档案缺少有效 ``refresh_token`` 时视为无可持久化内容，直接清除账号文件。
        """
        if not isinstance(profile, dict):
            return
        data = {
            "refresh_token": str(profile.get("refresh_token") or ""),
            "name": str(profile.get("name") or ""),
            "uuid": str(profile.get("uuid") or ""),
            "skin_url": profile.get("skin_url") or None,
            "slim": bool(profile.get("slim")),
        }
        if not data["refresh_token"]:
            self.clear()
            return

        with self._lock:
            os.makedirs(self._dir, exist_ok=True)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)

    def load(self) -> dict | None:
        """读取账号文件；缺失、损坏、缺少有效 ``refresh_token`` 时返回 ``None``。"""
        with self._lock:
            if not os.path.isfile(self._path):
                return None
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except (OSError, json.JSONDecodeError):
                return None
            if not isinstance(saved, dict):
                return None

            refresh_token = str(saved.get("refresh_token") or "")
            if not refresh_token:
                return None
            return {
                "refresh_token": refresh_token,
                "name": str(saved.get("name") or ""),
                "uuid": str(saved.get("uuid") or ""),
                "skin_url": saved.get("skin_url") or None,
                "slim": bool(saved.get("slim")),
            }

    def clear(self) -> None:
        """删除本地账号文件（退出登录 / 切离线 / 静默续期失败时调用）。"""
        with self._lock:
            try:
                if os.path.isfile(self._path):
                    os.remove(self._path)
            except OSError:
                pass
