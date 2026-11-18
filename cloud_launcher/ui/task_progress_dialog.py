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

"""统一竖向下载进度卡片（PCL2 风格，v1.3.13.0）。

所有下载链路——mod / 整合包 / 光影包 / 材质包 / 数据包——都复用这一张竖向卡片，不再画
横向进度条。卡片内容对齐用户第一张参考图：

- 左侧三项统计：总进度 %、下载速度、剩余文件；
- 右侧分阶段勾选清单，用 ✓（已完成）/ ●（进行中）/ ○（待处理）标记；
- 底部红色圆形 X 取消当前任务。

弹窗为无边框透明根 + 一块自绘磨砂 :class:`~cloud_launcher.ui.card_widget.Card`，模态
``exec`` 运行；取消走 ``reject``，同时置位取消标志并发出 ``cancelRequested``，由调用方
中断后台线程。纯 PySide6 + 标准库。
"""
import time

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .card_widget import Card
from .frosted_backdrop import capture_live_backdrop

# 阶段状态。
STATE_DONE = "done"
STATE_RUNNING = "running"
STATE_PENDING = "pending"

_DIALOG_WIDTH = 448
_PHASE_AREA_MAX_HEIGHT = 300


def format_speed(bps: float) -> str:
    """把字节/秒格式化为 B/s、KB/s 或 MB/s。"""
    bps = float(bps or 0.0)
    if bps >= 1024.0 * 1024.0:
        return "%.2f MB/s" % (bps / (1024.0 * 1024.0))
    if bps >= 1024.0:
        return "%.1f KB/s" % (bps / 1024.0)
    return "%d B/s" % int(bps)


class _CancelCircleButton(QPushButton):
    """底部红色圆形取消按钮（自绘，不走 QSS）。"""

    _DIAMETER = 46

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover = False
        self.setFixedSize(self._DIAMETER, self._DIAMETER)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        radius = self._DIAMETER / 2.0 - 1.0

        body = QPainterPath()
        body.addEllipse(QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0))
        alpha = 230 if self._hover else 205
        painter.fillPath(body, QColor(214, 84, 74, alpha))
        pen = QPen(QColor(255, 255, 255, 90))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(body, pen)

        symbol = QPen(QColor(255, 255, 255))
        symbol.setWidthF(2.4)
        symbol.setCapStyle(Qt.RoundCap)
        painter.setPen(symbol)
        gap = 9.0
        painter.drawLine(cx - gap, cy - gap, cx + gap, cy + gap)
        painter.drawLine(cx + gap, cy - gap, cx - gap, cy + gap)
        painter.end()


