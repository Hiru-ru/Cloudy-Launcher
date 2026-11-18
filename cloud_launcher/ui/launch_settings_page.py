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

"""设置页「启动」标签：账号管理 + 全局启动设置（版本隔离 / 高级功能）。

v1.3.21.0 曾把「版本隔离」与「高级功能」（内存、GC、Java、JVM/游戏参数、启动前命令、
四个高级开关）搬到**版本设置页**的「设置」标签，按版本独立配置（见
:class:`~cloud_launcher.version_launch_config.VersionLaunchConfig`），本页一度只留账号管理。
后续按用户「复制而非剪切」的口径，本标签通过 :class:`GlobalLaunchConfigPanel` 恢复这些
设置的**全局默认**编辑入口：这里的值对所有版本生效；版本设置页未单独覆盖的版本跟随全局，
单独覆盖后以版本设置为准（per-version 覆盖 > 全局默认 > 内置默认）。
本模块同时保留磨砂下拉 / 滑条等通用控件（``_ComboPopup`` / ``_GlassComboBox`` /
``_NoWheelSlider`` / ``_physical_memory_mb``），版本设置页直接导入复用。

账号管理在 v1.3.19.0 收敛为「单个当前账号行 + 悬停三点菜单」：卡片只展示当前账号
（离线 / 正版类型、昵称、UUID），鼠标悬停时右侧浮现「⋯」按钮，点击弹出磨砂菜单，
统一承载添加账号、切换账号（v1.3.20.0 起为二级弹窗选择）、重命名、皮肤导入 / 导出、
移除账号 / 退出登录。
v1.3.17.0 起离线昵称持久化到 config.offline_accounts 的多账号模型与单份会话保持不变；
切换账号二级弹窗同时列出当前正版账号（标注「（当前）」，v1.3.20.1 起）与全部离线账号；
v1.3.20.2 起「切换」与「退出登录」语义分离：切到离线只切内存会话、保留本地正版凭据
（account.json），离线态弹窗列出该正版条目，点击静默续期即可切回，不再误删账号；只有
明确点「退出登录」才清除凭据。多正版并存属后续链路。
v1.3.20.3 起下拉框与内存滑条的 ``wheelEvent`` 一律忽略：鼠标悬停滚动页面时不再误改
选项 / 数值，只能点击选择或拖动；同时下拉框不再用系统默认 popup，改由自定义
``_ComboPopup`` 承载透明 QListView，显示前抓取父窗真实渲染做 live 背景，跟随
``glass_mode`` 在磨砂 / 通透 / 普通三档间切换，数据模型与 currentIndexChanged 不变。
v1.3.20.4 修复下拉弹窗（及三点菜单）的「方形角」：Qt.Popup 顶层窗默认带系统 DWM 投影，
投影沿窗口直角矩形边缘绘制，即便内部 Card 是圆角，圆角外仍露出直角深色线形成方形；窗口
标志追加 ``Qt.NoDropShadowWindowHint`` 去掉该投影，Card 圆角外不再有直角，三档材质一致。

账号管理界面与配置落盘口径：只读展示当前离线 / 正版账号状态与昵称、UUID；添加 / 切换 /
重命名 / 移除与正版登录、退出登录均收敛到三点菜单，复用主窗口既有 ``AccountSession`` 与
``AccountStore``；支持本地皮肤文件导入 / 导出（皮肤文件落到 CLY 自定义皮肤目录，
渲染接入留待后续）。

本模块只负责界面、文件选择与配置写入；会话 / 账号存储由 host（MainWindow）持有。
"""
from __future__ import annotations

import ctypes
import os

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import java_runtime
from ..resources import data_dir
from .card_widget import Card
from .frosted_backdrop import capture_live_backdrop
from .ms_login_dialog import MsLoginDialog
from .account_restore_worker import AccountRestoreWorker


# 自定义皮肤存放子目录（位于 CLY 数据目录下）。
CUSTOM_SKIN_DIR = "custom_skins"


