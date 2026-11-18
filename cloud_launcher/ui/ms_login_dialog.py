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

"""微软正版登录弹窗：设备码流程的 PySide6 界面。

交互流程（思路移植自历史 v1.3.149 的 Tkinter 登录窗，线程与界面全部按当前 Qt 工程重写）：

1. 弹窗打开时在主线程同步申请设备码：拿到 8 位 ``user_code``、授权网址 ``verification_uri``；
2. 自动用系统浏览器打开授权网址，并把设备码复制到系统剪贴板；界面同时显示网址、大号
   等宽设备码与等待状态，用户可点链接重开网页、可随时取消；
3. 独立 ``QThread`` 后台轮询授权结果，授权完成后自动走完 Xbox / XSTS / Minecraft 链路
   拉取档案；成功信号回主线程关闭弹窗并把档案交给个人页；失败把中文错误显示在状态行；
4. 申请设备码阶段的网络失败保存在 ``construction_error``，由调用方决定是否弹出错误提示。

不引入第三方依赖；弹窗内不保存任何凭据到磁盘。
"""
import threading
import webbrowser

from PySide6.QtCore import Qt, QThread, QTimer, QPoint, QRect, QRectF, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from ..microsoft_auth import AuthError, MicrosoftAuth
from ..resources import resource_path


