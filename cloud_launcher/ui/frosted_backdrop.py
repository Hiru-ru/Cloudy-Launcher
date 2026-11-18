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

"""v1.2.4.1 局部磨砂（frosted glass）共享服务与面板自绘工具。

设计口径（相对 v1.2.4.0 的修正）：
- v1.2.4.0 是整窗壁纸先降采样柔化铺满、卡片只盖一层半透明白片——整张壁纸都是糊的。
- 本版改为：最底层 ``BackgroundLayer`` 只绘制**清晰** cover 壁纸（卡片外壁纸保持清晰）；
  模糊**只发生在每张卡片 / 侧栏玻璃片自身的圆角矩形内**——面板自绘时取它正后方那一小块
  清晰壁纸，先降采样、再平滑放大回来得到片内大半径柔化，叠三段白玻璃高光与细亮边。

技术红线沿用：不挂 ``QGraphicsBlurEffect``（会连带模糊上层子控件文字），不引入
PIL / numpy / scipy 等第三方模糊库；柔化仅靠两级缩放（先快缩放降采样、再平滑放大），
只用 PySide6 自带模块与 Python 标准库。

``backdrop`` 为模块级单例：主窗口加载壁纸后把清晰原图注入，窗口 resize 时重建与主窗口
同尺寸的清晰 cover 缓存；各玻璃面板在 paintEvent 中读取该缓存、截取自身后方小块做局部磨砂。
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)

from .. import constants as C
from .appearance import appearance


def cover_rect(viewport_w: int, viewport_h: int, source_w: int, source_h: int) -> QRectF:
    """等比 cover 铺满视口：缩放比例取较大一侧，居中对齐，返回绘制目标矩形。"""
    if source_w <= 0 or source_h <= 0:
        return QRectF(0, 0, viewport_w, viewport_h)
    scale = max(viewport_w / source_w, viewport_h / source_h)
    box_w = source_w * scale
    box_h = source_h * scale
    return QRectF(
        (viewport_w - box_w) / 2.0,
        (viewport_h - box_h) / 2.0,
        box_w,
        box_h,
    )


class FrostedBackdrop:
    """共享清晰壁纸持有方：保存原图，并按主窗口尺寸构建清晰 cover 缓存 + 预模糊缓存。"""

    def __init__(self) -> None:
        self._source: QPixmap | None = None
        self._brightness: float = 0.0
        self._window_pixmap: QPixmap | None = None
        self._blur_pixmap: QPixmap | None = None

    # ---------- 原图注入 ----------
    def set_source(self, pixmap: QPixmap | None, brightness: float = 0.0) -> None:
        if pixmap is not None and not pixmap.isNull():
            self._source = pixmap
            self._brightness = max(0.0, min(1.0, float(brightness)))
        else:
            self._source = None
            self._brightness = 0.0
        self._window_pixmap = None
        self._blur_pixmap = None

    @property
    def source(self) -> QPixmap | None:
        return self._source

    @property
    def brightness(self) -> float:
        return self._brightness

    def has_wallpaper(self) -> bool:
        return self._source is not None

    # ---------- 窗口尺寸清晰 cover 缓存 + 预模糊缓存 ----------
    def render_window(self, width: int, height: int) -> None:
        """按主窗口当前尺寸重建清晰 cover 缓存和预模糊缓存。"""
        if self._source is None or width <= 0 or height <= 0:
            self._window_pixmap = None
            self._blur_pixmap = None
            return

        shot = QPixmap(width, height)
        shot.fill(Qt.transparent)
        painter = QPainter(shot)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        target = cover_rect(width, height, self._source.width(), self._source.height())
        painter.drawPixmap(target, self._source, QRectF(self._source.rect()))
        painter.end()
        self._window_pixmap = shot

        # 预模糊：整窗壁纸缩到短边 PANEL_BLUR_SHORT_SIDE，保持比例
        bw, bh = width, height
        if bw <= bh:
            sw = C.PANEL_BLUR_SHORT_SIDE
            sh = max(1, int(bh * sw / bw))
        else:
            sh = C.PANEL_BLUR_SHORT_SIDE
            sw = max(1, int(bw * sh / bh))
        self._blur_pixmap = shot.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.FastTransformation)

    def window_pixmap(self) -> QPixmap | None:
        return self._window_pixmap

    def blur_pixmap(self) -> QPixmap | None:
        return self._blur_pixmap


# 模块级单例：主窗口注入原图 / 重建缓存，卡片与侧栏读取，避免层层传引用。
backdrop = FrostedBackdrop()


def _rgba(color: tuple[int, int, int, int]) -> QColor:
    return QColor(color[0], color[1], color[2], color[3])


def capture_live_backdrop(reference_widget):
    """把 ``reference_widget`` 当前真实渲染结果离屏抓下来，返回 (清晰, 预模糊)。

    与 :meth:`FrostedBackdrop.render_window` 只抓壁纸不同，这里用 ``QWidget.grab()``
    抓的是控件**整棵已渲染的子树**（含卡片、文字等），供模态弹窗做真正的「背景模糊」——
    弹窗后方的密集卡片被大半径柔化后，文字不再与弹窗内容叠字，同时保留玻璃观感而非白板。

    需在弹窗自身显示**之前**调用（弹窗若是其子控件，隐藏时不会被抓进快照）。
    """
    if reference_widget is None:
        return None, None
    clear = reference_widget.grab()
    if clear is None or clear.isNull():
        return None, None
    width, height = clear.width(), clear.height()
    if width <= 0 or height <= 0:
        return None, None
    if width <= height:
        sw = C.PANEL_BLUR_SHORT_SIDE
        sh = max(1, int(round(height * sw / width)))
    else:
        sh = C.PANEL_BLUR_SHORT_SIDE
        sw = max(1, int(round(width * sh / height)))
    blurred = clear.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.FastTransformation)
    return clear, blurred


def paint_frosted_panel(
    painter: QPainter,
    widget,
    radius: float,
    top_rgba: tuple[int, int, int, int],
    mid_rgba: tuple[int, int, int, int],
    bottom_rgba: tuple[int, int, int, int],
    border_rgba: tuple[int, int, int, int],
    reference_window=None,
    live=None,
) -> None:
    """在面板圆角矩形内绘制「局部磨砂背景块 + 三段白玻璃高光 + 细亮边」。

    - 模糊只取自该面板正后方的一小块背景，圆角路径裁剪，绝不溢出到面板之外；
    - ``live=(清晰图, 模糊图, 基准控件)`` 时（模态弹窗），背景块取自弹窗弹出前抓到的
      父控件真实渲染（含卡片文字），无壁纸时也能把后方密集卡片柔化压住、不再叠字；
      为 None 时沿用壁纸缓存（``backdrop``），无壁纸则只画白玻璃渐变；
    - 无壁纸且无 live 时只画三段白玻璃渐变与描边，与旧默认背景观感一致；
    - 子控件（文字 / 输入框 / 按钮 / GL 预览）由 Qt 在本 paintEvent 之后独立绘制，
      不会被本层柔化。
    """
    rect = QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    mode = appearance.glass_mode
    if live is not None:
        # 模态弹窗：使用弹出前抓到的父控件真实背景，坐标以该基准控件为原点。
        live_shot, live_blur, live_ref = live
        shot, blur = live_shot, live_blur
        base_widget = live_ref
    else:
        blur = backdrop.blur_pixmap()
        shot = backdrop.window_pixmap()
        base_widget = reference_window or widget.window()

    # ---- 普通档：不透明白片，壁纸/文字完全被挡住 ----
    if mode == C.GLASS_MODE_NORMAL:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillPath(path, _rgba(C.COLOR_NORMAL_PANEL_RGBA))
        # v1.3.9.1：普通档下背景染色同步覆盖面板（含侧栏白片），整窗跟随变色。
        tint = appearance.bg_tint_rgba()
        if tint is not None:
            r, g, b, _a = tint
            painter.save()
            painter.setClipPath(path)
            painter.fillRect(
                widget.rect(), QColor(r, g, b, C.TINT_NORMAL_PANEL_ALPHA)
            )
            painter.restore()
        pen = painter.pen()
        pen.setColor(_rgba(C.COLOR_NORMAL_BORDER_RGBA))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(path, pen)
        painter.restore()
        return

    # ---- 磨砂 / 通透：先铺面板正后方的背景块 ----
    if shot is not None and mode in (C.GLASS_MODE_FROST, C.GLASS_MODE_CLEAR):
        # 坐标基准：live 时为抓到的父控件，否则为显式传入的主窗口或自身 window()。
        if base_widget is not None:
            # 用全局坐标相减求原点，避免跨顶层窗口时 mapTo 返回陈旧/错误坐标。
            widget_global = widget.mapToGlobal(QPoint(0, 0))
            base_global = base_widget.mapToGlobal(QPoint(0, 0))
            origin = QPoint(
                widget_global.x() - base_global.x(),
                widget_global.y() - base_global.y(),
            )
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setClipPath(path)
            if mode == C.GLASS_MODE_FROST and blur is not None and not blur.isNull():
                # 磨砂：从预模糊整窗缓存按位置映射，不抠块再放大。
                sx = blur.width() / shot.width()
                sy = blur.height() / shot.height()
                # 用浮点矩形，不取整——滚动动画期间亚像素位置精确映射，避免 1px 抖动。
                src_rect = QRectF(
                    origin.x() * sx,
                    origin.y() * sy,
                    widget.width() * sx,
                    widget.height() * sy,
                )
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.drawPixmap(QRectF(widget.rect()), blur, src_rect)
            else:
                # 通透：直接铺清晰壁纸块，不做糊化（下方图片/文字可清楚辨认）。
                src_rect = QRectF(
                    origin.x(), origin.y(), widget.width(), widget.height()
                )
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.drawPixmap(QRectF(widget.rect()), shot, src_rect)
            painter.restore()

    # ---- 白玻璃高光与描边 ----
    if mode == C.GLASS_MODE_CLEAR:
        # 通透档使用统一的低 alpha 白玻璃，不沿用各面板自身较厚的色板。
        grad_top, grad_mid, grad_bottom = (
            C.COLOR_CLEAR_TOP_RGBA,
            C.COLOR_CLEAR_MID_RGBA,
            C.COLOR_CLEAR_BOTTOM_RGBA,
        )
        grad_border = C.COLOR_CLEAR_BORDER_RGBA
    else:
        grad_top, grad_mid, grad_bottom = top_rgba, mid_rgba, bottom_rgba
        grad_border = border_rgba

    gradient = QLinearGradient(0.0, rect.top(), 0.0, rect.bottom())
    gradient.setColorAt(0.0, _rgba(grad_top))
    gradient.setColorAt(0.45 if radius > 15 else 0.5, _rgba(grad_mid))
    gradient.setColorAt(1.0, _rgba(grad_bottom))
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.fillPath(path, gradient)

    pen = painter.pen()
    pen.setColor(_rgba(grad_border))
    pen.setWidthF(1.0)
    painter.setPen(pen)
    painter.strokePath(path, pen)
    painter.restore()
