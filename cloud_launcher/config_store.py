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

"""本地配置持久化：以 JSON 形式保存在应用目录下的 config.json。

当前版本（1.2.12.16）：本文件落盘离线昵称、离线皮肤、游玩统计、窗口位置与个人页选中的
已安装版本**别名**；微软正版的刷新令牌与公开身份由独立的 ``AccountStore`` 写入同级
``yd/account.json``，短期访问令牌不落盘；本配置不混入任何正版账号字段。

v1.2.11.0：新增 ``selected_version`` 字段记录个人页选中的已安装版本号，旧配置缺字段时
回退空串；昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。

v1.2.10.0：下载页分组图标、清单本地缓存与后台更新提示弹窗未新增任何配置字段，config
schema 与 v1.2.9.2 基线一致；昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。

v1.2.9.2：下载页四项真机缺陷修复未新增任何配置字段，config schema 与 v1.2.9.1 基线一致；
昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。

v1.2.9.1：下载页全量版本分类列表与分组内滚动动画未新增任何配置字段，config schema 与
v1.2.8.1 基线一致；昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。

v1.2.8.1：下载页白板修复与四分组版本号回填未新增任何配置字段，config schema 与
v1.2.7.1 基线一致；昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。

v1.2.7.1：下载页改为可折叠分组未新增任何配置字段，config schema 与 v1.2.6.1 基线一致；
昵称 / 皮肤 / 统计 / 窗口位置的读写与持久化口径保持不变。
"""
import json
import os
import threading

from . import constants as C
from . import pet_features as PF
from .resources import data_dir


CONFIG_FILENAME = "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "player_name": "Steve",
    "skin": C.DEFAULT_SKIN,
    "play_time_seconds": 0,
    "launch_count": 0,
    "last_played": "",
    "window_x": None,
    "window_y": None,
    "window_maximized": False,
    # v1.2.11.0：个人页选中的已安装版本号；空串表示尚未选择。
    "selected_version": "",
    # ---- v1.3.9.0：设置页个性化字段 ----
    "glass_mode": C.GLASS_MODE_FROST,
    "bg_tint": C.TINT_NONE,
    "nav_tint": C.TINT_NONE,
    "wallpaper_file": C.WALLPAPER_DEFAULT_KEY,
    # v1.3.9.3：品牌开关改显隐语义（Logo/名字关闭即隐藏），旧 brand_mode 已废弃。
    "logo_visible": C.LOGO_VISIBLE_DEFAULT,
    "name_visible": C.NAME_VISIBLE_DEFAULT,
    "custom_logo": "",
    "custom_name": "",
    "music_file": "",
    "music_enabled": False,
    "music_autoplay": True,
    # ---- v1.3.9.2：苹果动画总开关 ----
    "animations_enabled": C.ANIMATIONS_ENABLED_DEFAULT,
    # ---- v1.3.16.0：设置页「启动」标签（账号 / 版本隔离 / 高级功能）----
    "isolation_mode": C.ISOLATION_DEFAULT,
    "jvm_args": "",
    "game_args": "",
    "pre_launch_command": "",
    "java_path": "",
    "gc_mode": C.GC_DEFAULT_KEY,
    "disable_launch_wrapper": C.DISABLE_LAUNCH_WRAPPER_DEFAULT,
    "disable_lwjgl_unsafe": C.DISABLE_LWJGL_UNSAFE_DEFAULT,
    "prefer_discrete_gpu": C.PREFER_DISCRETE_GPU_DEFAULT,
    "verify_ssl": C.VERIFY_SSL_DEFAULT,
    "custom_skin": "",
    # v1.3.16.1：多离线账号昵称列表；正版账号沿用既有单份会话/令牌模型，多正版并存后接。
    "offline_accounts": [],
    # ---- v1.3.16.0：内存分配（自动 / 自定义 + 启动前内存优化）----
    "memory_mode": "auto",
    "custom_memory_mb": 2048,
    "pre_launch_memory_optimize": False,
    # v1.3.21.0：按版本独立的启动配置覆盖（key=版本别名，value=该版本覆盖字段）。
    "version_settings": {},
    # ---- v1.4.1.0：桌宠（独立 APP 经设置页文件选择导入）----
    # 导入的桌宠可执行文件绝对路径；空串表示尚未导入，未导入不可启用。
    "pet_app_path": "",
    # ---- 小云 AI（独立程序经设置·AI 页导入）----
    # 导入的小云 AI 可执行文件绝对路径；空串表示尚未导入，未导入不可翻译。
    "ai_app_path": "",
    # 上次桌宠窗口位置（关闭时回填，下次启动恢复）；None 由桌宠程序自行放右下角。
    "pet_window_x": None,
    "pet_window_y": None,
    # v1.4.4.0：桌宠功能开关（idle/hover/hunger/wolf/sleep），默认全开；
    # 仅在启动器「设置·桌宠」页配置，经 --features 透传，桌宠内部不提供开关。
    "pet_features": dict(PF.DEFAULT_FEATURES),
}


