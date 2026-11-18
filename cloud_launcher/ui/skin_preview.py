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

"""Minecraft 角色 GPU 三维预览组件（QOpenGLWidget 真三维渲染管线）。

本组件按 Minecraft 原版标准玩家模型几何，由 GPU 实时渲染角色：

- 头 8×8×8、躯干 8×12×4、双臂各 4×12×4、双腿各 4×12×4，尺寸与位置
  与游戏内玩家模型一致；皮肤为官方 64×64 原版贴图，整图作为一张纹理，
  各面按标准 UV 切片映射；
- 关节级动作：双臂绕肩关节做缓慢、小幅左右张合；指针跟随时分两层——整体刚体
  （躯干 / 双臂 / 双腿）朝指针方向做小幅同步偏转，头部绕颈枢轴以更大幅度领先
  左右转头、抬头 / 低头（斜向指针为两个角度的组合），关节枢轴设在肩 / 颈 / 髋
  连接处；取证脚本关闭日常跟随开关时，才由整体刚体承担全身 yaw / pitch 用于检查
  六面渲染；
- GPU 管线：透视投影、硬件深度缓冲遮挡、最近邻（Nearest）纹理采样、MC 式
  固定面朝向亮度档（顶面最亮、正面接近原色、侧面压暗、背面 / 底面最暗），
  与游戏内背包预览的渲染方式一致；
- 默认正面正对镜头；指针在整窗任意位置移动时，身体小幅同步偏转、头部领先跟随，
  按住左键可拖动，指针移出窗口回到正面；待机动画与指针 / 拖拽转向互不干扰。

对外接口与旧软件版保持一致：``set_skin`` / ``on_global_pointer`` /
``reset_target`` 以及拖拽鼠标事件；主窗口全局轮询跟随链路无需改动。

v1.2.4.3：3D 预览控件背景彻底透明，角色直接浮在外层磨砂卡片上，轮廓之外透出卡片局部
磨砂与壁纸，不再出现独立的白 / 灰矩形底板，也不允许退化成黑底。组合开关缺一不可：

- 颜色缓冲请求 8 位 alpha（``setAlphaBufferSize(8)``）；
- ``WA_TranslucentBackground`` + 关闭自动填充背景，控件自身不铺底色；
- ``WA_AlwaysStackOnTop``：Qt 官方说明 QOpenGLWidget 默认先于所有普通非 GL 控件绘制，
  下方 widget 透不过来；只开 alpha 缓冲在本机 Windows / DWM 真实屏幕合成下会把 alpha=0
  清屏区显示成黑色矩形（离屏 ``grab()`` 合成正常、屏幕合成发黑，这一差异必须用真实窗口
  屏幕截图复核，不能只看 widget 截图）。压到合成顺序最上层后，轮廓之外的 alpha=0 区域才能
  透出下方卡片磨砂；本控件矩形之上没有叠放其他控件，打破堆叠顺序的副作用在此场景不成立；
- ``GL_BLEND`` 源 alpha 混合，清屏 ``(0,0,0,0)``；角色不透明片 alpha=1，透明区不写底色。

本机 Intel UHD 620 / OpenGL 4.6 / Qt 6.12 真实窗口屏幕截图实测：透明区与卡片磨砂参照逐
通道一致，无黑底、无独立白板；几何、相机、指针跟随、待机摆臂与皮肤接口保持不变。
"""
import math
import os
import struct

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QSurfaceFormat,
    QImage,
    QMatrix4x4,
    QPainter,
    QVector3D,
)
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVertexArrayObject,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QSizePolicy

from .. import constants as C
from ..resources import resource_path


# ---------------------------------------------------------------------------
# 皮肤切片源矩形（单位皮肤像素，64×64 标准布局）。
# 每个部件给出 front / back / side_left / side_right / top / bottom 六面。
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
# 细臂（SLIM / Alex 模型）专用 64×64 切片：手臂宽 3，高度与深度不变。
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

