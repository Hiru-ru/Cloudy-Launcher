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

"""单版本启动配置视图（v1.3.21.0）。

设置页「启动」标签的版本隔离 / 高级功能（内存、GC、Java、JVM/游戏参数、四个开关）搬到
版本设置页后，每个版本持有**独立**的启动配置。本类是该配置的读写视图：

- 覆盖层保存在 ``ConfigStore`` 的 ``version_settings`` 字段（dict，key=版本别名）；
- 某字段未覆盖时，回落到「启动」标签的全局配置（``ConfigStore`` 同名字段），全局字段也
  缺失时再兜底 :data:`~cloud_launcher.config_store.DEFAULT_CONFIG` 内置默认；
- 对外属性接口与 ``ConfigStore`` 对齐，``java_runtime`` 的命令组装 / 目录解析可直接接收本类，
  无需改动；
- 账号不进版本设置：``player_name`` 等全局身份字段仍委托给底层 ``ConfigStore``。
"""
from __future__ import annotations

from . import constants as C
from .config_store import DEFAULT_CONFIG

# 本视图托管的字段名（全部为「按版本独立」的启动设置）。
_VERSION_FIELDS = (
    "isolation_mode",
    "gc_mode",
    "memory_mode",
    "custom_memory_mb",
    "jvm_args",
    "game_args",
    "pre_launch_command",
    "java_path",
    "disable_launch_wrapper",
    "disable_lwjgl_unsafe",
    "prefer_discrete_gpu",
    "verify_ssl",
    "pre_launch_memory_optimize",
)

_BOOL_FIELDS = (
    "disable_launch_wrapper",
    "disable_lwjgl_unsafe",
    "prefer_discrete_gpu",
    "verify_ssl",
    "pre_launch_memory_optimize",
)


