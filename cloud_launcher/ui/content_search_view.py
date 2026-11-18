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

"""v1.3.4.0 内容搜索视图：搜索框 + 搜索按钮 + 带图结果网格。

每个分类（mod / 整合包 / 光影包 / 资源包 / 数据包）一个视图。顶部为搜索输入框与
「搜索」按钮（回车同样触发）；下方滚动区以两列玻璃卡片网格展示结果，每张卡片
必须带图片——有本地图标则显示圆角图标，无图标 / 加载失败一律显示程序化绘制的
占位图，保证「每一个东西都有图」。

v1.3.6.0：卡片右下角新增「下载」入口，点击后弹视图内玻璃浮层选择目标游戏版本，
由后台线程把项目文件真实下载到该版本隔离目录（mods / shaderpacks /
resourcepacks / datapacks）。滚动区与浮层列表的垂直滚动条一律 AlwaysOff——用户
明确要求不要看到滑块，滚轮滚动照常可用。
"""
import math
import os

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import game_dirs
from ..content_install import KIND_LABELS
from ..modpack_install import PHASE_LABELS
from ..content_search import (
    DEFAULT_LIMIT,
    latest_releases,
    mod_loaders,
    release_versions,
    version_key,
)
from .content_install_worker import ContentInstallWorker
from .content_search_worker import ContentSearchWorker
from .frosted_backdrop import paint_frosted_panel
from .modpack_dialog import ModpackInstallDialog
from .modpack_install_worker import (
    ModpackInstallWorker,
    ModpackVersionListWorker,
)
from .task_progress_dialog import (
    STATE_DONE,
    STATE_RUNNING,
    TaskProgressDialog,
)

# 布局 / 尺寸。
_ICON = 64
_ICON_RADIUS = 12
_CARD_RADIUS = 14
_GRID_COLUMNS = 2
_GRID_GAP = 10
_BTN_WIDTH = 88
_BTN_HEIGHT = 38
_CARD_BTN_WIDTH = 58
_CARD_BTN_HEIGHT = 26

# 版本选择浮层尺寸。
_PICKER_WIDTH = 400
_PICKER_MAX_LIST = 220
_PICKER_RADIUS = 18

# 单文件内容下载的三阶段清单（对齐 PCL2 竖向卡片）。
_CONTENT_PHASES = ("解析下载文件", "下载文件", "校验并完成")

# 占位图缓存（按尺寸）。
_PLACEHOLDER_CACHE: dict[int, QPixmap] = {}
# 图标加载缓存：本地路径 + 尺寸 → 处理后的 QPixmap。
_ICON_CACHE: dict[tuple[str, int], QPixmap] = {}


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _format_size(value: int) -> str:
    if value >= 1_048_576:
        return f"{value / 1_048_576:.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.0f} KB"
    return f"{value} B"


def _wrap_list_tooltip(prefix: str, values: list, per_line: int = 6) -> str:
    """把长列表拼成多行纯文本工具提示，避免单行过长横向溢出屏幕。

    各平台 QToolTip 对纯文本的自动换行并不稳定（实测在 Windows 上会出现整条
    单行撑满、溢出屏幕的情况），这里显式按每行固定条数插入换行，宽度可控；
    values 需已按目标显示顺序排好。短列表不超过 per_line 时仍只占一行。
    """
    if not values:
        return prefix
    lines = []
    for start in range(0, len(values), per_line):
        lines.append("、".join(values[start:start + per_line]))
    lines[0] = prefix + lines[0]
    return "\n".join(lines)



def placeholder_pixmap(size: int) -> QPixmap:
    """程序化绘制占位图标：浅玻璃圆角底 + 图片符号（太阳 + 双峰）。"""
    cached = _PLACEHOLDER_CACHE.get(size)
    if cached is not None:
        return cached
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    rect = QPainterPath()
    rect.addRoundedRect(0, 0, size, size, _ICON_RADIUS, _ICON_RADIUS)
    p.fillPath(rect, QColor(255, 255, 255, 70))
    pen = QPen(QColor(150, 180, 200, 150))
    pen.setWidthF(max(1.5, size / 32.0))
    p.setPen(pen)
    p.drawPath(rect)

    # 太阳（右上小圆）。
    sun = size * 0.30
    p.setBrush(QColor(150, 190, 215, 180))
    p.setPen(Qt.NoPen)
    p.drawEllipse(int(size * 0.60), int(size * 0.24), int(sun), int(sun))

    # 双峰（三角）。
    p.setBrush(QColor(120, 165, 195, 190))
    base_y = size * 0.78
    p.drawPolygon(
        _points([(size * 0.18, base_y), (size * 0.42, size * 0.46),
                (size * 0.66, base_y)])
    )
    p.setBrush(QColor(140, 180, 205, 170))
    p.drawPolygon(
        _points([(size * 0.44, base_y), (size * 0.64, size * 0.56),
                (size * 0.84, base_y)])
    )
    p.end()
    _PLACEHOLDER_CACHE[size] = pix
    return pix


