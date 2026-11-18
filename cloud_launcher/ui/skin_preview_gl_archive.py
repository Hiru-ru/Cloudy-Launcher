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

"""Minecraft 离线角色 3D 预览组件。

- 使用官方原版皮肤贴图（resources/skins/steve.png、alex.png）；
- 由头、身体、双臂、双腿六个方块拼装；
- 鼠标悬停时角色跟随鼠标左右/俯仰转动，按住拖动可自由旋转，松开后缓慢回正；
- 仅离线角色（史蒂夫 / 艾利克斯），正版登录角色后续版本接入。
"""
import math
import os

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QImage, QMatrix4x4, QVector3D
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVertexArrayObject,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from .. import constants as C
from ..resources import resource_path

_DEBUG_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "gl_debug.log")


def _debug(msg: str) -> None:
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


# GL 标准常量（PySide6 未在 functions 对象上暴露，这里直接定义数值）
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_TRIANGLES = 0x0004
GL_UNSIGNED_INT = 0x1405
GL_FLOAT = 0x1406


# ---------------------------------------------------------------------------
# 皮肤 UV 布局（64x32 经典格式；64x64 贴图的上层区域完全兼容）
# 每个面给出贴图矩形 (x, y, w, h)，单位为皮肤像素。
# ---------------------------------------------------------------------------

# 头部 8x8x8
HEAD_UV = {
    "front": (8, 8, 8, 8),
    "back": (24, 8, 8, 8),
    "right": (0, 8, 8, 8),
    "left": (16, 8, 8, 8),
    "top": (8, 0, 8, 8),
    "bottom": (16, 0, 8, 8),
}

# 身体 8x12x4
BODY_UV = {
    "front": (20, 20, 8, 12),
    "back": (32, 20, 8, 12),
    "right": (16, 20, 4, 12),
    "left": (28, 20, 4, 12),
    "top": (20, 16, 8, 4),
    "bottom": (28, 16, 8, 4),
}

# 右臂 4x12x4（64x32 格式左臂镜像复用）
ARM_UV = {
    "front": (44, 20, 4, 12),
    "back": (52, 20, 4, 12),
    "right": (40, 20, 4, 12),
    "left": (48, 20, 4, 12),
    "top": (44, 16, 4, 4),
    "bottom": (48, 16, 4, 4),
}

# 右腿 4x12x4（左腿镜像复用）
LEG_UV = {
    "front": (4, 20, 4, 12),
    "back": (12, 20, 4, 12),
    "right": (0, 20, 4, 12),
    "left": (8, 20, 4, 12),
    "top": (4, 16, 4, 4),
    "bottom": (8, 16, 4, 4),
}

# 面亮度（环境 + 方向光近似）
SHADE = {
    "front": 1.0,
    "back": 0.55,
    "right": 0.84,
    "left": 0.68,
    "top": 1.08,
    "bottom": 0.5,
}

# 角色各部件：(中心 x, 中心 y, 宽, 高, 深, UV 表, 诊断色系数)。y 向上，脚底为 0。
_PARTS = [
    (0, 28, 8, 8, 8, HEAD_UV, 1.0),      # 头
    (0, 18, 8, 12, 4, BODY_UV, 0.85),    # 身体
    (-6, 18, 4, 12, 4, ARM_UV, 0.6),     # 右臂
    (6, 18, 4, 12, 4, ARM_UV, 0.4),      # 左臂
    (-2, 6, 4, 12, 4, LEG_UV, 1.0),      # 右腿
    (2, 6, 4, 12, 4, LEG_UV, 0.3),       # 左腿
]

TEX_W, TEX_H = 64, 32

