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

"""Minecraft 角色纯软件三维预览组件（QPainter 软件渲染，无 OpenGL 依赖）。

本组件按 Minecraft 原版标准玩家模型几何把角色建成真实立方体：

- 头 8×8×8、躯干 8×12×4、双臂各 4×12×4、双腿各 4×12×4，尺寸与位置
  与游戏内玩家模型一致；仅在被遮挡的接触面内部保留极小的防穿透重叠，
  外形轮廓（宽、高、厚、肩 / 髋分界）严格保持原版标准，不再手动加宽、
  不再给躯干额外前后盖板；
- 先在模型空间做关节级待机动画：躯干 / 头部随呼吸缓慢上下起伏，双臂绕
  肩关节做前后摆动与小幅外展（两个方向叠加出上下、左右与斜向摆臂），
  头部绕颈轻微左右 / 上下微动，双腿绕髋关节近乎直立、只做极小幅反相摆动；
  关节枢轴分别设在肩、颈、髋连接处，不绕肢体几何中心旋转；
- 关节变换之后再对整个人物做刚体 yaw / pitch 三维旋转，背面剔除不可见面；
- 按面法线与方向光源点乘计算明暗，并按面朝向叠加 MC 式档位（顶面最亮、侧面
  压暗、背面 / 底面最暗）；躯干 / 头部在前最亮、四肢退后略暗，贴合内侧窄面叠加
  接触暗部；画家算法（按深度从远到近）排序绘制；透视投影形成近大远小，每个可见面
  用仿射变换把皮肤切片映射到投影后的平行四边形；贴图采样使用最近邻（关闭平滑插值），
  保持 MC 方块像素硬边锐利，不做双线性柔化；
- 默认以 3/4 斜侧立像展示，指针跟随与拖拽只是在基础角之上叠加偏移；指针在整窗
  任意位置移动时叠加转向，按住左键可拖动自由旋转，指针移出窗口自动回到默认斜侧；
  待机动画与指针 / 拖拽转向互不干扰。

对外接口与旧版保持一致：``set_skin`` / ``on_global_pointer`` / ``reset_target``，
以及拖拽鼠标事件；主窗口全局轮询跟随链路无需改动。
"""
import math
import os

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QPolygonF, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import constants as C
from ..resources import resource_path


# ---------------------------------------------------------------------------
# 皮肤切片源矩形（单位皮肤像素，64×64 标准布局）。
# 每个部件给出 front / back / side_left / side_right / top / bottom 六面。
# 坐标与旧版 2.5D 已验证可正常显示的 front/back/side 保持一致，仅补 top/bottom。
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
LEG_CUT = {
    "front": (4, 20, 4, 12),
    "back": (12, 20, 4, 12),
    "side_left": (8, 20, 4, 12),
    "side_right": (0, 20, 4, 12),
    "top": (4, 16, 4, 4),
    "bottom": (8, 16, 4, 4),
}

