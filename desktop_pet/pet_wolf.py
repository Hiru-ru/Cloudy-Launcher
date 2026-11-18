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

"""云朵桌宠 MC 驯服狼（小狗）几何（仅标准库）。

依据 MC 1.20.1 ``WolfModel`` 的部件尺寸 / 枢轴 / 纹理偏移，在生成顶点时把 MC
模型空间（Y 向下、头朝 -Z）换算到桌宠坐标系（Y 向上、面朝 +Z）。第一版为静态
站立几何，部件枢轴信息保留，供后续走路 / 摇尾巴动画使用。
"""
import pet_constants as P

# 小狗在桌宠场景中的摆放：横向偏移到玩家侧方、上移使脚（局部 y=-24）落到地面 y=0。
WOLF_X = 12.0
WOLF_Y = 24.0
# 进场：从最终位置右侧偏移处走路进入，移动速度（桌宠单位/秒）。
WOLF_ENTER_OFFSET = 26.0
WOLF_MOVE_SPEED = 15.0

# 狼纹理实际尺寸（64×32，区别于玩家皮肤的 64×64）。
WOLF_TEX_W = 64
WOLF_TEX_H = 32

# 后腿动画枢轴下移到身体下沿（静态顶点不变，仅旋转中心下移），避免前摆时穿入身体。
HIND_ANIM_PIVOT_Y = -18.5

# (名称, MC 枢轴, box 局部偏移, box 尺寸 w/h/d, 纹理偏移 u/v)。
_WOLF_PARTS = [
    ("head", (-1.0, 13.5, -7.0), (-3.0, -3.0, -2.0), (6.0, 6.0, 4.0), (0, 0)),
    ("body", (0.0, 14.0, 2.0), (-4.0, -2.0, -3.0), (8.0, 6.0, 7.0), (18, 14)),
    # 后腿截短到身体下沿（MC box 从 y=2 起、高 6，去掉嵌入身体的 2 单位），
    # 这部分原本被身体遮挡，截短不改变可见外观，且走路时不再穿入身体。
    ("leg_hind_r", (-2.5, 16.0, 7.0), (-1.0, 2.0, -1.0), (2.0, 6.0, 2.0), (0, 18)),
    ("leg_hind_l", (0.5, 16.0, 7.0), (-1.0, 2.0, -1.0), (2.0, 6.0, 2.0), (0, 18)),
    ("leg_front_r", (-2.5, 16.0, -4.0), (-1.0, 0.0, -1.0), (2.0, 8.0, 2.0), (0, 18)),
    ("leg_front_l", (0.5, 16.0, -4.0), (-1.0, 0.0, -1.0), (2.0, 8.0, 2.0), (0, 18)),
    ("tail", (-1.0, 12.0, 8.0), (-1.0, 0.0, -1.0), (2.0, 8.0, 2.0), (9, 18)),
]

# 桌宠六面（与 pet_preview._FACES 同名）→ 转换后对应的 MC 面。
# 坐标转换 x'=x, y'=-y, z'=-z：front/back（脸朝 +z'）来源不变，top/bottom 因 Y 翻转互换。
_DESK_TO_MC = {
    "front": "front",
    "back": "back",
    "right": "right",
    "left": "left",
    "top": "bottom",
    "bottom": "top",
}

# 桌宠面的顶点索引与法线（同 pet_preview._FACES），基于标准 8 顶点顺序。
_FACES = [
    ("front", [7, 6, 5, 4], (0.0, 0.0, 1.0)),
    ("back", [2, 3, 0, 1], (0.0, 0.0, -1.0)),
    ("right", [2, 6, 5, 1], (1.0, 0.0, 0.0)),
    ("left", [7, 3, 0, 4], (-1.0, 0.0, 0.0)),
    ("top", [7, 6, 2, 3], (0.0, 1.0, 0.0)),
    ("bottom", [0, 1, 5, 4], (0.0, -1.0, 0.0)),
]
_TRIANGLE = [0, 1, 2, 0, 2, 3]