class VersionLaunchConfig:
    """单个版本的启动配置：覆盖层 + 内置默认，属性接口与 ``ConfigStore`` 一致。"""

    def __init__(self, store, alias: str = "") -> None:
        self._store = store
        self._alias = str(alias or "")

    # ------------------------------------------------------------------ #
    # 别名 / 覆盖层读写
    # ------------------------------------------------------------------ #
    @property
    def alias(self) -> str:
        return self._alias

    def set_alias(self, alias: str) -> None:
        """切换到另一个版本（版本设置页复用同一视图对象）。"""
        self._alias = str(alias or "")

    def _all_overrides(self) -> dict:
        if self._store is None:
            return {}
        raw = self._store.get("version_settings", {})
        return raw if isinstance(raw, dict) else {}

    def _overrides(self) -> dict:
        data = self._all_overrides().get(self._alias)
        return data if isinstance(data, dict) else {}

    def _write(self, key: str, value) -> None:
        # store 为 None（测试 / 无配置场景）时只读，无法落盘，直接忽略。
        if self._store is None:
            return
        raw = self._all_overrides()
        current = raw.get(self._alias)
        if not isinstance(current, dict):
            current = {}
        current[key] = value
        raw[self._alias] = current
        self._store.set("version_settings", raw)
        self._store.save()

    def _read(self, key: str):
        if key in self._overrides():
            return self._overrides()[key]
        if self._store is not None:
            # 未单独覆盖的版本跟随「启动」标签的全局配置（全局默认 + 版本覆盖口径）；
            # 全局字段缺失时再兜底内置默认。
            return self._store.get(key, DEFAULT_CONFIG[key])
        return DEFAULT_CONFIG[key]

    def reset_to_default(self) -> None:
        """清空该版本的全部覆盖，恢复跟随「启动」标签的全局配置。"""
        if self._store is None:
            return
        raw = self._all_overrides()
        if self._alias in raw:
            raw.pop(self._alias)
            self._store.set("version_settings", raw)
            self._store.save()

    # ------------------------------------------------------------------ #
    # 全局身份字段（账号不搬，委托底层 store）
    # ------------------------------------------------------------------ #
    @property
    def player_name(self) -> str:
        if self._store is None:
            return "Steve"
        return self._store.player_name

    # ------------------------------------------------------------------ #
    # 枚举字段
    # ------------------------------------------------------------------ #
    @property
    def isolation_mode(self) -> str:
        value = self._read("isolation_mode")
        return value if value in C.ISOLATION_KEYS else C.ISOLATION_DEFAULT

    @isolation_mode.setter
    def isolation_mode(self, value) -> None:
        self._write("isolation_mode",
                    value if value in C.ISOLATION_KEYS else C.ISOLATION_DEFAULT)

    @property
    def gc_mode(self) -> str:
        value = self._read("gc_mode")
        return value if value in C.GC_KEYS else C.GC_DEFAULT_KEY

    @gc_mode.setter
    def gc_mode(self, value) -> None:
        self._write("gc_mode", value if value in C.GC_KEYS else C.GC_DEFAULT_KEY)

    @property
    def memory_mode(self) -> str:
        return "custom" if self._read("memory_mode") == "custom" else "auto"

    @memory_mode.setter
    def memory_mode(self, value) -> None:
        self._write("memory_mode", "custom" if value == "custom" else "auto")

    # ------------------------------------------------------------------ #
    # 数值 / 字符串 / 布尔字段
    # ------------------------------------------------------------------ #
    @property
    def custom_memory_mb(self) -> int:
        try:
            return max(512, min(65536, int(self._read("custom_memory_mb"))))
        except (TypeError, ValueError):
            return 2048

    @custom_memory_mb.setter
    def custom_memory_mb(self, value) -> None:
        try:
            self._write("custom_memory_mb", max(512, min(65536, int(value))))
        except (TypeError, ValueError):
            self._write("custom_memory_mb", 2048)

    @property
    def jvm_args(self) -> str:
        return str(self._read("jvm_args") or "")

    @jvm_args.setter
    def jvm_args(self, value) -> None:
        self._write("jvm_args", str(value or ""))

    @property
    def game_args(self) -> str:
        return str(self._read("game_args") or "")

    @game_args.setter
    def game_args(self, value) -> None:
        self._write("game_args", str(value or ""))

    @property
    def pre_launch_command(self) -> str:
        return str(self._read("pre_launch_command") or "")

    @pre_launch_command.setter
    def pre_launch_command(self, value) -> None:
        self._write("pre_launch_command", str(value or ""))

    @property
    def java_path(self) -> str:
        return str(self._read("java_path") or "")

    @java_path.setter
    def java_path(self, value) -> None:
        self._write("java_path", str(value or "").strip())

    def _bool(self, key: str) -> bool:
        value = self._read(key)
        return value if isinstance(value, bool) else DEFAULT_CONFIG[key]

    def _set_bool(self, key: str, value: bool) -> None:
        self._write(key, bool(value))

    @property
    def disable_launch_wrapper(self) -> bool:
        return self._bool("disable_launch_wrapper")

    @disable_launch_wrapper.setter
    def disable_launch_wrapper(self, value) -> None:
        self._set_bool("disable_launch_wrapper", value)

    @property
    def disable_lwjgl_unsafe(self) -> bool:
        return self._bool("disable_lwjgl_unsafe")

    @disable_lwjgl_unsafe.setter
    def disable_lwjgl_unsafe(self, value) -> None:
        self._set_bool("disable_lwjgl_unsafe", value)

    @property
    def prefer_discrete_gpu(self) -> bool:
        return self._bool("prefer_discrete_gpu")

    @prefer_discrete_gpu.setter
    def prefer_discrete_gpu(self, value) -> None:
        self._set_bool("prefer_discrete_gpu", value)

    @property
    def verify_ssl(self) -> bool:
        return self._bool("verify_ssl")

    @verify_ssl.setter
    def verify_ssl(self, value) -> None:
        self._set_bool("verify_ssl", value)

    @property
    def pre_launch_memory_optimize(self) -> bool:
        return self._bool("pre_launch_memory_optimize")

    @pre_launch_memory_optimize.setter
    def pre_launch_memory_optimize(self, value) -> None:
        self._set_bool("pre_launch_memory_optimize", value)