# 部件世界参数与关节配置。
# 坐标系：x 向右、y 向上、z 朝观察者（前 +z）；脚底 y=0，总高 32；z 前后居中。
# 几何严格遵循 Minecraft 原版标准玩家模型：
#   头   x[-4,4]  y[24,32] z[-4,4]  8×8×8
#   躯干 x[-4,4]  y[12,24] z[-2,2]  8×12×4
#   右臂 x[-8,-4] y[12,24] z[-2,2]  4×12×4（屏幕左侧）
#   左臂 x[4,8]   y[12,24] z[-2,2]  4×12×4（屏幕右侧）
#   右腿 x[-4,0]  y[0,12]  z[-2,2]  4×12×4（屏幕左侧）
#   左腿 x[0,4]   y[0,12]  z[-2,2]  4×12×4（屏幕右侧）
# 为避免软件投影在数学相切边界漏出 1px 背景缝，只在被对方遮挡的接触面
# 内部保留 0.4 模型单位的防穿透重叠（头底下沉、手臂内沿伸入、腿顶伸入、
# 腿内侧互叠）；朝外的轮廓边严格保持原版坐标，肩、髋分界清晰。
# 绘制层级 layer：四肢先画(0)，躯干覆盖四肢伸入段(1)，头部最后(2)，
# 同一深度时避免四肢面压到躯干正面上。
# layer_light：前后分层亮度系数——躯干 / 头部在前最亮，双臂 / 双腿退后略暗，
# 避免四肢与躯干正面同亮而显得并排平铺；接触 AO 表压暗互相贴合的内侧窄面。
# joint：关节标识；pivot：局部旋转枢轴（肩 / 颈 / 髋连接处，不是肢体中心）。
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
        "name": "rarm", "wx": -8.0, "wy": 12.0, "w": 4.4, "h": 12.0, "depth": 4,
        "layer": 0, "cuts": ARM_CUT, "joint": "rarm", "pivot": (-6.0, 24.0, 0.0),
        "layer_light": 0.92,
    },
    {
        "name": "larm", "wx": 3.6, "wy": 12.0, "w": 4.4, "h": 12.0, "depth": 4,
        "layer": 0, "cuts": ARM_CUT, "joint": "larm", "pivot": (6.0, 24.0, 0.0),
        "layer_light": 0.92,
    },
    {
        "name": "rleg", "wx": -4.0, "wy": 0.0, "w": 4.4, "h": 12.4, "depth": 4,
        "layer": 0, "cuts": LEG_CUT, "joint": "rleg", "pivot": (-2.0, 12.0, 0.0),
        "layer_light": 0.88,
    },
    {
        "name": "lleg", "wx": -0.4, "wy": 0.0, "w": 4.4, "h": 12.4, "depth": 4,
        "layer": 0, "cuts": LEG_CUT, "joint": "lleg", "pivot": (2.0, 12.0, 0.0),
        "layer_light": 0.88,
    },
]

# 互相贴合的内侧窄面接触暗部（部件名, 局部面名）：转到侧方或肢体摆动露出时，
# 贴近躯干 / 另一条腿的一面再压暗一档，模拟关节夹缝与两腿之间的闭塞阴影。
_CONTACT_AO = {
    ("rarm", "right"): 0.72,
    ("larm", "left"): 0.72,
    ("rleg", "right"): 0.70,
    ("lleg", "left"): 0.70,
    ("body", "top"): 0.85,
}

# 立方体 8 个局部顶点编号（见文件头坐标系）。
# 0:(x0,y0,z0) 1:(x1,y0,z0) 2:(x1,y1,z0) 3:(x0,y1,z0)
# 4:(x0,y0,z1) 5:(x1,y0,z1) 6:(x1,y1,z1) 7:(x0,y1,z1)
#
# 六面：(面名, 顶点序 [P00, P10, P11, P01], 模型法线, 切片键)
# 顶点顺序保证：P00→P10 为贴图 u 方向，P00→P01 为贴图 v（向下）方向。
_FACES = [
    ("front", [7, 6, 5, 4], (0.0, 0.0, 1.0), "front"),
    ("back", [2, 3, 0, 1], (0.0, 0.0, -1.0), "back"),
    ("right", [2, 6, 5, 1], (1.0, 0.0, 0.0), "side_right"),
    ("left", [7, 3, 0, 4], (-1.0, 0.0, 0.0), "side_left"),
    ("top", [7, 6, 2, 3], (0.0, 1.0, 0.0), "top"),
    ("bottom", [0, 1, 5, 4], (0.0, -1.0, 0.0), "bottom"),
]

# 指针 / 拖拽偏移量（[-1, 1] 无量纲系数）映射到的弧度量程
_YAW_RAD = 0.92
_PITCH_RAD = 0.60

