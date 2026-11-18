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

"""云朵桌宠固定动作：过程式姿态动画（自包含，仅标准库）。

动作由「动作 ID + 已进行时间」驱动，姿态函数返回每个关节当前的三轴旋转角
（弧度，rx/ry/rz 约定与 ``pet_preview._joint_matrix`` 一致）。动作起止在内部用
smoothstep 做抬手 / 放手平滑，避免手臂跳变；动作结束后由渲染组件回到静止。

部分动作（跳跃 / 跳舞 / 欢呼）还会通过 ``root_at`` 返回整体平移（x/y/z），由渲染
组件左乘到所有玩家部件，实现原地起跳、节奏起伏等效果。

当前内置：

- ``WAVE`` 打招呼 / 哈喽：右手抬起在头侧左右挥动；
- ``CLAP`` 拍手：双臂前伸在胸前反复合拢张开；
- ``EAT`` 吃东西：右手把食物举到嘴边小幅啃咬；
- ``JUMP`` 跳跃：原地起跳腾空，手臂上举、腿收拢；
- ``CHEER`` 欢呼：双手高举过头，身体节奏起伏；
- ``YAWN`` 打哈欠：头后仰、右手捂嘴；
- ``DANCE`` 跳舞：身体左右摆动、手臂随节奏舞动。
"""
import math

WAVE = "wave"
CLAP = "clap"
EAT = "eat"
JUMP = "jump"
CHEER = "cheer"
YAWN = "yawn"
DANCE = "dance"
PET = "pet"

# 菜单展示名（按给定顺序）。
ACTION_LABELS = [
    (WAVE, "打招呼"),
    (CLAP, "拍手"),
    (EAT, "吃东西"),
    (JUMP, "跳跃"),
    (CHEER, "欢呼"),
    (YAWN, "打哈欠"),
    (DANCE, "跳舞"),
    (PET, "摸小狗"),
]
ACTION_IDS = [aid for aid, _ in ACTION_LABELS]

_JOINTS = ("head", "body", "rarm", "larm", "rleg", "lleg")


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _smoothstep(e):
    e = _clamp(e)
    return e * e * (3.0 - 2.0 * e)


def _neutral():
    return {j: (0.0, 0.0, 0.0) for j in _JOINTS}


# ---------------------------------------------------------------------------
# 打招呼 / 哈喽（右手挥手）
# ---------------------------------------------------------------------------
WAVE_DURATION = 2.2
_W_RAISE = 0.35
_W_LOWER = 1.85
_W_RZ = -2.60          # 右手举起角（向外上方，约 -149°）
_W_AMP = 0.38          # 挥动幅度（约 22°）
_W_HZ = 4.0            # 1.5s 内整数次（6 次），起止都回到举起角、无跳变


def _pose_wave(t):
    pose = _neutral()
    if t < _W_RAISE:
        rz = _W_RZ * _smoothstep(t / _W_RAISE)
    elif t <= _W_LOWER:
        rz = _W_RZ + _W_AMP * math.sin(2.0 * math.pi * _W_HZ * (t - _W_RAISE))
    else:
        down = _smoothstep(1.0 - (t - _W_LOWER) / (WAVE_DURATION - _W_LOWER))
        rz = _W_RZ * down
    pose["rarm"] = (0.0, 0.0, rz)
    return pose


# ---------------------------------------------------------------------------
# 拍手（双臂前伸，胸前合拢张开）
# ---------------------------------------------------------------------------
CLAP_DURATION = 2.2
_C_UP = 0.35
_C_LOWER = 1.85
_C_RX = -1.15              # 双臂前伸（向前，约 -66°）
_C_RZ_CLOSE = 1.30         # 合拢内收角
_C_RZ_OPEN = 0.92          # 张开内收角
_C_HZ = 4.0                # 1.5s 内 6 次开合


def _pose_clap(t):
    pose = _neutral()
    if t < _C_UP:
        k = _smoothstep(t / _C_UP)
        rz_mag = _C_RZ_OPEN * k
        rx = _C_RX * k
    elif t <= _C_LOWER:
        rx = _C_RX
        phase = 2.0 * math.pi * _C_HZ * (t - _C_UP)
        # (1-cos)/2 在 0..1 间往复，起点为合拢，半周期到张开，避免 sin 正负越界。
        s = 0.5 * (1.0 - math.cos(phase))
        rz_mag = _C_RZ_CLOSE + (_C_RZ_OPEN - _C_RZ_CLOSE) * s
    else:
        k = _smoothstep(1.0 - (t - _C_LOWER) / (CLAP_DURATION - _C_LOWER))
        rz_mag = _C_RZ_OPEN * k
        rx = _C_RX * k
    pose["rarm"] = (rx, 0.0, rz_mag)
    pose["larm"] = (rx, 0.0, -rz_mag)
    return pose