# 部件世界参数与关节配置。坐标系：x 向右、y 向上、z 朝观察者（前 +z）；
# 脚底 y=0，总高 32；z 前后居中。几何严格遵循 Minecraft 原版标准玩家模型。
_PARTS = [
    {
        "name": "head", "wx": -4.0, "wy": 23.6, "w": 8.0, "h": 8.4, "depth": 8,
        "layer": 2, "cuts": HEAD_CUT, "joint": "head", "pivot": (0.0, 24.0, 0.0),
        "layer_light": 1.02,
    },
    {
        "name": "body", "wx": -4.0, "wy": 12.0, "w": 8.0, "h": 12.0, "depth": 4,
        "layer": 1, "cuts": BODY_CUT, "joint": "body", "pivot": (0.0, 12.0, 0.0),
        "layer_light": 1.00,
    },
    {
        "name": "rarm", "wx": -8.0, "wy": 12.0, "w": 4.0, "h": 12.0, "depth": 4,
        "layer": 0, "cuts": ARM_CUT, "joint": "rarm", "pivot": (-6.0, 24.0, 0.0),
        "layer_light": 0.92,
    },
    {
        "name": "larm", "wx": 4.0, "wy": 12.0, "w": 4.0, "h": 12.0, "depth": 4,
        "layer": 0, "cuts": ARM_CUT, "joint": "larm", "pivot": (6.0, 24.0, 0.0),
        "layer_light": 0.92,
    },
    {
        "name": "rleg", "wx": -4.0, "wy": 0.0, "w": 4.0, "h": 12.4, "depth": 4,
        "layer": 0, "cuts": LEG_CUT, "joint": "rleg", "pivot": (-2.0, 12.0, 0.0),
        "layer_light": 0.88,
    },
    {
        "name": "lleg", "wx": 0.0, "wy": 0.0, "w": 4.0, "h": 12.4, "depth": 4,
        "layer": 0, "cuts": LEG_CUT, "joint": "lleg", "pivot": (2.0, 12.0, 0.0),
        "layer_light": 0.88,
    },
]

# 互相贴合的内侧窄面接触暗部（部件名, 局部面名）。
_CONTACT_AO = {
    ("rarm", "right"): 0.72,
    ("larm", "left"): 0.72,
    ("rleg", "right"): 0.70,
    ("lleg", "left"): 0.70,
    ("body", "top"): 0.85,
}

# 立方体 8 个局部顶点编号：
# 0:(x0,y0,z0) 1:(x1,y0,z0) 2:(x1,y1,z0) 3:(x0,y1,z0)
# 4:(x0,y0,z1) 5:(x1,y0,z1) 6:(x1,y1,z1) 7:(x0,y1,z1)
# 六面：(面名, 顶点序, 模型法线, 切片键)
_FACES = [
    ("front", [7, 6, 5, 4], (0.0, 0.0, 1.0), "front"),
    ("back", [2, 3, 0, 1], (0.0, 0.0, -1.0), "back"),
    ("right", [2, 6, 5, 1], (1.0, 0.0, 0.0), "side_right"),
    ("left", [7, 3, 0, 4], (-1.0, 0.0, 0.0), "side_left"),
    ("top", [7, 6, 2, 3], (0.0, 1.0, 0.0), "top"),
    ("bottom", [0, 1, 5, 4], (0.0, -1.0, 0.0), "bottom"),
]

# 指针 / 拖拽偏移量（[-1, 1] 无量纲系数）映射到的弧度量程。
# _YAW_RAD / _PITCH_RAD 仅用于取证脚本强制全身刚体角度；日常跟随分两层：整体刚体
# 小幅同步偏转（_BODY_YAW_RAD / _BODY_PITCH_RAD），头部关节以更大幅度领先跟随
# （_HEAD_YAW_RAD / _HEAD_PITCH_RAD）。
_YAW_RAD = 0.92
_PITCH_RAD = 0.42

# 默认正面展示角：静止时角色正对镜头，指针跟随只在零偏移之上叠加转向
_BASE_YAW_RAD = 0.0
_BASE_PITCH_RAD = 0.0

# 模型 y 范围 [0, 32]，刚体旋转中心与投影纵向基准取模型包围盒中点
_MODEL_CY = 16.0

# 相机：v1.1.3.4 从 v1.1.3.3 的 102 回调到 88，角色比上一版稍微放大一点，
# 四周仍保留均匀边距；FOV、标准模型几何保持不变。
_CAM_FOV = 38.0
_CAM_DIST = 88.0

# 头部领先跟随鼠标的量程（弧度）：绕颈枢轴左右转头 + 抬头 / 低头。脖子转动幅度
# 大于身体，左右约 ±31°、俯仰约 ±20°，斜向组合时头部自然扭向指针。
_HEAD_YAW_RAD = 0.55
_HEAD_PITCH_RAD = 0.35

