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

"""v1.2.12.0 单例下载状态浮层面板：顶部居中铺开 / 右下角收起丝滑动画、透明毛玻璃、5 秒空闲
自动收回；展开态底部居中加大叉取消按钮（取消当前下载任务），右上角小 X 仅收起面板。

交互口径（用户语音定稿，参考 iOS 通知横幅与「任务管理」安装面板）：

- **只出现一次**：整个下载页生命周期内只创建这一个面板实例；多次点击不同版本下载时复用
  同一面板，切换任务内容，不重复弹窗、不销毁重建。
- **铺开**：点击下载按钮后面板从收起位置丝滑铺开为顶部居中大面板（OutCubic 缓动），透明
  毛玻璃片内局部磨砂，不挂 QGraphicsBlurEffect。
- **自动收回**：展开后 5 秒内鼠标未进入 / 未点击面板，自动丝滑收回贴到右下角下载入口小
  胶囊；后台下载不中断，进度继续在小胶囊上显示。
- **重新铺开**：点击右下角小入口，面板再次丝滑全面铺开；鼠标进入面板即暂停空闲计时，
  离开后重新计时。
- **取消任务**：展开态底部居中的大叉按钮用于取消当前下载；右上角小 X 只收起浮层，不中断
  后台任务。
- **信息形态**（对齐任务管理安装面板参考图）：左侧竖排总进度百分比、下载速度、剩余文件
  数；右侧五步分步清单（完成打勾 ✓ / 进行中圆点 / 待办空心 / 本轮骨架跳过横线）；底部一条
  细进度条。

面板作为下载页直接子浮层，不参与父布局；几何由本类按顶部居中 / 右下角两套锚点动画驱动。
"""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .appearance import appearance
from .frosted_backdrop import paint_frosted_panel


def format_speed(bps: float) -> str:
    """把实时字节速度格式化为 B/s / KB/s / MB/s；非数值回退 0 B/s。"""
    try:
        value = max(0.0, float(bps))
    except (TypeError, ValueError):
        return "0 B/s"
    if value < 1024:
        return f"{value:.0f} B/s"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB/s"
    return f"{value / (1024 * 1024):.2f} MB/s"


# 步骤状态对应的图标符号与颜色键（颜色在 QSS / 文字属性里区分，这里只出符号）。
_STEP_ICON = {
    C.STEP_DONE: "✓",
    C.STEP_RUNNING: "●",
    C.STEP_PENDING: "○",
    C.STEP_SKIPPED: "–",
}


