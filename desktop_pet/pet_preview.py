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

"""云朵桌宠角色 GPU 三维渲染（独立 APP，自包含）。

与启动器内角色预览共用同一套 Minecraft 原版标准玩家模型几何与着色器，但动作口径不同：

- **头部**绕颈枢轴跟随鼠标做左右转头 / 抬头低头；躯干、双腿静止；
- **固定动作**：右键菜单可触发打招呼（挥手）、拍手等过程式姿态动画，动作期间
  手臂绕肩部枢轴做三轴旋转，动作起止平滑、结束自动回到静止（见 ``pet_actions``）；
- 透明背景：轮廓之外 alpha=0，配合无边框置顶窗口把角色直接浮在桌面上；
- 皮肤由启动器以命令行参数传入文件路径，支持经典 / 细臂（slim）两种模型，
  旧 64×32 皮肤自动补齐到 64×64。
"""
import math
import os
import random
import struct

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QMatrix4x4, QSurfaceFormat, QVector3D
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVertexArrayObject,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

import pet_actions as A
import pet_constants as P
import pet_wolf as W

# ---------------------------------------------------------------------------
# 皮肤切片（64×64 标准布局），与启动器 SkinPreview 完全一致。
# ---------------------------------------------------------------------------
HEAD_CUT = {
    "front": (8, 8, 8, 8),
    "back": (24, 8, 8, 8),
    "side_left": (16, 8, 8, 8),
    "side_right": (0, 8, 8, 8),
    "top": (8, 0, 8, 8),
    "bottom": (16, 0, 8, 8),
}
BODY_CUT = {
    "front": (20, 20, 8, 12),
    "back": (32, 20, 8, 12),
    "side_left": (28, 20, 4, 12),
    "side_right": (16, 20, 4, 12),
    "top": (20, 16, 8, 4),
    "bottom": (28, 16, 8, 4),
}
ARM_CUT = {
    "front": (44, 20, 4, 12),
    "back": (52, 20, 4, 12),
    "side_left": (48, 20, 4, 12),
    "side_right": (40, 20, 4, 12),
    "top": (44, 16, 4, 4),
    "bottom": (48, 16, 4, 4),
}
SLIM_ARM_CUT = {
    "front": (44, 20, 3, 12),
    "back": (51, 20, 3, 12),
    "side_left": (47, 20, 3, 12),
    "side_right": (40, 20, 3, 12),
    "top": (44, 16, 3, 4),
    "bottom": (47, 16, 3, 4),
}
LEG_CUT = {
    "front": (4, 20, 4, 12),
    "back": (12, 20, 4, 12),
    "side_left": (8, 20, 4, 12),
    "side_right": (0, 20, 4, 12),
    "top": (4, 16, 4, 4),
    "bottom": (8, 16, 4, 4),
}

_PARTS = [
    {"name": "head", "wx": -4.0, "wy": 23.6, "w": 8.0, "h": 8.4, "depth": 8,
     "cuts": HEAD_CUT, "joint": "head", "pivot": (0.0, 24.0, 0.0), "light": 1.02},
    {"name": "body", "wx": -4.0, "wy": 12.0, "w": 8.0, "h": 12.0, "depth": 4,
     "cuts": BODY_CUT, "joint": "body", "pivot": (0.0, 12.0, 0.0), "light": 1.00},
    {"name": "rarm", "wx": -8.0, "wy": 12.0, "w": 4.0, "h": 12.0, "depth": 4,
     "cuts": ARM_CUT, "joint": "rarm", "pivot": (-6.0, 24.0, 0.0), "light": 0.92},
    {"name": "larm", "wx": 4.0, "wy": 12.0, "w": 4.0, "h": 12.0, "depth": 4,
     "cuts": ARM_CUT, "joint": "larm", "pivot": (6.0, 24.0, 0.0), "light": 0.92},
    {"name": "rleg", "wx": -4.0, "wy": 0.0, "w": 4.0, "h": 12.4, "depth": 4,
     "cuts": LEG_CUT, "joint": "rleg", "pivot": (-2.0, 12.0, 0.0), "light": 0.88},
    {"name": "lleg", "wx": 0.0, "wy": 0.0, "w": 4.0, "h": 12.4, "depth": 4,
     "cuts": LEG_CUT, "joint": "lleg", "pivot": (2.0, 12.0, 0.0), "light": 0.88},
]

