# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Xiaoyun AI / 小云 AI
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

"""小云 AI 翻译进度窗口（自包含，不依赖启动器模块）。

窗口不放置任何配置表单：翻译目标、资源包输出目录与主题都由云朵启动器在拉起时
通过命令行传入，模型与推理引擎用内置默认候选；窗口显示后自动开始，界面只保留
对齐启动器安装进度卡片的纯进度展示——左侧总进度百分比 / 翻译速度 / 剩余条目，
右侧分阶段清单（✓ 已完成 / ● 进行中 / ○ 待处理），底部红色圆形按钮取消。

窗口为无边框工具窗口：不显示在 Windows 任务栏，背景透明，只显示一块毛玻璃卡片；
大卡片居中到启动器主窗口正中央（由启动器经 ``--anchor`` 传入几何），不可拖动。
显示约 3.5 秒后丝滑收缩为启动器右下角的小胶囊（后台翻译不中断，胶囊继续显示
百分比）；点击小胶囊重新铺开大卡片。完成 / 失败 / 取消时自动重新铺开并弹框。

主题不在本窗口切换，固定使用启动器传入的全局主题（磨砂 / 通透 / 普通）。
"""
import os
import time

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import ai_constants as C
from ai_worker import AiWorker

# 阶段状态。
STATE_DONE = "done"
STATE_RUNNING = "running"
STATE_PENDING = "pending"

# 大卡片显示后自动收缩为小胶囊的延时（毫秒）。
AUTO_HIDE_MS = 3500

# worker 的 phase 文案到阶段索引的映射（worker 文案固定，按关键词判定）。
PHASE_KEYWORDS = (
    ("扫描", 0),
    ("模型", 1),
    ("翻译", 2),
    ("资源包", 3),
)
# 右侧阶段清单（按实际执行顺序）。
PHASE_LABELS = (
    "扫描 jar 文件",
    "加载本地模型",
    "翻译语言条目",
    "生成汉化资源包",
)
# 小胶囊在各阶段显示的简短名称。
PHASE_PILL_NAMES = ("扫描中", "加载模型", "翻译中", "生成资源包")


def _rgba(t):
    return QColor(t[0], t[1], t[2], t[3])


class _CancelCircleButton(QPushButton):
    """红色圆形取消按钮（自绘，不走 QSS）。"""

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
        ring = QPen(QColor(255, 255, 255, 90))
        ring.setWidthF(1.0)
        painter.setPen(ring)
        painter.strokePath(body, ring)

        symbol = QPen(QColor(255, 255, 255))
        symbol.setWidthF(2.4)
        symbol.setCapStyle(Qt.RoundCap)
        painter.setPen(symbol)
        gap = 9.0
        painter.drawLine(cx - gap, cy - gap, cx + gap, cy + gap)
        painter.drawLine(cx + gap, cy - gap, cx - gap, cy + gap)
        painter.end()