# ---------------------------------------------------------------------------
# 吃东西（右手把食物举到嘴边，小幅往复啃）
# ---------------------------------------------------------------------------
EAT_DURATION = 2.6
_E_UP = 0.4
_E_LOWER = 2.2
_E_RX = -1.00           # 手臂向前举到脸前（约 -57°），不横扫身体
_E_RZ = 0.60            # 轻微内收（约 34°），让手靠近嘴但不与另一条手臂重叠
_E_AMP = 0.12           # 啃咬小幅前后（rx 往复），食物在嘴边轻移
_E_HZ = 3.5


def _pose_eat(t):
    pose = _neutral()
    if t < _E_UP:
        k = _smoothstep(t / _E_UP)
        rx = _E_RX * k
        rz = _E_RZ * k
    elif t <= _E_LOWER:
        rz = _E_RZ
        rx = _E_RX + _E_AMP * math.sin(2.0 * math.pi * _E_HZ * (t - _E_UP))
    else:
        k = _smoothstep(1.0 - (t - _E_LOWER) / (EAT_DURATION - _E_LOWER))
        rx = _E_RX * k
        rz = _E_RZ * k
    pose["rarm"] = (rx, 0.0, rz)
    return pose


# ---------------------------------------------------------------------------
# 跳跃（原地起跳：整体抛物线 + 手臂上举 + 腾空收腿）
# ---------------------------------------------------------------------------
JUMP_DURATION = 1.1
_J_UP = 0.32
_J_DOWN = 0.78
_J_H = 5.2            # 腾空最大高度
_J_ARM_RZ = 2.05      # 起跳时手臂外举幅度（rarm 负、larm 正）
_J_LEG = 0.42         # 腾空收腿前后幅度


def _pose_jump(t):
    pose = _neutral()
    if t < _J_UP:
        k = _smoothstep(t / _J_UP)
        pose["rarm"] = (0.0, 0.0, -_J_ARM_RZ * k)
        pose["larm"] = (0.0, 0.0, _J_ARM_RZ * k)
    elif t <= _J_DOWN:
        pose["rarm"] = (0.0, 0.0, -_J_ARM_RZ)
        pose["larm"] = (0.0, 0.0, _J_ARM_RZ)
        # 腾空：双腿一前一后小幅收拢。
        pose["rleg"] = (_J_LEG, 0.0, 0.0)
        pose["lleg"] = (-_J_LEG, 0.0, 0.0)
    else:
        k = _smoothstep(1.0 - (t - _J_DOWN) / (JUMP_DURATION - _J_DOWN))
        pose["rarm"] = (0.0, 0.0, -_J_ARM_RZ * k)
        pose["larm"] = (0.0, 0.0, _J_ARM_RZ * k)
    return pose


def _root_jump(t):
    # 整体抛物线：4p(1-p) 在中段达到峰值，起止均为 0，无跳变。
    p = t / JUMP_DURATION
    return (0.0, _J_H * 4.0 * p * (1.0 - p), 0.0)


# ---------------------------------------------------------------------------
# 欢呼（双手高举过头，身体节奏起伏）
# ---------------------------------------------------------------------------
CHEER_DURATION = 2.0
_CHEER_RZ = 2.25       # 双手外举幅度（rarm 负、larm 正）
_CHEER_HZ = 2.6
_CHEER_BOB = 1.1


def _pose_cheer(t):
    pose = _neutral()
    k = _smoothstep(min(1.0, t / 0.3))
    pose["rarm"] = (-0.15 * k, 0.0, -_CHEER_RZ * k)
    pose["larm"] = (-0.15 * k, 0.0, _CHEER_RZ * k)
    pose["head"] = (0.18 * k, 0.0, 0.0)
    return pose


def _root_cheer(t):
    if t < 0.25:
        return (0.0, 0.0, 0.0)
    return (0.0, _CHEER_BOB * abs(math.sin(2.0 * math.pi * _CHEER_HZ * (t - 0.25))), 0.0)


# ---------------------------------------------------------------------------
# 打哈欠（头后仰，右手捂嘴）
# ---------------------------------------------------------------------------
YAWN_DURATION = 2.2
_Y_OPEN = 0.45
_Y_CLOSE = 1.7
_Y_HEAD = 0.38
_Y_ARM_RX = -0.95
_Y_ARM_RZ = 0.55


