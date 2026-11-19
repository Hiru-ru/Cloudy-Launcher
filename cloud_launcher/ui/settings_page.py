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

"""v1.3.9.2 设置页：顶部「个性化 / 启动 / 桌宠 / AI」四个子标签。

个性化页全部落地，共五块：
1. 玻璃风格三档单选（磨砂玻璃 / 通透 / 普通），每档带小窗样式预览图可点选，
   鼠标悬停 3 秒弹出说明 tooltip；
2. 背景与导航栏七色染色盘（红橙黄绿青蓝紫，可分别选色或取消）；
3. 壁纸导入与选择（缩略图列表，默认项为空白；自定义壁纸最多导入三个）；
4. logo 和名字改写（四档分段 + Logo / 名字两个独立开关，双向同步；
   导入 Logo 行与名字输入框按模式条件显示，默认态什么都不显示）；
5. 背景音乐（只导一首歌、无限循环；只留添加 / 删除按钮，常驻显示当前歌曲文件名）。

另含苹果动画总开关（关闭后开关旋钮与全部 Q 弹动画瞬时完成）。
「启动」标签由 LaunchSettingsPage 承接账号管理 / 版本隔离 / 高级功能；桌宠 / AI 仍为占位骨架。
所有实际改动由 host（MainWindow）执行并落盘，本模块只负责界面与文件选择对话框。
"""
from __future__ import annotations

import math
import os

from PySide6.QtCore import (
    QEasingCurve,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import wallpaper as wallpaper_mod
from ..music_player import current_music_path
from .appearance import appearance
from .card_widget import Card
from .frosted_backdrop import backdrop, cover_rect
from .launch_settings_page import LaunchSettingsPage
from .pet_settings_page import PetSettingsPage
from .ai_settings_page import AiSettingsPage


# ---------------------------------------------------------------------------
# 通用小控件
# ---------------------------------------------------------------------------
class SwitchButton(QAbstractButton):
    """iOS 风格开关（自绘，缩小椭圆胶囊），checkable。

    旋钮位置、轨道颜色、流体形变统一由一个进度值 ``p``（0=关、1=开）驱动：
    - 旋钮中心在关 / 开两端间线性插值，途中按 ``sin(pi*p)`` 横向拉长（iOS 流体形变）；
    - 轨道颜色在关态灰与开态绿之间随进度渐变。

    切换由可靠的 ``toggled`` 信号驱动——真机鼠标点击走 C++ 事件路径，重写的
    ``checkStateSet`` 在该路径下不会被分发（QTest 实证），而 ``toggled`` 在点击、
    ``click()``、``setChecked`` 三条路径都可靠发射，因此不再依赖 checkStateSet。
    动画总开关关闭时瞬时到位、不做形变。
    """

    _W = C.SWITCH_W
    _H = C.SWITCH_H

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.PointingHandCursor)

        margin = C.SWITCH_KNOB_MARGIN
        self._knob_d = self._H - margin * 2
        # 进度 p：0=关，1=开。
        self._p = 0.0
        self._first_show = True

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(C.SWITCH_ANIM_DURATION_MS)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)

        # 单一可靠驱动源：真实点击 / click() / setChecked 都会发射 toggled。
        self.toggled.connect(self._on_toggled)

    # ---- 进度驱动 ----
    @staticmethod
    def _target_p(checked: bool) -> float:
        return 1.0 if checked else 0.0

    def _on_toggled(self, checked: bool) -> None:
        self._animate_to(self._target_p(checked))

    def _animate_to(self, target_p: float) -> None:
        self._anim.stop()
        if not appearance.animations_enabled:
            # 总开关关闭：瞬时落到精确端点，不做形变。
            self._p = float(target_p)
            self.update()
            return
        self._anim.setStartValue(self._p)
        self._anim.setEndValue(float(target_p))
        self._anim.start()

    def _on_anim_value(self, value) -> None:
        self._p = float(value)
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._first_show:
            # 首次显示瞬时校准，避免构建期进度与选中态不一致、动画堆积。
            self._first_show = False
            self._anim.stop()
            self._p = self._target_p(self.isChecked())
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        p = self._p
        margin = C.SWITCH_KNOB_MARGIN
        d = self._knob_d

        # 轨道颜色：关态灰 → 开态绿，随进度逐通道渐变。
        off_rgb = C.SWITCH_OFF_RGB
        on_rgb = C.SWITCH_ON_RGB
        track_rgb = tuple(
            round(off_rgb[i] + (on_rgb[i] - off_rgb[i]) * p) for i in range(3)
        )
        painter.setBrush(QColor(*track_rgb))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self._W, self._H, self._H / 2, self._H / 2)

        # 旋钮中心：关端中心 → 开端中心。
        off_center = margin + d / 2.0
        on_center = self._W - margin - d / 2.0
        center_x = off_center + (on_center - off_center) * p
        # iOS 流体形变：途中横向拉长，两端 sin(pi*p) 归零。
        stretch = C.SWITCH_KNOB_STRETCH_MAX * math.sin(math.pi * p)
        knob_w = d * (1.0 + stretch)
        knob_left = center_x - knob_w / 2.0

        # 白钮下方一层细阴影，做出 iOS 凸起感（随形变一起放大）。
        painter.setBrush(QColor(*C.SWITCH_KNOB_SHADOW_RGBA))
        painter.drawRoundedRect(
            QRectF(knob_left - 1, margin - 1, knob_w + 2, d + 2),
            d / 2.0,
            d / 2.0,
        )
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(
            QRectF(knob_left, margin, knob_w, d), d / 2.0, d / 2.0
        )
        painter.end()