# 关节名 → 枢轴，便于按动作部件取枢轴。
_PIVOT_BY_JOINT = {part["joint"]: part["pivot"] for part in _PARTS}

_CONTACT_AO = {
    ("rarm", "right"): 0.72,
    ("larm", "left"): 0.72,
    ("rleg", "right"): 0.70,
    ("lleg", "left"): 0.70,
    ("body", "top"): 0.85,
}

_FACES = [
    ("front", [7, 6, 5, 4], (0.0, 0.0, 1.0), "front"),
    ("back", [2, 3, 0, 1], (0.0, 0.0, -1.0), "back"),
    ("right", [2, 6, 5, 1], (1.0, 0.0, 0.0), "side_right"),
    ("left", [7, 3, 0, 4], (-1.0, 0.0, 0.0), "side_left"),
    ("top", [7, 6, 2, 3], (0.0, 1.0, 0.0), "top"),
    ("bottom", [0, 1, 5, 4], (0.0, -1.0, 0.0), "bottom"),
]

GL_DEPTH_TEST = 0x0B71
GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_TRIANGLES = 0x0004
GL_FLOAT = 0x1406

_STRIDE = 9 * 4

_VERTEX_SHADER = """
#version 120
attribute vec3 aPos;
attribute vec3 aNormal;
attribute vec2 aUV;
attribute float aPartShade;

uniform mat4 uModel;
uniform mat4 uViewProj;

varying vec2 vUV;
varying float vShade;

void main() {
    vUV = aUV;
    vec3 n = normalize(mat3(uModel) * aNormal);
    float shade;
    if (n.y > 0.5)       shade = 1.00;
    else if (n.y < -0.5) shade = 0.55;
    else if (n.z > 0.5)  shade = 0.92;
    else if (n.z < -0.5) shade = 0.55;
    else                 shade = 0.74;
    shade = clamp(shade * aPartShade, 0.24, 1.05);
    vShade = shade;
    gl_Position = uViewProj * uModel * vec4(aPos, 1.0);
}
"""

_FRAGMENT_SHADER = """
#version 120
uniform sampler2D uTex;
varying vec2 vUV;
varying float vShade;
void main() {
    vec4 c = texture2D(uTex, vUV);
    gl_FragColor = vec4(c.rgb * vShade, c.a);
}
"""


def _cube_vertices(wx, wy, w, h, d):
    x0, x1 = wx, wx + w
    y0, y1 = wy, wy + h
    z0, z1 = -d / 2.0, d / 2.0
    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]


def _uv_corners(rect):
    x, y, w, h = rect
    u0, u1 = x / P.TEX_W, (x + w) / P.TEX_W
    v_top = 1.0 - y / P.TEX_H
    v_bottom = 1.0 - (y + h) / P.TEX_H
    return [(u0, v_top), (u1, v_top), (u1, v_bottom), (u0, v_bottom)]


def _build_all_mesh(slim: bool):
    all_data = []
    ranges = []
    cursor = 0
    triangle = [0, 1, 2, 0, 2, 3]
    for part in _PARTS:
        geom = dict(part)
        if slim and geom["name"] in ("rarm", "larm"):
            geom["w"] = 3.0
            geom["cuts"] = SLIM_ARM_CUT
            geom["wx"] = -7.5 if geom["name"] == "rarm" else 4.5
        verts = _cube_vertices(geom["wx"], geom["wy"], geom["w"], geom["h"], geom["depth"])
        part_count = 0
        for face_name, idx, _normal, cut_key in _FACES:
            uv = _uv_corners(geom["cuts"][cut_key])
            shade = geom["light"] * _CONTACT_AO.get((geom["name"], face_name), 1.0)
            for i in triangle:
                vi = idx[i]
                px, py, pz = verts[vi]
                u, v = uv[i]
                all_data.extend([px, py, pz, _normal[0], _normal[1], _normal[2], u, v, shade])
                part_count += 1
        ranges.append((geom, cursor, part_count))
        cursor += part_count
    return all_data, ranges