# 日常状态整体刚体（躯干 / 双臂 / 双腿）小幅同步跟随指针的量程（弧度）：约为头部
# 幅度的三分之一，身体轻轻朝指针方向偏转，头部领先跟随；左右约 ±10°、俯仰约 ±6°，
# 斜向为 yaw / pitch 两轴自然叠加。整体绕模型中点旋转，标准相切部件相对位置不变，
# 不会互相穿插；小角度包围盒漂移在视锥留白之内，无需俯仰居中补偿。
_BODY_YAW_RAD = 0.18
_BODY_PITCH_RAD = 0.10

# 预览清屏：v1.2.4.3 起背景彻底透明。GL 帧缓冲开启 alpha 通道、控件标记透明背景，并加
# WA_AlwaysStackOnTop 把 GL 表面压到合成顺序最上层（QOpenGLWidget 默认先于普通控件绘制、
# 下方透不过来；仅开 alpha 缓冲在 Windows / DWM 屏幕合成下会把透明区显示成黑矩形，必须靠
# 该属性解决）；initializeGL 打开混合并以 (0,0,0,0) 清屏。角色片元按纹理 alpha 输出（不
# 透明皮肤片 alpha=1），轮廓之外 alpha=0，不写任何底色，合成时透出卡片局部磨砂与壁纸。
# 注意：透明是否成立要以真实窗口屏幕截图为准，widget 离屏 grab() 在未开 AlwaysStackOnTop 时
# 也可能显示正常，不能作为验收依据。

TEX_W, TEX_H = 64, 64

# 顶点布局：pos(3) + normal(3) + uv(2) + partShade(1) = 9 浮点，stride 36 字节
_STRIDE = 9 * 4

# GL 标准常量
GL_DEPTH_TEST = 0x0B71
GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_TRIANGLES = 0x0004
GL_FLOAT = 0x1406

# ---------------------------------------------------------------------------
# 待机手臂幅度（弧度 / 模型单位）。躯干 / 双腿静止；头部跟随指针的角度在 paintGL
# 中按 _HEAD_YAW_RAD / _HEAD_PITCH_RAD 计算，不属于待机动画。
# v1.1.3.3：左右外展只朝离开躯干的方向（内收回到竖直、不越过竖直贴面位置），
# 另叠加极小的前后轻摆；摆动全程手臂内侧不会扫进躯干侧面，根除动态穿模。
# ---------------------------------------------------------------------------
# 双臂左右外展（绕 z 轴，只向外张）：周期慢、幅度小
_ARM_SPREAD_PERIOD = 4.5
_ARM_SPREAD_RZ = 0.04
# 双臂前后轻摆（绕 x 轴，下端前后移动，x 方向位置不变，不会切入躯干）
_ARM_SWING_RX = 0.05

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
    // MC 式固定面朝向亮度档：顶面最亮、正面接近原色、侧面压暗、背面 / 底面最暗。
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
    u0, u1 = x / TEX_W, (x + w) / TEX_W
    v_top = 1.0 - y / TEX_H
    v_bottom = 1.0 - (y + h) / TEX_H
    return [(u0, v_top), (u1, v_top), (u1, v_bottom), (u0, v_bottom)]


def _build_all_mesh(slim: bool = False):
    """拼接六个部件全部三角形顶点，返回 (扁平顶点列表, 每部件 (start, count))。

    ``slim=True`` 时按细臂（Alex / 正版细臂模型）把双臂宽度从 4 改为 3、位置内收，
    其余部件几何保持不变；``slim=False`` 为标准经典模型（4×12×4 双臂）。
    """
    all_data = []
    ranges = []
    cursor = 0
    triangle = [0, 1, 2, 0, 2, 3]
    for part in _PARTS:
        part_geom = dict(part)
        # 细臂模型：双臂宽 3、左右内收半格，肩关节枢轴位置不变，手臂切片改用 3px 细臂布局
        if slim and part["name"] in ("rarm", "larm"):
            part_geom["w"] = 3.0
            part_geom["cuts"] = SLIM_ARM_CUT
            if part["name"] == "rarm":
                part_geom["wx"] = -7.5
            else:
                part_geom["wx"] = 4.5
        verts = _cube_vertices(part_geom["wx"], part_geom["wy"],
                                part_geom["w"], part_geom["h"], part_geom["depth"])
        part_count = 0
        for face_name, idx, normal, cut_key in _FACES:
            uv = _uv_corners(part_geom["cuts"][cut_key])
            part_shade = part_geom["layer_light"] * _CONTACT_AO.get((part_geom["name"], face_name), 1.0)
            for i in triangle:
                vi = idx[i]
                px, py, pz = verts[vi]
                u, v = uv[i]
                all_data.extend([px, py, pz, normal[0], normal[1], normal[2],
                                 u, v, part_shade])
                part_count += 1
        ranges.append((part_geom, cursor, part_count))
        cursor += part_count
    return all_data, ranges