def _mc_face_rect(texoff, w, h, d, mc_face):
    """返回 MC box 某面在纹理上的像素矩形 (x, y, w, h)。"""
    u, v = texoff
    if mc_face == "right":
        return (u, v + d, d, h)
    if mc_face == "front":
        return (u + d, v + d, w, h)
    if mc_face == "left":
        return (u + d + w, v + d, d, h)
    if mc_face == "back":
        return (u + d + w + d, v + d, w, h)
    if mc_face == "top":
        return (u + d, v, w, d)
    # bottom
    return (u + d + w, v, w, d)


def _uv_norm(rect):
    x, y, rw, rh = rect
    u0 = x / WOLF_TEX_W
    u1 = (x + rw) / WOLF_TEX_W
    v_top = 1.0 - y / WOLF_TEX_H
    v_bottom = 1.0 - (y + rh) / WOLF_TEX_H
    return [(u0, v_top), (u1, v_top), (u1, v_bottom), (u0, v_bottom)]


def build_wolf_mesh():
    """生成狼全部顶点（桌宠局部坐标，脚在 y=-24）与每部件字节范围。"""
    all_data = []
    ranges = []
    cursor = 0
    for name, pivot, off, size, texoff in _WOLF_PARTS:
        w, h, d = size
        # MC 枢轴转换到桌宠坐标（x'=x, y'=-y, z'=-z），供部件旋转使用。
        desk_pivot = (pivot[0], -pivot[1], -pivot[2])
        # MC 世界 AABB（第一版不做枢轴旋转）。
        mx0 = pivot[0] + off[0]
        my0 = pivot[1] + off[1]
        mz0 = pivot[2] + off[2]
        mx1, my1, mz1 = mx0 + w, my0 + h, mz0 + d
        # 转换到桌宠坐标并整理成标准 8 顶点顺序（z0 为 back）。
        x0, x1 = mx0, mx1
        y0, y1 = -my1, -my0
        z0, z1 = -mz1, -mz0
        verts = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        part_count = 0
        for desk_face, idx, normal in _FACES:
            mc_face = _DESK_TO_MC[desk_face]
            uv = _uv_norm(_mc_face_rect(texoff, w, h, d, mc_face))
            for i in _TRIANGLE:
                px, py, pz = verts[idx[i]]
                u, v = uv[i]
                all_data.extend([px, py, pz, normal[0], normal[1], normal[2],
                                 u, v, 1.0])
                part_count += 1
        # 后腿用下移后的动画枢轴，其余部件用转换枢轴；静态顶点不受影响。
        anim_pivot = desk_pivot
        if name.startswith("leg_hind"):
            anim_pivot = (desk_pivot[0], HIND_ANIM_PIVOT_Y, desk_pivot[2])
        ranges.append((name, anim_pivot, cursor, part_count))
        cursor += part_count
    return all_data, ranges


# ---------- 动画 ----------
import math  # noqa: E402

WALK_HZ = 2.4          # 走路时腿摆动频率
LEG_SWING = 0.55       # 腿前后摆幅（rad）
TAIL_UP = 1.9          # 驯服狼尾巴上翘基础角（rx，>90° 使尾巴向后上方翘起）
TAIL_WAG = 0.42        # 尾巴左右摇幅度（rz）
WALK_TAIL_HZ = 2.6     # 走路时摇尾频率
IDLE_TAIL_HZ = 1.3     # 静止时摇尾频率
HEAD_NOD = 0.10        # 走路时头部点动幅度
BODY_BOB = 0.55        # 走路时身体上下起伏幅度

# 被喂时的开心反应：快速摇尾、头部点动（咀嚼/开心）、身体轻跳。
FEED_DURATION = 1.7
HAPPY_TAIL_HZ = 5.2
HAPPY_TAIL_WAG = 0.62
HAPPY_HEAD_NOD = 0.32
HAPPY_BOB = 1.0