class GlassPanel(QWidget):
    """自绘三主题毛玻璃面板；圆角随窗口形态变化（大卡片固定圆角，小胶囊正半圆）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # 收起态点小胶囊：重新铺开大卡片。
        win = self.window()
        if event.button() == Qt.LeftButton and getattr(win, "mode", "") == "collapsed":
            win.expand()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        win = self.window()
        theme = getattr(win, "theme", C.DEFAULT_THEME)
        mode = getattr(win, "mode", "expanded")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = C.CARD_RADIUS if mode == "expanded" else rect.height() / 2.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        if theme == C.THEME_NORMAL:
            painter.fillPath(path, _rgba(C.CARD_NORMAL_PANEL))
            pen = QPen(_rgba(C.CARD_NORMAL_BORDER))
            painter.setPen(pen)
            painter.drawPath(path)
            painter.end()
            return

        origin = self.mapToGlobal(QPoint(0, 0))
        cw, ch = self.width(), self.height()
        clear = win.live_clear()
        blur = win.live_blur()
        painter.save()
        painter.setClipPath(path)
        if theme == C.THEME_FROST:
            if blur is not None and clear is not None:
                sx = blur.width() / clear.width()
                sy = blur.height() / clear.height()
                src = QRectF(origin.x() * sx, origin.y() * sy, cw * sx, ch * sy)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.drawPixmap(QRectF(self.rect()), blur, src)
            top, mid, bot, border = (C.CARD_GLASS_TOP, C.CARD_GLASS_MID,
                                     C.CARD_GLASS_BOTTOM, C.CARD_GLASS_BORDER)
        else:  # 通透：铺清晰后方，不糊化
            if clear is not None:
                src = QRectF(origin.x(), origin.y(), cw, ch)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.drawPixmap(QRectF(self.rect()), clear, src)
            top, mid, bot, border = (C.CARD_CLEAR_TOP, C.CARD_CLEAR_MID,
                                     C.CARD_CLEAR_BOTTOM, C.CARD_CLEAR_BORDER)
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad.setColorAt(0.0, _rgba(top))
        grad.setColorAt(0.5, _rgba(mid))
        grad.setColorAt(1.0, _rgba(bot))
        painter.fillPath(path, grad)
        painter.restore()

        painter.setPen(QPen(_rgba(border)))
        painter.drawPath(path)
        painter.end()


class AiWindow(QWidget):
    """小云 AI 纯翻译进度窗口：大卡片居中，3.5 秒后丝滑收缩为右下角小胶囊。"""

    def __init__(self, game_dir: str = "", output_dir: str = "",
                 theme: str = C.DEFAULT_THEME, anchor: tuple | None = None,
                 parent=None):
        super().__init__(parent)
        # 无边框工具窗口：不显示在任务栏；置顶确保浮在启动器之上不被遮挡；
        # 透明背景，只显示玻璃面板。
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(f"{C.AI_DISPLAY_NAME} {C.AI_VERSION_TAG}（{C.AI_STAGE}）")
        # 主题由启动器全局设置传入，本窗口不提供切换。
        self.theme = theme if theme in C.THEME_KEYS else C.DEFAULT_THEME
        self.mode = "expanded"  # expanded | collapsed
        self._game_dir = game_dir
        self._output_dir = output_dir
        self._anchor = anchor
        self._worker: AiWorker | None = None
        self._started = False
        self._ended = False
        self._live_clear: QPixmap | None = None
        self._live_blur: QPixmap | None = None

        # 翻译速度采样。
        self._last_done = 0
        self._last_time = time.monotonic()
        self._speed = 0.0

        # 两套形态：大卡片 body + 小胶囊 body，不参与父布局，几何由本类动画驱动。
        self._expanded_body = self._build_expanded_body()
        self._collapsed_body = self._build_collapsed_body()
        self._geom_anim: QPropertyAnimation | None = None

        # 初始为大卡片几何、隐藏，show() 时才出现。
        self._collapsed_body.hide()
        self.setGeometry(self._expanded_rect())
        self.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        # 两套 body 都铺满窗口，几何动画期间手动同步尺寸。
        super().resizeEvent(event)
        self._expanded_body.resize(self.size())
        self._collapsed_body.resize(self.size())

    # ---- 大卡片 body ----
    def _build_expanded_body(self) -> QWidget:
        body = QWidget(self)
        body.setAttribute(Qt.WA_TranslucentBackground, True)
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        panel = GlassPanel(body)
        panel.setFixedWidth(520)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        h = QHBoxLayout()
        h.setSpacing(18)
        h.addLayout(self._build_stats(), 0)
        h.addLayout(self._build_phase_list(), 1)
        outer.addLayout(h)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(
            "QProgressBar{background:rgba(255,255,255,150);border:none;border-radius:4px;}"
            "QProgressBar::chunk{background:#7fc2e8;border-radius:4px;}")
        outer.addWidget(self._bar)
        col.addWidget(panel)

        # 免责提示放在卡片下方居中。
        self.disc = QLabel("⚠ " + C.TRANSLATION_DISCLAIMER)
        self.disc.setStyleSheet("font-size:12px;color:#5f7d92;")
        self.disc.setWordWrap(True)
        self.disc.setAlignment(Qt.AlignCenter)
        col.addWidget(self.disc)

        # 红色圆形取消按钮居中。
        crow = QHBoxLayout()
        crow.setContentsMargins(0, 0, 0, 0)
        self._cancel_button = _CancelCircleButton()
        self._cancel_button.clicked.connect(self._cancel)
        crow.addStretch(1)
        crow.addWidget(self._cancel_button)
        crow.addStretch(1)
        col.addLayout(crow)
        return body

    # ---- 小胶囊 body ----
    def _build_collapsed_body(self) -> GlassPanel:
        panel = GlassPanel(self)
        panel.setFixedSize(C.PILL_WIDTH, C.PILL_HEIGHT)
        panel.setCursor(Qt.PointingHandCursor)
        panel.setToolTip("点击展开小云 AI 进度")
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(8)

        self._pill_icon = QLabel("☁")
        self._pill_icon.setFixedWidth(20)
        self._pill_icon.setAlignment(Qt.AlignCenter)
        self._pill_icon.setStyleSheet("font-size:15px;color:#5aa7d6;")
        row.addWidget(self._pill_icon)

        self._pill_name = QLabel("准备中")
        self._pill_name.setStyleSheet("font-size:13px;color:#2b3f51;")
        row.addWidget(self._pill_name, 1)

        self._pill_percent = QLabel("0%")
        self._pill_percent.setStyleSheet("font-size:14px;font-weight:700;color:#2b3f51;")
        row.addWidget(self._pill_percent)
        return panel

    def _build_stats(self) -> QVBoxLayout:
        stats = QVBoxLayout()
        stats.setSpacing(8)

        cap1 = QLabel("总进度")
        cap1.setStyleSheet("font-size:12px;color:#5f7d92;")
        stats.addWidget(cap1)
        self._percent_value = QLabel("0.00%")
        self._percent_value.setStyleSheet("font-size:26px;font-weight:700;color:#2b3f51;")
        stats.addWidget(self._percent_value)

        cap2 = QLabel("翻译速度")
        cap2.setStyleSheet("font-size:12px;color:#5f7d92;")
        stats.addWidget(cap2)
        self._speed_value = QLabel("—")
        self._speed_value.setStyleSheet("font-size:15px;font-weight:600;color:#2b3f51;")
        stats.addWidget(self._speed_value)

        cap3 = QLabel("剩余条目")
        cap3.setStyleSheet("font-size:12px;color:#5f7d92;")
        stats.addWidget(cap3)
        self._remain_value = QLabel("0")
        self._remain_value.setStyleSheet("font-size:15px;font-weight:600;color:#2b3f51;")
        stats.addWidget(self._remain_value)

        stats.addStretch(1)
        return stats

    def _build_phase_list(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(10)
        self._phase_icons: list[QLabel] = []
        for text in PHASE_LABELS:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon = QLabel("○")
            icon.setFixedSize(18, 18)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("font-size:13px;color:#9bb3c4;")
            self._phase_icons.append(icon)
            row.addWidget(icon, 0)
            label = QLabel(text)
            label.setStyleSheet("font-size:13px;color:#2b3f51;")
            label.setWordWrap(True)
            row.addWidget(label, 1)
            column.addLayout(row)
        column.addStretch(1)
        return column

    # ---- 阶段图标更新 ----
    def _set_phase_state(self, index: int, state: str) -> None:
        if index < 0 or index >= len(self._phase_icons):
            return
        icon = self._phase_icons[index]
        if state == STATE_DONE:
            icon.setText("✓")
            icon.setStyleSheet("font-size:13px;font-weight:700;color:#5aa7d6;")
        elif state == STATE_RUNNING:
            icon.setText("●")
            icon.setStyleSheet("font-size:12px;color:#5aa7d6;")
        else:
            icon.setText("○")
            icon.setStyleSheet("font-size:13px;color:#9bb3c4;")

    def _mark_phase_running(self, index: int) -> None:
        for i in range(len(self._phase_icons)):
            if i < index:
                self._set_phase_state(i, STATE_DONE)
            elif i == index:
                self._set_phase_state(i, STATE_RUNNING)
            else:
                self._set_phase_state(i, STATE_PENDING)

    @staticmethod
    def _phase_index(text: str) -> int | None:
        for keyword, index in PHASE_KEYWORDS:
            if keyword in text:
                return index
        return None

    # ---- 抓屏 / 居中 / 显示 ----
    def live_clear(self) -> QPixmap | None:
        return self._live_clear

    def live_blur(self) -> QPixmap | None:
        return self._live_blur

    def _capture_screen(self) -> None:
        """在显示自己之前抓全屏，作为毛玻璃卡片的后方画面。"""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        clear = screen.grabWindow(0)
        if clear.isNull():
            return
        self._live_clear = clear
        sw = C.BLUR_SHORT_SIDE
        sh = max(1, int(clear.height() * sw / clear.width()))
        self._live_blur = clear.scaled(sw, sh, Qt.IgnoreAspectRatio,
                                       Qt.FastTransformation)

    # ---- 几何锚点 ----
    def _expanded_rect(self) -> QRect:
        """大卡片几何：中心对齐启动器主窗口中心；无 anchor 回退屏幕居中。"""
        sh = self._expanded_body.sizeHint()
        w, h = sh.width(), sh.height()
        if self._anchor is not None:
            ax, ay, aw, ah = self._anchor
            cx = ax + aw // 2
            cy = ay + ah // 2
        else:
            geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
            cx = geo.center().x()
            cy = geo.center().y()
        return QRect(cx - w // 2, cy - h // 2, w, h)

    def _collapsed_rect(self) -> QRect:
        """小胶囊几何：贴启动器主窗口右下角；无 anchor 回退屏幕右下角。"""
        w, h = C.PILL_WIDTH, C.PILL_HEIGHT
        if self._anchor is not None:
            ax, ay, aw, ah = self._anchor
            x = ax + aw - w - C.PILL_MARGIN_RIGHT
            y = ay + ah - h - C.PILL_MARGIN_BOTTOM
        else:
            geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
            x = geo.right() - w - C.PILL_MARGIN_RIGHT
            y = geo.bottom() - h - C.PILL_MARGIN_BOTTOM
        return QRect(max(0, x), max(0, y), w, h)

    def _animate_geometry(self, target: QRect) -> None:
        if self._geom_anim is not None:
            try:
                self._geom_anim.stop()
            except RuntimeError:
                pass
        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(C.PANEL_ANIM_MS)
        anim.setStartValue(self.geometry())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._geom_anim = anim
        anim.start()

    def expand(self) -> None:
        """从小胶囊丝滑铺开为大卡片。"""
        if self.mode == "expanded":
            return
        self.mode = "expanded"
        self._collapsed_body.hide()
        self._expanded_body.show()
        self._expanded_body.resize(self.size())
        self._animate_geometry(self._expanded_rect())
        self.raise_()

    def collapse(self) -> None:
        """丝滑收缩为右下角小胶囊，后台翻译不中断。"""
        if self.mode == "collapsed":
            return
        self.mode = "collapsed"
        self._expanded_body.hide()
        self._collapsed_body.show()
        self._collapsed_body.resize(self.size())
        self._animate_geometry(self._collapsed_rect())
        self.raise_()

    def _reveal(self) -> None:
        """确保窗口可见并处于大卡片形态（完成 / 失败 / 取消弹框前调用）。"""
        if not self.isVisible():
            if self._live_clear is None:
                self._capture_screen()
            super().show()
        if self.mode != "expanded":
            self.expand()
        self.raise_()

    def show(self) -> None:
        # 首次显示前抓屏，确保毛玻璃不会抓到自己。
        if self._live_clear is None:
            self._capture_screen()
        self.mode = "expanded"
        self._collapsed_body.hide()
        self._expanded_body.show()
        self.setGeometry(self._expanded_rect())
        super().show()
        self.raise_()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._started:
            self._started = True
            # 等窗口先渲染出来再启动后台，避免首帧卡顿。
            QTimer.singleShot(120, self._auto_start)
        # 显示约 3.5 秒后自动收缩为小胶囊（已结束则不收缩）。
        QTimer.singleShot(AUTO_HIDE_MS, self._auto_collapse)

    def _auto_collapse(self) -> None:
        if not self._ended and self.isVisible() and self.mode == "expanded":
            self.collapse()

    # ---- 自动开始 ----
    def _auto_start(self) -> None:
        model = C.bundled_model_path()
        server = C.bundled_server_path()
        if not self._game_dir or not os.path.isdir(self._game_dir):
            self._fatal("缺少有效的翻译目标目录（应由启动器传入）。")
            return
        if not model:
            self._fatal("未找到内置模型文件，安装包可能已损坏。")
            return
        if not server:
            self._fatal("未找到内置推理引擎，安装包可能已损坏。")
            return
        out_dir = self._output_dir or self._game_dir
        os.makedirs(out_dir, exist_ok=True)

        self._worker = AiWorker(
            scan_root=self._game_dir, server_exe=server, model_path=model,
            output_dir=out_dir, pack_name="小云AI汉化资源包")
        self._worker.phase.connect(self._on_phase)
        self._worker.scan_progress.connect(self._on_scan)
        self._worker.translate_progress.connect(self._on_translate)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _fatal(self, message: str) -> None:
        self._ended = True
        self._reveal()
        self._msg(QMessageBox.Warning, message)
        self._cancel_button.setEnabled(False)

    def _cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._cancel_button.setEnabled(False)
            self._worker.request_cancel()

    def _msg(self, icon, text: str) -> int:
        """弹出与主窗口一起置顶的消息框，避免被 WindowStaysOnTopHint 主窗口遮挡。"""
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(C.AI_DISPLAY_NAME)
        box.setText(text)
        box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
        return box.exec()

    # ---- worker 回调 ----
    def _on_phase(self, text: str) -> None:
        index = self._phase_index(text)
        if index is None:
            return
        self._mark_phase_running(index)
        self._pill_name.setText(PHASE_PILL_NAMES[index])

    def _apply_percent(self, done: int, total: int, show_speed: bool) -> None:
        pct = (done * 100.0 / total) if total else 0.0
        self._percent_value.setText("%.2f%%" % pct)
        self._remain_value.setText(str(max(0, total - done)))
        self._bar.setValue(int(pct))
        self._pill_percent.setText("%d%%" % int(round(pct)))
        if show_speed:
            now = time.monotonic()
            dt = now - self._last_time
            if dt > 0.1:
                instant = max(0, done - self._last_done) / dt
                self._speed = (0.7 * self._speed + 0.3 * instant) if self._speed else instant
                self._last_done = done
                self._last_time = now
                self._speed_value.setText("%.1f 条/秒" % self._speed)

    def _on_scan(self, done: int, total: int, path: str) -> None:
        # 扫描仅 2-3 秒，进度由阶段清单的 ● 体现；不写总进度大数字，避免扫描完成
        # 后在第一条翻译到来前残留 100% / 剩余 0，让用户误以为翻译已结束。
        return

    def _on_translate(self, done: int, total: int, key: str) -> None:
        self._apply_percent(done, total, show_speed=True)

    def _on_finished(self, info: dict) -> None:
        self._ended = True
        if info.get("cancelled"):
            self._cancel_button.setEnabled(False)
            self._pill_icon.setText("✕")
            self._pill_name.setText("已取消")
            self._reveal()
            self._msg(QMessageBox.Information, info.get("reason", "已取消。"))
            return
        if "zip_path" not in info:
            self._reveal()
            self._msg(QMessageBox.Information,
                       info.get("reason", "未发现需要翻译的条目。"))
            return
        for i in range(len(self._phase_icons)):
            self._set_phase_state(i, STATE_DONE)
        self._percent_value.setText("100.00%")
        self._remain_value.setText("0")
        self._bar.setValue(100)
        self._cancel_button.setEnabled(False)
        self._pill_icon.setText("✓")
        self._pill_name.setText("翻译完成")
        self._pill_percent.setText("100%")
        self._reveal()
        msg = (
            f"翻译成功！\n\n涉及 jar：{info.get('jars')} 个；"
            f"命名空间：{info.get('namespaces')} 个；"
            f"翻译条目：{info.get('translated')} 条；"
            f"并行翻译线：{info.get('lines', 1)} 条。\n\n"
            f"资源包目录：{info.get('pack_dir')}\n"
            f"压缩包：{info.get('zip_path')}\n\n"
            f"请在游戏「资源包」中启用。{info.get('disclaimer', '')}")
        self._msg(QMessageBox.Information, msg)

    def _on_failed(self, message: str) -> None:
        self._ended = True
        self._cancel_button.setEnabled(False)
        self._pill_icon.setText("✕")
        self._pill_name.setText("翻译失败")
        self._reveal()
        self._msg(QMessageBox.Warning, message)

    def closeEvent(self, event) -> None:  # noqa: N802
        # 关闭窗口前确保工作线程收尾（其 finally 会停止 server，避免孤儿进程/原生崩溃）。
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(8000)
        super().closeEvent(event)