class DownloadPanel(QFrame):
    """下载任务单例浮层：展开顶部居中大面板 + 收起右下角小胶囊，两套形态共用一块毛玻璃面板。"""

    #: 底部大叉按钮：请求取消当前下载任务（由下载页转发给 worker 中断）。
    cancelRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadPanel")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._mode = "collapsed"  # collapsed | expanded
        self._running = False
        self._finished_ok = False
        self._version_id = ""
        self._percent = 0.0

        # 空闲自动收起定时器：单次触发，鼠标进入 / 点击后重置。
        # 任务结束（成功 / 失败 / 取消）后自动整体隐藏的倒计时；下载进行中不启动。
        self._autohide_timer = QTimer(self)
        self._autohide_timer.setSingleShot(True)
        self._autohide_timer.setInterval(C.DOWNLOAD_PANEL_AUTOHIDE_MS)
        self._autohide_timer.timeout.connect(self.dismiss)

        self._geom_anim: QPropertyAnimation | None = None

        self._build_expanded_body()
        self._build_collapsed_body()

        # 初始收起态几何、隐藏；start() 时才 show()。
        self.setGeometry(self._collapsed_rect())
        self._expanded_body.hide()
        self.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        """两套形态的内部 body 都铺满浮层自身；浮层不参与父布局，必须手动同步尺寸，
        否则 body 停留在 sizeHint 宽度，右列步骤文字会被自身裁切。"""
        super().resizeEvent(event)
        self._expanded_body.resize(self.size())
        self._collapsed_body.resize(self.size())

    # ------------------------------------------------------------------ #
    # 两套内部布局
    # ------------------------------------------------------------------ #
    def _build_expanded_body(self) -> None:
        body = QFrame(self)
        body.setObjectName("downloadPanelExpanded")
        body.setAttribute(Qt.WA_TranslucentBackground, True)
        self._expanded_body = body

        root = QVBoxLayout(body)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # 标题行：版本标题 + 右上角小 X（仅收起面板，不取消任务）。
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)
        self._title_label = QLabel("准备下载…")
        self._title_label.setObjectName("downloadPanelTitle")
        title_row.addWidget(self._title_label, 1)

        self._collapse_button = QPushButton("✕")
        self._collapse_button.setObjectName("downloadPanelCollapseBtn")
        self._collapse_button.setFixedSize(26, 26)
        self._collapse_button.setCursor(Qt.PointingHandCursor)
        self._collapse_button.clicked.connect(self._on_close_clicked)
        title_row.addWidget(self._collapse_button)
        root.addLayout(title_row)

        # 主体两列：左侧总进度 / 速度 / 剩余文件；右侧五步清单。
        main_row = QHBoxLayout()
        main_row.setSpacing(18)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(12)
        self._percent_label = self._build_stat(left_col, "总进度", "0.00%", "downloadPanelPercent")
        self._speed_label = self._build_stat(left_col, "下载速度", "0 B/s", "downloadPanelSpeed")
        self._remain_label = self._build_stat(left_col, "剩余文件", "0", "downloadPanelRemain")
        main_row.addLayout(left_col, 1)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(8)
        self._step_rows: list[dict] = []
        for index, title in enumerate(C.DOWNLOAD_STEP_TITLES):
            row = self._build_step_row(title)
            right_col.addWidget(row["frame"])
            self._step_rows.append(row)
        main_row.addLayout(right_col, 1.2)
        root.addLayout(main_row, 1)

        # 底部细进度条。
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("downloadPanelBar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        root.addWidget(self._progress_bar)

        # 底部居中大叉取消按钮：仅任务进行中可见；点击请求中断当前下载（不只是收起面板）。
        cancel_row = QHBoxLayout()
        cancel_row.setContentsMargins(0, 0, 0, 0)
        cancel_row.addStretch(1)
        self._cancel_button = QPushButton("✕")
        self._cancel_button.setObjectName("downloadPanelCancelBtn")
        self._cancel_button.setFixedSize(40, 40)
        self._cancel_button.setCursor(Qt.PointingHandCursor)
        self._cancel_button.setToolTip("取消下载")
        self._cancel_button.clicked.connect(self.cancelRequested.emit)
        cancel_row.addWidget(self._cancel_button)
        cancel_row.addStretch(1)
        root.addLayout(cancel_row)

    @staticmethod
    def _build_stat(parent: QVBoxLayout, caption: str, value: str,
                    value_object: str) -> QLabel:
        stat = QVBoxLayout()
        stat.setContentsMargins(0, 0, 0, 0)
        stat.setSpacing(2)
        cap = QLabel(caption)
        cap.setObjectName("downloadPanelStatCaption")
        stat.addWidget(cap)
        value_label = QLabel(value)
        value_label.setObjectName(value_object)
        stat.addWidget(value_label)
        parent.addLayout(stat)
        return value_label

    def _build_step_row(self, title: str) -> dict:
        frame = QFrame()
        frame.setObjectName("downloadStepRow")
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        icon = QLabel(_STEP_ICON[C.STEP_PENDING])
        icon.setObjectName("downloadStepIcon")
        icon.setFixedWidth(20)
        icon.setAlignment(Qt.AlignCenter)
        text = QLabel(title)
        text.setObjectName("downloadStepText")
        row.addWidget(icon)
        row.addWidget(text, 1)
        return {"frame": frame, "icon": icon, "text": text,
                "state": C.STEP_PENDING, "base_title": title}

    def _build_collapsed_body(self) -> None:
        body = QFrame(self)
        body.setObjectName("downloadPanelCollapsed")
        body.setAttribute(Qt.WA_TranslucentBackground, True)
        self._collapsed_body = body

        row = QHBoxLayout(body)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        self._collapsed_icon = QLabel("⬇")
        self._collapsed_icon.setObjectName("downloadCollapsedIcon")
        row.addWidget(self._collapsed_icon)

        self._collapsed_name = QLabel("下载中")
        self._collapsed_name.setObjectName("downloadCollapsedName")
        row.addWidget(self._collapsed_name, 1)

        self._collapsed_percent = QLabel("0%")
        self._collapsed_percent.setObjectName("downloadCollapsedPercent")
        row.addWidget(self._collapsed_percent)

    # ------------------------------------------------------------------ #
    # 几何锚点
    # ------------------------------------------------------------------ #
    def _parent_size(self) -> tuple[int, int]:
        parent = self.parentWidget()
        if parent is None:
            return C.WINDOW_WIDTH, C.WINDOW_HEIGHT
        return parent.width(), parent.height()

    def _expanded_rect(self) -> QRect:
        pw, ph = self._parent_size()
        w = C.DOWNLOAD_PANEL_EXPANDED_WIDTH
        h = C.DOWNLOAD_PANEL_EXPANDED_HEIGHT
        # 展开态：顶部水平居中铺开（对齐 iOS 顶部通知横幅参考图）。
        x = max(0, (pw - w) // 2)
        y = C.DOWNLOAD_PANEL_MARGIN_TOP
        return QRect(x, y, w, h)

    def _collapsed_rect(self) -> QRect:
        pw, ph = self._parent_size()
        w = C.DOWNLOAD_PANEL_COLLAPSED_WIDTH
        h = C.DOWNLOAD_PANEL_COLLAPSED_HEIGHT
        x = pw - w - C.DOWNLOAD_PANEL_MARGIN_RIGHT
        y = ph - h - C.DOWNLOAD_PANEL_MARGIN_BOTTOM
        return QRect(max(0, x), max(0, y), w, h)

    def reposition(self) -> None:
        """父容器尺寸变化后按当前形态重新锚定右下角；动画未运行时直接贴合。"""
        target = self._expanded_rect() if self._mode == "expanded" else self._collapsed_rect()
        if self._geom_anim is not None and self._geom_anim.state() == QPropertyAnimation.Running:
            self._geom_anim.setEndValue(target)
        else:
            self.setGeometry(target)

    # ------------------------------------------------------------------ #
    # 铺开 / 收回动画
    # ------------------------------------------------------------------ #
    def _animate_geometry(self, target: QRect) -> None:
        if self._geom_anim is not None:
            try:
                self._geom_anim.stop()
            except RuntimeError:
                pass
        if not appearance.animations_enabled:
            # 总开关关闭：几何瞬时到位，不播放展开/收起动画。
            self._geom_anim = None
            self.setGeometry(target)
            return
        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(C.DOWNLOAD_PANEL_ANIM_MS)
        anim.setStartValue(self.geometry())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._geom_anim = anim
        anim.start()

    def expand(self) -> None:
        """从收起小胶囊丝滑铺开为大面板；任务结束后重新启动自动隐藏倒计时。"""
        if self._mode == "expanded":
            self._arm_autohide()
            return
        self._mode = "expanded"
        self._collapsed_body.hide()
        self._expanded_body.show()
        self._expanded_body.resize(self.size())
        self._animate_geometry(self._expanded_rect())
        self.raise_()
        # 展开后若任务已结束，重新启动自动隐藏倒计时；下载进行中不启动。
        self._arm_autohide()

    def collapse(self) -> None:
        """丝滑收回为右下角小胶囊入口；后台下载继续，不中断。"""
        if self._mode == "collapsed":
            return
        self._autohide_timer.stop()
        self._mode = "collapsed"
        self._expanded_body.hide()
        self._collapsed_body.show()
        self._collapsed_body.resize(self.size())
        self._animate_geometry(self._collapsed_rect())
        self.raise_()
        # 收起为小胶囊后，任务结束仍按倒计时自动隐藏，下载中保持常驻。
        self._arm_autohide()

    def dismiss(self) -> None:
        """手动点叉 / 倒计时结束：完全隐藏整个面板（含右下角小胶囊）。"""
        self._autohide_timer.stop()
        self.hide()

    def _arm_autohide(self) -> None:
        """任务结束后启动自动隐藏倒计时；下载进行中不启动，保证下载中不自动消失。"""
        self._autohide_timer.stop()
        if not self._running:
            self._autohide_timer.start()

    def _on_close_clicked(self) -> None:
        """右上角小 X：下载中收起为小胶囊（不中断下载）；任务结束后立即整体隐藏。"""
        if self._running:
            self.collapse()
        else:
            self.dismiss()

    # ------------------------------------------------------------------ #
    # 鼠标交互：进入暂停倒计时、离开重新计时
    # ------------------------------------------------------------------ #
    def enterEvent(self, event) -> None:  # noqa: N802
        # 鼠标进入暂停自动隐藏（下载中倒计时本来就没启动）。
        self._autohide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        # 离开面板：任务结束重新计时，下载中不自动隐藏。
        self._arm_autohide()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            # v1.2.12.2：收起态右下角小胶囊被点击时重新铺开面板——点小入口没有任何反应，
            # 用户因此打不开进度面板、找不到取消按钮。
            if self._mode == "collapsed":
                self.expand()
                return
        super().mousePressEvent(event)

    # ------------------------------------------------------------------ #
    # 任务状态接入（由下载页 worker 信号驱动）
    # ------------------------------------------------------------------ #
    def start(self, version_id: str) -> None:
        """开始新任务：重置步骤与进度，铺开面板；单例复用，不重复创建。"""
        self._version_id = str(version_id or "")
        self._running = True
        self._finished_ok = False
        self._percent = 0.0
        self._title_label.setText(f"{self._version_id} 安装中")
        self._collapsed_name.setText(self._version_id or "下载中")
        self._collapsed_icon.setText("⬇")
        self._percent_label.setText("0.00%")
        self._speed_label.setText("0 B/s")
        self._remain_label.setText("0")
        self._progress_bar.setValue(0)
        self._collapsed_percent.setText("0%")
        self._cancel_button.show()
        for row in self._step_rows:
            self._set_step_row(row, C.STEP_PENDING, 0.0)
        self.show()
        self.expand()

    def update_progress(self, data: dict) -> None:
        """刷新总进度 / 速度 / 剩余文件；data 来自下载 worker 的 progress 信号。"""
        percent = float(data.get("percent") or 0.0)
        self._percent = percent
        self._percent_label.setText(f"{percent:.2f}%")
        self._speed_label.setText(format_speed(data.get("speed_bps") or 0))
        self._remain_label.setText(str(int(data.get("remaining_files") or 0)))
        self._progress_bar.setValue(int(round(percent)))
        self._collapsed_percent.setText(f"{int(round(percent))}%")

    def set_step(self, index: int, state: str, percent: float = 0.0) -> None:
        """更新五步清单中某一步的状态与进度。"""
        if 0 <= index < len(self._step_rows):
            self._set_step_row(self._step_rows[index], state, percent)

    @staticmethod
    def _set_step_row(row: dict, state: str, percent: float) -> None:
        row["state"] = state
        row["icon"].setText(_STEP_ICON.get(state, _STEP_ICON[C.STEP_PENDING]))
        row["icon"].setProperty("stepState", state)
        row["text"].setProperty("stepState", state)
        if state == C.STEP_RUNNING:
            row["text"].setText(f"{row['base_title']} 进行中…")
        else:
            row["text"].setText(row["base_title"])
        for widget in (row["icon"], row["text"]):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def mark_success(self, version_id: str) -> None:
        """任务完成：标题改为安装完成，进行中步骤收尾，启动 10 秒自动隐藏倒计时。"""
        self._running = False
        self._finished_ok = True
        self._cancel_button.hide()
        self._version_id = str(version_id or self._version_id)
        self._title_label.setText(f"{self._version_id} 安装完成")
        self._collapsed_name.setText("已安装")
        self._collapsed_icon.setText("✓")
        self._percent_label.setText("100.00%")
        self._progress_bar.setValue(100)
        self._collapsed_percent.setText("100%")
        for row in self._step_rows:
            if row["state"] == C.STEP_RUNNING:
                self._set_step_row(row, C.STEP_DONE, 100.0)
        self._arm_autohide()

    def mark_failed(self, reason: str = "") -> None:
        """任务失败：标题改为下载失败，保持展开便于查看原因，并启动自动隐藏倒计时。

        鼠标进入面板会暂停倒计时，用户可从容阅读失败原因，不会看一半消失。
        """
        self._running = False
        self._finished_ok = False
        self._cancel_button.hide()
        self._autohide_timer.stop()
        self._title_label.setText(f"{self._version_id} 下载失败")
        self._collapsed_name.setText("下载失败")
        self._collapsed_icon.setText("✕")
        for row in self._step_rows:
            if row["state"] == C.STEP_RUNNING:
                row["state"] = C.STEP_PENDING
        if self._mode == "collapsed":
            self.expand()
        self._arm_autohide()

    def mark_cancelled(self) -> None:
        """用户中途取消：标题改为已取消，隐藏大叉按钮，不弹失败提示，启动自动隐藏倒计时。

        保持当前展开 / 收起形态，不强制收起；10 秒无操作后整体隐藏，点叉可立即消失。
        """
        self._running = False
        self._finished_ok = False
        self._cancel_button.hide()
        self._autohide_timer.stop()
        self._title_label.setText(f"{self._version_id} 已取消")
        self._collapsed_name.setText("已取消")
        self._collapsed_icon.setText("✕")
        for row in self._step_rows:
            if row["state"] == C.STEP_RUNNING:
                row["state"] = C.STEP_PENDING
        self._arm_autohide()

    def shutdown(self) -> None:
        """关闭窗口前停掉自动隐藏定时器与几何动画，避免析构后信号访问已销毁控件。"""
        self._autohide_timer.stop()
        if self._geom_anim is not None:
            try:
                self._geom_anim.stop()
            except RuntimeError:
                pass
            self._geom_anim = None

    # ------------------------------------------------------------------ #
    # 自绘毛玻璃
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        radius = C.DOWNLOAD_PANEL_RADIUS if self._mode == "expanded" else self.height() / 2.0
        paint_frosted_panel(
            painter,
            self,
            radius,
            C.COLOR_GLASS_TOP_RGBA,
            C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA,
            C.COLOR_CARD_BORDER_RGBA,
        )
        painter.end()