def _pose_yawn(t):
    pose = _neutral()
    if t < _Y_OPEN:
        k = _smoothstep(t / _Y_OPEN)
    elif t <= _Y_CLOSE:
        k = 1.0
    else:
        k = _smoothstep(1.0 - (t - _Y_CLOSE) / (YAWN_DURATION - _Y_CLOSE))
    pose["head"] = (_Y_HEAD * k, 0.0, 0.0)
    pose["rarm"] = (_Y_ARM_RX * k, 0.0, _Y_ARM_RZ * k)
    return pose


# ---------------------------------------------------------------------------
# 跳舞（身体左右摆动，手臂随节奏舞动，小幅跳动）
# ---------------------------------------------------------------------------
DANCE_DURATION = 3.0
_D_HZ = 2.4
_D_BODY_RZ = 0.12
_D_ARM_RZ = 0.9
_D_BOB = 1.4
_D_HEAD_RY = 0.28


def _pose_dance(t):
    ph = 2.0 * math.pi * _D_HZ * t
    pose = _neutral()
    pose["body"] = (0.0, 0.0, _D_BODY_RZ * math.sin(ph))
    # 手臂在身体两侧随节奏摆动（与身体反相）。
    arm = _D_ARM_RZ * math.sin(ph + math.pi)
    pose["rarm"] = (-0.35, 0.0, -arm)
    pose["larm"] = (-0.35, 0.0, arm)
    pose["head"] = (0.0, _D_HEAD_RY * math.sin(ph), 0.0)
    return pose


def _root_dance(t):
    ph = 2.0 * math.pi * _D_HZ * t
    # 每拍轻跳一下。
    return (0.0, _D_BOB * abs(math.sin(ph)), 0.0)


# ---------------------------------------------------------------------------
# 摸小狗（左手伸到狗头顶，小幅抚摸）
# ---------------------------------------------------------------------------
PET_DURATION = 2.0
_P_UP = 0.35
_P_LOWER = 1.65
_P_RX = -0.53          # 手向前（狗头在靠前 z≈6）
_P_RZ = 0.96           # 手向外（+X 的狗），手尖精确落在狗头顶
_P_STROKE = 0.13       # 抚摸小幅往复（rz）
_P_HZ = 2.5


def _pose_pet(t):
    pose = _neutral()
    if t < _P_UP:
        k = _smoothstep(t / _P_UP)
        rx, rz = _P_RX * k, _P_RZ * k
    elif t <= _P_LOWER:
        rx = _P_RX
        rz = _P_RZ + _P_STROKE * math.sin(2.0 * math.pi * _P_HZ * (t - _P_UP))
    else:
        k = _smoothstep(1.0 - (t - _P_LOWER) / (PET_DURATION - _P_LOWER))
        rx, rz = _P_RX * k, _P_RZ * k
    pose["larm"] = (rx, 0.0, rz)
    # 头微微转向狗，像在看它。
    pose["head"] = (0.0, -0.35 * _smoothstep(min(1.0, t / 0.4)), 0.0)
    return pose


_POSE_FUNCS = {
    WAVE: (WAVE_DURATION, _pose_wave, None),
    CLAP: (CLAP_DURATION, _pose_clap, None),
    EAT: (EAT_DURATION, _pose_eat, None),
    JUMP: (JUMP_DURATION, _pose_jump, _root_jump),
    CHEER: (CHEER_DURATION, _pose_cheer, _root_cheer),
    YAWN: (YAWN_DURATION, _pose_yawn, None),
    DANCE: (DANCE_DURATION, _pose_dance, _root_dance),
    PET: (PET_DURATION, _pose_pet, None),
}


def is_valid(action_id) -> bool:
    return action_id in _POSE_FUNCS


def duration_of(action_id) -> float:
    return _POSE_FUNCS[action_id][0]


def root_at(action_id, t):
    """返回动作整体平移 (x,y,z)；无位移的动作返回 (0,0,0)。"""
    entry = _POSE_FUNCS[action_id]
    if entry[2] is None:
        return (0.0, 0.0, 0.0)
    t = max(0.0, min(t, entry[0]))
    return entry[2](t)


def pose_at(action_id, t):
    """返回 (姿态字典, 是否结束)；t 被夹到 [0, duration]。"""
    duration, func, _root = _POSE_FUNCS[action_id]
    t = max(0.0, min(t, duration))
    return func(t), t >= duration
