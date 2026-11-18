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

"""版本设置页（v1.3.12.0 做实）。

入口：个人页「游戏版本」横条在鼠标移入时显现的三点按钮，点击后带着当前选中版本别名进入
本页；页面左上返回按钮回到启动页（个人页）。

左侧分区导航只有三项：**概览 / 设置 / 修改**（首项按用户口径写「概览」，不写「概述」，
也不设独立的 Mod 管理分区）。

- **概览**：版本信息条（加载器 + 头像，整合包用整合包头像）、个性化（10 个真实 MC 经典
  方块头像 + 自定义头像、修改版本名）、版本详细信息（mod / 光影包 / 材质包 / 数据包各有
  几个，点击展开成第二张图的列表，每项有图标、无图标显示问号）、高级设置、补齐文件 /
  删除版本；
- **设置**：本轮仍是骨架页；
- **修改**：按第三张图做实——加载器增删、互斥不兼容置灰、点「开始修改」真正重跑加载器
  下载 / 处理器链并更新版本（见 :class:`~cloud_launcher.ui.version_modify_worker.VersionModifyWorker`）。
"""
import os
import shutil
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFontMetrics, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import game_dirs
from .. import java_runtime
from .. import version_content
from .. import version_meta
from ..resources import resource_path
from ..version_launch_config import VersionLaunchConfig
from .card_widget import Card
from .content_scan_worker import ContentScanWorker
from .frosted_backdrop import capture_live_backdrop
from .launch_settings_page import (
    _GlassComboBox,
    _NoWheelSlider,
    _physical_memory_mb,
)
from .loader_probe_worker import LoaderProbeWorker
from .settings_page import SwitchButton
from .version_meta_worker import VersionMetaWorker
from .version_modify_worker import VersionModifyWorker

# 分区顺序即导航顺序与内容栈下标顺序；首项文案必须是「概览」。
SECTIONS = (
    ("overview", "概览"),
    ("settings", "设置"),
    ("modify", "修改"),
)

_NAV_WIDTH = 116
_NAV_ITEM_HEIGHT = 40
_ROW_HEIGHT = 38
_AVATAR_SIZE = 44
_ICON_SIZE = 32

# 已装 mod 达到该数量即锁定修改分区：mod 较多时切换版本 / 加载器极易造成不兼容。
MOD_LOCK_THRESHOLD = 20

_BEIJING_TZ = timezone(timedelta(hours=8))


def _format_version_time(raw: str) -> str:
    """把加载器 / MC 版本的原始时间戳或 ISO 串格式化为 `yyyy/MM/dd HH:mm`；无法解析返回空串。"""
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.isdigit():
        ts = int(s)
        if ts > 10_000_000_000:  # 13 位毫秒时间戳
            ts //= 1000
        try:
            dt = datetime.fromtimestamp(ts, tz=_BEIJING_TZ)
        except (OverflowError, OSError, ValueError):
            return ""
        return dt.strftime("%Y/%m/%d %H:%M")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(_BEIJING_TZ)
        return dt.strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return s[:16]


def _version_time_text(versions: list[dict], ver: str) -> str:
    """从版本列表里取指定版本的已格式化发布时间；找不到或无时间返回空串。"""
    ver = str(ver or "")
    for item in versions or []:
        if str(item.get("version") or "") == ver:
            return _format_version_time(item.get("time") or "")
    return ""

# 头像选择器里的 10 个真实方块（资源来自 blockrender.dev，非自绘）。
BLOCK_AVATAR_IDS = (
    "grass_block", "dirt", "stone", "cobblestone", "oak_planks",
    "oak_log", "bedrock", "glass", "sand", "bricks",
)


# --------------------------------------------------------------------------- #
# 通用辅助
# --------------------------------------------------------------------------- #
def _block_resource(block_id: str) -> str:
    return resource_path("blocks/%s.png" % block_id)


def _avatar_file(alias: str, avatar_key: str) -> str:
    """把 install_meta 里的头像标识解析为真实文件路径；文件不存在回退草方块。"""
    key = str(avatar_key or "grass_block")
    if key == "custom":
        path = game_dirs.custom_avatar_path(alias)
    elif key == "modpack":
        path = os.path.join(game_dirs.version_dir(alias), "pack.png")
    else:
        path = _block_resource(key)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    return _block_resource("grass_block")


def _pixmap_from_bytes(data: bytes | None, size: int) -> QPixmap | None:
    if not data:
        return None
    pix = QPixmap()
    if not pix.loadFromData(data):
        return None
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _icon_label_from_bytes(data: bytes | None, size: int = _ICON_SIZE) -> QLabel:
    """内容行图标：有图用图，无图显示问号「?」。"""
    label = QLabel()
    label.setObjectName("contentRowIcon")
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignCenter)
    pix = _pixmap_from_bytes(data, size)
    if pix is not None:
        label.setPixmap(pix)
    else:
        label.setText("?")
        label.setStyleSheet(
            "font-size:16px;font-weight:700;color:%s;" % C.COLOR_TEXT_LIGHT)
    return label


# --------------------------------------------------------------------------- #
# 玻璃对话框基类
# --------------------------------------------------------------------------- #
class _GlassDialog(QDialog):
    """无边框透明根 + 一块自绘磨砂 Card 的弹窗基类。"""

    def __init__(self, title: str = "", parent=None, min_width: int = 320) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(min_width)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.card = Card(title)
        # 独立顶层弹窗：磨砂采样以主窗口为坐标基准，正确取到弹窗正后方的壁纸。
        self._live_ref = parent.window() if parent is not None else None
        if self._live_ref is not None:
            self.card.set_reference_window(self._live_ref)
        self._live_captured = False
        outer.addWidget(self.card)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        # 首次显示前抓取父窗口真实渲染（独立顶层窗不会被抓进其自身 grab），让卡片
        # 真正模糊后方内容，无壁纸时也不会叠字，且不做白板。
        if not self._live_captured and self._live_ref is not None:
            clear_pix, blur_pix = capture_live_backdrop(self._live_ref)
            self.card.set_live_backdrop(clear_pix, blur_pix, self._live_ref)
            self._live_captured = True
        self._center_over_reference()
        super().showEvent(event)

    def _center_over_reference(self) -> None:
        """居中到父窗口客户区并限制在其边界内，避免卡片超出快照范围出现无内容黑边。"""
        if self._live_ref is None:
            return
        ref = self._live_ref
        # 用客户区原点（mapToGlobal）而非 frameGeometry，与卡片 mapTo 客户区口径一致。
        client_origin = ref.mapToGlobal(QPoint(0, 0))
        client_w, client_h = ref.width(), ref.height()
        geo = self.frameGeometry()
        width, height = geo.width(), geo.height()
        x = client_origin.x() + (client_w - width) // 2
        y = client_origin.y() + (client_h - height) // 2
        # 夹在客户区内，保证卡片不越出快照范围。
        x = max(client_origin.x(), min(x, client_origin.x() + client_w - width))
        y = max(client_origin.y(), min(y, client_origin.y() + client_h - height))
        self.move(x, y)

    def add_widget(self, widget) -> None:
        self.card.add_widget(widget)

    def add_layout(self, layout) -> None:
        self.card.add_layout(layout)

    def button_row(self, buttons: list[QPushButton]) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)
        for button in buttons:
            row.addWidget(button)
        self.card.add_layout(row)
        return row


