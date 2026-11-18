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

"""云朵启动器侧的桌宠功能开关口径（仅标准库）。

启动器独立打包、不能 import 桌宠模块，因此在本文件维护一份与桌宠
``desktop_pet/pet_features.py`` **完全一致**的 key 与编解码字符串口径，
再经 ``pet_controller.build_argv`` 的 ``--features`` 透传给桌宠。

默认全部开启；未知 / 缺失 key 一律回退开启。
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
    """校正为合法 feature dict：只保留已知 bool key，缺失/损坏回退默认（开启）。"""
    out = dict(DEFAULT_FEATURES)
    if isinstance(d, dict):
        for k in FEATURE_KEYS:
            if k in d and isinstance(d[k], bool):
                out[k] = d[k]
    return out


def parse_features(text) -> dict:
    """解析 ``key=1,key=0``；空值/非法片段回退默认，不影响其他 key。"""
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
