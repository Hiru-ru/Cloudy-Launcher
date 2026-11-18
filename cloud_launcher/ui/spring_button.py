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

"""v1.2.4.6 按钮橡皮筋拉扯 + 松开弹簧回弹控制器与 ``SpringPushButton`` 基类。

设计口径（用户多轮语音澄清定稿）：
- 动作是「拉」不是点按：**左键按住**按钮后拖动，按钮整体朝指针方向被橡皮筋拽着走，
  拉得越远跟得越远；同时沿拉扯方向轻微拉长、垂直方向略压（果冻形变，文字跟着轻微
  变形）；**松开**后用 ``OutBack`` 过冲曲线弹簧拉回原位，轻轻晃一下再稳住。触发键为
  左键，不是右键，也不是光标悬停触发。
- v1.2.4.6 彻底取消「格挡」：上一版仍有两道墙——
  1. ``pull()`` 把偏移硬 clamp 到 16px，指针再往外偏移就锁死，手感像撞墙；
  2. ``QPainter`` 默认裁剪到按钮自身矩形，平移偏移后按钮一端被硬切平、露出父片，
     视觉上像被看不见的矩形框挡住。
  本轮改为**真实几何跟随**：按住拖动时按钮 ``move()`` 到跟随指针的位置（整个矩形一起
  走，不存在自身矩形裁内容的问题）；偏移不再做硬限幅，改用渐近软饱和曲线——日常拖拽
  范围内几乎线性跟手、没有撞墙感，只有指针拉到极远才缓慢趋近一个很大的上限，不会被
  拽飞出窗口。``paintEvent`` 同时 ``setClipping(False)`` 放开 painter 级矩形裁剪，果冻
  轻微拉伸也不被切。
- 松开后回弹动画把按钮几何从当前偏移弹簧拉回按压瞬间记录的原始位置；动画结束复位到
  原始 geometry，布局下次自然 relayout 时位置一致。
- ``SpringPushButton`` 仍是 ``QPushButton`` 子类，``click()`` / ``clicked`` 信号保留；
  只响应左键，悬停不变形。

技术红线：只用 PySide6 自带模块与 Python 标准库，不挂 QGraphicsBlurEffect、不引第三方库。

v1.2.5.1：本轮未改动拉扯 / 回弹控制器行为；五导航项 ``NavItem`` 复用本基类承载
图标 + 文字布局，选中态只切换 ``navActive`` 属性与图标显隐，橡皮筋手感规则保持 v1.2.4.6
基线不变。

v1.3.9.3：总开关关闭时全部动作彻底静止——按压收缩 / 果冻形变 / OutBack 回弹 / 光标
拉扯跟随（pull）一律不执行，按钮完全不动；只有总开关开启时才做橡皮筋与弹簧。
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRect, QVariantAnimation, Qt
from PySide6.QtGui import QCursor, QPainter
from PySide6.QtWidgets import (
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QWidget,
)

from .appearance import appearance

# 按住期间整体轻微收缩（橡皮筋被拉紧时略微收一下）；按压段快速缓出。
_PRESS_SCALE = 0.97
_PRESS_DURATION_MS = 80
# 松开回弹：OutBack 过冲，振幅收到柔和一档，避免过度弹跳。
_RELEASE_DURATION_MS = 300
_OUTBACK_OVERSHOOT = 1.10
# 拉扯阻尼：偏移 = 指针相对原中心向量 × 阻尼；再走渐近软饱和趋近最大跟随距离。
# v1.2.4.6 取消硬 clamp：日常拖拽几乎线性跟手，无撞墙感；max_len 只是极远距离的
# 渐近上限，不是一道硬墙。
_PULL_DAMPING = 0.34
_MAX_PULL_PX = 110.0
# 果冻形变：沿拉扯方向最多拉长 8%，垂直方向最多压缩 5%，幅度随偏移大小线性变化，
# 松手随偏移一起回弹归零。
_STRETCH_DIR = 0.08
_COMPRESS_PERP = 0.05


def _make_release_curve() -> QEasingCurve:
    curve = QEasingCurve(QEasingCurve.OutBack)
    curve.setOvershoot(_OUTBACK_OVERSHOOT)
    return curve


class SpringController:
    """绑定到任意控件的橡皮筋拉扯控制器：按住拖动几何跟随 + 果冻形变，松开弹簧回弹。

    控制器维护拉扯偏移、方向、整体缩放与两段动画；拖动期间直接移动目标控件几何，
    回弹动画每帧把几何拉回按压瞬间记录的原始位置。
    """

    def __init__(self, target: QWidget, max_pull: float = _MAX_PULL_PX,
                 damping: float = _PULL_DAMPING) -> None:
        self._target = target
        self._max_pull = max_pull
        self._damping = damping
        # 当前拉扯偏移（相对按压瞬间原始位置，父控件坐标）、拉扯方向单位向量与整体缩放。
        self.pull_x = 0.0
        self.pull_y = 0.0
        self.dir_x = 0.0
        self.dir_y = 0.0
        self.scale = 1.0
        self.dragging = False

        # 按压瞬间记录的原始位置与几何（父控件坐标系），回弹归位基准。
        self._orig_pos = QPoint(0, 0)
        self._orig_geo = QRect()

        self._press_anim = QVariantAnimation(target)
        self._press_anim.setDuration(_PRESS_DURATION_MS)
        self._press_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._press_anim.valueChanged.connect(self._on_press_value)

        self._release_anim = QVariantAnimation(target)
        self._release_anim.setDuration(_RELEASE_DURATION_MS)
        self._release_anim.setEasingCurve(_make_release_curve())
        self._release_anim.valueChanged.connect(self._on_release_value)

        # 回弹起点：松开瞬间记录的偏移与缩放。
        self._start_x = 0.0
        self._start_y = 0.0
        self._start_scale = 1.0

    # ---------- 按住 ----------
    def press(self) -> None:
        """左键按下：停止回弹，记录原始几何，进入拉扯态，整体轻微收缩。"""
        self._release_anim.stop()
        self._press_anim.stop()
        self.dragging = True
        self._orig_pos = self._target.pos()
        self._orig_geo = self._target.geometry()
        if not appearance.animations_enabled:
            # 动画总开关关闭：不做按压收缩，scale 恒 1.0。
            self.scale = 1.0
            return
        self._press_anim.setStartValue(self.scale)
        self._press_anim.setEndValue(_PRESS_SCALE)
        self._press_anim.start()

    def _on_press_value(self, value) -> None:
        if not appearance.animations_enabled:
            return
        self.scale = float(value)
        self._target.update()

    # ---------- 按住拖动：真实几何朝指针方向跟随 ----------
    def pull(self, global_pos: QPoint) -> None:
        """按钮几何跟随全局光标：在父控件坐标系内朝指针方向偏移，软饱和不设硬墙。

        ``global_pos`` 为 ``QCursor.pos()`` 全局坐标；映射到父控件坐标系后相对按压瞬间
        原始中心求向量，乘阻尼，再用 ``max_len / (max_len + len)`` 渐近曲线软化——指针在
        近处几乎 1:1 跟手，拉到极远时偏移缓慢趋近 ``max_len``，不会锁死在一个固定像素上。
        """
        if not self.dragging:
            return
        if not appearance.animations_enabled:
            # 总开关关闭：按钮完全静止，不做光标几何跟随，松开也无位移可复位。
            return
        parent = self._target.parentWidget()
        if parent is not None:
            parent_point = parent.mapFromGlobal(global_pos)
        else:
            parent_point = self._target.mapFromGlobal(global_pos)

        orig_center = QPointF(
            self._orig_pos.x() + self._target.width() / 2.0,
            self._orig_pos.y() + self._target.height() / 2.0,
        )
        vec = QPointF(parent_point) - orig_center
        raw = QPointF(vec.x() * self._damping, vec.y() * self._damping)

        length = math.hypot(raw.x(), raw.y())
        if length > 1e-6:
            # 渐近软饱和：factor = max_len / (max_len + length)，length=0 时为 1，
            # length 增大时 factor 单调趋近 0，偏移渐近 max_len，没有硬性截断点。
            factor = self._max_pull / (self._max_pull + length)
            offset = QPointF(raw.x() * factor, raw.y() * factor)
        else:
            offset = QPointF(0.0, 0.0)

        self.pull_x = offset.x()
        self.pull_y = offset.y()
        if length > 0.5:
            self.dir_x = offset.x() / max(1e-6, math.hypot(offset.x(), offset.y()))
            self.dir_y = offset.y() / max(1e-6, math.hypot(offset.x(), offset.y()))

        new_pos = QPoint(
            self._orig_pos.x() + round(self.pull_x),
            self._orig_pos.y() + round(self.pull_y),
        )
        self._target.move(new_pos)
        self._target.update()

    def pull_norm(self) -> float:
        """当前偏移占软饱和上限的归一化幅度（0..1），驱动果冻形变强度。"""
        return min(1.0, math.hypot(self.pull_x, self.pull_y) / self._max_pull)

    # ---------- 松开：弹簧把几何拉回原位并过冲 ----------
    def release(self) -> None:
        """左键松开：停止按压收缩，OutBack 弹簧把偏移与缩放拉回 0 / 1.0。"""
        if not self.dragging:
            return
        self.dragging = False
        self._press_anim.stop()
        self._release_anim.stop()
        if not appearance.animations_enabled:
            # 动画总开关关闭：瞬时复位几何，不做过冲回弹。
            self.pull_x = 0.0
            self.pull_y = 0.0
            self.scale = 1.0
            self._target.setGeometry(self._orig_geo)
            self._target.update()
            return
        self._start_x = self.pull_x
        self._start_y = self.pull_y
        self._start_scale = self.scale
        self._release_anim.setStartValue(0.0)
        self._release_anim.setEndValue(1.0)
        self._release_anim.start()

    def _on_release_value(self, t) -> None:
        # t 由 OutBack 曲线给出，回弹中段可略大于 1（过冲）；1 - t 随之变负，
        # 偏移反向轻晃、缩放轻微超过 1，形成橡皮筋弹回的手感。
        t = float(t)
        self.pull_x = self._start_x * (1.0 - t)
        self.pull_y = self._start_y * (1.0 - t)
        self.scale = self._start_scale + (1.0 - self._start_scale) * t

        new_pos = QPoint(
            self._orig_pos.x() + round(self.pull_x),
            self._orig_pos.y() + round(self.pull_y),
        )
        self._target.move(new_pos)
        self._target.update()

        if t >= 1.0:
            # 回弹到位：复位到按压瞬间记录的原始几何，保证布局基准一致。
            self._target.setGeometry(self._orig_geo)
            self.pull_x = 0.0
            self.pull_y = 0.0
            self.scale = 1.0
            self._target.update()

    # ---------- 绘制形变 ----------
    def apply_transform(self, painter: QPainter) -> None:
        """围绕控件当前矩形中心做果冻非均匀缩放；几何偏移已由 move() 完成，这里只形变。"""
        if not appearance.animations_enabled:
            # 动画总开关关闭：不做任何果冻形变。
            return
        cx = self._target.width() / 2.0
        cy = self._target.height() / 2.0
        norm = self.pull_norm()

        painter.translate(cx, cy)
        if norm > 0.01:
            angle = math.degrees(math.atan2(self.pull_y, self.pull_x))
            s_dir = self.scale * (1.0 + _STRETCH_DIR * norm)
            s_perp = self.scale * (1.0 - _COMPRESS_PERP * norm)
            painter.rotate(angle)
            painter.scale(s_dir, s_perp)
            painter.rotate(-angle)
        else:
            painter.scale(self.scale, self.scale)
        painter.translate(-cx, -cy)


class SpringPushButton(QPushButton):
    """带橡皮筋几何跟随 + 果冻形变 + 松开弹簧回弹的 ``QPushButton`` 基类。

    保留 ``QPushButton`` 全部信号、槽与 QSS 渲染能力；子类只需在需要时重写
    paintEvent 绘制自定义外形（如标题栏圆形凸起按钮），并在其中调用
    ``self._spring.apply_transform(painter)`` 复用同一套拉扯变换。子类可覆盖
    :attr:`PULL_MAX_PX` / :attr:`PULL_DAMPING` 调整跟随幅度（小按钮用更小上限）。
    """

    PULL_MAX_PX = _MAX_PULL_PX
    PULL_DAMPING = _PULL_DAMPING

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._spring = SpringController(
            self, max_pull=self.PULL_MAX_PX, damping=self.PULL_DAMPING
        )

    # ---------- 按住 / 拖动 / 松开：驱动橡皮筋控制器，同时走父类默认状态 ----------
    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        if event.button() == Qt.LeftButton and self.isEnabled():
            self._spring.press()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        if (event.buttons() & Qt.LeftButton) and self.isEnabled() and self._spring.dragging:
            # 全局光标映射由控制器在父控件坐标系内完成，指针拖出按钮矩形也持续跟随。
            self._spring.pull(QCursor.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        if event.button() == Qt.LeftButton and self.isEnabled():
            self._spring.release()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 放开 painter 级矩形裁剪：几何已 move 到跟随位置，果冻轻微拉伸不再被自身矩形切平。
        painter.setClipping(False)
        self._spring.apply_transform(painter)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, self)
        painter.end()