def _normalize_skin(image: QImage) -> QImage:
    if image.height() >= P.TEX_H:
        return image
    canvas = QImage(P.TEX_W, P.TEX_H, QImage.Format_RGBA8888)
    canvas.fill(Qt.transparent)
    from PySide6.QtGui import QPainter
    painter = QPainter(canvas)
    painter.drawImage(0, 0, image)
    painter.end()
    return canvas


# ---------------------------------------------------------------------------
# 手持食物（独立物品纹理，平面贴在右手，随 rarm 关节矩阵移动）
# ---------------------------------------------------------------------------
FOOD_DEFS = {
    "beef": "items/cooked_beef.png",
    "porkchop": "items/cooked_porkchop.png",
}
# 食物平面尺寸（以原点为中心，绘制时只平移到手尖、不旋转，始终正对观察者）。
_FOOD_SIZE = 4.6
# 手尖附着点：手臂下垂时该点的世界坐标，每帧用 rarm 矩阵变换得到当前手尖位置。
# 反向求解得到，使手臂前举（rx=-1.0, rz=0.6）后食物精确落在嘴前 (0,25.5,5.5)。
_FOOD_ANCHOR = (-0.201, 18.21, 1.163)


def _build_food_mesh():
    half = _FOOD_SIZE / 2.0
    x0, x1 = -half, half
    y0, y1 = -half, half
    # (x, y, u, v)：平面顶部 y1 对应 v=1（QImage 顶部），物品正立。
    corners = [
        (x0, y0, 0.0, 0.0),
        (x1, y0, 1.0, 0.0),
        (x1, y1, 1.0, 1.0),
        (x0, y1, 0.0, 1.0),
    ]
    normal = (0.0, 0.0, 1.0)
    data = []
    for i in (0, 1, 2, 0, 2, 3):
        px, py, u, v = corners[i]
        data.extend([px, py, 0.0, normal[0], normal[1], normal[2], u, v, 1.0])
    return data