_VERTEX_SHADER = """
#version 120
attribute vec3 aPos;
attribute vec2 aUV;
attribute float aShade;
uniform mat4 uMVP;
varying vec2 vUV;
varying float vShade;
void main() {
    vUV = aUV;
    vShade = aShade;
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

_FRAGMENT_SHADER = """
#version 120
uniform sampler2D uTex;
varying vec2 vUV;
varying float vShade;
void main() {
    // 诊断阶段：纯色 + 面明暗，不采样纹理
    gl_FragColor = vec4(0.35 * vShade, 0.62 * vShade, 0.82 * vShade, 1.0);
}
"""


def _face_vertices(center, size, face, uv_rect, part_shade=1.0):
    """生成单个面的 4 个 (position, uv)。返回扁平列表前先收集。"""
    cx, cy, _ = center
    w, h, d = size
    hw, hh, hd = w / 2, h / 2, d / 2
    x, y, uw, uh = uv_rect

    # 四个贴图角 UV（左上、右上、右下、左下），v 轴按 OpenGL 左下角翻转
    u0, u1 = x / TEX_W, (x + uw) / TEX_W
    v_top = 1.0 - y / TEX_H
    v_bottom = 1.0 - (y + uh) / TEX_H
    uv_corners = [(u0, v_top), (u1, v_top), (u1, v_bottom), (u0, v_bottom)]

    local = {
        "front": [(-hw, -hh, hd), (hw, -hh, hd), (hw, hh, hd), (-hw, hh, hd)],
        "back": [(hw, -hh, -hd), (-hw, -hh, -hd), (-hw, hh, -hd), (hw, hh, -hd)],
        "right": [(hw, -hh, hd), (hw, -hh, -hd), (hw, hh, -hd), (hw, hh, hd)],
        "left": [(-hw, -hh, -hd), (-hw, -hh, hd), (-hw, hh, hd), (-hw, hh, -hd)],
        "top": [(-hw, hh, hd), (-hw, hh, -hd), (hw, hh, -hd), (hw, hh, hd)],
        "bottom": [(-hw, -hh, -hd), (hw, -hh, -hd), (hw, -hh, hd), (-hw, -hh, hd)],
    }
    points = local[face]
    shade = SHADE[face] * part_shade

    result = []
    for i, (lx, ly, lz) in enumerate(points):
        px, py, pz = cx + lx, cy + ly, lz
        u, v = uv_corners[i]
        result.append((px, py, pz, u, v, shade))
    return result


def _build_mesh():
    """拼接所有部件，直接展开为三角形顶点（每面两个三角形）。

    返回顶点元组列表，每项 (x, y, z, u, v, shade)。
    """
    vertices = []
    triangle = [0, 1, 2, 0, 2, 3]
    for cx, cy, w, h, d, uv, ps in _PARTS:
        center = (cx, cy, 0)
        size = (w, h, d)
        for face, rect in uv.items():
            face_pts = _face_vertices(center, size, face, rect, ps)
            for i in triangle:
                vertices.append(face_pts[i])
    return vertices


class SkinPreview(QOpenGLWidget):
    """跟随鼠标转动的方块角色预览。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFormat(self._default_format())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(150, 190)

        self._skin_id = C.DEFAULT_SKIN
        self._texture: QOpenGLTexture | None = None
        self._program: QOpenGLShaderProgram | None = None
        self._vao = QOpenGLVertexArrayObject()
        self._vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vertex_count = 0
        self._loc_mvp = -1
        self._loc_tex = -1

        # 角度：当前角与目标角（弧度）
        self._yaw = 0.0
        self._pitch = 0.0
        self._yaw_target = 0.0
        self._pitch_target = 0.0
        self._dragging = False
        self._last_pos = QPointF(0, 0)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @staticmethod
    def _default_format():
        from PySide6.QtGui import QSurfaceFormat
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)
        # 使用驱动默认兼容上下文，避免部分显卡不支持 CoreProfile 3.3 导致崩溃
        return fmt

    # ---------- 皮肤切换 ----------
    def set_skin(self, skin_id: str) -> None:
        if skin_id not in C.SKIN_CHOICES:
            skin_id = C.DEFAULT_SKIN
        self._skin_id = skin_id
        if self._texture is not None:
            self._texture.destroy()
            self._texture = None
        self.update()

    # ---------- GL 初始化 ----------
    def initializeGL(self) -> None:
        _debug("[INIT] initializeGL entered")
        try:
            self._initialize_gl()
        except Exception as exc:  # noqa: BLE001 - GL 回调内异常需落盘排查
            import traceback
            _debug("[INIT] EXCEPTION: " + traceback.format_exc())
            raise

    def _initialize_gl(self) -> None:
        gl = self.context().functions()
        gl.glDisable(GL_DEPTH_TEST)
        gl.glEnable(GL_BLEND)
        gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)

        ctx = self.context()
        _debug(f"[GL] vendor: {gl.glGetString(0x1F00)}")
        _debug(f"[GL] renderer: {gl.glGetString(0x1F01)}")
        _debug(f"[GL] version: {gl.glGetString(0x1F02)}")
        _debug(f"[GL] format: {ctx.format().version()} profile={ctx.format().profile()}")

        self._program = QOpenGLShaderProgram()
        v_ok = self._program.addShaderFromSourceCode(
            QOpenGLShader.Vertex, _VERTEX_SHADER
        )
        f_ok = self._program.addShaderFromSourceCode(
            QOpenGLShader.Fragment, _FRAGMENT_SHADER
        )
        _debug(f"[GL] vertex compile: {v_ok} frag compile: {f_ok}")
        # 不强制绑定 location，由编译器分配；setAttributeBuffer 按名称解析真实位置
        self._program.link()
        _debug(f"[GL] linked: {self._program.isLinked()}")
        if self._program.log().strip():
            _debug(f"[GL] program log: {self._program.log()}")
        _debug(f"[GL] loc aPos/aUV/aShade: "
               f"{self._program.attributeLocation('aPos')} "
               f"{self._program.attributeLocation('aUV')} "
               f"{self._program.attributeLocation('aShade')}")
        self._loc_mvp = self._program.uniformLocation("uMVP")
        self._loc_tex = self._program.uniformLocation("uTex")
        _debug(f"[GL] loc uMVP/uTex: {self._loc_mvp} {self._loc_tex}")

        self._vao.create()
        binder = QOpenGLVertexArrayObject.Binder(self._vao)

        vertices = _build_mesh()
        flat = []
        for p in vertices:
            flat.extend(p)
        self._vertex_count = len(vertices)
        xs = [p[0] for p in vertices]
        ys = [p[1] for p in vertices]
        zs = [p[2] for p in vertices]
        _debug(f"[MESH] x[{min(xs)},{max(xs)}] y[{min(ys)},{max(ys)}] z[{min(zs)},{max(zs)}] n={len(vertices)}")

        self._vbo.create()
        self._vbo.bind()
        self._vbo.allocate(bytes(self._pack_vertices(flat)), len(flat) * 4)

        stride = 6 * 4  # position3 + uv2 + shade1
        self._program.bind()
        self._program.setAttributeBuffer("aPos", GL_FLOAT, 0, 3, stride)
        self._program.setAttributeBuffer("aUV", GL_FLOAT, 3 * 4, 2, stride)
        self._program.setAttributeBuffer("aShade", GL_FLOAT, 5 * 4, 1, stride)
        self._program.enableAttributeArray("aPos")
        self._program.enableAttributeArray("aUV")
        self._program.enableAttributeArray("aShade")
        self._program.release()
        _debug(f"[MESH] first vertex: {vertices[0]} last: {vertices[-1]} count={len(vertices)}")

        self._load_texture()

    @staticmethod
    def _pack_vertices(flat):
        import struct
        return struct.pack(f"{len(flat)}f", *flat)

    def _load_texture(self) -> None:
        info = C.SKIN_CHOICES[self._skin_id]
        path = resource_path(os.path.join("skins", info["file"]))
        image = QImage(path)
        _debug(f"[TEX] path={path} null={image.isNull()} size={image.size()}")
        if image.isNull():
            # 兜底：纯色占位，避免崩溃
            image = QImage(TEX_W, TEX_H, QImage.Format_RGBA8888)
            image.fill("#9fc9e0")
        image = image.mirrored(False, True)  # 垂直翻转匹配 UV

        self._texture = QOpenGLTexture(QOpenGLTexture.Target2D)
        self._texture.setData(image)
        self._texture.setMinificationFilter(QOpenGLTexture.Nearest)
        self._texture.setMagnificationFilter(QOpenGLTexture.Nearest)
        self._texture.setWrapMode(QOpenGLTexture.ClampToEdge)
        self._texture.setMipLevels(1)

    def resizeGL(self, w, h) -> None:
        gl = self.context().functions()
        gl.glViewport(0, 0, w, h)

    def paintGL(self) -> None:
        try:
            self._paint_gl()
        except Exception as exc:  # noqa: BLE001
            import traceback
            _debug("[PAINT] EXCEPTION: " + traceback.format_exc())
            raise

    def _paint_gl(self) -> None:
        gl = self.context().functions()
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self._texture is None or self._program is None:
            return

        self._frame_count = getattr(self, "_frame_count", 0) + 1
        if self._frame_count <= 5:
            _debug(f"[DRAW] frame={self._frame_count} vertices={self._vertex_count} "
                   f"tex={self._texture is not None} err={gl.glGetError()}")

        width, height = self.width(), self.height()
        aspect = width / max(1, height)

        proj = QMatrix4x4()
        proj.perspective(35.0, aspect, 0.1, 200.0)

        model = QMatrix4x4()
        model.translate(0.0, -16.0, 0.0)          # 绕角色自身中心旋转
        model.rotate(math.degrees(self._pitch), QVector3D(1, 0, 0))
        model.rotate(math.degrees(self._yaw), QVector3D(0, 1, 0))
        model.translate(0.0, 16.0, 0.0)

        view = QMatrix4x4()
        view.translate(0.0, -16.0, -55.0)          # 相机在 +Z 方向看向角色

        mvp = proj * view * model

        self._program.bind()
        self._program.setUniformValue(self._loc_mvp, mvp)
        self._program.setUniformValue(self._loc_tex, 0)
        if self._frame_count <= 5:
            _debug(f"[DRAW] after program/uniform err={gl.glGetError()}")
        self._texture.bind(0)
        if self._frame_count <= 5:
            _debug(f"[DRAW] after texture bind err={gl.glGetError()}")

        binder = QOpenGLVertexArrayObject.Binder(self._vao)
        self._vbo.bind()
        if self._frame_count <= 5:
            _debug(f"[DRAW] after vao/vbo err={gl.glGetError()}")
        gl.glDrawArrays(GL_TRIANGLES, 0, self._vertex_count)
        if self._frame_count <= 5:
            _debug(f"[DRAW] after draw err={gl.glGetError()}")
        self._program.release()

    # ---------- 动画 ----------
    def _tick(self) -> None:
        self._yaw += (self._yaw_target - self._yaw) * 0.12
        self._pitch += (self._pitch_target - self._pitch) * 0.12
        if abs(self._yaw - self._yaw_target) < 0.001:
            self._yaw = self._yaw_target
        if abs(self._pitch - self._pitch_target) < 0.001:
            self._pitch = self._pitch_target
        self.update()

    # ---------- 鼠标交互 ----------
    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            dx = event.position().x() - self._last_pos.x()
            dy = event.position().y() - self._last_pos.y()
            self._yaw_target = max(-1.4, min(1.4, self._yaw_target + dx * 0.012))
            self._pitch_target = max(-0.35, min(0.35, self._pitch_target - dy * 0.008))
            self._last_pos = event.position()
        else:
            nx = event.position().x() / max(1, self.width()) - 0.5
            ny = 0.5 - event.position().y() / max(1, self.height())
            self._yaw_target = max(-1.1, min(1.1, nx * 1.6))
            self._pitch_target = max(-0.2, min(0.2, ny * 0.35))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_pos = event.position()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._dragging:
            self._yaw_target = 0.0
            self._pitch_target = 0.0
        super().leaveEvent(event)