# 默认 3/4 斜侧展示角（弧度）：角色一开始就同时露出正面、一个侧面与少量头顶，
# 避免纯正面时各部件退成并排平面矩形、看起来像一张裁块贴图。指针跟随与拖拽
# 只是在这个基础角之上叠加偏移；指针离开窗口回到基础斜侧，而不是纯正面。
_BASE_YAW_RAD = 0.38
_BASE_PITCH_RAD = -0.10

# 方向光源（前上方偏右，归一化后使用）
_LIGHT = (0.35, 0.78, 0.55)
_LIGHT_LEN = math.sqrt(sum(v * v for v in _LIGHT))
_LIGHT = tuple(v / _LIGHT_LEN for v in _LIGHT)

# 环境光与漫反射强度；配合按面朝向的明暗档位拉开体块层次
_AMBIENT = 0.32
_DIFFUSE = 0.70

# 透视相机距离（模型 z 范围约 [-4, 4]）：距离越小近大远小越明显，立方体前后
# 边线不再平行，体积感更强；距离过大就退化成正交投影，看着像平面贴片。
_CAM_DIST = 34.0

# 模型 y 范围 [0, 32]，刚体旋转中心与投影纵向基准都取模型中点
_MODEL_CY = 16.0
_ROT_CENTER = (0.0, _MODEL_CY, 0.0)