def _points(pairs):
    from PySide6.QtGui import QPolygon
    poly = QPolygon()
    for x, y in pairs:
        poly.append(QPoint(int(x), int(y)))
    return poly


def _finish_pixmap(source: QPixmap, size: int, cache_key) -> QPixmap:
    """缩放 + 圆角裁剪统一处理；source 为空图时回退占位图，结果按 key 缓存。"""
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if source.isNull():
        result = placeholder_pixmap(size)
    else:
        scaled = source.scaled(size, size, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
        # 居中放到方形透明画布，再按圆角路径裁剪，保证非正方形图标也统一圆角。
        canvas = QPixmap(size, size)
        canvas.fill(Qt.transparent)
        cp = QPainter(canvas)
        cp.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, _ICON_RADIUS, _ICON_RADIUS)
        cp.setClipPath(path)
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        cp.drawPixmap(x, y, scaled)
        cp.end()
        result = canvas
    _ICON_CACHE[cache_key] = result
    return result


def _rounded_icon(local_path: str | None, size: int) -> QPixmap:
    """加载本地图标（第一页缓存路径）并缩放 / 圆角化；路径为空回退占位图。"""
    if not local_path:
        return placeholder_pixmap(size)
    return _finish_pixmap(QPixmap(local_path), size, ("path", local_path, size))


def _rounded_from_bytes(data: bytes | None, size: int) -> QPixmap:
    """从内存 bytes 加载图标（后续页不写缓存）并缩放 / 圆角化。"""
    if not data:
        return placeholder_pixmap(size)
    pix = QPixmap()
    pix.loadFromData(data)
    return _finish_pixmap(pix, size, ("bytes", data, size))


def _card_pixmap(item: dict, size: int) -> QPixmap:
    """按卡片数据选图标：优先本地缓存路径，其次内存 bytes，最后占位图。"""
    if item.get("icon_local"):
        return _rounded_icon(item.get("icon_local"), size)
    if item.get("icon_bytes"):
        return _rounded_from_bytes(item.get("icon_bytes"), size)
    return placeholder_pixmap(size)