def _dialog_button(text: str, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    # 弹窗按钮统一 36 高、圆角 12，与 modeButton 同一设计语言；主按钮用 dialogPrimary
    # 专属规则，不套用主窗口 44 高/圆角 22 的胶囊规则——Qt 在 border-radius 超过控件半高时
    # 会直接丢弃圆角（36 高的半高是 18，配 22 圆角会被渲染成方形），故弹窗单独定义。
    if primary:
        button.setProperty("dialogPrimary", True)
    else:
        button.setProperty("modeButton", True)
    button.setFixedHeight(36)
    button.setMinimumWidth(96)
    button.setCursor(Qt.PointingHandCursor)
    return button


class _RenameDialog(_GlassDialog):
    def __init__(self, current: str, parent=None) -> None:
        super().__init__("修改版本名", parent, min_width=340)
        self._edit = QLineEdit(current)
        self._edit.setFixedHeight(36)
        self._edit.selectAll()
        self.add_widget(self._edit)

        ok = _dialog_button("确定", primary=True)
        cancel = _dialog_button("取消")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        self.button_row([cancel, ok])

    def value(self) -> str:
        return self._edit.text().strip()


class _ConfirmDialog(_GlassDialog):
    def __init__(self, message: str, parent=None, danger: bool = True) -> None:
        super().__init__("请确认", parent, min_width=340)
        label = QLabel(message)
        label.setWordWrap(True)
        label.setProperty("vsHint", True)
        self.add_widget(label)

        ok = _dialog_button("确定", primary=True)
        cancel = _dialog_button("取消")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        self.button_row([cancel, ok])


class _VersionRow(QFrame):
    """版本列表里的一行：版本号 + 右侧发布时间；点击回调所选版本号。"""

    def __init__(self, ver: str, time_text: str, selected: bool, on_pick,
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("loaderVersionRow")
        self.setProperty("selected", bool(selected))
        self.setCursor(Qt.PointingHandCursor)
        self._on_pick = on_pick
        self._version = ver

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        title = QLabel(ver)
        title.setObjectName("loaderVersionRowTitle")
        layout.addWidget(title, 1)
        if time_text:
            time_label = QLabel(time_text)
            time_label.setObjectName("loaderVersionRowTime")
            layout.addWidget(time_label)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and callable(self._on_pick):
            self._on_pick(self._version)
        super().mousePressEvent(event)


# MC 版本清单分组展示顺序与中文小标题（april 愚人节版本不进选择列表）。
_MC_GROUPS = (
    ("release", "正式版"),
    ("snapshot", "预览版"),
    ("ancient", "远古版"),
)


class _McVersionDialog(_GlassDialog):
    """选择 Minecraft 底座版本：按正式 / 预览 / 远古分组，版本号右侧带发布时间。"""

    _DIALOG_WIDTH = 360
    _LIST_MAX_HEIGHT = 420

    def __init__(self, manifest: dict, current_version: str = "", parent=None) -> None:
        super().__init__("选择 Minecraft 版本", parent,
                         min_width=self._DIALOG_WIDTH)
        self._chosen = ""

        scroll = QScrollArea()
        scroll.setObjectName("mcVersionScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(self._LIST_MAX_HEIGHT)

        host = QWidget()
        host.setObjectName("page-container")
        column = QVBoxLayout(host)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        populated = False
        for key, label in _MC_GROUPS:
            entries = manifest.get(key) or []
            if not entries:
                continue
            populated = True
            group_title = QLabel("%s (%d)" % (label, len(entries)))
            group_title.setObjectName("loaderVersionCount")
            column.addWidget(group_title)
            for item in entries:
                ver = str(item.get("id") or "")
                if not ver:
                    continue
                time_text = _format_version_time(item.get("time") or "")
                row = _VersionRow(ver, time_text, ver == str(current_version or ""),
                                   self._pick, host)
                column.addWidget(row)
        if not populated:
            empty = QLabel("暂无版本清单，请检查网络后重试。")
            empty.setProperty("vsHint", True)
            column.addWidget(empty)
        column.addStretch(1)

        scroll.setWidget(host)
        self.add_widget(scroll)

        cancel = _dialog_button("取消")
        cancel.clicked.connect(self.reject)
        self.button_row([cancel])

    def _pick(self, version: str) -> None:
        self._chosen = version
        self.accept()

    def chosen(self) -> str:
        return self._chosen


class _ProgressDialog(_GlassDialog):
    """修改 / 补齐文件的进度弹窗，可取消。"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(title, parent, min_width=360)
        self._phase = QLabel("准备中…")
        self._phase.setObjectName("vsBusy")
        self.add_widget(self._phase)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self.add_widget(self._bar)

        self._percent = QLabel("0%")
        self._percent.setObjectName("vsBusy")
        self.add_widget(self._percent)

        self._cancel = _dialog_button("取消")
        self._cancel.clicked.connect(self.reject)
        self.button_row([self._cancel])

    def update_progress(self, snapshot: dict) -> None:
        percent = float(snapshot.get("percent") or 0.0)
        self._bar.setValue(int(percent))
        self._percent.setText("%.0f%%" % percent)
        message = str(snapshot.get("message") or snapshot.get("phase_label") or "")
        if message:
            self._phase.setText(message)

    def hide_cancel(self) -> None:
        self._cancel.setEnabled(False)
        self._cancel.setVisible(False)


# --------------------------------------------------------------------------- #
# 内容展开列表弹窗（第二张图）
# --------------------------------------------------------------------------- #
class _ContentListDialog(_GlassDialog):
    """内容列表：近全屏大尺寸、内部滚动（隐藏滚动条）、名称省略、逐项开关、删除、总开关。"""

    _MIN_DIALOG_WIDTH = 460
    _MAX_DIALOG_WIDTH = 680
    _MIN_DIALOG_HEIGHT = 400
    _MAX_DIALOG_HEIGHT = 560
    # 名称列之外的固定占位（卡片/行边距、图标、开关、删除按钮与间距）。
    _NAME_RESERVED = 212

    def __init__(self, kind: str, parent=None) -> None:
        # 按所在屏幕取适中尺寸（用户口径：近全屏太大，调小一点；且要落在主窗口内）。
        parent_win = parent.window() if parent is not None else None
        screen = parent_win.screen() if parent_win is not None else None
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        if avail is not None:
            dialog_width = max(self._MIN_DIALOG_WIDTH,
                               min(self._MAX_DIALOG_WIDTH,
                                   int(avail.width() * 0.62)))
            dialog_height = max(self._MIN_DIALOG_HEIGHT,
                                min(self._MAX_DIALOG_HEIGHT,
                                    int(avail.height() * 0.72)))
        else:
            dialog_width, dialog_height = self._MIN_DIALOG_WIDTH, 480

        super().__init__("", parent, min_width=dialog_width)
        self._kind = kind
        self._page = parent
        self._dialog_width = dialog_width
        self._name_width = dialog_width - self._NAME_RESERVED
        self.card.set_title(version_content.KIND_TITLES[kind])
        self._row_records: list[dict] = []

        # 顶部总开关行（一键关闭 / 打开全部）。
        master = QFrame()
        master.setObjectName("contentMasterRow")
        master_layout = QHBoxLayout(master)
        master_layout.setContentsMargins(4, 0, 4, 0)
        master_layout.setSpacing(8)
        master_label = QLabel("全部")
        master_label.setObjectName("contentRowName")
        self._master_switch = SwitchButton()
        master_layout.addWidget(master_label)
        master_layout.addStretch(1)
        master_layout.addWidget(self._master_switch)
        self.add_widget(master)
        self._master_switch.toggled.connect(self._on_master_toggled)

        self._busy = QLabel("正在读取…")
        self._busy.setObjectName("vsBusy")
        self.add_widget(self._busy)

        # 内部滚动区：占满剩余高度，滚动条彻底隐藏（滚轮仍可用）。
        self._scroll = QScrollArea()
        self._scroll.setObjectName("contentListScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._list_host = QWidget()
        self._list_host.setObjectName("page-container")
        self._list_column = QVBoxLayout(self._list_host)
        self._list_column.setContentsMargins(0, 0, 0, 0)
        self._list_column.setSpacing(8)
        self._list_column.addStretch(1)
        self._scroll.setWidget(self._list_host)
        self._scroll.setVisible(False)
        # stretch=1：让滚动区吃掉除标题/总开关/按钮外的全部高度。
        self.card.body_layout.addWidget(self._scroll, 1)

        close = _dialog_button("关闭")
        close.clicked.connect(self.accept)
        self.button_row([close])
        self.setFixedWidth(self._dialog_width)
        self.setFixedHeight(dialog_height)

    def populate(self, entries: list[dict]) -> None:
        self._busy.setVisible(False)
        # 清空旧行（保留末尾 stretch）。
        while self._list_column.count() > 1:
            item = self._list_column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._row_records = []
        if not entries:
            empty = QLabel("暂无内容")
            empty.setObjectName("vsBusy")
            empty.setAlignment(Qt.AlignCenter)
            self._list_column.insertWidget(0, empty)
            self._master_switch.setEnabled(False)
        else:
            self._master_switch.setEnabled(True)
            for index, entry in enumerate(entries):
                record = self._build_row(entry)
                self._row_records.append(record)
                self._list_column.insertWidget(index, record["row"])
            self._sync_master()
        self._scroll.setVisible(True)

    def _build_row(self, entry: dict) -> dict:
        row = QFrame()
        row.setObjectName("contentRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(_icon_label_from_bytes(entry.get("icon"), _ICON_SIZE))

        texts = QVBoxLayout()
        texts.setSpacing(2)
        raw_name = str(entry.get("name") or "未命名")
        name = QLabel()
        name.setObjectName("contentRowName")
        name.setFixedWidth(self._name_width)
        name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name.setText(self._elide(raw_name))
        name.setToolTip(raw_name)
        texts.addWidget(name)
        detail_text = str(entry.get("detail") or "")
        if detail_text:
            detail = QLabel()
            detail.setObjectName("contentRowDetail")
            detail.setFixedWidth(self._name_width)
            detail.setText(self._elide(detail_text))
            detail.setToolTip(detail_text)
            texts.addWidget(detail)
        layout.addLayout(texts, 1)

        switch = SwitchButton()
        switch.setChecked(not bool(entry.get("disabled")))
        switch.toggled.connect(
            lambda checked, e=entry: self._on_row_toggled(e, checked))
        layout.addWidget(switch)

        delete = QPushButton("删")
        delete.setObjectName("contentRowDelete")
        delete.setFixedSize(34, 34)
        delete.setCursor(Qt.PointingHandCursor)
        delete.setToolTip("删除")
        delete.clicked.connect(lambda _f=False, e=entry: self._on_delete(e))
        layout.addWidget(delete)

        return {"row": row, "entry": entry, "switch": switch, "delete": delete}

    def _elide(self, text: str) -> str:
        return QFontMetrics(self.font()).elidedText(
            str(text), Qt.ElideRight, self._name_width)

    def _on_row_toggled(self, entry: dict, checked: bool) -> None:
        ok, reason = version_content.toggle_content(
            entry.get("path", ""), bool(checked))
        if not ok:
            record = self._find_record(entry)
            if record is not None:  # 回滚开关视觉。
                record["switch"].blockSignals(True)
                record["switch"].setChecked(not checked)
                record["switch"].blockSignals(False)
            self._show_error(reason)
            return
        entry["disabled"] = not bool(checked)
        # 同步更新路径（加/去 .disabled），保证后续开关与删除指向真实文件。
        path = str(entry.get("path", ""))
        if checked and path.endswith(version_content._DISABLED_SUFFIX):
            entry["path"] = path[: -len(version_content._DISABLED_SUFFIX)]
        elif (not checked
              and not path.endswith(version_content._DISABLED_SUFFIX)):
            entry["path"] = path + version_content._DISABLED_SUFFIX
        self._sync_master()
        self._notify_parent()

    def _on_master_toggled(self, checked: bool) -> None:
        # 逐个 setChecked 会触发各自的 _on_row_toggled，数据层与总开关同步都在其中。
        for record in list(self._row_records):
            if record["switch"].isChecked() != checked:
                record["switch"].setChecked(checked)
        self._sync_master()

    def _on_delete(self, entry: dict) -> None:
        name = str(entry.get("name") or "")
        confirm = _ConfirmDialog(
            "确定删除「%s」吗？该内容会被永久删除，且无法恢复。" % name, self)
        if confirm.exec() != QDialog.Accepted:
            return
        ok, reason = version_content.delete_content(entry.get("path", ""))
        if not ok:
            self._show_error(reason)
            return
        record = self._find_record(entry)
        if record is not None:
            self._row_records.remove(record)
            self._list_column.removeWidget(record["row"])
            record["row"].deleteLater()
        if not self._row_records:
            empty = QLabel("暂无内容")
            empty.setObjectName("vsBusy")
            empty.setAlignment(Qt.AlignCenter)
            self._list_column.insertWidget(0, empty)
            self._master_switch.setEnabled(False)
        self._sync_master()
        self._notify_parent()

    def _sync_master(self) -> None:
        if not self._row_records:
            return
        all_on = all(r["switch"].isChecked() for r in self._row_records)
        self._master_switch.blockSignals(True)
        self._master_switch.setChecked(all_on)
        self._master_switch.blockSignals(False)

    def _find_record(self, entry: dict) -> dict | None:
        for record in self._row_records:
            if record["entry"] is entry:
                return record
        return None

    def _notify_parent(self) -> None:
        if self._page is not None and hasattr(self._page, "_refresh_counts"):
            self._page._refresh_counts()

    def _show_error(self, message: str) -> None:
        if self._page is not None and hasattr(self._page, "_show_message"):
            self._page._show_message(message)


# --------------------------------------------------------------------------- #
# 头像选择器
# --------------------------------------------------------------------------- #
class AvatarPicker(QWidget):
    """10 个真实方块头像 + 自定义头像的选择网格。"""

    def __init__(self, alias: str, current: str, on_pick, parent=None) -> None:
        super().__init__(parent)
        self._alias = alias
        self._on_pick = on_pick
        self._buttons: dict[str, QPushButton] = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for index, block_id in enumerate(BLOCK_AVATAR_IDS):
            button = QPushButton()
            button.setObjectName("avatarOption")
            button.setCheckable(True)
            button.setFixedSize(44, 44)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(block_id)
            pix = QPixmap(_block_resource(block_id))
            if not pix.isNull():
                button.setIcon(QIcon(pix))
                button.setIconSize(button.size() * 0.92)
            button.clicked.connect(lambda _f=False, k=block_id: self._on_pick(k))
            grid.addWidget(button, index // 5, index % 5)
            self._buttons[block_id] = button

        custom = QPushButton("+")
        custom.setObjectName("avatarOption")
        custom.setCheckable(True)
        custom.setFixedSize(44, 44)
        custom.setCursor(Qt.PointingHandCursor)
        custom.setToolTip("自定义头像")
        custom.clicked.connect(self._choose_custom)
        grid.addWidget(custom, 1, 5)
        self._buttons["custom"] = custom

        self.set_current(current)

    def set_alias(self, alias: str) -> None:
        self._alias = alias

    def set_current(self, key: str) -> None:
        for value, button in self._buttons.items():
            button.setChecked(value == key)

    def _choose_custom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择自定义头像", "", "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        target = game_dirs.custom_avatar_path(self._alias)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(path, target)
        except OSError:
            return
        self._on_pick("custom")


# --------------------------------------------------------------------------- #
# 修改分区加载器行
# --------------------------------------------------------------------------- #
class LoaderRow(QFrame):
    """修改分区一行：顶部名称 + 状态 + 移除 X + 展开箭头，下方内联展开全部版本列表。"""

    def __init__(self, key: str, name: str, on_select, on_pick_version,
                 on_remove=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("loaderRow")
        self._key = key
        self._on_select = on_select
        self._on_pick_version = on_pick_version
        self._on_remove = on_remove
        self._expanded = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(14, 6, 10, 6)
        head.setSpacing(10)
        root.addLayout(head)

        self._name = QLabel(name)
        self._name.setObjectName("loaderRowName")
        self._name.setFixedWidth(92)
        head.addWidget(self._name)

        self._status_col = QWidget()
        self._status_col.setObjectName("loaderRowStatusCol")
        col = QVBoxLayout(self._status_col)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        self._status = QLabel("")
        self._status.setObjectName("loaderRowStatus")
        col.addWidget(self._status)
        self._sub = QLabel("")
        self._sub.setObjectName("loaderRowSub")
        col.addWidget(self._sub)
        head.addWidget(self._status_col, 1)

        self._remove = QPushButton("×")
        self._remove.setObjectName("loaderRowRemove")
        self._remove.setFixedSize(26, 26)
        self._remove.setCursor(Qt.PointingHandCursor)
        self._remove.clicked.connect(self._handle_remove)
        self._remove.setVisible(False)
        head.addWidget(self._remove)

        self._chevron = QLabel("›")
        self._chevron.setObjectName("loaderRowChevron")
        self._chevron.setFixedSize(20, 26)
        head.addWidget(self._chevron)

        self._body = QWidget()
        self._body.setObjectName("loaderRowBody")
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(10, 0, 10, 8)
        body_layout.setSpacing(4)
        self._count = QLabel("")
        self._count.setObjectName("loaderVersionCount")
        body_layout.addWidget(self._count)
        self._option_box = QVBoxLayout()
        self._option_box.setSpacing(2)
        body_layout.addLayout(self._option_box)
        self._body.setVisible(False)
        root.addWidget(self._body)

    def _handle_remove(self) -> None:
        if callable(self._on_remove):
            self._on_remove(self._key)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.property("selectable"):
            self._on_select(self._key)
        super().mousePressEvent(event)

    def _rebuild_options(self, versions: list[dict], current: str) -> None:
        while self._option_box.count():
            item = self._option_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        current = str(current or "")
        valid = [item for item in versions if str(item.get("version") or "")]
        self._count.setText("全部版本 (%d)" % len(valid))
        for item in valid:
            ver = str(item.get("version") or "")
            time_text = _format_version_time(item.get("time") or "")
            row = _VersionRow(
                ver, time_text, ver == current,
                lambda v: self._on_pick_version(self._key, v))
            self._option_box.addWidget(row)

    def set_state(self, *, selectable: bool, status: str,
                  show_remove: bool, show_chevron: bool,
                  disabled: bool = False, versions: list[dict] = (),
                  current: str = "", expanded: bool = False,
                  sub: str = "") -> None:
        self.setProperty("selectable", bool(selectable))
        self.setProperty("disabledRow", bool(disabled))
        self.setEnabled(not disabled)
        self._status.setText(status)
        self._sub.setText(sub)
        self._sub.setVisible(bool(sub))
        self._remove.setVisible(show_remove)
        self._chevron.setVisible(show_chevron)
        # 记录期望可见态，供离屏逻辑测试（isVisible 需整链真正显示才为真）。
        self._show_remove = bool(show_remove)
        self._show_chevron = bool(show_chevron)

        self._rebuild_options(list(versions), current)
        self._expanded = bool(expanded) and bool(versions)
        self._body.setVisible(self._expanded)
        self._chevron.setText("∨" if self._expanded else "›")
        # 触发属性选择器重新求值。
        self.style().unpolish(self)
        self.style().polish(self)


# --------------------------------------------------------------------------- #
# 主页面
# --------------------------------------------------------------------------- #
class VersionSettingsPage(QWidget):
    """单个版本的设置页：三分区导航 + 分区内容，返回启动页。"""

    closed = Signal()

    def __init__(self, config=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("versionSettingsPage")
        self._config = config
        self._alias = ""
        # v1.3.21.0：本版本独立的启动配置视图（覆盖 + 默认兜底）。
        self._launch_cfg = VersionLaunchConfig(config, "")
        self._mc_version = ""
        self._loader = C.LOADER_VANILLA
        self._loader_version = ""
        self._meta: dict = {}

        # 修改分区工作态。
        self._chosen_loader = C.LOADER_VANILLA
        self._chosen_version = ""
        self._chosen_mc_version = ""
        self._expanded_loader = ""
        self._probe: dict | None = None
        # MC 版本清单（分组字典）缓存；None 表示尚未拉取。
        self._manifest: dict | None = None

        # 后台线程引用。
        self._content_worker: ContentScanWorker | None = None
        self._probe_worker: LoaderProbeWorker | None = None
        self._meta_worker: VersionMetaWorker | None = None
        self._modify_worker: VersionModifyWorker | None = None
        self._progress_dialog: _ProgressDialog | None = None
        self._content_dialog: _ContentListDialog | None = None

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI 搭建
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(self._build_header_row())

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addLayout(self._build_section_nav())

        self._stack = QStackedWidget()
        self._stack.setObjectName("vsStack")
        self._stack.addWidget(self._build_overview_section())
        self._stack.addWidget(self._build_settings_section())
        self._stack.addWidget(self._build_modify_section())

        scroll = QScrollArea()
        scroll.setObjectName("vs-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 按用户要求删除竖向滚动条（滚轮仍可滚动），彻底隐藏而非占位。
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self._stack)
        body.addWidget(scroll, 1)

        outer.addLayout(body, 1)
        self._switch_section("overview")

    def _build_header_row(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)
        header.setSpacing(12)

        self._back_button = QPushButton("←")
        self._back_button.setObjectName("vsBackBtn")
        self._back_button.setFixedSize(36, 36)
        self._back_button.setCursor(Qt.PointingHandCursor)
        self._back_button.setToolTip("返回启动页")
        self._back_button.clicked.connect(self.closed.emit)
        header.addWidget(self._back_button)

        title = QLabel("版本设置")
        title.setProperty("vsTitle", True)
        header.addWidget(title)

        self._version_title = QLabel("—")
        self._version_title.setProperty("vsVersionTitle", True)
        header.addWidget(self._version_title)

        header.addStretch(1)
        self._loader_chip = QLabel("—")
        self._loader_chip.setProperty("vsSkeletonChip", True)
        header.addWidget(self._loader_chip)
        return header

    def _build_section_nav(self) -> QVBoxLayout:
        nav = QVBoxLayout()
        nav.setSpacing(8)
        self._section_buttons: dict[str, QPushButton] = {}
        for key, text in SECTIONS:
            button = QPushButton(text)
            button.setProperty("vsNavItem", True)
            button.setCheckable(True)
            button.setFixedSize(_NAV_WIDTH, _NAV_ITEM_HEIGHT)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, k=key: self._switch_section(k))
            nav.addWidget(button)
            self._section_buttons[key] = button
        nav.addStretch(1)
        return nav

    # ---------- 概览 ---------- #
    def _build_overview_section(self) -> QWidget:
        page = QWidget()
        page.setObjectName("vsSectionPage")
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 8, 0)
        column.setSpacing(12)

        column.addWidget(self._build_info_card())
        column.addWidget(self._build_personalize_card())
        column.addWidget(self._build_detail_card())
        column.addWidget(self._build_advanced_card())
        column.addStretch(1)
        return page

    def _build_info_card(self) -> Card:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(14)
        self._info_icon = QLabel()
        self._info_icon.setFixedSize(_AVATAR_SIZE, _AVATAR_SIZE)
        row.addWidget(self._info_icon)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self._info_title = QLabel("—")
        self._info_title.setProperty("vsInfoTitle", True)
        texts.addWidget(self._info_title)
        self._info_sub = QLabel("")
        self._info_sub.setProperty("vsInfoSub", True)
        texts.addWidget(self._info_sub)
        row.addLayout(texts, 1)
        card.add_layout(row)
        return card

    def _build_personalize_card(self) -> Card:
        card = Card("个性化")

        caption = QLabel("头像")
        caption.setProperty("vsFieldCaption", True)
        card.add_widget(caption)

        self._avatar_picker = AvatarPicker(
            self._alias, "grass_block", self._pick_avatar)
        card.add_widget(self._avatar_picker)

        rename = QPushButton("修改版本名")
        rename.setProperty("modeButton", True)
        rename.setFixedHeight(_ROW_HEIGHT)
        rename.setCursor(Qt.PointingHandCursor)
        rename.clicked.connect(self._open_rename)
        card.add_widget(rename)
        return card

    def _build_detail_card(self) -> Card:
        card = Card("版本详细信息")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._count_buttons: dict[str, QPushButton] = {}
        kinds = ("mod", "shader", "resourcepack", "datapack")
        labels = ("mod", "光影包", "材质包", "数据包")
        for index, (kind, label) in enumerate(zip(kinds, labels)):
            button = QPushButton("%s：0" % label)
            # 单独立 countButton 玻璃 chip，避免 modeButton 白片观感（用户不要白板）。
            button.setProperty("countButton", True)
            button.setFixedHeight(_ROW_HEIGHT)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _f=False, k=kind: self._open_content_list(k))
            grid.addWidget(button, index // 2, index % 2)
            grid.setColumnStretch(index % 2, 1)
            self._count_buttons[kind] = button
        card.add_layout(grid)
        return card

    def _build_advanced_card(self) -> Card:
        card = Card("高级设置")
        hint = QLabel("「补齐文件」可修复缺失或损坏的版本文件；「删除版本」会一并移除该版本的全部文件。")
        hint.setProperty("vsHint", True)
        hint.setWordWrap(True)
        card.add_widget(hint)

        row = QHBoxLayout()
        row.setSpacing(10)

        repair = QPushButton("补齐文件")
        repair.setProperty("modeButton", True)
        repair.setFixedHeight(_ROW_HEIGHT)
        repair.setCursor(Qt.PointingHandCursor)
        repair.clicked.connect(self._repair_files)
        row.addWidget(repair, 1)

        delete = QPushButton("删除版本")
        delete.setProperty("modeButton", True)
        delete.setFixedHeight(_ROW_HEIGHT)
        delete.setCursor(Qt.PointingHandCursor)
        delete.clicked.connect(self._delete_version)
        row.addWidget(delete, 1)
        card.add_layout(row)
        return card

    # ---------- 设置（骨架） ---------- #
    def _build_settings_section(self) -> QWidget:
        page = QWidget()
        page.setObjectName("vsSectionPage")
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 8, 0)
        column.setSpacing(12)

        # ---- 卡片 1：版本隔离 ----
        iso_card = Card("版本隔离")
        iso_caption = QLabel("隔离策略")
        iso_caption.setProperty("fieldLabel", True)
        iso_card.add_widget(iso_caption)
        self._set_isolation_combo = _GlassComboBox()
        self._set_isolation_combo.setProperty("versionPicker", True)
        for key in C.ISOLATION_KEYS:
            self._set_isolation_combo.addItem(C.ISOLATION_LABELS[key], key)
        self._set_isolation_combo.currentIndexChanged.connect(
            self._on_set_isolation_changed)
        iso_card.add_widget(self._set_isolation_combo)
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
        self._set_jvm_edit = QTextEdit()
        self._set_jvm_edit.setPlaceholderText(
            "-XX:-OmitStackTraceInFastThrow\n"
            "-Dfml.ignoreInvalidMinecraftCertificates=True\n"
            "-Dfml.ignorePatchDiscrepancies=True"
        )
        self._set_jvm_edit.setFixedHeight(88)
        self._set_jvm_edit.textChanged.connect(self._on_set_jvm_changed)
        card.add_widget(self._set_jvm_edit)

        game_caption = QLabel("游戏参数")
        game_caption.setProperty("fieldLabel", True)
        card.add_widget(game_caption)
        self._set_game_args = QLineEdit()
        self._set_game_args.setPlaceholderText("传给游戏主类的附加参数，留空则使用默认")
        self._set_game_args.editingFinished.connect(self._on_set_game_args)
        card.add_widget(self._set_game_args)

        pre_caption = QLabel("启动前执行命令")
        pre_caption.setProperty("fieldLabel", True)
        card.add_widget(pre_caption)
        self._set_pre_cmd = QLineEdit()
        self._set_pre_cmd.setPlaceholderText("拉起游戏前运行的命令，留空则不执行（后续版本接入）")
        self._set_pre_cmd.editingFinished.connect(self._on_set_pre_command)
        card.add_widget(self._set_pre_cmd)

        java_row = QHBoxLayout()
        java_caption = QLabel("Java 列表")
        java_caption.setProperty("fieldLabel", True)
        self._set_java_combo = _GlassComboBox()
        self._set_java_combo.setProperty("versionPicker", True)
        self._set_java_combo.currentIndexChanged.connect(self._on_set_java_changed)
        self._set_java_refresh = QPushButton("刷新")
        self._set_java_refresh.setProperty("dialogButton", True)
        self._set_java_refresh.setCursor(Qt.PointingHandCursor)
        self._set_java_refresh.clicked.connect(self._refresh_set_java_list)
        java_row.addWidget(java_caption)
        java_row.addWidget(self._set_java_combo, 1)
        java_row.addWidget(self._set_java_refresh)
        card.add_layout(java_row)

        gc_row = QHBoxLayout()
        gc_caption = QLabel("内存管理")
        gc_caption.setProperty("fieldLabel", True)
        self._set_gc_combo = _GlassComboBox()
        self._set_gc_combo.setProperty("versionPicker", True)
        for key in C.GC_KEYS:
            self._set_gc_combo.addItem(C.GC_LABELS[key], key)
        self._set_gc_combo.currentIndexChanged.connect(self._on_set_gc_changed)
        gc_row.addWidget(gc_caption)
        gc_row.addWidget(self._set_gc_combo, 1)
        card.add_layout(gc_row)

        mem_caption = QLabel("内存分配")
        mem_caption.setProperty("fieldLabel", True)
        card.add_widget(mem_caption)

        self._set_mem_group = QButtonGroup(self)
        self._set_mem_auto = QRadioButton("自动配置")
        self._set_mem_custom = QRadioButton("自定义")
        self._set_mem_group.addButton(self._set_mem_auto)
        self._set_mem_group.addButton(self._set_mem_custom)
        self._set_mem_auto.toggled.connect(self._on_set_memory_mode)
        mem_mode_row = QHBoxLayout()
        mem_mode_row.addWidget(self._set_mem_auto)
        mem_mode_row.addWidget(self._set_mem_custom)
        mem_mode_row.addStretch(1)
        card.add_layout(mem_mode_row)

        self._set_mem_slider = _NoWheelSlider(Qt.Horizontal)
        self._set_mem_slider.setRange(512, 8192)
        self._set_mem_slider.setSingleStep(256)
        self._set_mem_slider.setPageStep(512)
        self._set_mem_value = QLabel("")
        self._set_mem_value.setProperty("cardValue", True)
        self._set_mem_slider.valueChanged.connect(self._on_set_memory_slider)
        mem_slider_row = QHBoxLayout()
        mem_slider_row.addWidget(self._set_mem_slider, 1)
        mem_slider_row.addWidget(self._set_mem_value)
        card.add_layout(mem_slider_row)

        self._set_mem_optimize = QCheckBox("启动游戏前进行内存优化")
        self._set_mem_optimize.toggled.connect(self._on_set_memory_optimize)
        card.add_widget(self._set_mem_optimize)

        self._set_mem_bar = QProgressBar()
        self._set_mem_bar.setRange(0, 100)
        self._set_mem_bar.setTextVisible(False)
        card.add_widget(self._set_mem_bar)
        self._set_mem_info = QLabel("")
        self._set_mem_info.setProperty("sectionHint", True)
        card.add_widget(self._set_mem_info)

        self._set_wrapper = QCheckBox("禁用 Java Launch Wrapper")
        self._set_unsafe = QCheckBox("禁用 LWJGL Unsafe Agent")
        self._set_gpu = QCheckBox("使用高性能显卡")
        self._set_ssl = QCheckBox("在正版登录时验证 SSL 证书")
        for check, attr in (
            (self._set_wrapper, "disable_launch_wrapper"),
            (self._set_unsafe, "disable_lwjgl_unsafe"),
            (self._set_gpu, "prefer_discrete_gpu"),
            (self._set_ssl, "verify_ssl"),
        ):
            check.toggled.connect(lambda _=False, a=attr: self._on_set_switch(a))
            card.add_widget(check)

        column.addWidget(card)
        column.addStretch(1)
        return page

    # ---------- 设置标签：回填与事件 ----------
    @staticmethod
    def _select_combo_by_data(combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _refresh_settings_page(self) -> None:
        """进入版本时把该版本的独立启动配置回填到全部控件。

        回填期间统一阻塞所有控件信号：仅查看版本不应触发任何落盘，否则会把默认值也固化成
        「覆盖」；只有用户真正交互（选择 / 输入 / 拖动）时才写入版本配置。
        """
        cfg = self._launch_cfg
        controls = (
            self._set_isolation_combo,
            self._set_jvm_edit,
            self._set_game_args,
            self._set_pre_cmd,
            self._set_java_combo,
            self._set_gc_combo,
            self._set_mem_auto,
            self._set_mem_custom,
            self._set_mem_slider,
            self._set_mem_optimize,
            self._set_wrapper,
            self._set_unsafe,
            self._set_gpu,
            self._set_ssl,
        )
        for control in controls:
            control.blockSignals(True)
        try:
            self._set_jvm_edit.setPlainText(cfg.jvm_args)
            self._set_game_args.setText(cfg.game_args)
            self._set_pre_cmd.setText(cfg.pre_launch_command)
            self._select_combo_by_data(self._set_isolation_combo, cfg.isolation_mode)
            self._select_combo_by_data(self._set_gc_combo, cfg.gc_mode)
            self._set_mem_auto.setChecked(cfg.memory_mode != "custom")
            self._set_mem_custom.setChecked(cfg.memory_mode == "custom")
            self._set_mem_slider.setValue(cfg.custom_memory_mb)
            self._set_mem_optimize.setChecked(cfg.pre_launch_memory_optimize)
            self._set_wrapper.setChecked(cfg.disable_launch_wrapper)
            self._set_unsafe.setChecked(cfg.disable_lwjgl_unsafe)
            self._set_gpu.setChecked(cfg.prefer_discrete_gpu)
            self._set_ssl.setChecked(cfg.verify_ssl)
            self._refresh_set_java_list()
        finally:
            for control in controls:
                control.blockSignals(False)
        self._update_set_memory_controls()
        self._refresh_set_memory_info()

    def _on_set_isolation_changed(self) -> None:
        key = self._set_isolation_combo.currentData()
        if key:
            self._launch_cfg.isolation_mode = key

    def _on_set_jvm_changed(self) -> None:
        self._launch_cfg.jvm_args = self._set_jvm_edit.toPlainText()

    def _on_set_game_args(self) -> None:
        self._launch_cfg.game_args = self._set_game_args.text()

    def _on_set_pre_command(self) -> None:
        self._launch_cfg.pre_launch_command = self._set_pre_cmd.text()

    def _on_set_gc_changed(self) -> None:
        key = self._set_gc_combo.currentData()
        if key:
            self._launch_cfg.gc_mode = key

    def _refresh_set_java_list(self) -> None:
        current = self._launch_cfg.java_path
        self._set_java_combo.blockSignals(True)
        self._set_java_combo.clear()
        self._set_java_combo.addItem("自动探测（推荐）", "")
        entries = java_runtime.list_java()
        selected = 0
        for index, entry in enumerate(entries, start=1):
            version = entry.get("version") or "未知版本"
            self._set_java_combo.addItem(f"{version} · {entry['path']}", entry["path"])
            if entry["path"] == current:
                selected = index
        if current and not any(
            self._set_java_combo.itemData(i) == current
            for i in range(self._set_java_combo.count())
        ):
            self._set_java_combo.addItem(current, current)
            selected = self._set_java_combo.count() - 1
        self._set_java_combo.setCurrentIndex(selected)
        self._set_java_combo.blockSignals(False)

    def _on_set_java_changed(self) -> None:
        self._launch_cfg.java_path = self._set_java_combo.currentData() or ""

    def _on_set_memory_mode(self) -> None:
        self._launch_cfg.memory_mode = (
            "custom" if self._set_mem_custom.isChecked() else "auto")
        self._update_set_memory_controls()
        self._refresh_set_memory_info()

    def _on_set_memory_slider(self, value: int) -> None:
        self._launch_cfg.custom_memory_mb = value
        self._update_set_memory_controls()
        self._refresh_set_memory_info()

    def _on_set_memory_optimize(self, value: bool) -> None:
        self._launch_cfg.pre_launch_memory_optimize = value

    def _on_set_switch(self, attr: str) -> None:
        check = {
            "disable_launch_wrapper": self._set_wrapper,
            "disable_lwjgl_unsafe": self._set_unsafe,
            "prefer_discrete_gpu": self._set_gpu,
            "verify_ssl": self._set_ssl,
        }[attr]
        setattr(self._launch_cfg, attr, check.isChecked())

    def _update_set_memory_controls(self) -> None:
        custom = self._set_mem_custom.isChecked()
        self._set_mem_slider.setEnabled(custom)
        self._set_mem_value.setEnabled(custom)
        self._set_mem_value.setText(f"{self._set_mem_slider.value()} MB")

    def _set_allocated_mb(self) -> int:
        if self._launch_cfg.memory_mode == "custom":
            return self._launch_cfg.custom_memory_mb
        return C.DEFAULT_JVM_XMX_MB

    def _refresh_set_memory_info(self) -> None:
        total_mb, avail_mb = _physical_memory_mb()
        allocated = self._set_allocated_mb()
        if total_mb <= 0:
            self._set_mem_bar.setValue(0)
            self._set_mem_info.setText(f"游戏分配：{allocated} MB")
            return
        used_mb = total_mb - avail_mb
        ratio = int(used_mb / total_mb * 100)
        self._set_mem_bar.setValue(max(0, min(100, ratio)))
        self._set_mem_info.setText(
            f"已使用内存 {used_mb / 1024:.1f} GB / {total_mb / 1024:.1f} GB"
            f"　　游戏分配 {allocated / 1024:.1f} GB"
        )

    # ---------- 修改 ---------- #
    def _build_modify_section(self) -> QWidget:
        page = QWidget()
        page.setObjectName("vsSectionPage")
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 8, 0)
        column.setSpacing(12)

        name_card = Card("版本名")
        self._modify_name = QLineEdit()
        self._modify_name.setFixedHeight(38)
        name_card.add_widget(self._modify_name)
        column.addWidget(name_card)

        loader_card = Card("加载器")
        self._loader_rows: dict[str, LoaderRow] = {}

        base_row = LoaderRow("minecraft", "Minecraft",
                             self._pick_mc_version, lambda _k, _v: None)
        base_row.set_state(selectable=False, status=self._mc_version,
                           show_remove=False, show_chevron=False)
        loader_card.add_widget(base_row)
        self._base_row = base_row

        for key in C.LOADER_CARD_ORDER:
            label = C.LOADER_LABELS[key]
            row = LoaderRow(key, label, self._select_loader_row,
                            self._pick_loader_version, self._remove_loader)
            loader_card.add_widget(row)
            self._loader_rows[key] = row

        self._probe_status = QLabel("正在检查加载器兼容性…")
        self._probe_status.setObjectName("vsBusy")
        loader_card.add_widget(self._probe_status)
        column.addWidget(loader_card)

        start = QPushButton("开始修改")
        start.setProperty("primaryButton", True)
        start.setFixedHeight(44)
        start.setCursor(Qt.PointingHandCursor)
        start.clicked.connect(self._start_modify)
        self._start_button = start
        column.addWidget(start)
        column.addStretch(1)
        return page

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #
    def show_version(self, alias: str) -> None:
        alias = str(alias or "").strip()
        self._alias = alias
        self._launch_cfg.set_alias(alias)
        self._meta = game_dirs.read_install_meta(alias)

        entry = self._find_entry(alias)
        # 优先用已安装条目 / 元数据里的真实 MC 版本；两者都缺（外部或未装完的版本）时，
        # 从本地版本 JSON（含 inheritsFrom）解析底座版本，最后才退回别名——避免把别名当
        # 真实 MC 版本号去远程清单定位，触发 KeyError「清单中找不到版本」。
        self._mc_version = str(
            entry.get("mc_version")
            or self._meta.get("mc_version")
            or game_dirs.local_version_base(alias)
            or alias)
        self._loader = str(entry.get("loader") or self._meta.get("loader") or C.LOADER_VANILLA)
        self._loader_version = str(
            entry.get("loader_version") or self._meta.get("loader_version") or "")

        self._chosen_loader = self._loader
        self._chosen_version = self._loader_version
        self._chosen_mc_version = self._mc_version
        self._probe = None

        self._refresh_header()
        self._refresh_info_card()
        self._refresh_counts()
        self._refresh_modify_page()
        self._refresh_settings_page()
        if not self._is_modpack():
            # 整合包锁定，无需也不应做加载器探测。
            self._start_probe()
        self._switch_section("overview")

    def refresh_for_alias(self, alias: str) -> None:
        """内容/整合包安装完成后即时刷新：仅当本页正查看该别名时更新，不切分区。"""
        alias = str(alias or "").strip()
        if not alias or self._alias != alias:
            return
        self._meta = game_dirs.read_install_meta(alias)
        entry = self._find_entry(alias)
        if entry:
            self._mc_version = str(entry.get("mc_version") or self._mc_version)
            self._loader = str(entry.get("loader") or self._loader)
            self._loader_version = str(
                entry.get("loader_version") or self._loader_version)
        self._chosen_mc_version = self._mc_version
        self._refresh_header()
        self._refresh_info_card()
        self._refresh_counts()
        self._refresh_modify_page()

    def _find_entry(self, alias: str) -> dict:
        for item in game_dirs.scan_installed_entries():
            if str(item.get("alias") or "") == alias:
                return item
        return {}

    # ---------- 头部 / 信息卡 ---------- #
    def _loader_text(self) -> str:
        if self._loader == C.LOADER_VANILLA:
            return "原版"
        label = C.LOADER_LABELS.get(self._loader, self._loader)
        if self._loader_version:
            return "%s %s" % (label, self._loader_version)
        return label

    def _refresh_header(self) -> None:
        self._version_title.setText(self._alias or "—")
        self._loader_chip.setText(self._loader_text())

    def _refresh_info_card(self) -> None:
        avatar_key = str(self._meta.get("avatar") or "grass_block")
        self._info_icon.setPixmap(self._avatar_pixmap(avatar_key, _AVATAR_SIZE))
        self._info_title.setText(self._alias or "—")
        self._info_sub.setText("MC %s · %s" % (self._mc_version, self._loader_text()))
        self._avatar_picker.set_alias(self._alias)
        self._avatar_picker.set_current(avatar_key)

    def _avatar_pixmap(self, avatar_key: str, size: int) -> QPixmap:
        path = _avatar_file(self._alias, avatar_key)
        pix = QPixmap(path)
        if pix.isNull():
            return pix
        return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # ---------- 头像 / 改名 ---------- #
    def _pick_avatar(self, key: str) -> None:
        game_dirs.update_install_meta(self._alias, avatar=key)
        self._meta = game_dirs.read_install_meta(self._alias)
        self._avatar_picker.set_current(key)
        self._refresh_info_card()

    def _open_rename(self) -> None:
        dialog = _RenameDialog(self._alias, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._perform_rename(dialog.value())

    def _perform_rename(self, new_name: str) -> bool:
        new_name = str(new_name or "").strip()
        if not new_name or new_name == self._alias:
            return False
        ok, reason = game_dirs.rename_version(self._alias, new_name)
        if not ok:
            self._show_message(reason)
            return False
        if self._config is not None and self._config.selected_version == self._alias:
            self._config.selected_version = new_name
            self._config.save()
        self.show_version(new_name)
        return True

    # ---------- 计数 / 展开列表 ---------- #
    def _refresh_counts(self) -> None:
        counts = version_content.count_content(self._alias)
        label_map = {
            "mod": "mod", "shader": "光影包",
            "resourcepack": "材质包", "datapack": "数据包",
        }
        for kind, button in self._count_buttons.items():
            button.setText("%s：%d" % (label_map[kind], int(counts.get(kind, 0))))

    def _open_content_list(self, kind: str) -> None:
        if self._content_worker is not None and self._content_worker.isRunning():
            return
        dialog = _ContentListDialog(kind, self)
        self._content_dialog = dialog

        worker = ContentScanWorker(self._alias, kind)
        self._content_worker = worker
        worker.succeeded.connect(dialog.populate)
        worker.failed.connect(lambda msg: dialog.populate([]))
        worker.start()
        dialog.exec()
        if worker.isRunning():
            worker.requestInterruption()
            worker.wait(3000)

    # ---------- 修改分区 ---------- #
    def _start_probe(self) -> None:
        if self._probe_worker is not None and self._probe_worker.isRunning():
            return
        worker = LoaderProbeWorker(self._mc_version)
        self._probe_worker = worker
        worker.succeeded.connect(self._on_probe_done)
        worker.failed.connect(lambda _m: self._on_probe_done({}))
        worker.start()

    def _on_probe_done(self, result: dict) -> None:
        self._probe = result if isinstance(result, dict) else {}
        if self._is_modpack():
            # 整合包锁定：探测结果不得覆盖锁定态与提示。
            return
        self._probe_status.setText("")
        self._refresh_loader_rows()

    def _is_modpack(self) -> bool:
        """整合包口径：头像标记 modpack 或存在 modpack_name 字段。"""
        if str(self._meta.get("avatar") or "") == "modpack":
            return True
        return bool(str(self._meta.get("modpack_name") or "").strip())

    def _has_content(self) -> bool:
        counts = version_content.count_content(self._alias)
        return any(int(counts.get(k, 0)) > 0 for k in
                   ("mod", "shader", "resourcepack", "datapack"))

    def _mod_count(self) -> int:
        return int(version_content.count_content(self._alias).get("mod", 0))

    def _locked_by_mods(self) -> bool:
        """mod 达到阈值即锁定修改分区：内容较多时切换版本 / 加载器极易不兼容。"""
        return self._mod_count() >= MOD_LOCK_THRESHOLD

    def _refresh_modify_page(self) -> None:
        self._modify_name.setText(self._alias)
        mod_locked = self._locked_by_mods()
        if self._is_modpack():
            # 整合包锁定：禁用所有加载器行与开始按钮，明确提示勿切换。
            self._modify_name.setEnabled(False)
            self._base_row.set_state(selectable=False, status=self._mc_version,
                                     show_remove=False, show_chevron=False,
                                     disabled=True)
            for row in self._loader_rows.values():
                row.set_state(selectable=False, status="已锁定",
                              show_remove=False, show_chevron=False,
                              disabled=True)
            self._probe_status.setText(
                "这是整合包版本，请勿切换版本或加载器。")
            self._start_button.setEnabled(False)
            return
        if mod_locked:
            # mod 较多：锁定版本 / 加载器切换，避免不兼容。
            self._modify_name.setEnabled(False)
            self._base_row.set_state(selectable=False, status=self._chosen_mc_version,
                                     show_remove=False, show_chevron=False,
                                     disabled=True)
            for row in self._loader_rows.values():
                row.set_state(selectable=False, status="已锁定",
                              show_remove=False, show_chevron=False,
                              disabled=True)
            self._probe_status.setText(
                "已安装 %d 个以上 mod，为避免不兼容，不能切换版本或加载器。"
                % MOD_LOCK_THRESHOLD)
            self._start_button.setEnabled(False)
            return
        self._modify_name.setEnabled(True)
        self._base_row.set_state(selectable=True, status=self._chosen_mc_version,
                                 show_remove=False, show_chevron=True)
        self._start_button.setEnabled(True)
        self._probe_status.setText("正在检查加载器兼容性…")
        self._refresh_loader_rows()

    def _select_loader_row(self, key: str) -> None:
        if self._chosen_loader == key:
            # 再次点击已选中行：展开 / 收起内联版本列表。
            self._expanded_loader = "" if self._expanded_loader == key else key
            self._refresh_loader_rows()
            return
        info = (self._probe or {}).get(key) or {}
        versions = info.get("versions") or []
        version = ""
        if versions:
            version = str(versions[0].get("version") or "")
        self._chosen_loader = key
        self._chosen_version = version
        self._expanded_loader = key
        self._refresh_loader_rows()

    def _remove_loader(self, _key: str) -> None:
        self._chosen_loader = C.LOADER_VANILLA
        self._chosen_version = ""
        self._expanded_loader = ""
        self._refresh_loader_rows()

    def _pick_loader_version(self, key: str, version: str) -> None:
        """内联版本列表点选：记录所选加载器与版本号。"""
        if not version:
            return
        self._chosen_loader = key
        self._chosen_version = version
        self._refresh_loader_rows()

    def _pick_mc_version(self, _key: str) -> None:
        """点击 Minecraft 行：拉取清单（首次）后弹出底座版本选择窗。"""
        if self._is_modpack() or self._locked_by_mods():
            return
        if self._manifest is None:
            self._probe_status.setText("正在拉取 Minecraft 版本清单…")
            self._start_meta_worker()
            return
        self._open_mc_dialog()

    def _start_meta_worker(self) -> None:
        if self._meta_worker is not None and self._meta_worker.isRunning():
            return
        worker = VersionMetaWorker()
        self._meta_worker = worker
        worker.succeeded.connect(self._on_meta_done)
        worker.failed.connect(lambda _m: self._on_meta_done(None))
        worker.start()

    def _on_meta_done(self, payload) -> None:
        if isinstance(payload, dict):
            self._manifest = payload.get("manifest") or {}
        else:
            self._manifest = None
        if self._manifest:
            self._open_mc_dialog()
        else:
            self._probe_status.setText("正在检查加载器兼容性…")
            self._show_message("版本清单拉取失败，请检查网络后重试。")

    def _open_mc_dialog(self) -> None:
        dialog = _McVersionDialog(self._manifest or {},
                                  self._chosen_mc_version, self)
        if dialog.exec() == QDialog.Accepted and dialog.chosen():
            self._chosen_mc_version = dialog.chosen()
            self._base_row.set_state(
                selectable=True, status=self._chosen_mc_version,
                show_remove=False, show_chevron=True)

    def _refresh_loader_rows(self) -> None:
        chosen_label = C.LOADER_LABELS.get(self._chosen_loader, "")
        for key, row in self._loader_rows.items():
            info = (self._probe or {}).get(key) or {}
            available = bool(info.get("available"))
            versions = info.get("versions") or []

            if self._chosen_loader == key:
                version = self._chosen_version or str(info.get("version") or "")
                vtime = _version_time_text(versions, version)
                sub = ("发布于 " + vtime) if vtime else ""
                row.set_state(selectable=True, status=version,
                              show_remove=True, show_chevron=bool(versions),
                              versions=versions, current=version,
                              expanded=(key == self._expanded_loader),
                              sub=sub)
                continue

            if self._chosen_loader != C.LOADER_VANILLA:
                row.set_state(selectable=False,
                              status="与 %s 不兼容" % chosen_label,
                              show_remove=False, show_chevron=False,
                              disabled=True, versions=versions,
                              current=str(info.get("version") or ""))
                continue

            # 原版态：可添加或无。
            if available:
                latest = str(info.get("version") or "")
                latest_time = _version_time_text(versions, latest)
                latest_sub = ("发布于 " + latest_time) if latest_time else ""
                row.set_state(selectable=True, status=latest or "可以添加",
                              show_remove=False, show_chevron=bool(versions),
                              versions=versions, current=latest,
                              sub=latest_sub)
            else:
                row.set_state(selectable=False, status="无",
                              show_remove=False, show_chevron=False,
                              disabled=True)

    def _start_modify(self) -> None:
        if self._modify_worker is not None and self._modify_worker.isRunning():
            return
        if self._is_modpack():
            # 双保险：整合包已锁定，开始按钮也已禁用。
            self._show_message("这是整合包版本，不能切换版本或加载器。")
            return
        if self._locked_by_mods():
            self._show_message(
                "已安装 %d 个以上 mod，为避免不兼容，不能切换版本或加载器。"
                % MOD_LOCK_THRESHOLD)
            return
        new_name = self._modify_name.text().strip()
        if new_name and new_name != self._alias:
            if not self._perform_rename(new_name):
                return
        mc_changed = bool(self._chosen_mc_version) and \
            self._chosen_mc_version != self._mc_version
        # 点“开始修改”先确认：含内容警告不兼容；更换底座单独提示；取消即不改。
        if self._has_content():
            message = ("该版本已安装 mod、材质包、光影包或数据包，切换加载器可能导致内容不兼容。"
                       "确定要继续修改吗？")
        elif mc_changed:
            message = ("将把游戏底座从 %s 更换为 %s，旧版本专属文件会保留，"
                       "已装 mod 可能与新版本不兼容。确定要继续吗？"
                       % (self._mc_version, self._chosen_mc_version))
        else:
            message = "确定要对版本「%s」开始修改吗？" % self._alias
        if mc_changed and self._has_content():
            message += "\n同时将更换游戏底座到 %s，已装 mod 可能不兼容。" % self._chosen_mc_version
        dialog = _ConfirmDialog(message, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._run_worker(self._chosen_loader, self._chosen_version, "开始修改")

    def _repair_files(self) -> None:
        if self._modify_worker is not None and self._modify_worker.isRunning():
            return
        self._run_worker(self._loader, self._loader_version, "补齐文件",
                         mc_version=self._mc_version)

    def _run_worker(self, loader: str, version: str, title: str,
                    mc_version: str | None = None) -> None:
        progress = _ProgressDialog(title, self)
        self._progress_dialog = progress

        base_mc = mc_version or self._chosen_mc_version or self._mc_version
        worker = VersionModifyWorker(self._alias, base_mc,
                                     loader, version)
        self._modify_worker = worker
        worker.progress.connect(progress.update_progress)
        worker.succeeded.connect(self._on_modify_succeeded)
        worker.failed.connect(self._on_modify_failed)
        worker.start()

        if progress.exec() == QDialog.Rejected and worker.isRunning():
            worker.requestInterruption()
            worker.wait(8000)

    def _on_modify_succeeded(self, result: dict) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.hide_cancel()
            self._progress_dialog.accept()
        self.show_version(str(result.get("alias") or self._alias))
        self._switch_section("overview")

    def _on_modify_failed(self, message: str) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.accept()
        self._show_message(message)

    # ---------- 删除版本 ---------- #
    def _delete_version(self) -> None:
        dialog = _ConfirmDialog(
            "确定删除版本「%s」吗？该版本的存档、配置与文件都会一起删除，且无法恢复。" % self._alias,
            self)
        if dialog.exec() != QDialog.Accepted:
            return
        if self._config is not None and self._config.selected_version == self._alias:
            self._config.selected_version = ""
            self._config.save()
        game_dirs.remove_version_dir(self._alias)
        self.closed.emit()

    # ---------- 工具 ---------- #
    def _show_message(self, message: str) -> None:
        dialog = _GlassDialog("提示", self, min_width=320)
        label = QLabel(str(message))
        label.setWordWrap(True)
        label.setProperty("vsHint", True)
        dialog.add_widget(label)
        ok = _dialog_button("知道了", primary=True)
        ok.clicked.connect(dialog.accept)
        dialog.button_row([ok])
        dialog.exec()

    def _switch_section(self, key: str) -> None:
        keys = [item[0] for item in SECTIONS]
        index = keys.index(key) if key in keys else 0
        self._stack.setCurrentIndex(index)
        for item_key, button in self._section_buttons.items():
            button.setChecked(item_key == key)

    # ---------- 生命周期 ---------- #
    def shutdown(self) -> None:
        for worker in (self._content_worker, self._probe_worker, self._modify_worker):
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.wait(5000)