class _LoginWorker(QThread):
    """后台轮询设备码授权并完成整条 Xbox / Minecraft 认证链路。"""

    succeeded = Signal(dict)
    failed = Signal(str)
    status = Signal(str)

    def __init__(self, auth: MicrosoftAuth, device_code: str, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth
        self._device_code = device_code
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            self.status.emit("正在等待浏览器授权…")
            token = self._auth.poll_token(self._device_code, cancel=self._cancel)
            self.status.emit("正在验证 Xbox 与 Minecraft 档案…")
            profile = self._auth.fetch_profile(
                token["access_token"], token.get("refresh_token", "")
            )
            self.succeeded.emit(profile)
        except AuthError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # 未预期异常统一转为可读中文提示，避免线程崩溃无反馈
            self.failed.emit(f"登录失败：{exc}")


# 自绘玻璃配色（QSS rgba 换算为 0-255 alpha，避免依赖样式表对后代控件的背景接管）。
# 弹窗面板本身接近纯白，后代控件若叠纯白玻璃在白底上无色差、轮廓消失，因此这里采用
# 略冷、略暗一档的浅蓝灰玻璃 + 冷浅蓝细边，在白面板上显出柔和层次但不浮凸。
_CODE_TOP = QColor(236, 245, 251, 205)
_CODE_BOTTOM = QColor(224, 239, 248, 158)
_CODE_BORDER = QColor(190, 222, 238, 128)

_GLASS_BG = QColor(235, 244, 250, 150)
_GLASS_BG_HOVER = QColor(222, 238, 248, 190)
_GLASS_BG_PRESSED = QColor(210, 232, 244, 160)
_GLASS_BG_DISABLED = QColor(245, 248, 250, 90)
_GLASS_BORDER = QColor(190, 222, 238, 110)
_GLASS_BORDER_HOVER = QColor(162, 207, 233, 150)
_TEXT_DARK = QColor(0x2B, 0x47, 0x59)
_TEXT_MUTED = QColor(0x6D, 0x8A, 0x9C)
_TEXT_DISABLED = QColor(109, 138, 156, 140)


class _CodeFrame(QFrame):
    """自绘圆角玻璃码框。

    实测在该独立无边框 QDialog 内，后代 QFrame / QLabel / QPushButton 的 QSS
    background 与 border-radius 不会被样式表接管（真实桌面像素采样确认与面板同色、
    无独立玻璃色差），因此码框背景、渐变、圆角、弱边全部由 ``paintEvent`` 用
    ``QPainterPath`` 圆角矩形自绘；内部仅放透明等宽文字标签。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # 关闭原生背景与边框绘制，避免与自绘图层叠加
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        inner = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(inner, 16, 16)

        gradient = QLinearGradient(0, inner.top(), 0, inner.bottom())
        gradient.setColorAt(0.0, _CODE_TOP)
        gradient.setColorAt(1.0, _CODE_BOTTOM)
        painter.fillPath(path, gradient)

        pen = painter.pen()
        pen.setColor(_CODE_BORDER)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(path, pen)
        painter.end()


class _GlassButton(QFrame):
    """自绘玻璃胶囊按钮：背景、圆角、弱边由 paintEvent 绘制，内部仅放透明文字标签。

    hover / pressed / disabled 状态切换自绘底色与文字色，点击对外发 ``clicked`` 信号。
    """

    clicked = Signal()

    def __init__(self, text: str, radius: int = 18, parent=None) -> None:
        super().__init__(parent)
        self._radius = radius
        self._hover = False
        self._pressed = False
        self._enabled = True
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)
        self._label = QLabel(text)
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)

        self.setStyleSheet("background: transparent; border: none;")
        self._refresh_label()

    def _state(self):
        if not self._enabled:
            return _GLASS_BG_DISABLED, _GLASS_BORDER, _TEXT_DISABLED
        if self._pressed:
            return _GLASS_BG_PRESSED, _GLASS_BORDER, _TEXT_DARK
        if self._hover:
            return _GLASS_BG_HOVER, _GLASS_BORDER_HOVER, _TEXT_DARK
        return _GLASS_BG, _GLASS_BORDER, _TEXT_DARK

    def _refresh_label(self) -> None:
        _, _, text_color = self._state()
        self._label.setStyleSheet(
            f"background:transparent; border:none; font-size:13px; color:{text_color.name(QColor.HexArgb)};"
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        bg, border, _ = self._state()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        inner = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(inner, self._radius, self._radius)
        painter.fillPath(path, bg)

        pen = painter.pen()
        pen.setColor(border)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(path, pen)
        painter.end()

    def setText(self, text: str) -> None:
        self._label.setText(text)

    def setEnabled(self, on: bool) -> None:  # noqa: N802
        self._enabled = on
        self.setCursor(Qt.ArrowCursor if not on else Qt.PointingHandCursor)
        self._refresh_label()
        self.update()

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self._refresh_label()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self._refresh_label()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self._enabled:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self._pressed and self._enabled:
            self._pressed = False
            self._refresh_label()
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)


class _GlassIconButton(QFrame):
    """标题栏自绘小图标按钮：默认透明，hover 浅玻璃圆角，点击发 ``clicked``。"""

    clicked = Signal()

    def __init__(self, glyph: str, parent=None) -> None:
        super().__init__(parent)
        self._hover = False
        self.setFixedSize(32, 30)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._label = QLabel(glyph)
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)

        self.setStyleSheet("background: transparent; border: none;")
        self._refresh_label()

    def _refresh_label(self) -> None:
        color = _TEXT_DARK if self._hover else _TEXT_MUTED
        self._label.setStyleSheet(
            f"background:transparent; border:none; font-size:14px; color:{color.name(QColor.HexArgb)};"
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._hover:
            inner = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            path = QPainterPath()
            path.addRoundedRect(inner, 10, 10)
            painter.fillPath(path, QColor(190, 222, 238, 60))
        painter.end()

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self._refresh_label()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self._refresh_label()
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)



class MsLoginDialog(QDialog):
    """设备码授权模态弹窗。``exec()`` 返回后读取 ``self.profile`` 判断是否登录成功。"""

    def __init__(self, parent: QWidget | None = None, auth: MicrosoftAuth | None = None) -> None:
        super().__init__(parent)
        self.auth = auth or MicrosoftAuth()
        self.profile: dict | None = None
        self.construction_error: str | None = None
        self._worker: _LoginWorker | None = None
        self._info: dict | None = None
        self._drag_pos: QPoint | None = None

        # 与主窗口一致：去掉系统原生标题栏与直角窗口外壳，由内部玻璃圆角面板绘制，
        # 避免系统标题栏在四角留下无法磨平的硬直角。窗口本身背景透明，圆角外不填系统灰底。
        self.setWindowTitle("微软正版登录")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setProperty("dialogRoot", True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 主线程先申请设备码；失败记录到 construction_error，由调用方决定提示方式。
        try:
            self._info = self.auth.request_device_code()
        except AuthError as exc:
            self.construction_error = str(exc)
            return
        except Exception as exc:
            self.construction_error = f"登录发起失败：{exc}"
            return

        self._build_ui()
        self._start_polling()

    # ---------- 界面 ----------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 窗口本身透明；玻璃圆角面板作为唯一可见容器，圆角外区域保持透明不发灰。
        # 弹窗内控件不依赖应用全局选择器规则（该独立顶层窗口上选择器匹配不生效），
        # 面板与各控件样式在本地直接设置，保证视觉稳定可复现。
        panel = QFrame()
        panel.setObjectName("dialogPanel")
        self._panel = panel
        panel.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 rgba(255,255,255,250),"
            " stop:0.45 rgba(255,255,255,244),"
            " stop:1 rgba(255,255,255,238));"
            "border: 1px solid rgba(255,255,255,188);"
            "border-radius: 20px;"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        outer.addWidget(panel)

        self._build_title_bar(panel_layout)

        body = QVBoxLayout()
        body.setContentsMargins(24, 8, 24, 20)
        body.setSpacing(11)
        panel_layout.addLayout(body)

        title = QLabel("微软账号登录（设备码）")
        title.setProperty("dialogTitle", True)
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{C.COLOR_TEXT};")
        body.addWidget(title)

        intro = QLabel(
            "将在浏览器中打开微软授权页面，完成授权后本窗口会自动登录，无需手动操作本窗口。"
        )
        intro.setProperty("dialogHint", True)
        intro.setWordWrap(True)
        intro.setStyleSheet(f"font-size:13px; color:{C.COLOR_TEXT_LIGHT}; line-height:150%;")
        body.addWidget(intro)

        url_label = QLabel(f'<a href="{self._info["verification_uri"]}" style="color:{C.COLOR_PRIMARY};">'
                           f'{self._info["verification_uri"]}</a>')
        url_label.setOpenExternalLinks(True)
        url_label.setWordWrap(True)
        url_label.setProperty("dialogLink", True)
        url_label.setStyleSheet("font-size:13px; padding:2px 0;")
        body.addWidget(url_label)

        hint = QLabel("设备码已自动复制到剪贴板，如未复制请在网页手动输入：")
        hint.setProperty("dialogHint", True)
        hint.setStyleSheet(f"font-size:13px; color:{C.COLOR_TEXT_LIGHT};")
        body.addWidget(hint)

        # 码框：背景 / 圆角 / 边框由外层 QFrame 本地表绘制（QFrame 背景在无边框透明
        # 对话框上稳定接管），内部标签只负责等宽大字号文字，自身保持透明。
        code_frame = _CodeFrame()
        code_frame.setProperty("deviceCode", True)
        self._code_frame = code_frame
        code_layout = QVBoxLayout(code_frame)
        code_layout.setContentsMargins(18, 14, 18, 14)
        code_label = QLabel(self._info["user_code"])
        code_label.setAlignment(Qt.AlignCenter)
        code_label.setStyleSheet(
            "background:transparent; border:none;"
            "font-family:Consolas,\"Courier New\",monospace;"
            f"font-size:28px; font-weight:700; letter-spacing:4px; color:{C.COLOR_TEXT};"
        )
        code_layout.addWidget(code_label)
        body.addWidget(code_frame)

        self.status_label = QLabel("正在等待授权… 授权完成后自动登录")
        self.status_label.setProperty("dialogStatus", True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"font-size:13px; color:{C.COLOR_TEXT_LIGHT}; min-height:22px;")
        body.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = _GlassButton("取消", radius=18)
        self.cancel_button.setProperty("dialogButton", True)
        self.cancel_button.setFixedHeight(36)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        buttons.addWidget(self.cancel_button)
        body.addLayout(buttons)

        # 自动打开浏览器并复制设备码到剪贴板
        webbrowser.open(self._info["verification_uri"])
        try:
            QGuiApplication.clipboard().setText(self._info["user_code"])
        except Exception:
            pass

    def _build_title_bar(self, outer: QVBoxLayout) -> None:
        bar = QWidget()
        bar.setProperty("dialogTitleBar", True)
        bar.setStyleSheet("background: transparent;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(18, 12, 12, 4)
        bar_layout.setSpacing(10)

        logo = QLabel()
        pix = QPixmap(resource_path("cloud_logo.png"))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        bar_layout.addWidget(logo)

        brand = QLabel("微软正版登录")
        brand.setProperty("dialogTitleText", True)
        brand.setStyleSheet(f"font-size:14px; font-weight:600; color:{C.COLOR_TEXT};")
        bar_layout.addWidget(brand)
        bar_layout.addStretch(1)

        close_btn = _GlassIconButton("✕")
        close_btn.setProperty("dialogClose", True)
        close_btn.clicked.connect(self._on_cancel_clicked)
        bar_layout.addWidget(close_btn)

        outer.addWidget(bar)
        self._title_bar = bar

    # ---------- 标题栏拖动 ----------
    def _title_bar_rect(self) -> QRect:
        """标题栏在弹窗坐标系下的矩形（标题栏挂在内部 panel 上，需做父子坐标映射）。"""
        if not hasattr(self, "_title_bar"):
            return QRect()
        bar = self._title_bar
        top_left = bar.mapTo(self, bar.geometry().topLeft())
        return QRect(top_left, bar.geometry().size())

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton
                and self._title_bar_rect().contains(event.position().toPoint())):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _start_polling(self) -> None:
        self._worker = _LoginWorker(self.auth, self._info["device_code"], parent=self)
        self._worker.status.connect(self._on_status)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    # ---------- 线程回调（主线程）----------
    def _on_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_succeeded(self, profile: dict) -> None:
        self.profile = profile
        self.status_label.setText("登录成功！")
        self.status_label.setProperty("statusOk", True)
        self.cancel_button.setEnabled(False)
        # 短暂停留让成功状态可见，再关闭弹窗把档案交回个人页
        QTimer.singleShot(400, self.accept)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("登录失败：" + message)
        self.status_label.setProperty("statusError", True)
        self.cancel_button.setText("关闭")

    def _on_cancel_clicked(self) -> None:
        self._cancel_worker()
        self.reject()

    def _cancel_worker(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(800)

    # ---------- 窗口关闭保护 ----------
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._cancel_worker()
        super().closeEvent(event)