class SkinPreview(QOpenGLWidget):
    """跟随指针转动的方块角色 GPU 三维预览。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        # 颜色缓冲保留 8 位 alpha：清屏 alpha=0 的透明区才能在合成到父控件时透出磨砂卡片，
        # 而不是被不透明底色矩形盖住。
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        # 控件背景透明：轮廓之外不绘制任何底色，父卡片磨砂由 Qt 先绘制、GL 帧缓冲按 alpha
        # 叠加；关闭自动填充背景，避免 Qt 再铺一层系统底色。
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Qt 官方说明：QOpenGLWidget 默认先于所有普通非 GL 控件绘制，下方 widget 透不过来，
        # alpha 缓冲本身不足以让半透明区透出父控件；需要 WA_AlwaysStackOnTop 把 GL 表面压到
        # 合成顺序最上层，轮廓之外的 alpha=0 区域才能透出下方卡片磨砂。本控件矩形之上没有任何
        # 叠放控件（卡片标题在 body 之外），打破堆叠顺序的副作用在此场景不构成问题。
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAutoFillBackground(False)
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._skin_id = C.DEFAULT_SKIN
        # 外部（正版）皮肤：QImage 纹理与细臂标志；为空时回退内置史蒂夫 / 艾利克斯贴图
        self._external_image: QImage | None = None
        self._external_slim = False
        self._slim = False

        self._prog = None
        self._texture = None
        self._vbo = None
        self._vao = None
        self._part_ranges = []
        self._loc = {}

        # 角度偏移：当前偏移与目标偏移（yaw 左右，pitch 俯仰，均为 [-1, 1]）。
        self._yaw = 0.0
        self._pitch = 0.0
        self._yaw_target = 0.0
        self._pitch_target = 0.0
        # 测试取证脚本关闭此开关时，渲染角只取偏移，复现标准角度矩阵。
        self._base_view_enabled = True
        self._dragging = False
        self._last_pos = QPointF(0, 0)

        # 待机动画相位（秒），由 16ms 定时器累计。
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ---------- 皮肤切换 ----------
    def set_skin(self, skin_id: str) -> None:
        """离线内置皮肤：清空外部正版纹理，按内置史蒂夫 / 艾利克斯加载。"""
        if skin_id not in C.SKIN_CHOICES:
            skin_id = C.DEFAULT_SKIN
        had_external = self._external_image is not None
        self._external_image = None
        self._external_slim = False
        # 内置两条贴图沿用既有经典网格，不切换细臂，保持已达标回归观感不变
        self._slim = False
        # 仅在原本就是离线内置且皮肤未变时跳过重建；从外部皮肤切回必须强制重建纹理 / 网格
        if not had_external and skin_id == self._skin_id and self._texture is not None:
            return
        self._skin_id = skin_id
        self._refresh_assets()

    def set_external_skin(self, image: QImage, slim: bool) -> None:
        """加载正版外部皮肤纹理；``slim=True`` 切换细臂模型，失败由调用方回退内置皮肤。"""
        if image is None or image.isNull():
            return
        self._external_image = self._normalize_skin(image)
        self._external_slim = slim
        self._slim = slim
        self._refresh_assets()

    def _refresh_assets(self) -> None:
        """上下文已初始化时重建纹理与（必要时）网格；未初始化则由 initializeGL 构建。"""
        if self._texture is not None:
            self._rebuild_texture()
        if self._vbo is not None:
            self._rebuild_mesh()
        self.update()

    @staticmethod
    def _normalize_skin(image: QImage) -> QImage:
        """旧版 64×32 皮肤补齐到 64×64 透明画布，避免第二层 UV 越界；新版 64×64 原样返回。"""
        if image.height() >= TEX_H:
            return image
        canvas = QImage(TEX_W, TEX_H, QImage.Format_RGBA8888)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawImage(0, 0, image)
        painter.end()
        return canvas

    def _current_image(self) -> QImage:
        if self._external_image is not None:
            return self._external_image
        info = C.SKIN_CHOICES[self._skin_id]
        path = resource_path(os.path.join("skins", info["file"]))
        image = QImage(path)
        if image.isNull():
            image = QImage(TEX_W, TEX_H, QImage.Format_RGBA8888)
            image.fill("#9fc9e0")
        return image

    def _rebuild_texture(self) -> None:
        if self._texture is not None:
            self._texture.destroy()
            self._texture = None
        image = self._current_image().mirrored(False, True)  # 垂直翻转匹配 UV
        self._texture = QOpenGLTexture(QOpenGLTexture.Target2D)
        self._texture.setData(image)
        self._texture.setMinificationFilter(QOpenGLTexture.Nearest)
        self._texture.setMagnificationFilter(QOpenGLTexture.Nearest)
        self._texture.setWrapMode(QOpenGLTexture.ClampToEdge)
        self._texture.setMipLevels(1)

    def _rebuild_mesh(self) -> None:
        """按当前经典 / 细臂标志重建顶点缓冲；网格几何随模型类型切换。"""
        all_data, self._part_ranges = _build_all_mesh(self._slim)
        binder = QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo.bind()
        self._vbo.allocate(struct.pack(f"{len(all_data)}f", *all_data), len(all_data) * 4)

    # ---------- GL 初始化 ----------
    def initializeGL(self) -> None:
        gl = self.context().functions()
        gl.glEnable(GL_DEPTH_TEST)
        # 打开源 alpha 混合：不透明角色片 alpha=1 正常覆盖，透明背景与贴图半透明像素按
        # alpha 混合；清屏 RGBA 全 0，轮廓之外保持透明，交由父卡片磨砂透出。
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
        self._vao = QOpenGLVertexArrayObject()
        self._vao.create()
        binder = QOpenGLVertexArrayObject.Binder(self._vao)
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

    def resizeGL(self, w, h) -> None:
        self.context().functions().glViewport(0, 0, w, h)

    # ---------- 动画 ----------
    def _tick(self) -> None:
        # 指数平滑朝目标角收敛：系数提高后跟随更跟手，同时保留柔和过渡，避免生硬跳变。
        self._yaw += (self._yaw_target - self._yaw) * 0.20
        self._pitch += (self._pitch_target - self._pitch) * 0.20
        if abs(self._yaw - self._yaw_target) < 0.001:
            self._yaw = self._yaw_target
        if abs(self._pitch - self._pitch_target) < 0.001:
            self._pitch = self._pitch_target
        self._phase += 0.016
        self.update()

    # ---------- 全局指针跟随（由主窗口转发整窗归一化坐标） ----------
    def on_global_pointer(self, nx: float, ny: float) -> None:
        """接收归一化指针坐标（nx/ny ∈ [-1, 1]，x 向右为正，y 向上为正）。"""
        if self._dragging:
            return
        self._yaw_target = max(-1.0, min(1.0, nx))
        self._pitch_target = max(-1.0, min(1.0, ny))

    def reset_target(self) -> None:
        """指针离开窗口时回正到默认基础斜侧角。"""
        if not self._dragging:
            self._yaw_target = 0.0
            self._pitch_target = 0.0

    # ---------- 鼠标拖拽自由旋转 ----------
    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            dx = event.position().x() - self._last_pos.x()
            dy = event.position().y() - self._last_pos.y()
            self._yaw_target = max(-1.0, min(1.0, self._yaw_target + dx * 0.014))
            self._pitch_target = max(-1.0, min(1.0, self._pitch_target - dy * 0.010))
            self._last_pos = event.position()
        # 非拖拽时的指针跟随统一由主窗口整窗轮询转发，这里不再用组件局部坐标另算，
        # 避免两套坐标基准不一致造成的轻微抖动。
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_pos = event.position()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        super().mouseReleaseEvent(event)

    # ---------- 关节级待机动画 ----------
    def _joint_angles(self, head_rx: float = 0.0, head_ry: float = 0.0) -> dict[str, dict[str, float]]:
        # 关节层躯干 / 双腿中立：身体的小幅指针跟随由 paintGL 刚体矩阵统一承担，
        # 这里只负责待机双臂轻摆。头部角度由 paintGL 按当前状态传入：日常跟随鼠标
        # 以更大幅度转头 / 抬头低头，取证强制全身角度时头部保持中立、由刚体承担转向。
        wave = math.sin(2.0 * math.pi * self._phase / _ARM_SPREAD_PERIOD)
        spread = abs(wave)  # 左右外展只朝离开躯干方向，回到竖直即止，不向内收进躯干
        swing = wave        # 前后轻摆，下端沿前后移动，x 方向位置不变，不会切入躯干
        return {
            "body": {"rx": 0.0, "ry": 0.0, "rz": 0.0, "lift": 0.0},
            "head": {"rx": head_rx, "ry": head_ry, "rz": 0.0, "lift": 0.0},
            "rarm": {"rx": swing * _ARM_SWING_RX, "ry": 0.0,
                     "rz": -spread * _ARM_SPREAD_RZ, "lift": 0.0},
            "larm": {"rx": swing * _ARM_SWING_RX, "ry": 0.0,
                     "rz": spread * _ARM_SPREAD_RZ, "lift": 0.0},
            "rleg": {"rx": 0.0, "ry": 0.0, "rz": 0.0, "lift": 0.0},
            "lleg": {"rx": 0.0, "ry": 0.0, "rz": 0.0, "lift": 0.0},
        }

    @staticmethod
    def _joint_matrix(pivot, rx: float, ry: float, rz: float, lift: float) -> QMatrix4x4:
        """绕枢轴先 X、再 Y、再 Z 做局部旋转，再加呼吸上下位移。"""
        j = QMatrix4x4()
        j.translate(pivot[0], pivot[1], pivot[2])
        if rz:
            j.rotate(math.degrees(rz), QVector3D(0, 0, 1))
        if ry:
            j.rotate(math.degrees(ry), QVector3D(0, 1, 0))
        if rx:
            j.rotate(math.degrees(rx), QVector3D(1, 0, 0))
        j.translate(-pivot[0], -pivot[1], -pivot[2])
        if lift:
            j.translate(0.0, lift, 0.0)
        return j

    # ---------- GL 绘制 ----------
    def paintGL(self) -> None:
        gl = self.context().functions()
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self._prog is None or self._texture is None:
            return

        aspect = self.width() / max(1, self.height())
        proj = QMatrix4x4()
        proj.perspective(_CAM_FOV, aspect, 0.1, 200.0)
        view = QMatrix4x4()
        view.translate(0.0, -_MODEL_CY, -_CAM_DIST)
        view_proj = proj * view

        if self._base_view_enabled:
            # 日常指针跟随：整体刚体（躯干 / 双臂 / 双腿）朝指针方向做小幅同步偏转，
            # 头部绕颈枢轴以更大幅度领先跟随。ny 向上为正，绕 X 轴负角度为后仰
            # （抬头），因此刚体与头部俯仰角统一取负，鼠标上移抬头、下移低头。
            rigid_yaw = self._yaw * _BODY_YAW_RAD
            rigid_pitch = -self._pitch * _BODY_PITCH_RAD
            head_ry = self._yaw * _HEAD_YAW_RAD
            head_rx = -self._pitch * _HEAD_PITCH_RAD
        else:
            # 取证脚本强制角度：由整体刚体承担全身 yaw / pitch，用于检查躯干六面
            # 渲染；头部保持中立。俯仰同样取负，使 pitch=+1 抬头、-1 低头。
            rigid_yaw = self._yaw * _YAW_RAD
            rigid_pitch = -self._pitch * _PITCH_RAD
            head_ry = 0.0
            head_rx = 0.0

        # 整体刚体旋转（绕模型中点 y=16）；日常状态为小幅身体跟随，取证状态承担全身转向。
        rigid = QMatrix4x4()
        rigid.translate(0.0, -_MODEL_CY, 0.0)
        rigid.rotate(math.degrees(rigid_pitch), QVector3D(1, 0, 0))
        rigid.rotate(math.degrees(rigid_yaw), QVector3D(0, 1, 0))
        rigid.translate(0.0, _MODEL_CY, 0.0)

        angles = self._joint_angles(head_rx=head_rx, head_ry=head_ry)

        self._prog.bind()
        self._prog.setUniformValue(self._loc["viewproj"], view_proj)
        self._prog.setUniformValue(self._loc["tex"], 0)
        self._texture.bind(0)

        binder = QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo.bind()
        for part, start, count in self._part_ranges:
            ja = angles[part["joint"]]
            joint = self._joint_matrix(part["pivot"], ja["rx"], ja["ry"], ja["rz"], ja["lift"])
            model = rigid * joint
            self._prog.setUniformValue(self._loc["model"], model)
            gl.glDrawArrays(GL_TRIANGLES, start, count)
        self._prog.release()