# 被摸时的舒服反应（柔和，区别于被喂的剧烈）：慢摇尾、头轻蹭、身体小幅前倾。
PETTED_DURATION = 2.0
PETTED_TAIL_HZ = 1.6
PETTED_TAIL_WAG = 0.5
PETTED_HEAD_TILT = 0.22     # 头向玩家方向轻蹭（rz）
PETTED_HEAD_NOD = 0.12      # 轻微低头（rx）
PETTED_BODY_LEAN = 0.10     # 身体小幅前倾
PETTED_BOB = 0.35

# 对角腿同相：front-right 与 hind-left 一组，front-left 与 hind-right 一组。
_LEG_PHASE = {
    "leg_front_r": 0.0,
    "leg_hind_l": 0.0,
    "leg_front_l": math.pi,
    "leg_hind_r": math.pi,
}


def wolf_pose_at(t, walking, happy=False, petted=False):
    """返回每个部件的 (rx, ry, rz)；t 为动画时间（秒）。

    happy 为被喂的开心反应（最优先）；petted 为被摸的舒服反应（次之）；
    否则按 walking 走路 / 静止姿态。
    """
    pose = {}
    if happy:
        for name in _LEG_PHASE:
            pose[name] = (0.0, 0.0, 0.0)
        tail_phase = 2.0 * math.pi * HAPPY_TAIL_HZ * t
        pose["tail"] = (TAIL_UP, 0.0, HAPPY_TAIL_WAG * math.sin(tail_phase))
        nod = HAPPY_HEAD_NOD * abs(math.sin(tail_phase))
        pose["head"] = (nod, 0.0, 0.0)
        pose["body"] = (0.0, 0.0, 0.0)
        return pose
    if petted:
        for name in _LEG_PHASE:
            pose[name] = (0.0, 0.0, 0.0)
        tail_phase = 2.0 * math.pi * PETTED_TAIL_HZ * t
        pose["tail"] = (TAIL_UP, 0.0, PETTED_TAIL_WAG * math.sin(tail_phase))
        # 头向玩家（-X 方向，rz 负）轻蹭，并轻微低头。
        pose["head"] = (PETTED_HEAD_NOD, 0.0,
                        -PETTED_HEAD_TILT * (0.6 + 0.4 * math.sin(tail_phase)))
        pose["body"] = (PETTED_BODY_LEAN, 0.0, 0.0)
        return pose
    if walking:
        phase_leg = 2.0 * math.pi * WALK_HZ * t
        for name, ph in _LEG_PHASE.items():
            pose[name] = (LEG_SWING * math.sin(phase_leg + ph), 0.0, 0.0)
        tail_phase = 2.0 * math.pi * WALK_TAIL_HZ * t
        pose["tail"] = (TAIL_UP, 0.0, TAIL_WAG * math.sin(tail_phase))
        nod = HEAD_NOD * math.sin(phase_leg)
        pose["head"] = (nod, 0.0, 0.0)
        pose["body"] = (0.0, 0.0, 0.0)
    else:
        for name in _LEG_PHASE:
            pose[name] = (0.0, 0.0, 0.0)
        tail_phase = 2.0 * math.pi * IDLE_TAIL_HZ * t
        pose["tail"] = (TAIL_UP, 0.0, TAIL_WAG * 0.7 * math.sin(tail_phase))
        pose["head"] = (0.0, 0.0, 0.0)
        pose["body"] = (0.0, 0.0, 0.0)
    return pose


def body_bob_at(t, walking, happy=False, petted=False):
    """身体整体上下起伏（y 平移）：开心轻跳、被摸小幅起伏、走路起伏、静止为 0。"""
    if happy:
        return HAPPY_BOB * abs(math.sin(2.0 * math.pi * HAPPY_TAIL_HZ * t))
    if petted:
        return PETTED_BOB * (0.5 + 0.5 * math.sin(2.0 * math.pi * PETTED_TAIL_HZ * t))
    if not walking:
        return 0.0
    return BODY_BOB * abs(math.sin(2.0 * math.pi * WALK_HZ * t))