class LabeledSwitch(QWidget):
    """文字标签（左）+ 开关（右）。"""

    toggled = Signal(bool)

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(text)
        label.setProperty("switchLabel", True)
        row.addWidget(label)
        row.addStretch(1)

        self.switch = SwitchButton()
        self.switch.toggled.connect(self.toggled.emit)
        row.addWidget(self.switch)

    def set_value(self, value: bool) -> None:
        self.switch.setChecked(bool(value))

    def value(self) -> bool:
        return self.switch.isChecked()


class SegmentedGroup(QWidget):
    """一排互斥的分段按钮；valueChanged( key )。"""

    valueChanged = Signal(str)

    def __init__(self, options: list[tuple[str, str]], parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._group = QButtonGroup(self)
        self._buttons: dict[str, QPushButton] = {}
        for key, text in options:
            btn = QPushButton(text)
            btn.setProperty("segOption", True)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self.valueChanged.emit(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            row.addWidget(btn, 1)
        row.addStretch(1)

    def set_value(self, key: str) -> None:
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)

    def value(self) -> str:
        checked = self._group.checkedButton()
        for key, btn in self._buttons.items():
            if btn is checked:
                return key
        return ""


# ---------------------------------------------------------------------------
# 玻璃三档样式预览图（摆样子，可点选）
# ---------------------------------------------------------------------------
def _build_sample_background(w: int, h: int) -> QPixmap:
    """预览底图：优先用当前真实壁纸 cover 缩放，否则默认渐变加图形。"""
    pix = QPixmap(w, h)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)
    source = backdrop.source
    if source is not None:
        target = cover_rect(w, h, source.width(), source.height())
        painter.drawPixmap(target, source, QRectF(source.rect()))
    else:
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(C.COLOR_BG_TOP))
        gradient.setColorAt(1.0, QColor(C.COLOR_BG_BOTTOM))
        painter.fillRect(0, 0, w, h, gradient)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(120, 170, 220, 180))
        painter.drawEllipse(QRectF(-10, -8, 40, 40))
        painter.setBrush(QColor(240, 180, 120, 170))
        painter.drawEllipse(QRectF(w - 34, h - 30, 42, 42))
    painter.end()
    return pix