class PetPreview(QOpenGLWidget):
    """桌宠角色：头部跟随鼠标，手臂可播放固定动作（打招呼 / 拍手）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 独立透明窗在 Windows/DWM 下需压到合成最上层，否则透明区发黑。
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAutoFillBackground(False)

        self._image: QImage | None = None
        self._slim = False
        self._prog = None
        self._texture = None
        self._vbo = None
        self._vao = None
        self._part_ranges = []
        self._loc = {}

        # 仅头部角度（当前值 / 目标值），[-1,1] 归一化。
        self._yaw = 0.0
        self._pitch = 0.0
        self._yaw_target = 0.0
        self._pitch_target = 0.0

        # 当前固定动作（None 为空闲）与已进行时间（秒）。
        self._action_id = None
        self._action_elapsed = 0.0

        # 睡眠状态：是否入睡与姿态过渡系数（0..1，平滑蜷缩/醒来）。
        self._sleeping = False
        self._sleep_blend = 0.0

        # 手持食物：独立纹理字典、当前食物 id；食物顶点并入主 VBO，记录起始/数量。
        self._food_textures = {}
        self._food_id = "beef"
        self._food_start = 0
        self._food_count = 0

        # 小狗（驯服狼）：独立纹理、显隐状态；顶点并入主 VBO，记录起始/数量。
        self._wolf_texture = None
        self._wolf_visible = False
        self._wolf_start = 0
        self._wolf_count = 0
        # 狼动画时间（秒）与是否走路（进场/移动时 True，陪伴静止时 False）。
        self._wolf_time = 0.0
        self._wolf_walking = False
        # 进场：当前 x 位置与是否正在进场（从右侧走入，到达 WOLF_X 后静止）。
        self._wolf_x = W.WOLF_X
        self._wolf_entering = False
        # 被喂：开心反应已进行时间（None 表示未在被喂）。
        self._wolf_feed_time = None
        # 被摸：舒服反应已进行时间（None 表示未在被摸）。
        self._wolf_pet_time = None

        self._timer = QTimer(self)
        self._timer.setInterval(P.POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ---------- 皮肤 ----------
    def set_skin_file(self, path: str, slim: bool) -> bool:
        """从文件加载皮肤；失败返回 False，由调用方保留旧皮肤或回退默认。"""
        image = QImage(path)
        if image.isNull():
            return False
        self._image = _normalize_skin(image)
        self._slim = bool(slim)
        if self._texture is not None:
            self._rebuild_texture()
        if self._vbo is not None:
            self._rebuild_mesh()
        self.update()
        return True

    def _current_image(self) -> QImage:
        if self._image is not None:
            return self._image
        image = QImage(P.default_skin_path())
        if image.isNull():
            image = QImage(P.TEX_W, P.TEX_H, QImage.Format_RGBA8888)
            image.fill("#9fc9e0")
        return image

    def _rebuild_texture(self) -> None:
        if self._texture is not None:
            self._texture.destroy()
            self._texture = None
        image = self._current_image().mirrored(False, True)
        self._texture = QOpenGLTexture(QOpenGLTexture.Target2D)
        self._texture.setData(image)
        self._texture.setMinificationFilter(QOpenGLTexture.Nearest)
        self._texture.setMagnificationFilter(QOpenGLTexture.Nearest)
        self._texture.setWrapMode(QOpenGLTexture.ClampToEdge)
        self._texture.setMipLevels(1)

    def _rebuild_mesh(self) -> None:
        all_data, self._part_ranges = _build_all_mesh(self._slim)
        QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo.bind()
        self._vbo.allocate(struct.pack(f"{len(all_data)}f", *all_data), len(all_data) * 4)

    # ---------- GL 初始化 ----------
    def initializeGL(self) -> None:
        gl = self.context().functions()
        gl.glEnable(GL_DEPTH_TEST)
        gl.glEnable(GL_BLEND)
        gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)

        self._prog = QOpenGLShaderProgram()
        v_ok = self._prog.addShaderFromSourceCode(QOpenGLShader.Vertex, _VERTEX_SHADER)
        f_ok = self._prog.addShaderFromSourceCode(QOpenGLShader.Fragment, _FRAGMENT_SHADER)
        self._prog.link()
        if not (v_ok and f_ok and self._prog.isLinked()):
            raise RuntimeError("shader compile/link failed: " + self._prog.log())

        self._loc = {
            "viewproj": self._prog.uniformLocation("uViewProj"),
            "model": self._prog.uniformLocation("uModel"),
            "tex": self._prog.uniformLocation("uTex"),
        }

        all_data, self._part_ranges = _build_all_mesh(self._slim)
        # 食物平面顶点并入主 VBO 末尾，复用同一 VAO/属性，仅 drawArrays 区间不同。
        food_data = _build_food_mesh()
        self._food_start = len(all_data) // 9
        self._food_count = len(food_data) // 9
        all_data = all_data + food_data
        # 小狗（驯服狼）顶点继续追加，独立纹理、独立 model 矩阵。
        wolf_data, self._wolf_ranges = W.build_wolf_mesh()
        self._wolf_start = len(all_data) // 9
        self._wolf_count = len(wolf_data) // 9
        all_data = all_data + wolf_data

        self._vao = QOpenGLVertexArrayObject()
        self._vao.create()
        QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vbo.create()
        self._vbo.bind()
        self._vbo.allocate(struct.pack(f"{len(all_data)}f", *all_data), len(all_data) * 4)

        self._prog.bind()
        self._prog.setAttributeBuffer("aPos", GL_FLOAT, 0, 3, _STRIDE)
        self._prog.setAttributeBuffer("aNormal", GL_FLOAT, 3 * 4, 3, _STRIDE)
        self._prog.setAttributeBuffer("aUV", GL_FLOAT, 6 * 4, 2, _STRIDE)
        self._prog.setAttributeBuffer("aPartShade", GL_FLOAT, 8 * 4, 1, _STRIDE)
        for name in ("aPos", "aNormal", "aUV", "aPartShade"):
            self._prog.enableAttributeArray(name)
        self._prog.release()

        self._rebuild_texture()
        self._build_food_textures()
        self._build_wolf_texture()

    def _build_wolf_texture(self) -> None:
        """加载驯服狼纹理（独立 QImage，不做上下翻转，UV 已按桌宠坐标定义）。"""
        path = P.resource_path("entity/wolf/wolf_tame.png")
        image = QImage(path)
        if image.isNull():
            raise RuntimeError("wolf texture missing: " + path)
        texture = QOpenGLTexture(image.mirrored(False, True))
        texture.setMinificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setMagnificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        self._wolf_texture = texture

    def _build_food_textures(self) -> None:
        """加载各食物物品纹理（独立 QImage，不做上下翻转，UV 已按正立定义）。"""
        for fid, rel in FOOD_DEFS.items():
            path = P.resource_path(rel)
            image = QImage(path)
            if image.isNull():
                raise RuntimeError("food texture missing: " + path)
            texture = QOpenGLTexture(image.mirrored(False, True))
            texture.setMinificationFilter(QOpenGLTexture.Filter.Nearest)
            texture.setMagnificationFilter(QOpenGLTexture.Filter.Nearest)
            texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
            self._food_textures[fid] = texture

    def resizeGL(self, w, h) -> None:
        self.context().functions().glViewport(0, 0, w, h)

    # ---------- 头部跟随 ----------
    def on_pointer(self, nx: float, ny: float) -> None:
        self._yaw_target = max(-1.0, min(1.0, nx))
        self._pitch_target = max(-1.0, min(1.0, ny))

    # ---------- 固定动作 ----------
    def trigger_action(self, action_id, food_id=None) -> None:
        """触发指定固定动作；动作播放中再次触发会立即切换到新动作。

        EAT 时可通过 ``food_id`` 指定牛排 / 猪排；缺省则随机选择。
        """
        if not A.is_valid(action_id):
            return
        if action_id == A.EAT:
            if food_id is not None and food_id in FOOD_DEFS:
                self._food_id = food_id
            else:
                # 未指定时随机选牛排 / 猪排。
                self._food_id = random.choice(list(FOOD_DEFS.keys()))
        self._action_id = action_id
        self._action_elapsed = 0.0

    def stop_action(self) -> None:
        """立即停止动作（鼠标一动回到正常时调用）。"""
        self._action_id = None
        self._action_elapsed = 0.0

    def is_acting(self) -> bool:
        return self._action_id is not None

    # ---------- 睡眠 ----------
    def set_sleeping(self, flag: bool) -> None:
        self._sleeping = bool(flag)
        self.update()

    def is_sleeping(self) -> bool:
        return self._sleeping

    def _sleep_pose(self):
        """返回睡眠姿态（各关节 rx/ry/rz），按当前过渡系数缩放。"""
        b = self._sleep_blend
        return {
            "head": (-0.55 * b, 0.0, 0.0),
            "body": (-0.40 * b, 0.0, 0.0),
            "rarm": (-0.70 * b, 0.0, 0.0),
            "larm": (-0.70 * b, 0.0, 0.0),
            # 双腿水平前伸（坐姿），脚抬起以补偿整体下沉、不穿入地面。
            "rleg": (-1.20 * b, 0.0, 0.0),
            "lleg": (-1.20 * b, 0.0, 0.0),
        }

    def _action_pose(self):
        if self._action_id is None:
            return None
        pose, _ = A.pose_at(self._action_id, self._action_elapsed)
        return pose

    def _tick(self) -> None:
        # 睡眠姿态过渡（蜷缩 / 醒来）。
        target_blend = 1.0 if self._sleeping else 0.0
        self._sleep_blend += (target_blend - self._sleep_blend) * P.SLEEP_BLEND_FACTOR
        if abs(self._sleep_blend - target_blend) < 0.002:
            self._sleep_blend = target_blend
        self._yaw += (self._yaw_target - self._yaw) * P.SMOOTH_FACTOR
        self._pitch += (self._pitch_target - self._pitch) * P.SMOOTH_FACTOR
        if abs(self._yaw - self._yaw_target) < 0.001:
            self._yaw = self._yaw_target
        if abs(self._pitch - self._pitch_target) < 0.001:
            self._pitch = self._pitch_target
        # 推进固定动作计时，结束自动复位。
        if self._action_id is not None:
            self._action_elapsed += P.POLL_INTERVAL_MS / 1000.0
            _pose, finished = A.pose_at(self._action_id, self._action_elapsed)
            if finished:
                self.stop_action()
        # 推进小狗动画时间（走路/摇尾巴）。
        if self._wolf_visible:
            dt = P.POLL_INTERVAL_MS / 1000.0
            self._wolf_time += dt
            # 进场：从右侧走路进入，到达最终位置后转为静止陪伴。
            if self._wolf_entering:
                self._wolf_x -= W.WOLF_MOVE_SPEED * dt
                if self._wolf_x <= W.WOLF_X:
                    self._wolf_x = W.WOLF_X
                    self._wolf_entering = False
                    self._wolf_walking = False
            # 被喂开心反应：推进计时，持续到 FEED_DURATION 后结束。
            if self._wolf_feed_time is not None:
                self._wolf_feed_time += dt
                if self._wolf_feed_time >= W.FEED_DURATION:
                    self._wolf_feed_time = None
            # 被摸舒服反应：推进计时，持续到 PETTED_DURATION 后结束。
            if self._wolf_pet_time is not None:
                self._wolf_pet_time += dt
                if self._wolf_pet_time >= W.PETTED_DURATION:
                    self._wolf_pet_time = None
        self.update()

    @staticmethod
    def _joint_matrix(pivot, rx, ry, rz=0.0):
        j = QMatrix4x4()
        j.translate(pivot[0], pivot[1], pivot[2])
        # 旋转顺序与启动器 skin_preview 对齐：先 Z、再 Y、再 X。
        if rz:
            j.rotate(math.degrees(rz), QVector3D(0, 0, 1))
        if ry:
            j.rotate(math.degrees(ry), QVector3D(0, 1, 0))
        if rx:
            j.rotate(math.degrees(rx), QVector3D(1, 0, 0))
        j.translate(-pivot[0], -pivot[1], -pivot[2])
        return j

    # ---------- 绘制 ----------
    def paintGL(self) -> None:
        gl = self.context().functions()
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self._prog is None or self._texture is None:
            return

        aspect = self.width() / max(1, self.height())
        proj = QMatrix4x4()
        proj.perspective(P.CAM_FOV, aspect, 0.1, 200.0)
        view = QMatrix4x4()
        view.translate(0.0, -P.MODEL_CY, -P.CAM_DIST)
        view_proj = proj * view

        # 头部始终跟随鼠标：左右→绕 Y 转头，上下→绕 X 抬头/低头（取负使上移抬头）。
        head_ry = self._yaw * P.HEAD_YAW_RAD
        head_rx = -self._pitch * P.HEAD_PITCH_RAD
        action_pose = self._action_pose()
        sleep_pose = self._sleep_pose() if self._sleep_blend > 0.001 else None
        # 整体位移：动作 root（跳跃/跳舞/欢呼）+ 睡眠蜷缩下沉。
        root_matrix = QMatrix4x4()
        if self._action_id is not None:
            root_matrix.translate(*A.root_at(self._action_id, self._action_elapsed))
        if sleep_pose is not None:
            root_matrix.translate(0.0, -7.5 * self._sleep_blend, 0.0)

        self._prog.bind()
        self._prog.setUniformValue(self._loc["viewproj"], view_proj)
        self._prog.setUniformValue(self._loc["tex"], 0)
        self._texture.bind(0)

        QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo.bind()
        for geom, start, count in self._part_ranges:
            joint = geom["joint"]
            if sleep_pose is not None:
                # 睡眠（含过渡）：睡眠姿态优先，头部不再跟随鼠标。
                srx, sry, srz = sleep_pose[joint]
                joint_model = self._joint_matrix(geom["pivot"], srx, sry, srz)
            elif joint == "head":
                joint_model = self._joint_matrix(geom["pivot"], head_rx, head_ry)
            elif action_pose is not None:
                arx, ary, arz = action_pose[joint]
                joint_model = self._joint_matrix(geom["pivot"], arx, ary, arz)
            else:
                # 无动作时身体各部件静止：单位关节矩阵。
                joint_model = QMatrix4x4()
            model = root_matrix * joint_model
            self._prog.setUniformValue(self._loc["model"], model)
            gl.glDrawArrays(GL_TRIANGLES, start, count)

        # 吃东西：食物始终正对观察者，只跟随手尖位置（rarm 矩阵变换附着点）。
        if self._action_id == A.EAT:
            food_tex = self._food_textures.get(self._food_id)
            if food_tex is not None:
                arx, ary, arz = action_pose["rarm"]
                arm_matrix = self._joint_matrix(
                    _PIVOT_BY_JOINT["rarm"], arx, ary, arz)
                hand_pos = arm_matrix.map(QVector3D(*_FOOD_ANCHOR))
                # 玩家整体位移（如跳跃）时，手持食物一起跟随。
                hand_pos = root_matrix.map(hand_pos)
                food_model = QMatrix4x4()
                food_model.translate(hand_pos)
                self._prog.setUniformValue(self._loc["model"], food_model)
                food_tex.bind(0)
                gl.glDrawArrays(GL_TRIANGLES, self._food_start, self._food_count)
                self._texture.bind(0)

        # 小狗（驯服狼）：独立纹理，部件级旋转（走路/摇尾巴/被喂开心），平移到玩家侧方。
        if self._wolf_visible and self._wolf_texture is not None:
            happy = self._wolf_feed_time is not None
            petted = not happy and self._wolf_pet_time is not None
            if happy:
                anim_t = self._wolf_feed_time
            elif petted:
                anim_t = self._wolf_pet_time
            else:
                anim_t = self._wolf_time
            walking = self._wolf_walking and not (happy or petted)
            wolf_pose = W.wolf_pose_at(
                anim_t, walking, happy=happy, petted=petted)
            bob = W.body_bob_at(
                anim_t, walking, happy=happy, petted=petted)
            base = QMatrix4x4()
            base.translate(self._wolf_x, W.WOLF_Y + bob, 0.0)
            self._wolf_texture.bind(0)
            for name, desk_pivot, rel_start, rel_count in self._wolf_ranges:
                wrx, wry, wrz = wolf_pose[name]
                part_model = QMatrix4x4(base)
                part_model *= self._joint_matrix(desk_pivot, wrx, wry, wrz)
                self._prog.setUniformValue(self._loc["model"], part_model)
                gl.glDrawArrays(
                    GL_TRIANGLES, self._wolf_start + rel_start, rel_count)
            self._texture.bind(0)
        self._prog.release()

    # ---------- 小狗显隐 ----------
    def show_wolf(self) -> None:
        # 从右侧走路进场：重置时间与位置，进入走路状态。
        self._wolf_visible = True
        self._wolf_time = 0.0
        self._wolf_x = W.WOLF_X + W.WOLF_ENTER_OFFSET
        self._wolf_entering = True
        self._wolf_walking = True
        self.update()

    def hide_wolf(self) -> None:
        self._wolf_visible = False
        self._wolf_entering = False
        self._wolf_walking = False
        self._wolf_x = W.WOLF_X
        self._wolf_feed_time = None
        self._wolf_pet_time = None
        self.update()

    def feed_wolf(self) -> None:
        """喂小狗：触发开心反应（快速摇尾/点头/轻跳），进场中也可立即反应。"""
        if not self._wolf_visible:
            return
        self._wolf_feed_time = 0.0
        self.update()

    def is_wolf_feeding(self) -> bool:
        return self._wolf_feed_time is not None

    def pet_wolf(self) -> None:
        """摸小狗：触发舒服反应（慢摇尾/轻蹭），进场中也可立即反应。"""
        if not self._wolf_visible:
            return
        self._wolf_pet_time = 0.0
        self.update()

    def is_wolf_petted(self) -> bool:
        return self._wolf_pet_time is not None

    def is_wolf_visible(self) -> bool:
        return self._wolf_visible