class ConfigStore:
    """线程安全的配置读写器。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = os.path.join(data_dir(), CONFIG_FILENAME)
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    @property
    def path(self) -> str:
        return self._path

    def load(self) -> None:
        with self._lock:
            if os.path.isfile(self._path):
                try:
                    with open(self._path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    if isinstance(saved, dict):
                        self._data.update(saved)
                except (OSError, json.JSONDecodeError):
                    # 配置损坏时回退到默认值，不影响启动
                    self._data = dict(DEFAULT_CONFIG)
            # 剔除旧版本废弃字段（旧版手绘头像标识，本版已由 skin 取代）
            self._data.pop("avatar_id", None)
            # 角色取值合法性校正
            if self._data.get("skin") not in C.SKIN_CHOICES:
                self._data["skin"] = C.DEFAULT_SKIN
            # 启动次数 / 最近游玩日期类型校正，损坏或缺失时回退默认值
            try:
                self._data["launch_count"] = max(0, int(self._data.get("launch_count", 0)))
            except (TypeError, ValueError):
                self._data["launch_count"] = 0
            if not isinstance(self._data.get("last_played"), str):
                self._data["last_played"] = ""
            # 选中版本号类型校正：非字符串回退空串。
            if not isinstance(self._data.get("selected_version"), str):
                self._data["selected_version"] = ""
            # ---- v1.3.9.0 个性化字段合法性校正 ----
            if self._data.get("glass_mode") not in C.GLASS_MODE_KEYS:
                self._data["glass_mode"] = C.GLASS_MODE_FROST
            if self._data.get("bg_tint") not in (C.TINT_NONE,) + tuple(C.TINT_KEYS):
                self._data["bg_tint"] = C.TINT_NONE
            if self._data.get("nav_tint") not in (C.TINT_NONE,) + tuple(C.TINT_KEYS):
                self._data["nav_tint"] = C.TINT_NONE
            if not isinstance(self._data.get("wallpaper_file"), str):
                self._data["wallpaper_file"] = C.WALLPAPER_DEFAULT_KEY
            # v1.3.9.3：旧 brand_mode 四档下 Logo/名字始终可见，迁移后直接丢弃该字段；
            # 显隐由新的 logo_visible / name_visible 布尔承载。
            self._data.pop("brand_mode", None)
            for key, default in (
                ("logo_visible", C.LOGO_VISIBLE_DEFAULT),
                ("name_visible", C.NAME_VISIBLE_DEFAULT),
            ):
                if not isinstance(self._data.get(key), bool):
                    self._data[key] = default
            for key in ("custom_logo", "custom_name", "music_file"):
                if not isinstance(self._data.get(key), str):
                    self._data[key] = ""
            for key in ("music_enabled", "music_autoplay"):
                if not isinstance(self._data.get(key), bool):
                    self._data[key] = DEFAULT_CONFIG[key]
            # v1.3.9.2：动画总开关布尔校正，缺失/损坏回退默认。
            if not isinstance(self._data.get("animations_enabled"), bool):
                self._data["animations_enabled"] = DEFAULT_CONFIG["animations_enabled"]
            # ---- v1.3.16.0：启动设置字段合法性校正 ----
            if self._data.get("isolation_mode") not in C.ISOLATION_KEYS:
                self._data["isolation_mode"] = C.ISOLATION_DEFAULT
            if self._data.get("gc_mode") not in C.GC_KEYS:
                self._data["gc_mode"] = C.GC_DEFAULT_KEY
            if self._data.get("memory_mode") not in ("auto", "custom"):
                self._data["memory_mode"] = "auto"
            for key in ("jvm_args", "game_args", "pre_launch_command", "java_path", "custom_skin"):
                if not isinstance(self._data.get(key), str):
                    self._data[key] = ""
            for key in (
                "disable_launch_wrapper",
                "disable_lwjgl_unsafe",
                "prefer_discrete_gpu",
                "verify_ssl",
                "pre_launch_memory_optimize",
            ):
                if not isinstance(self._data.get(key), bool):
                    self._data[key] = DEFAULT_CONFIG[key]
            try:
                mb = int(self._data.get("custom_memory_mb", 2048))
                self._data["custom_memory_mb"] = max(512, min(65536, mb))
            except (TypeError, ValueError):
                self._data["custom_memory_mb"] = 2048
            # 离线账号昵称列表：非列表回退空列表；逐项去空白、去重保序；
            # 旧配置没有列表时，用当前离线昵称回填一条，避免老用户首次进入账号列表为空。
            raw_accounts = self._data.get("offline_accounts", [])
            accounts: list[str] = []
            if isinstance(raw_accounts, list):
                for item in raw_accounts:
                    name = str(item or "").strip()
                    if name and name not in accounts:
                        accounts.append(name)
            if not accounts:
                current_name = str(self._data.get("player_name", "") or "").strip()
                if current_name:
                    accounts.append(current_name)
            self._data["offline_accounts"] = accounts

            # v1.3.21.0：按版本启动配置覆盖结构校正——必须是 alias->dict 的映射，
            # 损坏项整体回退空 dict；不在这里逐字段校验（VersionLaunchConfig 读取时兜底）。
            raw_vs = self._data.get("version_settings", {})
            if not isinstance(raw_vs, dict):
                raw_vs = {}
            cleaned_vs = {}
            for alias, override in raw_vs.items():
                if isinstance(alias, str) and isinstance(override, dict) and override:
                    cleaned_vs[alias] = override
            self._data["version_settings"] = cleaned_vs

            # ---- v1.4.1.0：桌宠字段校正 ----
            # 已记录的桌宠路径若文件已不存在则保留字符串（界面据此提示重新导入），
            # 仅做类型校正；窗口坐标非整数回退 None。
            if not isinstance(self._data.get("pet_app_path"), str):
                self._data["pet_app_path"] = ""
            if not isinstance(self._data.get("ai_app_path"), str):
                self._data["ai_app_path"] = ""
            for key in ("pet_window_x", "pet_window_y"):
                value = self._data.get(key)
                if value is not None:
                    try:
                        self._data[key] = int(value)
                    except (TypeError, ValueError):
                        self._data[key] = None
            # 桌宠功能开关：必须是已知 key 的 bool 映射，损坏/缺失整体回退默认全开。
            self._data["pet_features"] = PF.normalize(self._data.get("pet_features"))

    def save(self) -> None:
        with self._lock:
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value

    def update(self, **kwargs) -> None:
        with self._lock:
            self._data.update(kwargs)

    # ---- 常用字段便捷访问 ----
    @property
    def player_name(self) -> str:
        return str(self.get("player_name", "Steve"))

    @player_name.setter
    def player_name(self, value: str) -> None:
        name = (value or "").strip() or "Steve"
        self.set("player_name", name)

    @property
    def offline_accounts(self) -> list[str]:
        raw = self.get("offline_accounts", [])
        out: list[str] = []
        if isinstance(raw, list):
            for item in raw:
                name = str(item or "").strip()
                if name and name not in out:
                    out.append(name)
        return out

    @offline_accounts.setter
    def offline_accounts(self, value) -> None:
        out: list[str] = []
        for item in (value or []):
            name = str(item or "").strip()
            if name and name not in out:
                out.append(name)
        self.set("offline_accounts", out)

    @property
    def skin(self) -> str:
        value = self.get("skin", C.DEFAULT_SKIN)
        return value if value in C.SKIN_CHOICES else C.DEFAULT_SKIN

    @skin.setter
    def skin(self, value: str) -> None:
        if value in C.SKIN_CHOICES:
            self.set("skin", value)

    @property
    def play_time_seconds(self) -> int:
        try:
            return int(self.get("play_time_seconds", 0))
        except (TypeError, ValueError):
            return 0

    @play_time_seconds.setter
    def play_time_seconds(self, value: int) -> None:
        self.set("play_time_seconds", max(0, int(value)))

    @property
    def launch_count(self) -> int:
        try:
            return max(0, int(self.get("launch_count", 0)))
        except (TypeError, ValueError):
            return 0

    @launch_count.setter
    def launch_count(self, value: int) -> None:
        self.set("launch_count", max(0, int(value)))

    @property
    def last_played(self) -> str:
        value = self.get("last_played", "")
        return value if isinstance(value, str) else ""

    @last_played.setter
    def last_played(self, value: str) -> None:
        self.set("last_played", value if isinstance(value, str) else "")

    @property
    def selected_version(self) -> str:
        value = self.get("selected_version", "")
        return value if isinstance(value, str) else ""

    @selected_version.setter
    def selected_version(self, value: str) -> None:
        self.set("selected_version", str(value or "").strip())

    # ---- v1.3.16.0：启动设置便捷访问 ----
    @property
    def isolation_mode(self) -> str:
        value = self.get("isolation_mode", C.ISOLATION_DEFAULT)
        return value if value in C.ISOLATION_KEYS else C.ISOLATION_DEFAULT

    @isolation_mode.setter
    def isolation_mode(self, value: str) -> None:
        self.set("isolation_mode", value if value in C.ISOLATION_KEYS else C.ISOLATION_DEFAULT)

    @property
    def gc_mode(self) -> str:
        value = self.get("gc_mode", C.GC_DEFAULT_KEY)
        return value if value in C.GC_KEYS else C.GC_DEFAULT_KEY

    @gc_mode.setter
    def gc_mode(self, value: str) -> None:
        self.set("gc_mode", value if value in C.GC_KEYS else C.GC_DEFAULT_KEY)

    @property
    def memory_mode(self) -> str:
        return self.get("memory_mode", "auto") if self.get("memory_mode", "auto") in ("auto", "custom") else "auto"

    @memory_mode.setter
    def memory_mode(self, value: str) -> None:
        self.set("memory_mode", "custom" if value == "custom" else "auto")

    @property
    def custom_memory_mb(self) -> int:
        try:
            return max(512, min(65536, int(self.get("custom_memory_mb", 2048))))
        except (TypeError, ValueError):
            return 2048

    @custom_memory_mb.setter
    def custom_memory_mb(self, value: int) -> None:
        try:
            self.set("custom_memory_mb", max(512, min(65536, int(value))))
        except (TypeError, ValueError):
            self.set("custom_memory_mb", 2048)

    def _bool(self, key: str, default: bool) -> bool:
        value = self.get(key, default)
        return value if isinstance(value, bool) else default

    def _set_bool(self, key: str, value: bool) -> None:
        self.set(key, bool(value))

    @property
    def jvm_args(self) -> str:
        return str(self.get("jvm_args", "") or "")

    @jvm_args.setter
    def jvm_args(self, value: str) -> None:
        self.set("jvm_args", str(value or ""))

    @property
    def game_args(self) -> str:
        return str(self.get("game_args", "") or "")

    @game_args.setter
    def game_args(self, value: str) -> None:
        self.set("game_args", str(value or ""))

    @property
    def pre_launch_command(self) -> str:
        return str(self.get("pre_launch_command", "") or "")

    @pre_launch_command.setter
    def pre_launch_command(self, value: str) -> None:
        self.set("pre_launch_command", str(value or ""))

    @property
    def java_path(self) -> str:
        return str(self.get("java_path", "") or "")

    @java_path.setter
    def java_path(self, value: str) -> None:
        self.set("java_path", str(value or "").strip())

    @property
    def custom_skin(self) -> str:
        return str(self.get("custom_skin", "") or "")

    @custom_skin.setter
    def custom_skin(self, value: str) -> None:
        self.set("custom_skin", str(value or "").strip())

    @property
    def disable_launch_wrapper(self) -> bool:
        return self._bool("disable_launch_wrapper", C.DISABLE_LAUNCH_WRAPPER_DEFAULT)

    @disable_launch_wrapper.setter
    def disable_launch_wrapper(self, value: bool) -> None:
        self._set_bool("disable_launch_wrapper", value)

    @property
    def disable_lwjgl_unsafe(self) -> bool:
        return self._bool("disable_lwjgl_unsafe", C.DISABLE_LWJGL_UNSAFE_DEFAULT)

    @disable_lwjgl_unsafe.setter
    def disable_lwjgl_unsafe(self, value: bool) -> None:
        self._set_bool("disable_lwjgl_unsafe", value)

    @property
    def prefer_discrete_gpu(self) -> bool:
        return self._bool("prefer_discrete_gpu", C.PREFER_DISCRETE_GPU_DEFAULT)

    @prefer_discrete_gpu.setter
    def prefer_discrete_gpu(self, value: bool) -> None:
        self._set_bool("prefer_discrete_gpu", value)

    @property
    def verify_ssl(self) -> bool:
        return self._bool("verify_ssl", C.VERIFY_SSL_DEFAULT)

    @verify_ssl.setter
    def verify_ssl(self, value: bool) -> None:
        self._set_bool("verify_ssl", value)

    @property
    def pre_launch_memory_optimize(self) -> bool:
        return self._bool("pre_launch_memory_optimize", False)

    @pre_launch_memory_optimize.setter
    def pre_launch_memory_optimize(self, value: bool) -> None:
        self._set_bool("pre_launch_memory_optimize", value)

    # ---- v1.4.1.0：桌宠 ----
    @property
    def pet_app_path(self) -> str:
        return str(self.get("pet_app_path", "") or "")

    @pet_app_path.setter
    def pet_app_path(self, value: str) -> None:
        self.set("pet_app_path", str(value or "").strip())

    # ---- 小云 AI ----
    @property
    def ai_app_path(self) -> str:
        return str(self.get("ai_app_path", "") or "")

    @ai_app_path.setter
    def ai_app_path(self, value: str) -> None:
        self.set("ai_app_path", str(value or "").strip())

    @property
    def pet_window_x(self):
        return self.get("pet_window_x")

    @pet_window_x.setter
    def pet_window_x(self, value) -> None:
        self.set("pet_window_x", None if value is None else int(value))

    @property
    def pet_window_y(self):
        return self.get("pet_window_y")

    @pet_window_y.setter
    def pet_window_y(self, value) -> None:
        self.set("pet_window_y", None if value is None else int(value))

    @property
    def pet_features(self) -> dict:
        """桌宠功能开关（合法 dict，默认全开）。"""
        return PF.normalize(self.get("pet_features"))

    @pet_features.setter
    def pet_features(self, value) -> None:
        self.set("pet_features", PF.normalize(value))

    def set_pet_feature(self, key: str, flag: bool) -> None:
        """更新单个开关并立即持久化。"""
        features = self.pet_features
        if key in PF.FEATURE_KEYS:
            features[key] = bool(flag)
            self.pet_features = features
            self.save()