def _physical_memory_mb() -> tuple[int, int]:
    """返回物理内存 (总量 MB, 可用 MB)；读取失败返回 (0, 0)。

    仅用标准库 ctypes 调 Win32 ``GlobalMemoryStatusEx``，不引入 psutil 等第三方依赖。
    """
    try:
        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MemoryStatusEx()
        stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return 0, 0
        total_mb = int(stat.ullTotalPhys // (1024 * 1024))
        avail_mb = int(stat.ullAvailPhys // (1024 * 1024))
        return total_mb, avail_mb
    except (OSError, AttributeError, ValueError):
        return 0, 0


class _AddAccountDialog(QDialog):
    """添加账号弹窗：先选类型（离线 / 正版），离线需填写昵称，正版走微软设备码登录。

    与项目其他弹窗一致：无边框透明根 + 一块自绘磨砂 Card 底板，避免系统标题栏
    在四角留硬直角，也避免独立顶层窗客户区与整窗截图口径不一致裁掉底部按钮。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加账号")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(360)
        self._kind = "offline"

        ref_window = parent.window() if parent is not None else None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._card = Card("添加账号", self)
        if ref_window is not None:
            self._card.set_reference_window(ref_window)
        outer.addWidget(self._card)
        body = self._card.body_layout

        hint = QLabel("选择要添加的账号类型：")
        hint.setProperty("fieldLabel", True)
        body.addWidget(hint)

        self._offline_radio = QRadioButton("离线账号（本地昵称，无需联网）")
        self._ms_radio = QRadioButton("正版账号（微软设备码登录）")
        self._offline_radio.setChecked(True)
        self._offline_radio.toggled.connect(self._sync_mode)
        body.addWidget(self._offline_radio)
        body.addWidget(self._ms_radio)

        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        name_caption = QLabel("昵称")
        name_caption.setProperty("fieldLabel", True)
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(16)
        self._name_edit.setPlaceholderText("输入离线昵称")
        name_row.addWidget(name_caption)
        name_row.addWidget(self._name_edit, 1)
        body.addLayout(name_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("添加")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        body.addWidget(buttons)

        self._sync_mode()
        self.adjustSize()

    def _center_over_reference(self) -> None:
        """居中到父窗口客户区；无父窗口时保持初始位置。"""
        ref = self.parentWidget()
        if ref is None:
            return
        ref = ref.window()
        if ref is None:
            return
        origin = ref.mapToGlobal(QPoint(0, 0))
        geo = self.frameGeometry()
        x = origin.x() + (ref.width() - geo.width()) // 2
        y = origin.y() + (ref.height() - geo.height()) // 2
        self.move(x, y)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._center_over_reference()
        super().showEvent(event)

    def _sync_mode(self) -> None:
        self._kind = "offline" if self._offline_radio.isChecked() else "microsoft"
        self._name_edit.setEnabled(self._kind == "offline")

    def _on_accept(self) -> None:
        if self._kind == "offline" and not self._name_edit.text().strip():
            QMessageBox.warning(self, C.APP_FULL_NAME, "请输入离线昵称。")
            return
        self.accept()

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def name(self) -> str:
        return self._name_edit.text().strip()


class _RenameAccountDialog(QDialog):
    """重命名当前离线账号：无边框磨砂 Card + 单个昵称输入框。"""

    def __init__(self, current: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("重命名账号")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(340)

        ref_window = parent.window() if parent is not None else None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._card = Card("重命名账号", self)
        if ref_window is not None:
            self._card.set_reference_window(ref_window)
        outer.addWidget(self._card)
        body = self._card.body_layout

        self._edit = QLineEdit(current)
        self._edit.setMaxLength(16)
        self._edit.selectAll()
        body.addWidget(self._edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        body.addWidget(buttons)
        self.adjustSize()

    def _center_over_reference(self) -> None:
        ref = self.parentWidget()
        if ref is None:
            return
        ref = ref.window()
        if ref is None:
            return
        origin = ref.mapToGlobal(QPoint(0, 0))
        geo = self.frameGeometry()
        x = origin.x() + (ref.width() - geo.width()) // 2
        y = origin.y() + (ref.height() - geo.height()) // 2
        self.move(x, y)

    def showEvent(self, event) -> None:  # noqa: N802
        self._center_over_reference()
        super().showEvent(event)

    def _on_accept(self) -> None:
        if not self._edit.text().strip():
            QMessageBox.warning(self, C.APP_FULL_NAME, "昵称不能为空。")
            return
        self.accept()

    def value(self) -> str:
        return self._edit.text().strip()


class _AccountRow(QPushButton):
    """单个当前账号行：类型标签 + 昵称 + UUID，悬停浮现三点「更多」按钮。

    复用 ``accountRow`` 玻璃样式；本身不响应点击，所有操作收敛到三点菜单。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("accountRow", True)
        self.setCheckable(False)
        # QPushButton 作为容器时 minimumSizeHint 不包含内部布局，
        # 显式给最小高度，避免行被压扁、子控件高度塌为 0。
        self.setMinimumHeight(44)
        self.setCursor(Qt.ArrowCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(10)

        self._tag = QLabel("离线")
        self._tag.setProperty("accountTag", True)
        self._tag.setFixedHeight(24)
        self._tag.setMinimumWidth(46)
        self._tag.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._tag)

        self._name_label = QLabel("")
        self._name_label.setProperty("accountName", True)
        self._name_label.setMinimumWidth(56)
        lay.addWidget(self._name_label, 1)

        self._uuid_label = QLabel("")
        self._uuid_label.setProperty("uuidLabel", True)
        lay.addWidget(self._uuid_label)

        self.more_button = QPushButton("⋯")
        self.more_button.setProperty("ghostAction", True)
        self.more_button.setFixedSize(34, 28)
        self.more_button.setCursor(Qt.PointingHandCursor)
        self.more_button.setToolTip("更多操作")
        self.more_button.hide()
        lay.addWidget(self.more_button)

    def set_state(self, kind: str, name: str, uuid: str) -> None:
        self._tag.setText("正版" if kind == "microsoft" else "离线")
        self._name_label.setText(name or "未命名")
        if uuid:
            self._uuid_label.setText(uuid[:8] + "…")
            self.setToolTip("UUID：" + uuid)
        else:
            self._uuid_label.setText("")
            self.setToolTip("")

    def enterEvent(self, event) -> None:  # noqa: N802
        self.more_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        # 鼠标移到子按钮（三点）上时全局光标仍在本控件几何内，避免误隐藏导致闪烁。
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        self.more_button.hide()
        super().leaveEvent(event)


class _AccountMenu(QWidget):
    """三点「更多」磨砂弹出菜单（Qt.Popup：点击外部自动关闭，无边框）。"""

    def __init__(self, parent=None, title: str = "账号操作") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        # NoDropShadowWindowHint：去掉系统沿直角矩形绘制的投影，保证 Card 圆角外不出现方形角。
        self.setWindowFlags(
            Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        ref_window = parent.window() if parent is not None else None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._card = Card(title, self)
        if ref_window is not None:
            self._card.set_reference_window(ref_window)
        outer.addWidget(self._card)
        self._body = self._card.body_layout
        self._body.setSpacing(2)

    def add_item(self, text: str, callback, danger: bool = False) -> None:
        btn = QPushButton(text)
        btn.setProperty("menuItem", True)
        if danger:
            btn.setProperty("danger", True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(34)
        btn.setMinimumWidth(190)

        def _run(_=False):
            self.close()
            callback()

        btn.clicked.connect(_run)
        self._body.addWidget(btn)

    def add_separator(self) -> None:
        line = QFrame()
        line.setProperty("menuSeparator", True)
        line.setFixedHeight(1)
        self._body.addWidget(line)

    def popup_below(self, anchor_widget) -> None:
        self.adjustSize()
        # 定位到锚点按钮下方，菜单右缘对齐按钮右缘。
        bottom_right = anchor_widget.mapToGlobal(anchor_widget.rect().bottomRight())
        x = bottom_right.x() - self.width()
        y = bottom_right.y() + 6
        self.move(x, y)
        self.show()


class _ComboPopup(QWidget):
    """下拉框自定义磨砂弹出面板（Qt.Popup，点击外部关闭）：三档玻璃跟随 appearance。

    QComboBox 的数据模型与 currentIndexChanged 不变；这里用透明 QListView 共享其 model，
    背景由内部 Card 的磨砂 / 通透 / 普通承载，替代默认 QSS 纯色弹窗。
    """

    def __init__(self, combo: "_GlassComboBox") -> None:
        super().__init__(combo)
        self._combo = combo
        # NoDropShadowWindowHint：去掉系统沿窗口直角矩形绘制的 DWM 投影——否则 Card 虽为
        # 圆角，投影仍在圆角外沿直角边缘形成可见「方形角」（v1.3.20.4 修复）。
        self.setWindowFlags(
            Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._card = Card(None, self)
        self._live_ref = combo.window()
        if self._live_ref is not None:
            self._card.set_reference_window(self._live_ref)
        self._live_captured = False
        outer.addWidget(self._card)

        self._view = QListView()
        self._view.setProperty("comboView", True)
        self._view.setModel(combo.model())
        self._view.setCurrentIndex(combo.model().index(combo.currentIndex(), 0))
        self._view.setFrameStyle(0)
        self._view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setCursor(Qt.PointingHandCursor)
        row_h = max(1, self._view.sizeHintForRow(0))
        self._view.setFixedHeight(row_h * combo.count() + 6)
        self._view.clicked.connect(self._on_pick)
        self._card.add_widget(self._view)

    def _on_pick(self, index) -> None:
        if index.isValid():
            self._combo.setCurrentIndex(index.row())
        self.close()

    def showEvent(self, event) -> None:  # noqa: N802
        # 显示前抓主窗口真实渲染：磨砂档真正模糊后方内容，通透档显示清晰后方，
        # 无壁纸时也不会只剩半透明白片。
        if not self._live_captured and self._live_ref is not None:
            clear_pix, blur_pix = capture_live_backdrop(self._live_ref)
            self._card.set_live_backdrop(clear_pix, blur_pix, self._live_ref)
            self._live_captured = True
        super().showEvent(event)

    def popup_below(self, anchor) -> None:
        self.adjustSize()
        self.setFixedWidth(anchor.width())
        bottom_left = anchor.mapToGlobal(anchor.rect().bottomLeft())
        self.move(bottom_left.x(), bottom_left.y() + 4)
        self.show()


class _GlassComboBox(QComboBox):
    """下拉框：忽略滚轮（防误改），展开用自定义磨砂面板，只能点击选择。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._popup: _ComboPopup | None = None

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    def showPopup(self) -> None:  # noqa: N802
        popup = _ComboPopup(self)
        self._popup = popup
        popup.popup_below(self)

    def hidePopup(self) -> None:  # noqa: N802
        if self._popup is not None:
            self._popup.close()
            self._popup = None


class _NoWheelSlider(QSlider):
    """滑条：忽略滚轮（防误改），只能拖动滑块。"""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class GlobalLaunchConfigPanel(QWidget):
    """「启动」标签的全局启动设置：版本隔离 + 高级功能，绑定全局 ``ConfigStore``。

    这里编辑的是对所有版本生效的默认值；版本设置页未单独覆盖的版本（VersionLaunchConfig）
    读取这里的同名字段。控件口径与版本设置页「设置」标签保持一致。
    """

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)

        # ---- 卡片 1：版本隔离 ----
        iso_card = Card("版本隔离")
        iso_caption = QLabel("隔离策略")
        iso_caption.setProperty("fieldLabel", True)
        iso_card.add_widget(iso_caption)
        self._isolation_combo = _GlassComboBox()
        self._isolation_combo.setProperty("versionPicker", True)
        for key in C.ISOLATION_KEYS:
            self._isolation_combo.addItem(C.ISOLATION_LABELS[key], key)
        self._isolation_combo.currentIndexChanged.connect(self._on_isolation_changed)
        iso_card.add_widget(self._isolation_combo)
        iso_hint = QLabel(
            "隔离后该版本的存档、配置与模组与其他版本互不干扰；关闭隔离则共享同一目录。")
        iso_hint.setProperty("sectionHint", True)
        iso_hint.setWordWrap(True)
        iso_card.add_widget(iso_hint)
        column.addWidget(iso_card)

        # ---- 卡片 2：高级功能 ----
        card = Card("高级功能")

        jvm_caption = QLabel("Java 虚拟机参数")
        jvm_caption.setProperty("fieldLabel", True)
        card.add_widget(jvm_caption)
        self._jvm_edit = QTextEdit()
        self._jvm_edit.setPlaceholderText(
            "-XX:-OmitStackTraceInFastThrow\n"
            "-Dfml.ignoreInvalidMinecraftCertificates=True\n"
            "-Dfml.ignorePatchDiscrepancies=True"
        )
        self._jvm_edit.setFixedHeight(88)
        self._jvm_edit.textChanged.connect(self._on_jvm_changed)
        card.add_widget(self._jvm_edit)

        game_caption = QLabel("游戏参数")
        game_caption.setProperty("fieldLabel", True)
        card.add_widget(game_caption)
        self._game_args = QLineEdit()
        self._game_args.setPlaceholderText("传给游戏主类的附加参数，留空则使用默认")
        self._game_args.editingFinished.connect(self._on_game_args)
        card.add_widget(self._game_args)

        pre_caption = QLabel("启动前执行命令")
        pre_caption.setProperty("fieldLabel", True)
        card.add_widget(pre_caption)
        self._pre_cmd = QLineEdit()
        self._pre_cmd.setPlaceholderText("拉起游戏前运行的命令，留空则不执行（后续版本接入）")
        self._pre_cmd.editingFinished.connect(self._on_pre_command)
        card.add_widget(self._pre_cmd)

        java_row = QHBoxLayout()
        java_caption = QLabel("Java 列表")
        java_caption.setProperty("fieldLabel", True)
        self._java_combo = _GlassComboBox()
        self._java_combo.setProperty("versionPicker", True)
        self._java_combo.currentIndexChanged.connect(self._on_java_changed)
        self._java_refresh = QPushButton("刷新")
        self._java_refresh.setProperty("dialogButton", True)
        self._java_refresh.setCursor(Qt.PointingHandCursor)
        self._java_refresh.clicked.connect(self._refresh_java_list)
        java_row.addWidget(java_caption)
        java_row.addWidget(self._java_combo, 1)
        java_row.addWidget(self._java_refresh)
        card.add_layout(java_row)

        gc_row = QHBoxLayout()
        gc_caption = QLabel("内存管理")
        gc_caption.setProperty("fieldLabel", True)
        self._gc_combo = _GlassComboBox()
        self._gc_combo.setProperty("versionPicker", True)
        for key in C.GC_KEYS:
            self._gc_combo.addItem(C.GC_LABELS[key], key)
        self._gc_combo.currentIndexChanged.connect(self._on_gc_changed)
        gc_row.addWidget(gc_caption)
        gc_row.addWidget(self._gc_combo, 1)
        card.add_layout(gc_row)

        mem_caption = QLabel("内存分配")
        mem_caption.setProperty("fieldLabel", True)
        card.add_widget(mem_caption)

        self._mem_group = QButtonGroup(self)
        self._mem_auto = QRadioButton("自动配置")
        self._mem_custom = QRadioButton("自定义")
        self._mem_group.addButton(self._mem_auto)
        self._mem_group.addButton(self._mem_custom)
        self._mem_auto.toggled.connect(self._on_memory_mode)
        mem_mode_row = QHBoxLayout()
        mem_mode_row.addWidget(self._mem_auto)
        mem_mode_row.addWidget(self._mem_custom)
        mem_mode_row.addStretch(1)
        card.add_layout(mem_mode_row)

        self._mem_slider = _NoWheelSlider(Qt.Horizontal)
        self._mem_slider.setRange(512, 8192)
        self._mem_slider.setSingleStep(256)
        self._mem_slider.setPageStep(512)
        self._mem_value = QLabel("")
        self._mem_value.setProperty("cardValue", True)
        self._mem_slider.valueChanged.connect(self._on_memory_slider)
        mem_slider_row = QHBoxLayout()
        mem_slider_row.addWidget(self._mem_slider, 1)
        mem_slider_row.addWidget(self._mem_value)
        card.add_layout(mem_slider_row)

        self._mem_optimize = QCheckBox("启动游戏前进行内存优化")
        self._mem_optimize.toggled.connect(self._on_memory_optimize)
        card.add_widget(self._mem_optimize)

        self._mem_bar = QProgressBar()
        self._mem_bar.setRange(0, 100)
        self._mem_bar.setTextVisible(False)
        card.add_widget(self._mem_bar)
        self._mem_info = QLabel("")
        self._mem_info.setProperty("sectionHint", True)
        card.add_widget(self._mem_info)

        self._wrapper = QCheckBox("禁用 Java Launch Wrapper")
        self._unsafe = QCheckBox("禁用 LWJGL Unsafe Agent")
        self._gpu = QCheckBox("使用高性能显卡")
        self._ssl = QCheckBox("在正版登录时验证 SSL 证书")
        for check, attr in (
            (self._wrapper, "disable_launch_wrapper"),
            (self._unsafe, "disable_lwjgl_unsafe"),
            (self._gpu, "prefer_discrete_gpu"),
            (self._ssl, "verify_ssl"),
        ):
            check.toggled.connect(lambda _=False, a=attr: self._on_switch(a))
            card.add_widget(check)

        column.addWidget(card)
        column.addStretch(1)

        self.refresh()

    # ------------------------------------------------------------------ #
    # 回填
    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """把全局配置回填到全部控件（回填期间阻塞信号，不触发落盘）。"""
        controls = (
            self._isolation_combo,
            self._jvm_edit,
            self._game_args,
            self._pre_cmd,
            self._java_combo,
            self._gc_combo,
            self._mem_auto,
            self._mem_custom,
            self._mem_slider,
            self._mem_optimize,
            self._wrapper,
            self._unsafe,
            self._gpu,
            self._ssl,
        )
        for control in controls:
            control.blockSignals(True)
        try:
            self._jvm_edit.setPlainText(self._config.jvm_args)
            self._game_args.setText(self._config.game_args)
            self._pre_cmd.setText(self._config.pre_launch_command)
            self._select_combo_by_data(self._isolation_combo, self._config.isolation_mode)
            self._select_combo_by_data(self._gc_combo, self._config.gc_mode)
            self._mem_auto.setChecked(self._config.memory_mode != "custom")
            self._mem_custom.setChecked(self._config.memory_mode == "custom")
            self._mem_slider.setValue(self._config.custom_memory_mb)
            self._mem_optimize.setChecked(self._config.pre_launch_memory_optimize)
            self._wrapper.setChecked(self._config.disable_launch_wrapper)
            self._unsafe.setChecked(self._config.disable_lwjgl_unsafe)
            self._gpu.setChecked(self._config.prefer_discrete_gpu)
            self._ssl.setChecked(self._config.verify_ssl)
            self._refresh_java_list()
        finally:
            for control in controls:
                control.blockSignals(False)
        self._update_memory_controls()
        self._refresh_memory_info()

    @staticmethod
    def _select_combo_by_data(combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    # ------------------------------------------------------------------ #
    # 事件：写全局配置并落盘
    # ------------------------------------------------------------------ #
    def _commit(self) -> None:
        self._config.save()

    def _on_isolation_changed(self) -> None:
        key = self._isolation_combo.currentData()
        if key:
            self._config.isolation_mode = key
            self._commit()

    def _on_jvm_changed(self) -> None:
        self._config.jvm_args = self._jvm_edit.toPlainText()
        self._commit()

    def _on_game_args(self) -> None:
        self._config.game_args = self._game_args.text()
        self._commit()

    def _on_pre_command(self) -> None:
        self._config.pre_launch_command = self._pre_cmd.text()
        self._commit()

    def _on_gc_changed(self) -> None:
        key = self._gc_combo.currentData()
        if key:
            self._config.gc_mode = key
            self._commit()

    def _refresh_java_list(self) -> None:
        current = self._config.java_path
        self._java_combo.blockSignals(True)
        self._java_combo.clear()
        self._java_combo.addItem("自动探测（推荐）", "")
        entries = java_runtime.list_java()
        selected = 0
        for index, entry in enumerate(entries, start=1):
            version = entry.get("version") or "未知版本"
            self._java_combo.addItem(f"{version} · {entry['path']}", entry["path"])
            if entry["path"] == current:
                selected = index
        if current and not any(
            self._java_combo.itemData(i) == current
            for i in range(self._java_combo.count())
        ):
            self._java_combo.addItem(current, current)
            selected = self._java_combo.count() - 1
        self._java_combo.setCurrentIndex(selected)
        self._java_combo.blockSignals(False)

    def _on_java_changed(self) -> None:
        self._config.java_path = self._java_combo.currentData() or ""
        self._commit()

    def _on_memory_mode(self) -> None:
        self._config.memory_mode = (
            "custom" if self._mem_custom.isChecked() else "auto")
        self._update_memory_controls()
        self._refresh_memory_info()
        self._commit()

    def _on_memory_slider(self, value: int) -> None:
        self._config.custom_memory_mb = value
        self._update_memory_controls()
        self._refresh_memory_info()
        self._commit()

    def _on_memory_optimize(self, value: bool) -> None:
        self._config.pre_launch_memory_optimize = value
        self._commit()

    def _on_switch(self, attr: str) -> None:
        check = {
            "disable_launch_wrapper": self._wrapper,
            "disable_lwjgl_unsafe": self._unsafe,
            "prefer_discrete_gpu": self._gpu,
            "verify_ssl": self._ssl,
        }[attr]
        setattr(self._config, attr, check.isChecked())
        self._commit()

    def _update_memory_controls(self) -> None:
        custom = self._mem_custom.isChecked()
        self._mem_slider.setEnabled(custom)
        self._mem_value.setEnabled(custom)
        self._mem_value.setText(f"{self._mem_slider.value()} MB")

    def _allocated_mb(self) -> int:
        if self._config.memory_mode == "custom":
            return self._config.custom_memory_mb
        return C.DEFAULT_JVM_XMX_MB

    def _refresh_memory_info(self) -> None:
        total_mb, avail_mb = _physical_memory_mb()
        allocated = self._allocated_mb()
        if total_mb <= 0:
            self._mem_bar.setValue(0)
            self._mem_info.setText(f"游戏分配：{allocated} MB")
            return
        used_mb = total_mb - avail_mb
        ratio = int(used_mb / total_mb * 100)
        self._mem_bar.setValue(max(0, min(100, ratio)))
        self._mem_info.setText(
            f"已使用内存 {used_mb / 1024:.1f} GB / {total_mb / 1024:.1f} GB"
            f"　　游戏分配 {allocated / 1024:.1f} GB"
        )


class LaunchSettingsPage(QWidget):
    """设置页「启动」标签全部内容（滚动卡片）。"""

    def __init__(self, config, host, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._host = host
        self._switch_worker = None
        self.setObjectName("launch-page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_widget = QWidget()
        list_widget.setObjectName("settingsList")
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(12)

        self._build_account_section()
        # 全局启动设置（版本隔离 + 高级功能）：对所有版本生效的默认值，
        # 版本设置页未单独覆盖的版本跟随这里。
        self._global_panel = GlobalLaunchConfigPanel(config)
        self._list_layout.addWidget(self._global_panel)
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------ #
    # 刷新
    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """切到本标签时刷新账号状态与全局启动设置。"""
        self._refresh_account_state()
        self._global_panel.refresh()

    # ------------------------------------------------------------------ #
    # 1) 账号管理
    # ------------------------------------------------------------------ #
    def _build_account_section(self) -> None:
        card = Card("账号管理")
        # 单个当前账号行；所有操作收敛到悬停浮现的三点菜单。
        self._account_row = _AccountRow()
        self._account_row.more_button.clicked.connect(self._open_account_menu)
        card.add_widget(self._account_row)
        self._list_layout.addWidget(card)

    def _session(self):
        return getattr(self._host, "session", None)

    def _account_store(self):
        return getattr(self._host, "account_store", None)

    def _saved_official(self):
        """读取本地已保存的正版账号（含 refresh_token）；无有效凭据则返回 None。"""
        store = self._account_store()
        if store is None:
            return None
        try:
            return store.load()
        except OSError:
            return None

    # ---- 当前账号展示与三点菜单 ----
    def _current_account(self) -> tuple[str, str, str]:
        """返回当前账号 (kind, name, uuid)。"""
        session = self._session()
        if session is not None and getattr(session, "is_microsoft", False):
            return ("microsoft",
                    str(getattr(session, "name", "") or ""),
                    str(getattr(session, "uuid", "") or ""))
        name = self._config.player_name
        return ("offline", name, java_runtime.offline_uuid(name))

    def _open_account_menu(self) -> None:
        menu = _AccountMenu(self)
        menu.add_item("＋ 添加账号", self._open_add_account_dialog)

        # 存在其他可切换的离线账号时，给出统一「切换账号」入口（二级弹窗选择）。
        kind, current_name, _ = self._current_account()
        others = [n for n in self._config.offline_accounts
                  if n != current_name]
        # 离线态下若本地仍保留正版凭据，也可通过该入口切回正版。
        has_saved_official = kind == "offline" and self._saved_official() is not None
        if others or has_saved_official:
            menu.add_item("切换账号", self._open_switch_menu)

        menu.add_separator()
        if kind == "offline":
            menu.add_item("重命名账号", self._rename_current_account)
        menu.add_item("导入皮肤", self._import_skin)
        menu.add_item("导出皮肤", self._export_skin)
        menu.add_separator()
        if kind == "microsoft":
            menu.add_item("退出登录", self._logout_official, danger=True)
        else:
            menu.add_item("移除账号", self._remove_current_account, danger=True)

        menu.popup_below(self._account_row.more_button)

    def _build_switch_menu(self) -> "_AccountMenu":
        """构建二级弹窗：正版条目置顶（当前正版标注当前；离线态列已保存正版可切回），
        随后列全部离线账号，当前离线账号标注「（当前）」。"""
        kind, current_name, _uuid = self._current_account()
        sub = _AccountMenu(self, title="切换账号")
        saved = self._saved_official()
        if kind == "microsoft":
            # 当前正版：置顶标注当前，点击仅关闭弹窗。
            sub.add_item(current_name + "（当前）", lambda: None)
        elif saved:
            # 离线态但本地保留正版凭据：列出该正版账号，点击静默续期切回。
            sub.add_item(str(saved.get("name") or ""), self._switch_to_official)
        # 离线账号：当前离线昵称标注当前，其余点击即切换。
        for name in self._config.offline_accounts:
            if kind == "offline" and name == current_name:
                sub.add_item(name + "（当前）", lambda: None)
            else:
                sub.add_item(name, lambda n=name: self._switch_to_offline(n))
        return sub

    def _open_switch_menu(self) -> None:
        """打开二级弹窗；延迟到下一事件循环弹出，避免焦点抢占导致闪烁。"""
        sub = self._build_switch_menu()
        QTimer.singleShot(
            0, lambda: sub.popup_below(self._account_row.more_button))


    def _rename_current_account(self) -> None:
        _kind, old_name, _uuid = self._current_account()
        dialog = _RenameAccountDialog(old_name, self)
        if dialog.exec() != QDialog.Accepted:
            return
        new_name = dialog.value()
        if new_name == old_name:
            return
        accounts = self._config.offline_accounts
        if new_name in accounts:
            QMessageBox.information(
                self, C.APP_FULL_NAME,
                f"离线账号「{new_name}」已存在，无法重名。")
            return
        self._config.player_name = new_name
        if old_name in accounts:
            accounts[accounts.index(old_name)] = new_name
        elif new_name not in accounts:
            accounts.append(new_name)
        self._config.offline_accounts = accounts
        self._config.save()
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()

    def _remove_current_account(self) -> None:
        _kind, name, _uuid = self._current_account()
        answer = QMessageBox.question(
            self,
            C.APP_FULL_NAME,
            f"确定移除离线账号「{name}」吗？移除后将切换到其他账号。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._remove_offline_account(name)

    def _refresh_account_state(self) -> None:
        kind, name, uuid = self._current_account()
        self._account_row.set_state(kind, name, uuid)

    # ---- 添加 / 切换 / 移除账号 ----
    def _open_add_account_dialog(self) -> None:
        dialog = _AddAccountDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.kind == "offline":
            self._add_offline_account(dialog.name)
        else:
            self._open_official_login()

    def _add_offline_account(self, name: str, notify: bool = True) -> None:
        name = (name or "").strip()
        if not name:
            return
        accounts = self._config.offline_accounts
        if name in accounts:
            if notify:
                QMessageBox.information(self, C.APP_FULL_NAME, f"离线账号「{name}」已存在。")
            return
        accounts.append(name)
        self._config.offline_accounts = accounts
        # 新添加的离线账号直接切为当前离线身份。
        self._switch_to_offline(name)

    def _switch_to_offline(self, name: str) -> None:
        """临时切到离线：只切内存会话，保留本地正版凭据（不删 account.json）以便切回。"""
        session = self._session()
        if session is not None:
            session.switch_offline()
        self._config.player_name = name
        self._config.save()
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()

    def _switch_to_official(self) -> None:
        """用本地保存的 refresh_token 静默续期，切回正版会话。"""
        saved = self._saved_official()
        if not saved:
            return
        refresh_token = str(saved.get("refresh_token") or "")
        if not refresh_token:
            return
        worker = AccountRestoreWorker(refresh_token, parent=self)
        self._switch_worker = worker
        worker.succeeded.connect(self._on_switch_official_succeeded)
        worker.failed.connect(self._on_switch_official_failed)
        worker.start()

    def _on_switch_official_succeeded(self, profile: dict) -> None:
        """续期成功：切正版内存会话，回写轮换后的新刷新令牌，刷新本页与个人页。"""
        session = self._session()
        store = self._account_store()
        if session is not None:
            session.set_microsoft(profile)
        if store is not None:
            store.save(profile)
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()
        self._switch_worker = None

    def _on_switch_official_failed(self, message: str) -> None:
        """续期失败说明本地令牌已失效：按既有口径清除失效凭据，保持离线并提示。"""
        store = self._account_store()
        if store is not None:
            store.clear()
        self._switch_worker = None
        QMessageBox.information(
            self, C.APP_FULL_NAME,
            "正版登录态已失效，需要重新登录。" + str(message or ""))

    def shutdown(self) -> None:
        """窗口关闭前等待在途的切回正版线程收尾，避免 QThread 被析构触发原生崩溃。"""
        if self._switch_worker is not None and self._switch_worker.isRunning():
            self._switch_worker.requestInterruption()
            self._switch_worker.wait(int(C.RESTORE_HTTP_TIMEOUT * 1000) + 2000)
        self._switch_worker = None

    def _remove_offline_account(self, name: str) -> None:
        accounts = [n for n in self._config.offline_accounts if n != name]
        self._config.offline_accounts = accounts
        # 移除的若是当前离线昵称，回退到列表第一条；列表空则回退默认 Steve。
        if self._config.player_name == name:
            self._config.player_name = accounts[0] if accounts else "Steve"
        self._config.save()
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()

    def _open_official_login(self) -> None:
        session = self._session()
        store = self._account_store()
        if session is not None and getattr(session, "is_microsoft", False):
            self._refresh_account_state()
            return
        dialog = MsLoginDialog(self)
        if dialog.construction_error:
            QMessageBox.warning(self, C.APP_FULL_NAME, dialog.construction_error)
            return
        dialog.exec()
        if dialog.profile and session is not None:
            session.set_microsoft(dialog.profile)
            if store is not None:
                store.save(dialog.profile)
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()

    def _logout_official(self) -> None:
        answer = QMessageBox.question(
            self,
            C.APP_FULL_NAME,
            "确定退出当前正版账号吗？退出后将回到离线模式。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        session = self._session()
        store = self._account_store()
        if session is not None:
            session.switch_offline()
        if store is not None:
            store.clear()
        self._refresh_account_state()
        profile_page = getattr(self._host, "profile_page", None)
        if profile_page is not None:
            profile_page.refresh()

    def _custom_skin_dir(self) -> str:
        path = os.path.join(data_dir(), CUSTOM_SKIN_DIR)
        os.makedirs(path, exist_ok=True)
        return path

    def _import_skin(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, "选择皮肤图片", "", "皮肤图片 (*.png *.jpg *.jpeg)"
        )
        if not src:
            return
        try:
            import shutil

            dst = os.path.join(self._custom_skin_dir(), os.path.basename(src))
            shutil.copyfile(src, dst)
            self._config.custom_skin = dst
            self._config.save()
            QMessageBox.information(self, C.APP_FULL_NAME, "皮肤已导入，重启后在角色预览中生效。")
        except OSError as exc:
            QMessageBox.warning(self, C.APP_FULL_NAME, f"皮肤导入失败：{exc}")

    def _export_skin(self) -> None:
        src = self._config.custom_skin
        if not src or not os.path.isfile(src):
            QMessageBox.information(self, C.APP_FULL_NAME, "当前没有可导出的本地皮肤文件。")
            return
        dst, _ = QFileDialog.getSaveFileName(
            self, "导出皮肤", os.path.basename(src), "皮肤图片 (*.png)"
        )
        if not dst:
            return
        try:
            import shutil

            shutil.copyfile(src, dst)
            QMessageBox.information(self, C.APP_FULL_NAME, "皮肤已导出。")
        except OSError as exc:
            QMessageBox.warning(self, C.APP_FULL_NAME, f"皮肤导出失败：{exc}")