class TaskProgressDialog(QDialog):
    """竖向下载进度卡片（模态）。"""

    cancelRequested = Signal()

    def __init__(self, title: str, phase_labels: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self._cancelled = False
        self._phase_labels = [str(text) for text in phase_labels]
        self._phase_states = [STATE_PENDING] * len(self._phase_labels)

        # 内容下载（单文件）时由字节增量自行估算速度。
        self._last_bytes = 0
        self._last_time = time.monotonic()
        self._speed = 0.0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.card = Card(title)
        # 独立顶层弹窗：磨砂采样以父窗口为坐标基准，取弹窗正后方的真实渲染。
        self._live_ref = parent.window() if parent is not None else None
        if self._live_ref is not None:
            self.card.set_reference_window(self._live_ref)
        self._live_captured = False
        outer.addWidget(self.card)

        self.card.add_layout(self._build_body())
        self.card.add_layout(self._build_cancel_row())

        self.setFixedWidth(_DIALOG_WIDTH)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        # 显示前抓父窗口真实渲染，让卡片模糊后方内容；无壁纸时也不会只剩半透明白片。
        if not self._live_captured and self._live_ref is not None:
            clear_pix, blur_pix = capture_live_backdrop(self._live_ref)
            self.card.set_live_backdrop(clear_pix, blur_pix, self._live_ref)
            self._live_captured = True
        self._center_over_reference()
        super().showEvent(event)

    def _center_over_reference(self) -> None:
        """居中到父窗口客户区并夹在其边界内，避免卡片越出快照范围出现无内容黑边。"""
        if self._live_ref is None:
            return
        ref = self._live_ref
        client_origin = ref.mapToGlobal(QPoint(0, 0))
        client_w, client_h = ref.width(), ref.height()
        geo = self.frameGeometry()
        width, height = geo.width(), geo.height()
        x = client_origin.x() + (client_w - width) // 2
        y = client_origin.y() + (client_h - height) // 2
        x = max(client_origin.x(), min(x, client_origin.x() + client_w - width))
        y = max(client_origin.y(), min(y, client_origin.y() + client_h - height))
        self.move(x, y)

    # ------------------------------------------------------------------ #
    # 内部布局
    # ------------------------------------------------------------------ #
    def _build_body(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(18)
        body.addLayout(self._build_stats(), 0)
        body.addLayout(self._build_phase_list(), 1)
        return body

    def _build_stats(self) -> QVBoxLayout:
        stats = QVBoxLayout()
        stats.setSpacing(6)

        self._percent_value = self._add_stat(stats, "总进度", "0%")
        self._percent_value.setStyleSheet(
            "font-size:24px;font-weight:700;color:%s;" % C.COLOR_TEXT)
        self._speed_value = self._add_stat(stats, "下载速度", "0 B/s")
        self._remain_value = self._add_stat(stats, "剩余文件", "0")
        stats.addStretch(1)
        return stats

    @staticmethod
    def _add_stat(layout: QVBoxLayout, caption: str, value: str) -> QLabel:
        cap = QLabel(caption)
        cap.setProperty("hintLabel", True)
        layout.addWidget(cap)
        val = QLabel(value)
        val.setStyleSheet("font-size:15px;font-weight:600;color:%s;" % C.COLOR_TEXT)
        layout.addWidget(val)
        return val

    def _build_phase_list(self) -> QVBoxLayout:
        wrapper = QVBoxLayout()
        wrapper.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("taskPhaseScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(_PHASE_AREA_MAX_HEIGHT)

        host = QWidget()
        host.setObjectName("page-container")
        column = QVBoxLayout(host)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)

        self._phase_icons: list[QLabel] = []
        for text in self._phase_labels:
            column.addLayout(self._build_phase_row(text))
        column.addStretch(1)
        scroll.setWidget(host)
        wrapper.addWidget(scroll)
        return wrapper

    def _build_phase_row(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        icon = QLabel("○")
        icon.setFixedSize(18, 18)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:13px;color:%s;" % C.COLOR_TEXT_LIGHT)
        self._phase_icons.append(icon)
        row.addWidget(icon, 0)

        label = QLabel(text)
        label.setStyleSheet("font-size:13px;color:%s;" % C.COLOR_TEXT)
        label.setWordWrap(True)
        row.addWidget(label, 1)
        return row

    def _build_cancel_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self._cancel_button = _CancelCircleButton()
        self._cancel_button.clicked.connect(self._handle_cancel)
        row.addStretch(1)
        row.addWidget(self._cancel_button)
        row.addStretch(1)
        return row

    # ------------------------------------------------------------------ #
    # 对外更新接口
    # ------------------------------------------------------------------ #
    def set_title(self, title: str) -> None:
        self.card.set_title(str(title))

    def set_phase_state(self, index: int, state: str) -> None:
        """把某阶段标记为 done/running/pending，并刷新图标颜色与符号。"""
        if index < 0 or index >= len(self._phase_icons):
            return
        self._phase_states[index] = state
        icon = self._phase_icons[index]
        if state == STATE_DONE:
            icon.setText("✓")
            icon.setStyleSheet("font-size:13px;font-weight:700;color:%s;" % C.COLOR_PRIMARY)
        elif state == STATE_RUNNING:
            icon.setText("●")
            icon.setStyleSheet("font-size:12px;color:%s;" % C.COLOR_PRIMARY)
        else:
            icon.setText("○")
            icon.setStyleSheet("font-size:13px;color:%s;" % C.COLOR_TEXT_LIGHT)

    def mark_phase_running(self, index: int) -> None:
        """进入某阶段：之前的阶段全部置完成，当前置进行中，其余待处理。"""
        for i in range(len(self._phase_icons)):
            if i < index:
                self.set_phase_state(i, STATE_DONE)
            elif i == index:
                self.set_phase_state(i, STATE_RUNNING)
            else:
                self.set_phase_state(i, STATE_PENDING)

    def set_progress(self, percent: float, speed_bps: float | None = None,
                     remaining: int | None = None) -> None:
        """更新总进度（百分比），可选速度与剩余文件。"""
        percent = max(0.0, min(100.0, float(percent or 0.0)))
        self._percent_value.setText("%.2f%%" % percent)
        if speed_bps is not None:
            self._speed = float(speed_bps)
            self._speed_value.setText(format_speed(self._speed))
        if remaining is not None:
            self._remain_value.setText(str(int(remaining)))

    def update_byte_progress(self, done: int, total: int,
                             remaining: int | None = None) -> None:
        """单文件下载：按字节数算百分比，并由字节增量估算瞬时速度。"""
        done = int(done or 0)
        total = int(total or 0)
        now = time.monotonic()
        dt = now - self._last_time
        if dt > 0.05:
            instant = max(0, done - self._last_bytes) / dt
            self._speed = 0.7 * self._speed + 0.3 * instant if self._speed else instant
            self._last_bytes = done
            self._last_time = now
            self._speed_value.setText(format_speed(self._speed))
        percent = (done / total * 100.0) if total > 0 else 0.0
        if remaining is None:
            remaining = 0 if done >= total and total > 0 else 1
        self.set_progress(percent, remaining=remaining)

    def finish_success(self) -> None:
        """全部阶段置完成、进度 100%、剩余 0。"""
        for i in range(len(self._phase_icons)):
            self.set_phase_state(i, STATE_DONE)
        self.set_progress(100.0, speed_bps=0.0, remaining=0)

    def is_cancelled(self) -> bool:
        return self._cancelled

    def hide_cancel(self) -> None:
        self._cancel_button.setEnabled(False)
        self._cancel_button.setVisible(False)

    def _handle_cancel(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        self.cancelRequested.emit()
        self.reject()