# ---------------------------------------------------------------------------
# 待机动画幅度（弧度 / 模型单位，贴近游戏内背包预览的轻微动态感，不做大幅度
# 挥舞、跳跃或走路动作）。绕 X 前后摆主要在侧视可见；绕 Z 外展在正面平面
# 左右张开并带动手臂下端抬落，两轴叠加即形成上下、左右与斜向摆动弧线。
# ---------------------------------------------------------------------------
_BREATH_PERIOD = 2.1          # 呼吸起伏周期（秒）
_BREATH_LIFT = 0.20           # 躯干 / 头随呼吸上下浮动（模型单位）
_BREATH_TILT = 0.022          # 躯干随呼吸极轻微前后俯仰
_ARM_SWING_PERIOD = 1.55      # 手臂前后摆动周期（秒）
_ARM_SWING_RX = 0.16          # 手臂前后摆幅（绕肩关节 X 轴，侧视可见，约 9°）
_ARM_SPREAD_PERIOD = 3.2      # 手臂左右外展周期（秒，比前后摆慢，叠出斜向）
_ARM_SPREAD_RZ = 0.16         # 手臂正面外展 / 抬落幅度（绕肩关节 Z 轴，约 9°）
_HEAD_YAW_AMP = 0.09          # 头部左右微动幅度
_HEAD_PITCH_AMP = 0.06        # 头部上下微动幅度
_LEG_SWING_RX = 0.035         # 腿部闲置反相小幅摆动（近乎直立）


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class SkinPreview(QWidget):
    """跟随指针转动的方块角色纯软件三维预览。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(160, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._skin_id = C.DEFAULT_SKIN
        self._skin_image: QImage | None = None
        self._cuts: dict[str, QPixmap] = {}

        # 角度偏移：当前偏移与目标偏移（yaw 左右，pitch 俯仰，均为 [-1, 1]
        # 无量纲系数）；最终渲染角 = 默认 3/4 基础展示角 + 指针 / 拖拽偏移。
        self._yaw = 0.0
        self._pitch = 0.0
        self._yaw_target = 0.0
        self._pitch_target = 0.0
        # 测试取证脚本关闭此开关时，渲染角只取偏移，便于复现纯正面 / 正侧矩阵。
        self._base_view_enabled = True
        self._dragging = False
        self._last_pos = QPointF(0, 0)

        # 待机动画相位（秒），由 16ms 定时器累计，驱动呼吸 / 摆臂 / 头部微动
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._load_skin_image()

    # ---------- 皮肤切换 ----------
    def set_skin(self, skin_id: str) -> None:
        if skin_id not in C.SKIN_CHOICES:
            skin_id = C.DEFAULT_SKIN
        if skin_id == self._skin_id:
            return
        self._skin_id = skin_id
        self._cuts.clear()
        self._load_skin_image()
        self.update()

    def _load_skin_image(self) -> None:
        info = C.SKIN_CHOICES[self._skin_id]
        path = resource_path(os.path.join("skins", info["file"]))
        image = QImage(path)
        if image.isNull():
            image = QImage(64, 64, QImage.Format_RGBA8888)
            image.fill(QColor("#9fc9e0"))
        self._skin_image = image

    def _slice(self, cuts: dict[str, tuple[int, int, int, int]], face: str) -> QPixmap:
        key = f"{self._skin_id}:{face}:{cuts[face]}"
        if key not in self._cuts:
            x, y, w, h = cuts[face]
            rect = self._skin_image.copy(x, y, w, h)
            self._cuts[key] = QPixmap.fromImage(rect)
        return self._cuts[key]

    # ---------- 动画 ----------
    def _tick(self) -> None:
        self._yaw += (self._yaw_target - self._yaw) * 0.12
        self._pitch += (self._pitch_target - self._pitch) * 0.12
        if abs(self._yaw - self._yaw_target) < 0.001:
            self._yaw = self._yaw_target
        if abs(self._pitch - self._pitch_target) < 0.001:
            self._pitch = self._pitch_target
        # 16ms 一拍，累计待机相位；摆臂 / 呼吸与指针转向解耦，互不抢占
        self._phase += 0.016
        self.update()

    # ---------- 全局指针跟随（由主窗口转发整窗归一化坐标） ----------
    def on_global_pointer(self, nx: float, ny: float) -> None:
        """接收归一化指针坐标（nx/ny ∈ [-1, 1]，x 向右为正，y 向上为正）。

        指针在右（nx>0）角色朝屏幕右侧；指针在上（ny>0）抬头看上方。
        """
        if self._dragging:
            return
        self._yaw_target = max(-1.0, min(1.0, nx))
        self._pitch_target = max(-1.0, min(1.0, ny))

    def reset_target(self) -> None:
        """指针离开窗口时回正到正面。"""
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
        else:
            nx = event.position().x() / max(1, self.width()) * 2.0 - 1.0
            ny = (1.0 - event.position().y() / max(1, self.height())) * 2.0 - 1.0
            self.on_global_pointer(nx, ny)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_pos = event.position()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        super().mouseReleaseEvent(event)

    # ---------- 三维变换 ----------
    def _rotated(self, point: tuple[float, float, float],
                 yaw: float, pitch: float) -> tuple[float, float, float]:
        """把世界顶点绕旋转中心先绕 Y 轴 yaw、再绕 X 轴 pitch 旋转。"""
        q = _sub(point, _ROT_CENTER)
        cx, sx = math.cos(yaw), math.sin(yaw)
        # 绕 Y 轴
        qx = q[0] * cx + q[2] * sx
        qz = -q[0] * sx + q[2] * cx
        qy = q[1]
        # 绕 X 轴
        cp, sp = math.cos(pitch), math.sin(pitch)
        qy2 = qy * cp - qz * sp
        qz2 = qy * sp + qz * cp
        return (qx + _ROT_CENTER[0], qy2 + _ROT_CENTER[1], qz2 + _ROT_CENTER[2])

    def _rotated_normal(self, n: tuple[float, float, float],
                        yaw: float, pitch: float) -> tuple[float, float, float]:
        """法线只做纯旋转（不平移）。"""
        cx, sx = math.cos(yaw), math.sin(yaw)
        nx = n[0] * cx + n[2] * sx
        nz = -n[0] * sx + n[2] * cx
        ny = n[1]
        cp, sp = math.cos(pitch), math.sin(pitch)
        ny2 = ny * cp - nz * sp
        nz2 = ny * sp + nz * cp
        return (nx, ny2, nz2)

    @staticmethod
    def _face_shade(n: tuple[float, float, float]) -> float:
        """环境光 + 方向光漫反射，再按旋转后法线的主朝向叠加 MC 式明暗档位。

        顶面最亮、正面标准、左右侧面压暗、背面 / 底面最暗；拉开体块之间的明暗
        层次，避免各面亮度接近而显平。
        """
        diffuse = max(0.0, _dot(n, _LIGHT))
        shade = _AMBIENT + _DIFFUSE * diffuse
        if n[1] > 0.5:            # 顶面
            factor = 1.07
        elif n[1] < -0.5:         # 底面
            factor = 0.58
        elif n[2] > 0.5:          # 正面
            factor = 1.00
        elif n[2] < -0.5:         # 背面
            factor = 0.62
        else:                     # 左右侧面
            factor = 0.80
        shade *= factor
        return max(0.28, min(1.05, shade))

    # ---------- 关节级待机动画 ----------
    def _joint_angles(self) -> dict[str, dict[str, float]]:
        """按当前相位计算每个关节的局部旋转角与呼吸位移。

        返回 ``rx/ry/rz`` 为绕枢轴的欧拉角（弧度，顺序 X→Y→Z），``lift`` 为
        叠加在关节上的 y 方向呼吸平移（模型单位）。手臂前后摆与左右外展使用
        不同周期叠加，自然形成上下、左右以及斜向的小幅摆动；双腿近乎直立。
        """
        t = self._phase
        breath = math.sin(2.0 * math.pi * t / _BREATH_PERIOD)
        swing = math.sin(2.0 * math.pi * t / _ARM_SWING_PERIOD)
        spread = math.sin(2.0 * math.pi * t / _ARM_SPREAD_PERIOD + 0.7)
        head_yaw = math.sin(2.0 * math.pi * t / 2.6) * _HEAD_YAW_AMP
        head_pitch = math.sin(2.0 * math.pi * t / 1.9 + 1.0) * _HEAD_PITCH_AMP
        leg = math.sin(2.0 * math.pi * t / _ARM_SWING_PERIOD + math.pi) * _LEG_SWING_RX
        lift = breath * _BREATH_LIFT
        return {
            "body": {"rx": breath * _BREATH_TILT, "ry": 0.0, "rz": 0.0, "lift": lift},
            "head": {"rx": head_pitch, "ry": head_yaw, "rz": 0.0, "lift": lift},
            "rarm": {"rx": swing * _ARM_SWING_RX, "ry": 0.0,
                     "rz": -spread * _ARM_SPREAD_RZ, "lift": 0.0},
            "larm": {"rx": -swing * _ARM_SWING_RX, "ry": 0.0,
                     "rz": spread * _ARM_SPREAD_RZ, "lift": 0.0},
            "rleg": {"rx": leg, "ry": 0.0, "rz": 0.0, "lift": 0.0},
            "lleg": {"rx": -leg, "ry": 0.0, "rz": 0.0, "lift": 0.0},
        }

    @staticmethod
    def _rotate_about(p: tuple[float, float, float],
                      pivot: tuple[float, float, float],
                      rx: float, ry: float, rz: float) -> tuple[float, float, float]:
        """绕枢轴先 X、再 Y、再 Z 做局部旋转（肢体关节动画）。"""
        qx, qy, qz = p[0] - pivot[0], p[1] - pivot[1], p[2] - pivot[2]
        if rx:
            c, s = math.cos(rx), math.sin(rx)
            qy, qz = qy * c - qz * s, qy * s + qz * c
        if ry:
            c, s = math.cos(ry), math.sin(ry)
            qx, qz = qx * c + qz * s, -qx * s + qz * c
        if rz:
            c, s = math.cos(rz), math.sin(rz)
            qx, qy = qx * c - qy * s, qx * s + qy * c
        return (qx + pivot[0], qy + pivot[1], qz + pivot[2])

    @staticmethod
    def _rotate_normal_local(n: tuple[float, float, float],
                            rx: float, ry: float, rz: float) -> tuple[float, float, float]:
        """法线做与顶点相同的局部旋转（绕原点，不平移）。"""
        qx, qy, qz = n
        if rx:
            c, s = math.cos(rx), math.sin(rx)
            qy, qz = qy * c - qz * s, qy * s + qz * c
        if ry:
            c, s = math.cos(ry), math.sin(ry)
            qx, qz = qx * c + qz * s, -qx * s + qz * c
        if rz:
            c, s = math.cos(rz), math.sin(rz)
            qx, qy = qx * c - qy * s, qx * s + qy * c
        return (qx, qy, qz)

    # ---------- 绘制 ----------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # 关闭平滑像素变换：仿射放大皮肤切片时走最近邻采样，保留 MC 方块
        # 像素的锐利硬边；开启平滑会把 4×12 / 8×8 小切片双线性柔化而发糊。
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._draw_character(painter)
        painter.end()

    def _cube_vertices(self, wx: float, wy: float, w: float,
                      h: float, d: float) -> list[tuple[float, float, float]]:
        x0, x1 = wx, wx + w
        y0, y1 = wy, wy + h
        z0, z1 = -d / 2.0, d / 2.0
        return [
            (x0, y0, z0),  # 0
            (x1, y0, z0),  # 1
            (x1, y1, z0),  # 2
            (x0, y1, z0),  # 3
            (x0, y0, z1),  # 4
            (x1, y0, z1),  # 5
            (x1, y1, z1),  # 6
            (x0, y1, z1),  # 7
        ]

    def _draw_character(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        # 单位像素：角色世界宽 16、高 32，四周留余量
        unit = min(w / 18.0, h / 34.0)
        center_x = w / 2.0
        center_y = h / 2.0

        base_yaw = _BASE_YAW_RAD if self._base_view_enabled else 0.0
        base_pitch = _BASE_PITCH_RAD if self._base_view_enabled else 0.0
        yaw = base_yaw + self._yaw * _YAW_RAD
        pitch = base_pitch + self._pitch * _PITCH_RAD

        self._draw_ground_shadow(painter, center_x, center_y, unit)

        angles = self._joint_angles()
        faces: list[dict] = []
        for part in _PARTS:
            wx, wy = part["wx"], part["wy"]
            pw, ph, depth = part["w"], part["h"], part["depth"]
            layer, cuts, joint = part["layer"], part["cuts"], part["joint"]
            pivot = part["pivot"]
            ja = angles[joint]
            rx, ry, rz, lift = ja["rx"], ja["ry"], ja["rz"], ja["lift"]

            verts = self._cube_vertices(wx, wy, pw, ph, depth)
            # 1) 模型空间关节动画：绕肩 / 颈 / 髋枢轴局部旋转，再加呼吸上下位移
            local = [self._rotate_about(v, pivot, rx, ry, rz) for v in verts]
            if lift:
                local = [(v[0], v[1] + lift, v[2]) for v in local]
            # 2) 整体刚体 yaw / pitch（跟随指针 / 拖拽）
            rotated = [self._rotated(v, yaw, pitch) for v in local]

            for face_name, idx, normal, cut_key in _FACES:
                n_local = self._rotate_normal_local(normal, rx, ry, rz)
                n = self._rotated_normal(n_local, yaw, pitch)
                # 背面剔除：仅当法线明显朝后（n·视线 <= -0.65，约 130° 以上）才去掉。
                # 俯仰 / 侧视时保留接近水平的躯干顶面、手臂侧面与头底面，避免这些
                # 相邻面被剔除后空腔透出卡片背景。
                if n[2] <= -0.65:
                    continue

                # 投影四个屏幕点（弱透视：近大远小）
                screen: list[QPointF] = []
                z_sum = 0.0
                for vi in idx:
                    v = rotated[vi]
                    persp = _CAM_DIST / (_CAM_DIST - v[2])
                    sx = center_x + v[0] * unit * persp
                    sy = center_y - (v[1] - _MODEL_CY) * unit * persp
                    screen.append(QPointF(sx, sy))
                    z_sum += v[2]
                depth_key = z_sum / 4.0

                # 明暗：环境光 + 漫反射按面朝向分档，再乘部件前后分层亮度，
                # 最后对互相贴合的内侧窄面叠加接触 AO 暗部。
                shade = self._face_shade(n) * part["layer_light"]
                shade *= _CONTACT_AO.get((part["name"], face_name), 1.0)
                shade = max(0.24, min(1.05, shade))

                faces.append({
                    "points": screen,
                    "depth": depth_key,
                    "layer": layer,
                    "shade": shade,
                    "pixmap": self._slice(cuts, cut_key),
                    "cut": cuts[cut_key],
                })

        # 画家算法：先按 z 深度从远到近；同一深度再按部件层级（四肢 0 → 躯干 1
        # → 头部 2），保证同层重叠时躯干、头部覆盖四肢伸入段。
        faces.sort(key=lambda f: (f["depth"], f["layer"]))

        for f in faces:
            self._draw_face(painter, f)

    def _draw_face(self, painter: QPainter, face: dict) -> None:
        p00, p10, p11, p01 = face["points"]
        pixmap = face["pixmap"]
        _cx, _cy, cw, ch = face["cut"]

        # 把四边形四点沿各自远离质心方向轻微外扩，仅压盖软件投影在标准相切
        # 边界残留的不到 1px 细缝；外扩量很小，不改变标准模型外形轮廓。
        pts = [p00, p10, p11, p01]
        c_x = sum(p.x() for p in pts) / 4.0
        c_y = sum(p.y() for p in pts) / 4.0
        grow = 0.6
        grown = []
        for p in pts:
            dx, dy = p.x() - c_x, p.y() - c_y
            dist = math.hypot(dx, dy)
            if dist > 1e-6:
                p = QPointF(p.x() + dx / dist * grow, p.y() + dy / dist * grow)
            grown.append(p)
        p00, p10, p11, p01 = grown

        painter.resetTransform()
        # 仿射映射：单位矩形 (0,0)-(1,1) → 屏幕平行四边形
        t = QTransform(
            p10.x() - p00.x(), p10.y() - p00.y(),
            p01.x() - p00.x(), p01.y() - p00.y(),
            p00.x(), p00.y(),
        )
        painter.setTransform(t)
        painter.setOpacity(1.0)
        painter.drawPixmap(QRectF(0, 0, 1, 1), pixmap, QRectF(0, 0, cw, ch))

        # 按法线明暗叠加黑色遮罩（顶面最亮、侧面中等、背面最暗）
        dark = 1.0 - face["shade"]
        if dark > 0.01:
            poly = QPolygonF([QPointF(0, 0), QPointF(1, 0),
                             QPointF(1, 1), QPointF(0, 1)])
            painter.setOpacity(dark)
            painter.setBrush(QColor(0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(poly)
            painter.setOpacity(1.0)

    def _draw_ground_shadow(self, painter: QPainter,
                            center_x: float, center_y: float, unit: float) -> None:
        """角色脚下柔和椭圆阴影，增强三维落地感。"""
        painter.resetTransform()
        # 脚底世界 y=0，相对模型中心的偏移为 -_MODEL_CY
        shadow_y = center_y + _MODEL_CY * unit
        rx = 7.5 * unit
        ry = 1.8 * unit
        painter.setOpacity(0.22)
        painter.setBrush(QColor(60, 90, 110))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center_x, shadow_y), rx, ry)
        painter.setOpacity(1.0)