class GlassPreviewButton(QAbstractButton):
    """单个玻璃档位的小窗预览：壁纸底 + 该模式面板效果，可点选。

    鼠标悬停 3 秒后弹出说明性 tooltip（解释该档样式、是否 iOS 风格）。
    """

    def __init__(self, mode: str, parent=None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(C.GLASS_PREVIEW_W, C.GLASS_PREVIEW_H)
        self.toggled.connect(lambda _v: self.update())

        # 悬停 3 秒才出说明；离开即取消。
        self._tip_timer = QTimer(self)
        self._tip_timer.setSingleShot(True)
        self._tip_timer.setInterval(C.GLASS_PREVIEW_TOOLTIP_DELAY_MS)
        self._tip_timer.timeout.connect(self._show_tooltip)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._tip_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._tip_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def _show_tooltip(self) -> None:
        QToolTip.showText(
            self.mapToGlobal(self.rect().center()),
            C.GLASS_PREVIEW_TOOLTIPS.get(self.mode, ""),
            self,
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        canvas_h = self.height() - 22
        canvas_rect = QRectF(0, 0, self.width(), canvas_h)
        path = QPainterPath()
        path.addRoundedRect(canvas_rect, C.GLASS_PREVIEW_RADIUS, C.GLASS_PREVIEW_RADIUS)
        painter.save()
        painter.setClipPath(path)
        sample = _build_sample_background(self.width(), canvas_h)
        painter.drawPixmap(0, 0, sample)
        panel_rect = canvas_rect.adjusted(
            C.GLASS_PREVIEW_PANEL_MARGIN,
            C.GLASS_PREVIEW_PANEL_MARGIN,
            -C.GLASS_PREVIEW_PANEL_MARGIN,
            -C.GLASS_PREVIEW_PANEL_MARGIN,
        )
        self._paint_panel(painter, sample, panel_rect)
        painter.restore()

        if self.isChecked():
            pen = QPen(QColor(*C.GLASS_PREVIEW_RING_RGBA))
            pen.setWidthF(2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(
                canvas_rect.adjusted(1, 1, -1, -1),
                C.GLASS_PREVIEW_RADIUS,
                C.GLASS_PREVIEW_RADIUS,
            )

        painter.setPen(QColor(C.COLOR_TEXT))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, canvas_h, self.width(), 22),
            Qt.AlignCenter,
            C.GLASS_MODE_LABELS[self.mode],
        )
        painter.end()

    def _paint_panel(self, painter: QPainter, sample: QPixmap,
                     panel_rect: QRectF) -> None:
        radius = 7.0
        panel_path = QPainterPath()
        panel_path.addRoundedRect(panel_rect, radius, radius)
        painter.save()
        painter.setClipPath(panel_path)

        if self.mode == C.GLASS_MODE_FROST:
            # 片内磨砂：裁出面板后方底图，降采样再放大，再叠白玻璃渐变。
            crop = sample.copy(
                int(panel_rect.left()), int(panel_rect.top()),
                int(panel_rect.width()), int(panel_rect.height()),
            )
            small = crop.scaled(
                max(1, int(panel_rect.width() / 4)),
                max(1, int(panel_rect.height() / 4)),
                Qt.IgnoreAspectRatio, Qt.FastTransformation,
            )
            painter.drawPixmap(panel_rect, small, QRectF(small.rect()))
            grad = QLinearGradient(0, panel_rect.top(), 0, panel_rect.bottom())
            grad.setColorAt(0, QColor(*C.COLOR_GLASS_TOP_RGBA))
            grad.setColorAt(0.5, QColor(*C.COLOR_GLASS_MID_RGBA))
            grad.setColorAt(1, QColor(*C.COLOR_GLASS_BOTTOM_RGBA))
            painter.fillRect(panel_rect, grad)
            border = C.COLOR_CARD_BORDER_RGBA
            line_color = QColor(255, 255, 255, 205)
        elif self.mode == C.GLASS_MODE_CLEAR:
            # 通透：不糊化，只叠很淡的白玻璃。
            grad = QLinearGradient(0, panel_rect.top(), 0, panel_rect.bottom())
            grad.setColorAt(0, QColor(*C.COLOR_CLEAR_TOP_RGBA))
            grad.setColorAt(0.5, QColor(*C.COLOR_CLEAR_MID_RGBA))
            grad.setColorAt(1, QColor(*C.COLOR_CLEAR_BOTTOM_RGBA))
            painter.fillRect(panel_rect, grad)
            border = C.COLOR_CLEAR_BORDER_RGBA
            line_color = QColor(255, 255, 255, 205)
        else:
            # 普通：不透明白片；有背景染色时面板内同步叠染色。
            painter.fillRect(panel_rect, QColor(*C.COLOR_NORMAL_PANEL_RGBA))
            tint = appearance.bg_tint_rgba()
            if tint is not None:
                r, g, b, _a = tint
                painter.fillRect(
                    panel_rect, QColor(r, g, b, C.TINT_NORMAL_PANEL_ALPHA)
                )
            border = C.COLOR_NORMAL_BORDER_RGBA
            line_color = QColor(178, 194, 206, 220)

        # 模拟内容线（小方块 + 三条横线），仿原型红色手绘窗。
        painter.setPen(Qt.NoPen)
        painter.setBrush(line_color)
        left = panel_rect.left() + 8
        top = panel_rect.top() + 8
        painter.drawRoundedRect(QRectF(left, top, 9, 9), 2, 2)
        painter.drawRoundedRect(
            QRectF(left + 14, top + 1, panel_rect.width() - 26, 4), 2, 2
        )
        painter.drawRoundedRect(
            QRectF(left, top + 16, panel_rect.width() - 40, 4), 2, 2
        )
        painter.drawRoundedRect(
            QRectF(left, panel_rect.bottom() - 10, panel_rect.width() - 20, 4),
            2, 2,
        )
        painter.restore()

        pen = QPen(QColor(*border))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(panel_rect, radius, radius)


class GlassPreviewGroup(QWidget):
    """三档玻璃样式预览组（单选）；valueChanged 发出 mode。"""

    valueChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        self._group = QButtonGroup(self)
        self._buttons: dict[str, GlassPreviewButton] = {}
        for mode in C.GLASS_MODE_KEYS:
            btn = GlassPreviewButton(mode)
            self._group.addButton(btn)
            row.addWidget(btn)
            self._buttons[mode] = btn
        row.addStretch(1)
        self._group.buttonClicked.connect(
            lambda b: self.valueChanged.emit(b.mode)
        )

    def set_value(self, mode: str) -> None:
        btn = self._buttons.get(mode)
        if btn is not None:
            btn.setChecked(True)

    def value(self) -> str:
        checked = self._group.checkedButton()
        if checked is None:
            return ""
        return checked.mode

    def refresh(self) -> None:
        for btn in self._buttons.values():
            btn.update()


class SwatchButton(QAbstractButton):
    """圆形色块按钮（checkable）；is_none=True 时画「无」（白底斜杠）。"""

    _SIZE = 30

    def __init__(self, color_key: str, is_none: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._key = C.TINT_NONE if is_none else color_key
        self._is_none = is_none
        self.setCheckable(True)
        self.setFixedSize(self._SIZE, self._SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(lambda _v: self.update())

    @property
    def color_key(self) -> str:
        return self._key

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(2, 2, -2, -2)

        if self._is_none:
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QColor(180, 192, 202))
            painter.drawEllipse(rect)
            painter.setPen(QColor(220, 90, 90))
            painter.drawLine(rect.left() + 5, rect.bottom() - 5,
                             rect.right() - 5, rect.top() + 5)
        else:
            r, g, b = C.TINT_COLORS[self._key]
            painter.setBrush(QColor(r, g, b))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(rect)

        if self.isChecked():
            pen = painter.pen()
            pen.setColor(QColor(C.COLOR_PRIMARY_DARK))
            pen.setWidthF(2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        painter.end()


class SwatchRow(QWidget):
    """「无」+ 七个色块的互斥组；valueChanged( key )。"""

    valueChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._group = QButtonGroup(self)
        self._buttons: dict[str, SwatchButton] = {}
        none_btn = SwatchButton("", is_none=True)
        self._group.addButton(none_btn)
        self._buttons[C.TINT_NONE] = none_btn
        row.addWidget(none_btn)
        none_btn.clicked.connect(lambda: self.valueChanged.emit(C.TINT_NONE))

        for key in C.TINT_KEYS:
            btn = SwatchButton(key)
            self._group.addButton(btn)
            self._buttons[key] = btn
            row.addWidget(btn)
            btn.clicked.connect(lambda _=False, k=key: self.valueChanged.emit(k))
        row.addStretch(1)

    def set_value(self, key: str) -> None:
        btn = self._buttons.get(key) or self._buttons[C.TINT_NONE]
        btn.setChecked(True)


class MusicHoverRow(QWidget):
    """音乐文件行：常驻显示当前歌曲文件名；只留添加 / 删除按钮。

    无歌曲时常驻显示「添加音乐」按钮；有歌曲时悬停浮现「重新添加 / 删除」。
    """

    addRequested = Signal()
    deleteRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)

        self._name = QLabel("")
        self._name.setProperty("sectionHint", True)
        row.addWidget(self._name)
        row.addStretch(1)

        # 无歌曲时的常驻添加按钮。
        self._add_btn = QPushButton("添加音乐")
        self._add_btn.setProperty("ghostAction", True)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.clicked.connect(self.addRequested.emit)
        row.addWidget(self._add_btn)

        self._readd_btn = QPushButton("重新添加")
        self._readd_btn.setProperty("ghostAction", True)
        self._readd_btn.setCursor(Qt.PointingHandCursor)
        self._readd_btn.clicked.connect(self.addRequested.emit)
        row.addWidget(self._readd_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setProperty("ghostAction", True)
        self._delete_btn.setProperty("danger", True)
        self._delete_btn.setCursor(Qt.PointingHandCursor)
        self._delete_btn.clicked.connect(self.deleteRequested.emit)
        row.addWidget(self._delete_btn)

        self._hover_buttons = (self._readd_btn, self._delete_btn)
        self._set_hover_visible(False)

    def _set_hover_visible(self, visible: bool) -> None:
        if visible:
            self._readd_btn.setVisible(True)
            self._delete_btn.setVisible(True)
        else:
            for btn in self._hover_buttons:
                btn.setVisible(False)

    def enterEvent(self, event) -> None:  # noqa: N802
        if self._has_song:
            self._set_hover_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._set_hover_visible(False)
        super().leaveEvent(event)

    def refresh(self, has_song: bool, display_name: str = "") -> None:
        """根据当前音乐状态刷新文案与按钮。

        display_name 为导入时记录的原始文件名（config music_file）；
        缺失时回退到磁盘上的 bgm 文件名。
        """
        self._has_song = has_song
        if has_song:
            shown = display_name or os.path.basename(current_music_path())
            self._name.setText(f"♪ {shown}")
            self._add_btn.setVisible(False)
            self._set_hover_visible(False)
        else:
            self._name.setText("")
            self._set_hover_visible(False)
            self._add_btn.setVisible(True)


# ---------------------------------------------------------------------------
# 个性化页
# ---------------------------------------------------------------------------
class PersonalizationPage(QWidget):
    """个性化页全部内容（滚动卡片）。"""

    def __init__(self, config, host, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._host = host
        self.setObjectName("personalization-page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 右侧宽滚动条彻底删除：永不显示，滚轮仍可滚动。
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_widget = QWidget()
        list_widget.setObjectName("settingsList")
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(12)

        self._build_glass_section()
        self._build_tint_section()
        self._build_wallpaper_section()
        self._build_brand_section()
        self._build_music_section()
        self._build_animation_section()
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

    # ---- 1) 玻璃风格 ----
    def _build_glass_section(self) -> None:
        card = Card("玻璃风格")
        self._glass_group = GlassPreviewGroup()
        self._glass_group.set_value(self._config.get("glass_mode"))
        self._glass_group.valueChanged.connect(self._host.set_glass_mode)
        card.add_widget(self._glass_group)
        self._list_layout.addWidget(card)

    # ---- 2) 七色染色 ----
    def _build_tint_section(self) -> None:
        card = Card("背景和导航栏调色盘")

        self._bg_row = SwatchRow()
        self._bg_row.set_value(self._config.get("bg_tint"))
        self._bg_row.valueChanged.connect(self._host.set_bg_tint)
        card.add_widget(self._bg_row)

        self._nav_row = SwatchRow()
        self._nav_row.set_value(self._config.get("nav_tint"))
        self._nav_row.valueChanged.connect(self._host.set_nav_tint)
        card.add_widget(self._nav_row)
        self._list_layout.addWidget(card)

    # ---- 3) 壁纸导入与选择 ----
    def _build_wallpaper_section(self) -> None:
        card = Card("壁纸导入和选择")

        action_row = QWidget()
        action_layout = QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        import_btn = QPushButton("导入壁纸")
        import_btn.setProperty("ghostAction", True)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._on_import_wallpaper)
        action_layout.addWidget(import_btn)
        action_layout.addStretch(1)
        card.add_widget(action_row)

        self._wallpaper_group = QButtonGroup(self)
        self._wallpaper_group.setExclusive(True)
        self._wallpaper_thumbs: dict[str, QPushButton] = {}

        self._thumbs_row = QWidget()
        self._thumbs_layout = QHBoxLayout(self._thumbs_row)
        self._thumbs_layout.setContentsMargins(0, 0, 0, 0)
        self._thumbs_layout.setSpacing(8)
        card.add_widget(self._thumbs_row)
        self._reload_wallpaper_thumbs()
        self._list_layout.addWidget(card)

    def _reload_wallpaper_thumbs(self) -> None:
        while self._thumbs_layout.count():
            item = self._thumbs_layout.takeAt(0)
            if item.widget() is not None:
                self._wallpaper_group.removeButton(item.widget())
                item.widget().deleteLater()
        self._wallpaper_thumbs.clear()

        # 默认档：空白缩略图（不渲染任何壁纸画面，避免与导入壁纸重复）。
        self._add_thumb(C.WALLPAPER_DEFAULT_KEY, "默认（空白）", None)
        for filename in wallpaper_mod.list_wallpapers():
            pix, _ = wallpaper_mod.load_named_wallpaper(filename)
            self._add_thumb(filename, filename, pix)
        self._thumbs_layout.addStretch(1)

        selected = self._config.get("wallpaper_file", C.WALLPAPER_DEFAULT_KEY)
        btn = self._wallpaper_thumbs.get(selected)
        if btn is not None:
            btn.setChecked(True)

    def _add_thumb(self, key: str, tooltip: str, pix: QPixmap | None) -> None:
        btn = QPushButton()
        btn.setObjectName("wallpaperThumb")
        btn.setCheckable(True)
        btn.setFixedSize(QSize(76, 56))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip)
        if pix is not None and not pix.isNull():
            btn.setIcon(QIcon(pix))
            btn.setIconSize(QSize(70, 50))
        btn.clicked.connect(lambda _=False, k=key: self._host.set_wallpaper_selection(k))
        self._wallpaper_group.addButton(btn)
        self._wallpaper_thumbs[key] = btn
        self._thumbs_layout.addWidget(btn)

    def _on_import_wallpaper(self) -> None:
        # 自定义壁纸最多三个，达到上限不再弹文件选择框。
        if len(wallpaper_mod.list_wallpapers()) >= C.WALLPAPER_MAX_COUNT:
            return
        path, _ = self._get_open_file(
            "选择壁纸图片",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        filename = self._host.import_wallpaper_file(path)
        if filename:
            self._reload_wallpaper_thumbs()

    def refresh_wallpaper_thumbs(self) -> None:
        """外部（host）切换壁纸后同步选中态。"""
        self._reload_wallpaper_thumbs()

    # ---- 4) Logo / 名字显隐 ----
    def _build_brand_section(self) -> None:
        card = Card("Logo 和名字")

        # 两个开关是显隐语义：Logo 关闭=整个隐藏 Logo；名字关闭=隐藏名字。
        self._logo_switch = LabeledSwitch("Logo")
        self._logo_switch.toggled.connect(self._on_logo_visible_toggled)
        card.add_widget(self._logo_switch)

        self._name_switch = LabeledSwitch("名字")
        self._name_switch.toggled.connect(self._on_name_visible_toggled)
        card.add_widget(self._name_switch)

        # 导入 Logo（替换内容，常驻显示，与显隐开关相互独立）。
        logo_row = QWidget()
        logo_layout = QHBoxLayout(logo_row)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addStretch(1)
        logo_btn = QPushButton("导入 Logo")
        logo_btn.setProperty("ghostAction", True)
        logo_btn.setCursor(Qt.PointingHandCursor)
        logo_btn.clicked.connect(self._on_import_logo)
        logo_layout.addWidget(logo_btn)
        card.add_widget(logo_row)

        # 名字输入框（替换内容，常驻显示）。
        name_row = QWidget()
        name_layout = QHBoxLayout(name_row)
        name_layout.setContentsMargins(0, 0, 0, 0)
        self._name_field = QLineEdit()
        self._name_field.setObjectName("customNameField")
        self._name_field.setText(self._config.get("custom_name", ""))
        self._name_field.setPlaceholderText("输入新的名字")
        self._name_field.editingFinished.connect(
            lambda: self._host.set_custom_name(self._name_field.text())
        )
        name_layout.addWidget(self._name_field, 1)
        card.add_widget(name_row)

        # 构建期用 guard 静默回填显隐，避免首次 set_value 发射 toggled 触发 host。
        self._brand_sync_guard = True
        try:
            self._logo_switch.set_value(
                self._config.get("logo_visible", C.LOGO_VISIBLE_DEFAULT)
            )
            self._name_switch.set_value(
                self._config.get("name_visible", C.NAME_VISIBLE_DEFAULT)
            )
        finally:
            self._brand_sync_guard = False

        self._list_layout.addWidget(card)

    def _on_logo_visible_toggled(self, visible: bool) -> None:
        """Logo 开关：关闭即整个隐藏 Logo。"""
        if self._brand_sync_guard:
            return
        self._host.set_logo_visible(bool(visible))

    def _on_name_visible_toggled(self, visible: bool) -> None:
        """名字开关：关闭即隐藏名字。"""
        if self._brand_sync_guard:
            return
        self._host.set_name_visible(bool(visible))

    def _on_import_logo(self) -> None:
        path, _ = self._get_open_file(
            "选择 logo 图片",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.ico)",
        )
        if not path:
            return
        self._host.import_logo_file(path)

    def refresh_brand(self) -> None:
        """外部（host）改动后回填名字输入框与两个显隐开关。"""
        self._name_field.setText(self._config.get("custom_name", ""))
        self._brand_sync_guard = True
        try:
            self._logo_switch.set_value(
                self._config.get("logo_visible", C.LOGO_VISIBLE_DEFAULT)
            )
            self._name_switch.set_value(
                self._config.get("name_visible", C.NAME_VISIBLE_DEFAULT)
            )
        finally:
            self._brand_sync_guard = False

    # ---- 5) 背景音乐 ----
    def _build_music_section(self) -> None:
        card = Card("背景音乐设置")

        self._music_row = MusicHoverRow()
        self._music_row.addRequested.connect(self._on_add_music)
        self._music_row.deleteRequested.connect(self._host.remove_music_file)
        card.add_widget(self._music_row)

        self.refresh_music()
        self._list_layout.addWidget(card)

    def _on_add_music(self) -> None:
        path, _ = self._get_open_file(
            "选择一首背景音乐",
            "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac)",
        )
        if path:
            self._host.add_music_file(path)

    def refresh_music(self) -> None:
        has_song = bool(current_music_path())
        # music_file 记录导入时的原始文件名，用于歌名展示。
        display_name = self._config.get("music_file", "") or ""
        self._music_row.refresh(has_song, display_name)

    # ---- 6) 动画总开关 ----
    def _build_animation_section(self) -> None:
        card = Card("动画效果")

        self._anim_switch = LabeledSwitch("苹果动画（Q弹效果）")
        self._anim_switch.set_value(self._config.get("animations_enabled", True))
        self._anim_switch.toggled.connect(self._host.set_animations_enabled)
        card.add_widget(self._anim_switch)

        self._list_layout.addWidget(card)

    def refresh_animations(self) -> None:
        self._anim_switch.set_value(
            self._config.get("animations_enabled", True)
        )

    # ---- 文件选择对话框 ----
    def _get_open_file(self, caption: str, flt: str) -> tuple[str, str]:
        from PySide6.QtWidgets import QFileDialog

        dialog = QFileDialog(self.window(), caption)
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec() != QFileDialog.Accepted:
            return "", ""
        names = dialog.selectedFiles()
        if not names:
            return "", ""
        return names[0], dialog.selectedNameFilter()


# ---------------------------------------------------------------------------
# 设置页（四标签）
# ---------------------------------------------------------------------------
class SettingsPage(QWidget):
    """设置页：顶部子标签栏 + 页面栈。"""

    def __init__(self, config, host, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settings-page")
        self._config = config
        self._host = host

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # 子标签栏
        tab_bar = QWidget()
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(8)

        self._tab_group = QButtonGroup(self)
        self._tab_buttons: dict[str, QPushButton] = {}
        tab_defs = [
            ("personalization", "个性化"),
            ("launch", "启动"),
            ("pet", "桌宠"),
            ("ai", "AI"),
        ]
        for key, text in tab_defs:
            btn = QPushButton(text)
            btn.setProperty("categoryTab", True)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            # 按比例缩小、不铺满：固定高度的椭圆胶囊，宽度按内容走。
            btn.setFixedHeight(C.SETTINGS_TAB_H)
            self._tab_group.addButton(btn)
            self._tab_buttons[key] = btn
            tab_layout.addWidget(btn)
        tab_layout.addStretch(1)
        root.addWidget(tab_bar)

        # 页面栈
        self.stack = QStackedWidget()
        self.personalization_page = PersonalizationPage(config, host)
        self.launch_page = LaunchSettingsPage(config, host)
        self.stack.addWidget(self.personalization_page)
        self.stack.addWidget(self.launch_page)
        # 桌宠：独立 APP 导入 + 皮肤口径 + 启停；host 为 MainWindow（需访问 session）。
        self.pet_page = PetSettingsPage(config, host)
        self.stack.addWidget(self.pet_page)
        self.ai_page = AiSettingsPage(config, host)
        self.stack.addWidget(self.ai_page)
        root.addWidget(self.stack, 1)

        first_btn = self._tab_buttons["personalization"]
        first_btn.setChecked(True)
        first_btn.setProperty("categoryActive", True)
        self._tab_group.buttonClicked.connect(self._on_tab_clicked)

    def _on_tab_clicked(self, button: QAbstractButton) -> None:
        for index, key in enumerate(
            ("personalization", "launch", "pet", "ai")
        ):
            if self._tab_buttons[key] is button:
                # 同步 categoryActive 属性，驱动选中态 QSS。
                for k, btn in self._tab_buttons.items():
                    active = k == key
                    btn.setProperty("categoryActive", active)
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
                self.stack.setCurrentIndex(index)
                if key == "launch":
                    self.launch_page.refresh()
                return

    # ---- 供 host 调用的转发 ----
    def refresh_wallpaper(self) -> None:
        self.personalization_page.refresh_wallpaper_thumbs()

    def refresh_brand(self) -> None:
        self.personalization_page.refresh_brand()

    def refresh_music(self) -> None:
        self.personalization_page.refresh_music()

    def refresh_animations(self) -> None:
        self.personalization_page.refresh_animations()

    def refresh_previews(self) -> None:
        self.personalization_page._glass_group.refresh()
