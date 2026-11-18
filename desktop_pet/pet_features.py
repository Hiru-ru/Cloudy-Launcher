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

"""云朵桌宠功能开关定义与编解码（仅标准库）。

开关由云朵启动器「设置 · 桌宠」页配置，以 ``--features`` 命令行参数传入，
桌宠解析后对各控制器 ``set_enabled``。默认全部开启；未知 / 缺失的 key 一律回退开启。

本模块只维护 key 口径与字符串编解码，不依赖 Qt，便于离屏回归直接调用。
"""

IDLE = "idle"        # 空闲随机小动作
HOVER = "hover"      # 悬停喂食菜单
HUNGER = "hunger"    # 饥饿值
WOLF = "wolf"        # 小狗随机进场
SLEEP = "sleep"      # 困倦 / 睡眠

# (key, 展示名)，顺序即设置页与编码顺序。
FEATURE_ITEMS = [
    (IDLE, "空闲小动作"),
    (HOVER, "悬停喂食菜单"),
    (HUNGER, "饥饿值"),
    (WOLF, "小狗陪伴"),
    (SLEEP, "困倦睡觉"),
]
FEATURE_KEYS = [k for k, _ in FEATURE_ITEMS]
FEATURE_LABELS = dict(FEATURE_ITEMS)

# 默认全部开启。
DEFAULT_FEATURES = {k: True for k in FEATURE_KEYS}

_TRUE_TOKENS = ("1", "true", "yes", "on")


def normalize(d) -> dict:
    """把任意输入校正为合法 feature dict：只保留已知 key，缺失/损坏回退默认（开启）。"""
    out = dict(DEFAULT_FEATURES)
    if isinstance(d, dict):
        for k in FEATURE_KEYS:
            if k in d and isinstance(d[k], bool):
                out[k] = d[k]
    return out


def parse_features(text) -> dict:
    """解析 ``key=1,key=0`` 形式；空值 / 非法片段回退默认，不影响其他 key。"""
    out = dict(DEFAULT_FEATURES)
    if not text or not isinstance(text, str):
        return out
    for chunk in text.split(","):
        chunk = chunk.strip()
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip()
        if key in FEATURE_KEYS:
            out[key] = value.strip().lower() in _TRUE_TOKENS
    return out


def encode_features(d) -> str:
    """编码为 ``--features`` 字符串，只输出已知 key。"""
    return ",".join(
        "%s=%d" % (k, 1 if d.get(k, True) else 0) for k in FEATURE_KEYS)