class ContentCard(QFrame):
    """单条结果卡片：圆角图标 + 标题 + 简介 + 作者 / 下载量 + 下载按钮。"""

    #: 点「下载」时对外回传本条结果字典。
    downloadClicked = Signal(object)

    def __init__(self, item: dict, kind: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contentCard")
        self._item = item
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(12)

        icon = QLabel()
        icon.setFixedSize(_ICON, _ICON)
        icon.setPixmap(_card_pixmap(item, _ICON))
        row.addWidget(icon, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)

        title = QLabel(item.get("title", ""))
        title.setObjectName("contentCardTitle")
        # 长标题不得撑宽列：水平方向忽略内容最小宽度，超长由 elide 截断。
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        f = QFont()
        f.setPointSize(11)
        f.setWeight(QFont.DemiBold)
        title.setFont(f)
        col.addWidget(title)

        desc = QLabel(item.get("description", ""))
        desc.setObjectName("contentCardDesc")
        desc.setWordWrap(False)
        desc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(desc, 1)

        meta = QLabel(
            "作者：%s　·　下载量：%s"
            % (item.get("author", "—"), _format_count(item.get("downloads", 0)))
        )
        meta.setObjectName("contentCardMeta")
        meta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(meta)

        # v1.3.8.0：mod 卡片标注「这是什么加载器」（仅模组分类，从 categories 提取）。
        if kind == "mod":
            loaders = item.get("loaders") or mod_loaders(
                item.get("categories"))
            if loaders:
                loader_lbl = QLabel("加载器：%s" % "、".join(loaders))
                loader_lbl.setObjectName("contentCardLoaders")
                # 加载器较多时自动换行完整显示，不被窄列裁切；同网格行高度自动对齐。
                loader_lbl.setWordWrap(True)
                loader_lbl.setSizePolicy(QSizePolicy.Ignored,
                                         QSizePolicy.Preferred)
                loader_lbl.setToolTip(
                    _wrap_list_tooltip("这个模组支持的加载器：", loaders, 6))
                col.addWidget(loader_lbl)

        # v1.3.7.0：卡片上标注支持哪些游戏版本（只列最新 3 个正式版，完整列表见 tooltip）。
        rels = release_versions(item.get("supported_versions"))
        newest = latest_releases(item.get("supported_versions"), 3)
        if newest:
            ver_text = "支持：%s 等 %s 个正式版" % ("、".join(newest), len(rels))
        else:
            ver_text = "支持：%s" % "、".join(
                (item.get("supported_versions") or [])[:3]) or "版本信息缺失"
        ver = QLabel(ver_text)
        ver.setObjectName("contentCardVersions")
        ver.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        if rels:
            ordered = sorted(rels, key=version_key, reverse=True)
            ver.setToolTip(_wrap_list_tooltip("支持的正式版：", ordered, 6))
        col.addWidget(ver)

        row.addLayout(col, 1)

        # v1.3.11.0：整合包下载已支持（选版本 + 命名 + 新建隔离实例），按钮统一启用。
        self._download_btn = QPushButton("下载")
        self._download_btn.setObjectName("contentCardDownloadBtn")
        self._download_btn.setFixedSize(_CARD_BTN_WIDTH, _CARD_BTN_HEIGHT)
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_btn.clicked.connect(
            lambda: self.downloadClicked.emit(self._item)
        )
        row.addWidget(self._download_btn, 0, Qt.AlignBottom)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        """片内局部磨砂卡片底板：只模糊本卡片正后方那一小块壁纸。

        v1.3.8.2：此前卡片背景是 QSS 的半透明白平涂，壁纸在卡内保持清晰锐利，
        mod / 整合包 / 光影等内容页因此丢了磨砂底；与启动页卡片、原版游戏分组条
        的口径不统一。改为和 ``Card`` 一样自绘：圆角矩形内截取正后方壁纸做局部柔化，
        再叠三段白玻璃高光与细亮边，卡片之外的壁纸仍保持清晰。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 与启动页 Card 同一档白玻璃色板，保证全程序卡片观感一致；
        # 不切更白的 TOP 档（历史教训：alpha 186 叠磨砂会糊成不透明白板）。
        paint_frosted_panel(
            painter,
            self,
            _CARD_RADIUS,
            C.COLOR_GLASS_TOP_RGBA,
            C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA,
            C.COLOR_CARD_BORDER_RGBA,
        )
        painter.end()

    def elide_text(self, width: int) -> None:
        """按卡片可用宽度把标题与简介截断为单行省略号。"""
        for name in ("contentCardTitle", "contentCardDesc"):
            label = self.findChild(QLabel, name)
            if label is not None:
                full = label.property("fullText")
                if not isinstance(full, str):
                    full = label.text()
                    label.setProperty("fullText", full)
                label.setText(label.fontMetrics().elidedText(
                    full, Qt.ElideRight, width))


class ContentVersionPicker(QFrame):
    """视图内玻璃浮层：选择把当前内容下载到哪个已安装游戏版本。

    不参与父布局，由 :meth:`open_for` 手动定位居中；点「取消」或「下载」后隐藏。
    背景走 QSS 玻璃填充（主窗口样式表对普通子控件生效），尺寸按常量固定计算，
    避免依赖隐藏状态下的 sizeHint。
    """

    cancelled = Signal()
    confirmed = Signal(object, bool)  # (版本条目, 是否覆盖同名文件)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contentVersionPicker")
        # 背景由 paintEvent 自绘磨砂（跟随玻璃设置），不用 QSS 死白背景。
        self.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._title = QLabel("下载到哪个版本")
        self._title.setObjectName("contentPickerTitle")
        self._title.setFixedHeight(22)
        title_row.addWidget(self._title, 1)
        self._close = QPushButton("✕")
        self._close.setObjectName("contentPickerClose")
        self._close.setFixedSize(24, 24)
        self._close.setCursor(Qt.PointingHandCursor)
        self._close.clicked.connect(self._on_cancel)
        title_row.addWidget(self._close, 0, Qt.AlignTop)
        root.addLayout(title_row)

        self._subtitle = QLabel("")
        self._subtitle.setObjectName("contentPickerSubtitle")
        self._subtitle.setFixedHeight(18)
        root.addWidget(self._subtitle)

        # 版本列表：滚动条 AlwaysOff（用户要求不要看到滑块），滚轮仍可滚。
        self._scroll = QScrollArea()
        self._scroll.setObjectName("contentPickerScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)

        self._list_host = QWidget()
        self._list_host.setObjectName("contentPickerList")
        self._list_host.setAutoFillBackground(False)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._scroll.setWidget(self._list_host)
        root.addWidget(self._scroll, 0)

        self._footer = QLabel("")
        self._footer.setObjectName("contentPickerFooter")
        self._footer.setWordWrap(True)
        self._footer.setFixedHeight(32)
        root.addWidget(self._footer)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("contentPickerCancel")
        self._cancel_btn.setFixedSize(72, 32)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        self._ok_btn = QPushButton("下载")
        self._ok_btn.setObjectName("contentPickerOk")
        self._ok_btn.setFixedSize(88, 32)
        self._ok_btn.setCursor(Qt.PointingHandCursor)
        self._ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(self._ok_btn)
        root.addLayout(btn_row)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._entries: list[dict] = []
        self._overwrite = False

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        # 自绘局部磨砂，随外观设置在普通/磨砂/通透三档间切换。
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        paint_frosted_panel(
            painter,
            self,
            18.0,
            C.COLOR_GLASS_TOP_RGBA,
            C.COLOR_GLASS_MID_RGBA,
            C.COLOR_GLASS_BOTTOM_RGBA,
            C.COLOR_CARD_BORDER_RGBA,
        )
        painter.end()

    # ------------------------------------------------------------------ #
    def open_for(self, item: dict, entries: list[dict], kind: str,
                 overwrite: bool = False, overwrite_name: str = "") -> None:
        """按条目与已安装版本列表铺开浮层；``overwrite`` 时直接用于覆盖确认。"""
        self._overwrite = overwrite
        self._build_list(entries, kind, item)
        self._title.setText("确认覆盖同名文件" if overwrite else "下载到哪个版本")
        self._subtitle.setText(
            "「%s」→ %s目录" % (item.get("title", ""), KIND_LABELS.get(kind, kind))
        )
        hints = {
            "mod": "文件会下到目标版本的 mods 目录，进游戏即加载。",
            "shader": "文件会下到 shaderpacks 目录，需在游戏内启用（要装 Iris 或 OptiFine）。",
            "resourcepack": "文件会下到 resourcepacks 目录，进游戏后在选项里启用。",
            "datapack": "文件会下到版本的 datapacks 目录，存档内需启用数据包。",
        }
        footer = hints.get(kind, "")
        if overwrite:
            footer = "目标目录已有「%s」，是否覆盖？" % overwrite_name
        self._footer.setText(footer)
        self._ok_btn.setText("覆盖下载" if overwrite else "下载")
        self.reposition()
        self.show()
        self.raise_()

    def _build_list(self, entries: list[dict], kind: str,
                    item: dict | None = None) -> None:
        while self._list_layout.count():
            old = self._list_layout.takeAt(0)
            w = old.widget()
            if w is not None:
                w.deleteLater()
        self._entries = list(entries)
        # v1.3.7.0：项目支持的游戏版本列表，用来给不兼容的已安装版本置灰标注。
        supported = set((item or {}).get("supported_versions") or [])
        check_compat = bool(supported)
        first_compatible = None
        for entry in self._entries:
            loader_key = str(entry.get("loader") or "")
            alias = str(entry.get("alias") or "")
            mc_ver = entry.get("mc_version", "") or alias
            compatible = (not check_compat) or (mc_ver in supported)
            # v1.3.14.5：同一游戏版本常装了多个实例（默认命名、自己改的名、整合包版…），
            # 旧标签只写「mc_version · 加载器」，多个 26.3 长得完全一样，没法选。
            # 现以版本名（即启动器里显示的版本目录名）为主标签，原生版本号与加载器作补充，
            # 版本名与原生版本号相同时不重复展示。
            parts = [alias or mc_ver]
            if mc_ver and mc_ver != (alias or ""):
                parts.append(mc_ver)
            parts.append(C.LOADER_LABELS.get(loader_key, loader_key or "原版游戏"))
            full_label = "　·　".join(p for p in parts if p)
            label = full_label
            if len(label) > 30:  # 名字过长的版本按字数截断，完整内容放 tooltip。
                label = label[:29] + "…"
            btn = QPushButton(label if compatible else label + "（不支持）")
            btn.setProperty("versionOption", True)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor if compatible else Qt.ArrowCursor)
            btn.setToolTip("版本：%s\n隔离目录：versions/%s" % (full_label, alias)
                           if compatible else
                           "「%s」不支持游戏版本 %s，无法下载"
                           % ((item or {}).get("title", ""), mc_ver))
            if not compatible:
                btn.setEnabled(False)
            self._group.addButton(btn)
            self._list_layout.addWidget(btn)
            if compatible and first_compatible is None:
                first_compatible = btn
        if first_compatible is not None:
            first_compatible.setChecked(True)
        self._list_layout.addStretch(1)

    def selected_entry(self) -> dict | None:
        checked = self._group.checkedButton()
        if checked is None:
            return None
        index = self._group.buttons().index(checked)
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def reposition(self) -> None:
        """在父控件内居中；高度按「内边距 + 标题 + 副标题 + 列表 + 页脚 + 按钮」算死。"""
        parent = self.parentWidget()
        if parent is None:
            return
        count = max(1, len(self._entries))
        list_h = min(_PICKER_MAX_LIST, count * 40)
        self._scroll.setFixedHeight(list_h)
        # 16 + 22 + 8 + 18 + 8 + list_h + 8 + 32 + 8 + 32 + 16
        height = 162 + list_h
        width = max(320, min(470, parent.width() - 48))
        height = min(height, max(200, parent.height() - 24))
        x = max(6, (parent.width() - width) // 2)
        y = max(6, (parent.height() - height) // 2)
        self.setGeometry(x, y, width, height)

    def _on_cancel(self) -> None:
        self.hide()
        self.cancelled.emit()

    def _on_ok(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            return
        self.hide()
        self.confirmed.emit(entry, self._overwrite)


class PaginationBar(QFrame):
    """分页栏：上一页 / 页码按钮 / 下一页 / 页码信息，点击发 pageChanged。"""

    pageChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contentPagination")
        self._page = 1
        self._total_pages = 1
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 6, 0, 2)
        root.setSpacing(6)

        self._prev = QPushButton("上一页")
        self._prev.setObjectName("pageNavBtn")
        self._prev.setCursor(Qt.PointingHandCursor)
        self._prev.clicked.connect(lambda: self._go(self._page - 1))
        root.addWidget(self._prev)

        self._pages_holder = QWidget()
        self._pages_layout = QHBoxLayout(self._pages_holder)
        self._pages_layout.setContentsMargins(0, 0, 0, 0)
        self._pages_layout.setSpacing(5)
        root.addWidget(self._pages_holder)

        self._next = QPushButton("下一页")
        self._next.setObjectName("pageNavBtn")
        self._next.setCursor(Qt.PointingHandCursor)
        self._next.clicked.connect(lambda: self._go(self._page + 1))
        root.addWidget(self._next)

        self._info = QLabel("第 1 / 1 页")
        self._info.setObjectName("pageInfo")
        root.addWidget(self._info)
        root.addStretch(1)

    def _go(self, page: int) -> None:
        if 1 <= page <= self._total_pages and page != self._page:
            self.pageChanged.emit(page)

    def update_state(self, page: int, total_pages: int) -> None:
        self._page = page
        self._total_pages = max(1, total_pages)
        self._rebuild()

    def _page_slots(self) -> list:
        """页码槽位：总页数多时只显示首尾与当前页附近，None 表示省略号。"""
        total = self._total_pages
        page = self._page
        if total <= 7:
            return list(range(1, total + 1))
        slots = [1]
        left = max(2, page - 1)
        right = min(total - 1, page + 1)
        if left > 2:
            slots.append(None)
        slots.extend(range(left, right + 1))
        if right < total - 1:
            slots.append(None)
        slots.append(total)
        return slots

    def _rebuild(self) -> None:
        while self._pages_layout.count():
            w = self._pages_layout.takeAt(0).widget()
            if w is not None:
                # dots 是 QLabel，不在 button group 里，只对真正的按钮执行 remove。
                if isinstance(w, QAbstractButton):
                    self._group.removeButton(w)
                w.deleteLater()
        for slot in self._page_slots():
            if slot is None:
                dots = QLabel("…")
                dots.setObjectName("pageDots")
                self._pages_layout.addWidget(dots)
                continue
            btn = QPushButton(str(slot))
            btn.setObjectName("pageNumberBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedSize(30, 30)
            if slot == self._page:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked=False, p=slot: self._go(p))
            self._group.addButton(btn)
            self._pages_layout.addWidget(btn)
        self._prev.setEnabled(self._page > 1)
        self._next.setEnabled(self._page < self._total_pages)
        self._info.setText("第 %s / %s 页" % (self._page, self._total_pages))


class ContentSearchView(QWidget):
    """分类搜索视图：搜索行 + 状态提示 + 两列带图结果网格 + 真实下载。"""

    #: 内容/整合包安装成功后发出目标版本别名，供主窗口即时刷新（免重启）。
    contentChanged = Signal(str)

    def __init__(self, kind: str, hint: str, parent=None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._worker: ContentSearchWorker | None = None
        self._install_worker: ContentInstallWorker | None = None
        self._task_dialog: TaskProgressDialog | None = None
        self._install_outcome = ""
        self._failed_reason = ""
        self._exists_path = ""
        self._pending_item: dict | None = None
        self._pending_entry: dict | None = None
        self._pending_name = ""
        # v1.3.11.0 整合包链路：版本列表线程、安装线程、弹窗、当前项目。
        self._modpack_list_worker: ModpackVersionListWorker | None = None
        self._modpack_worker: ModpackInstallWorker | None = None
        self._modpack_item: dict | None = None
        self._modpack_outcome = ""
        self._modpack_failed_reason = ""
        # v1.3.7.0 分页状态：新搜索回到第 1 页，翻页只改 offset，内容不重复。
        self._page = 1
        self._total_pages = 1
        self._query = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self._input = QLineEdit()
        self._input.setPlaceholderText(hint)
        self._input.setFixedHeight(_BTN_HEIGHT)
        self._input.returnPressed.connect(self._on_search)
        search_row.addWidget(self._input, 1)

        self._search_btn = QPushButton("搜索")
        self._search_btn.setProperty("contentSearchBtn", True)
        self._search_btn.setFixedSize(_BTN_WIDTH, _BTN_HEIGHT)
        self._search_btn.setCursor(Qt.PointingHandCursor)
        self._search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_btn)
        outer.addLayout(search_row)

        self._status = QLabel("输入关键词后点击「搜索」，也可直接搜索浏览热门内容。")
        self._status.setObjectName("contentStatus")
        outer.addWidget(self._status)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("content-scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # v1.3.6.0：彻底隐藏垂直滚动条。Windows 上 QSS 宽度压不住原生滚动条，
        # 用户明确要求「不要看到滑块」；AlwaysOff 后滚轮滚动照常可用。
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setObjectName("content-container")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(_GRID_GAP)
        self._grid.setColumnStretch(_GRID_COLUMNS - 1, 0)
        for col in range(_GRID_COLUMNS):
            self._grid.setColumnStretch(col, 1)
        self._grid.addWidget(_tail_spring(), 0, 0)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

        # v1.3.7.0 分页栏：滚动区下方，收到结果后才显示。
        self._pagination = PaginationBar(self)
        self._pagination.pageChanged.connect(self._goto_page)
        self._pagination.hide()
        outer.addWidget(self._pagination)

        # 版本选择浮层：本视图的直接子控件，不参与布局。
        self._picker = ContentVersionPicker(self)
        self._picker.cancelled.connect(self._on_picker_cancelled)
        self._picker.confirmed.connect(self._on_picker_confirmed)

        # 整合包选版本 + 命名浮层：同样是直接子控件，不参与布局。
        self._modpack_dialog = ModpackInstallDialog(self)
        self._modpack_dialog.cancelled.connect(self._on_modpack_dialog_cancelled)
        self._modpack_dialog.confirmed.connect(self._on_modpack_dialog_confirmed)

    # ---------------- 搜索 ---------------- #
    def trigger_default_search(self) -> None:
        """首次切到该分类时可调用：空关键词直接拉一批热门内容。"""
        if self._worker is None:
            self._on_search()

    def _on_search(self) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            QMessageBox.information(self, C.APP_FULL_NAME, "正在下载内容，请等这次下载完成再搜索。")
            return
        self._query = self._input.text().strip()
        self._page = 1
        self._run_search()

    def _goto_page(self, page: int) -> None:
        """分页栏翻页：同一 query、offset 递增，每页内容不重复。"""
        if self._install_worker is not None and self._install_worker.isRunning():
            QMessageBox.information(self, C.APP_FULL_NAME, "正在下载内容，请等这次下载完成再翻页。")
            return
        self._page = page
        self._run_search()

    def _run_search(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        self._clear_grid()
        self._set_busy(True)
        self._status.setText("正在搜索，请稍候…（第 %s 页）" % self._page)

        offset = (self._page - 1) * DEFAULT_LIMIT
        worker = ContentSearchWorker(self._kind, query=self._query,
                                     offset=offset, parent=self)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self._on_failed)
        self._worker = worker
        worker.start()

    def _on_succeeded(self, result: dict) -> None:
        self._set_busy(False)
        items = result.get("items", [])
        if not items:
            self._pagination.hide()
            self._status.setText("没有找到匹配的内容，换个关键词试试。")
            return
        # 总页数按 total_hits 与每页条数折算；第一页写缓存，后续页仅内存浏览不落缓存。
        total_hits = result.get("total_hits", 0)
        self._total_pages = max(1, math.ceil(total_hits / DEFAULT_LIMIT))
        if self._page == 1:
            head = "共找到 %s 个结果，当前展示第 1 页 %s 个（数据与图片已保存到本地文件夹）。"
        else:
            head = "共找到 %s 个结果，当前第 %s 页，展示 %s 个（本页不写缓存，可直接下载）。"
        self._status.setText(head % (total_hits, self._page, len(items))
                             if self._page != 1
                             else head % (total_hits, len(items)))
        self._clear_grid()
        for index, item in enumerate(items):
            card = ContentCard(item, self._kind, self._container)
            card.downloadClicked.connect(self._on_card_download)
            r, c = divmod(index, _GRID_COLUMNS)
            self._grid.addWidget(card, r, c)
        self._grid.addWidget(_tail_spring(),
                             (len(items) // _GRID_COLUMNS) + 1, 0, 1, _GRID_COLUMNS)
        self._pagination.update_state(self._page, self._total_pages)
        self._pagination.show()
        # 翻页后回到列表顶部；elide 保证新卡片文字不溢出。
        self._scroll.verticalScrollBar().setValue(0)
        self._elide_cards()

    def _on_failed(self, reason: str) -> None:
        self._set_busy(False)
        self._status.setText(reason + "，请检查网络后重试。")

    def _set_busy(self, busy: bool) -> None:
        self._search_btn.setEnabled(not busy)
        self._search_btn.setText("搜索中…" if busy else "搜索")

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _elide_cards(self) -> None:
        # 卡片内文字区宽度 ≈ 视图半宽 - 图标 - 下载按钮 - 内边距/间距。
        text_width = max(80, (self._container.width() // _GRID_COLUMNS)
                         - _ICON - _CARD_BTN_WIDTH - 12 * 2 - 12 - 12 - 24)
        for card in self._container.findChildren(ContentCard):
            card.elide_text(text_width)

    # ---------------- 下载 ---------------- #
    def _on_card_download(self, item: dict) -> None:
        if self._kind == "modpack":
            self._start_modpack_flow(item)
            return
        if self._install_worker is not None and self._install_worker.isRunning():
            QMessageBox.information(self, C.APP_FULL_NAME, "正在下载内容，请等这次下载完成。")
            return

        entries = game_dirs.scan_installed_entries()
        if not entries:
            QMessageBox.information(
                self, C.APP_FULL_NAME,
                "还没有已安装的游戏版本。请先到「原版游戏」分类下载安装一个版本，"
                "再把「%s」下进去。" % KIND_LABELS.get(self._kind, "内容"))
            return

        # v1.3.7.0：所有已安装版本都不兼容时，明确提醒无法下载，不打开选择浮层。
        supported = set(item.get("supported_versions") or [])
        if supported and not any(
            (e.get("mc_version") or e.get("alias")) in supported for e in entries
        ):
            kind_name = KIND_LABELS.get(self._kind, "内容")
            newest = latest_releases(item.get("supported_versions"), 5)
            QMessageBox.warning(
                self, C.APP_FULL_NAME,
                "「%s」不支持你已安装的任何游戏版本，无法下载这个%s。"
                % (item.get("title", ""), kind_name)
                + ("\n\n它支持的正式版：%s" % "、".join(newest) if newest else ""))
            return

        self._pending_item = item
        self._pending_entry = None
        self._picker.open_for(item, entries, self._kind)

    def _on_picker_cancelled(self) -> None:
        self._pending_item = None
        self._pending_entry = None

    def _on_picker_confirmed(self, entry: dict, overwrite: bool) -> None:
        if self._pending_item is None:
            return
        self._pending_entry = entry
        self._pending_name = ""
        self._start_install(self._pending_item, entry, overwrite)

    def _start_install(self, item: dict, entry: dict, overwrite: bool) -> None:
        self._install_outcome = ""
        self._failed_reason = ""
        self._exists_path = ""
        self._status.setText("正在解析 %s 的下载文件…" % item.get("title", ""))
        worker = ContentInstallWorker(
            item.get("project_id", ""),
            self._kind,
            str(entry.get("alias") or ""),
            str(entry.get("mc_version") or ""),
            str(entry.get("loader") or ""),
            overwrite=overwrite,
            parent=self,
        )
        worker.resolved.connect(self._on_install_resolved)
        worker.progress.connect(self._on_install_progress)
        worker.retrying.connect(self._on_install_retrying)
        worker.succeeded.connect(self._on_install_succeeded)
        worker.failed.connect(self._on_install_failed)
        worker.target_exists.connect(self._on_install_exists)
        self._install_worker = worker

        dialog = TaskProgressDialog(
            "%s 下载中" % str(item.get("title") or ""), _CONTENT_PHASES, self)
        self._task_dialog = dialog
        dialog.mark_phase_running(0)
        dialog.cancelRequested.connect(worker.requestInterruption)
        worker.start()
        dialog.exec()

        alias = str(entry.get("alias") or "")
        outcome = self._install_outcome
        self._task_dialog = None
        if outcome == "failed":
            self._status.setText(self._failed_reason)
            QMessageBox.warning(self, C.APP_FULL_NAME, self._failed_reason)
        elif outcome == "exists":
            self._open_overwrite_picker(self._exists_path)
        elif outcome == "succeeded":
            self._status.setText("已下载到 versions/%s。" % alias)
            self.contentChanged.emit(alias)
        self._pending_item = None
        self._pending_entry = None

    def _open_overwrite_picker(self, path: str) -> None:
        """目标目录已有同名文件：弹浮层征询覆盖，绝不静默改名。"""
        if self._pending_item is None or self._pending_entry is None:
            return
        name = os.path.basename(path)
        self._status.setText("目标目录已有「%s」，等待确认是否覆盖。" % name)
        entries = [self._pending_entry]
        self._picker.open_for(self._pending_item, entries, self._kind,
                              overwrite=True, overwrite_name=name)

    def _on_install_resolved(self, info: dict) -> None:
        self._pending_name = str(info.get("filename") or "")
        if self._task_dialog is not None:
            self._task_dialog.set_phase_state(0, STATE_DONE)
            self._task_dialog.set_phase_state(1, STATE_RUNNING)

    def _on_install_progress(self, done: int, total: int) -> None:
        if self._task_dialog is not None:
            self._task_dialog.update_byte_progress(done, total)

    def _on_install_retrying(self, attempt: int, total: int) -> None:
        # 线路重试时保持「下载文件」阶段进行中，不改变阶段勾选。
        if self._task_dialog is not None:
            self._task_dialog.set_phase_state(1, STATE_RUNNING)

    def _on_install_succeeded(self, result: dict) -> None:
        self._install_worker = None
        self._install_outcome = "succeeded"
        dialog = self._task_dialog
        if dialog is not None:
            dialog.finish_success()
            dialog.hide_cancel()
            self._pump(0.6)
            dialog.accept()

    def _on_install_failed(self, reason: str) -> None:
        self._install_worker = None
        self._install_outcome = "failed"
        self._failed_reason = str(reason)
        if self._task_dialog is not None:
            self._task_dialog.reject()

    def _on_install_exists(self, path: str) -> None:
        self._install_worker = None
        self._install_outcome = "exists"
        self._exists_path = str(path)
        if self._task_dialog is not None:
            self._task_dialog.reject()

    @staticmethod
    def _pump(seconds: float) -> None:
        """驱动事件循环并等待，让用户看到 100% 完成态。"""
        import time
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.02)

    # ---------------- 整合包下载 ---------------- #
    def _start_modpack_flow(self, item: dict) -> None:
        if self._modpack_worker is not None and self._modpack_worker.isRunning():
            QMessageBox.information(self, C.APP_FULL_NAME, "正在安装整合包，请等这次安装完成。")
            return
        if self._modpack_list_worker is not None and self._modpack_list_worker.isRunning():
            QMessageBox.information(self, C.APP_FULL_NAME, "正在获取整合包版本，请稍候。")
            return
        self._modpack_item = item
        self._status.setText("正在获取「%s」的版本列表…" % item.get("title", ""))
        worker = ModpackVersionListWorker(
            str(item.get("project_id") or ""), self)
        worker.succeeded.connect(self._on_modpack_versions)
        worker.failed.connect(self._on_modpack_versions_failed)
        self._modpack_list_worker = worker
        worker.start()

    def _on_modpack_versions(self, versions: list[dict]) -> None:
        self._modpack_list_worker = None
        if not versions:
            self._status.setText("这个整合包暂时没有可下载的版本。")
            QMessageBox.information(
                self, C.APP_FULL_NAME, "这个整合包暂时没有可下载的 .mrpack 版本。")
            self._modpack_item = None
            return
        if self._modpack_item is None:
            return
        self._status.setText("请选择整合包版本并命名。")
        self._modpack_dialog.open_for(self._modpack_item, versions)

    def _on_modpack_versions_failed(self, reason: str) -> None:
        self._modpack_list_worker = None
        self._status.setText(reason)
        QMessageBox.warning(self, C.APP_FULL_NAME, reason)
        self._modpack_item = None

    def _on_modpack_dialog_cancelled(self) -> None:
        self._status.setText("已取消整合包安装。")
        self._modpack_item = None

    def _on_modpack_dialog_confirmed(self, chosen: dict, alias: str) -> None:
        if self._modpack_item is None:
            return
        chosen = dict(chosen)
        chosen["project_id"] = str(self._modpack_item.get("project_id") or "")
        chosen["modpack_name"] = str(self._modpack_item.get("title") or "")
        self._modpack_outcome = ""
        self._modpack_failed_reason = ""
        self._status.setText("开始安装整合包到 %s…" % alias)
        worker = ModpackInstallWorker(chosen, alias, self)
        worker.phaseChanged.connect(self._on_modpack_phase)
        worker.progress.connect(self._on_modpack_progress)
        worker.succeeded.connect(self._on_modpack_succeeded)
        worker.failed.connect(self._on_modpack_failed)
        self._modpack_worker = worker

        dialog = TaskProgressDialog(
            "%s 安装中" % str(chosen.get("modpack_name") or "整合包"),
            PHASE_LABELS, self)
        self._task_dialog = dialog
        dialog.mark_phase_running(0)
        dialog.cancelRequested.connect(worker.requestInterruption)
        worker.start()
        dialog.exec()

        self._task_dialog = None
        if self._modpack_outcome == "failed":
            self._status.setText(self._modpack_failed_reason)
            QMessageBox.warning(
                self, C.APP_FULL_NAME, self._modpack_failed_reason)
        elif self._modpack_outcome == "succeeded":
            self._status.setText("整合包「%s」安装完成。" % alias)
            self.contentChanged.emit(alias)
        self._modpack_item = None

    def _on_modpack_phase(self, index: int, label: str) -> None:
        if self._task_dialog is not None:
            self._task_dialog.mark_phase_running(index)

    def _on_modpack_progress(self, percent: float, done: int,
                             total: int, speed: float, remaining: int) -> None:
        if self._task_dialog is not None:
            self._task_dialog.set_progress(
                float(percent), float(speed), int(remaining))

    def _on_modpack_succeeded(self, result: dict) -> None:
        self._modpack_worker = None
        self._modpack_outcome = "succeeded"
        dialog = self._task_dialog
        if dialog is not None:
            dialog.finish_success()
            dialog.hide_cancel()
            self._pump(0.6)
            dialog.accept()

    def _on_modpack_failed(self, reason: str) -> None:
        self._modpack_worker = None
        self._modpack_outcome = "failed"
        self._modpack_failed_reason = str(reason)
        if self._task_dialog is not None:
            self._task_dialog.reject()

    # ---------------- 生命周期 ---------------- #
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._elide_cards()
        if self._picker.isVisible():
            self._picker.reposition()
        if self._modpack_dialog.isVisible():
            self._modpack_dialog.reposition()

    def shutdown(self) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            self._install_worker.requestInterruption()
            self._install_worker.wait(3000)
        self._install_worker = None
        if self._modpack_worker is not None and self._modpack_worker.isRunning():
            self._modpack_worker.requestInterruption()
            self._modpack_worker.wait(3000)
        self._modpack_worker = None
        if self._modpack_list_worker is not None and self._modpack_list_worker.isRunning():
            self._modpack_list_worker.requestInterruption()
            self._modpack_list_worker.wait(2000)
        self._modpack_list_worker = None
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        self._worker = None


def _tail_spring() -> QWidget:
    spring = QWidget()
    spring.setObjectName("content-spring")
    sp = QVBoxLayout(spring)
    sp.setContentsMargins(0, 0, 0, 0)
    sp.addStretch(1)
    return spring
