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

"""版本详情视图：返回箭头 + 版本别名输入框 + 五张加载器分组卡片 + 底部开始下载胶囊。

进入视图后自动在后台线程扫描当前 MC 版本对 Forge / NeoForge / Fabric / OptiFine 的支持性；
探测结果按 MC 版本缓存到 ``yd/loader_support_cache.json``（见 :mod:`cloud_launcher.loaders`），
同一版本再次打开直接读缓存、不重新联网。

v1.2.12.2：
- 每个加载器分组卡片整块与候选版本行改为片内局部磨砂（毛玻璃）自绘背板，压在用户自换
  壁纸的大字 / 卡通插画之上保证标题与版本号可读；选中分组换浅蓝玻璃；不可用分组压暗。

v1.2.12.1：
- 修复新年度版本号（如 26.3）被探测逻辑误判置灰、卡片点不动的问题；
- 可用加载器分组对齐 PCL2 形态：横条点击展开 / 收起，下方列出「全部版本(N)」竖排候选，
  单选具体版本、默认选中最新稳定版；不可用分组置灰、不可展开；原版分组始终可选、不展开；
- 分组横条内标题 / 状态 / 箭头文字标签鼠标事件穿透到分组本体，点在文字上也能触发点击。

视图只负责收集「MC 版本号 / 自定义别名 / 所选加载器 / 加载器版本」并对外发信号；实际下载
任务由下载页统一调度单例 worker，别名冲突 / 重复下载口径由下载页判定。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .loader_probe_worker import LoaderProbeWorker
from .appearance import appearance
from .frosted_backdrop import paint_frosted_panel

# 展开 / 收起手风琴动画时长（毫秒）：展开略快、收起略缓，模拟 PCL2 手感。
_EXPAND_MS = 220
_COLLAPSE_MS = 180
_MAX_HEIGHT_INF = 16777215


def _format_release_time(raw: str) -> str:
    """把端点 ISO 时间规整为 ``YYYY/MM/DD HH:MM``；缺失 / 解析失败返回空串。"""
    text = str(raw or "").strip()
    if not text:
        return ""
    # 形如 2026-10-29T20:21:34.000Z / 2026-10-29 20:21:34
    head = text.replace("T", " ")[:16]
    parts = head.split(" ")
    if len(parts) != 2:
        return ""
    date_part = parts[0].split("-")
    if len(date_part) != 3:
        return ""
    return f"{date_part[0]}/{date_part[1]}/{date_part[2]} {parts[1]}"


class _VersionRow(QFrame):
    """分组展开区内单条候选版本行：版本号 + 可选发布时间，点击单选。

    背板由 paintEvent 片内局部磨砂自绘（不挂 QGraphicsBlurEffect），选中行换浅蓝玻璃。
    """

    chosen = Signal(str)

    def __init__(self, version: str, time_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loaderVersionRow")
        self._version = version
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)

        self._version_label = QLabel(version)
        self._version_label.setObjectName("loaderVersionRowTitle")
        row.addWidget(self._version_label)
        row.addStretch(1)

        self._time_label = QLabel(time_text)
        self._time_label.setObjectName("loaderVersionRowTime")
        if time_text:
            row.addWidget(self._time_label)

        for child in (self._version_label, self._time_label):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    @property
    def version(self) -> str:
        return self._version

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._selected:
            top, mid, bottom, border = (
                C.COLOR_DETAIL_ACTIVE_TOP_RGBA,
                C.COLOR_DETAIL_ACTIVE_MID_RGBA,
                C.COLOR_DETAIL_ACTIVE_BOTTOM_RGBA,
                C.COLOR_DETAIL_ACTIVE_BORDER_RGBA,
            )
        else:
            top, mid, bottom, border = (
                C.COLOR_DETAIL_ROW_TOP_RGBA,
                C.COLOR_DETAIL_ROW_MID_RGBA,
                C.COLOR_DETAIL_ROW_BOTTOM_RGBA,
                C.COLOR_DETAIL_ROW_BORDER_RGBA,
            )
        paint_frosted_panel(
            painter, self, C.COLOR_DETAIL_ROW_RADIUS, top, mid, bottom, border
        )
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        if event.button() == Qt.LeftButton:
            self.chosen.emit(self._version)
        super().mousePressEvent(event)


class _LoaderSection(QFrame):
    """加载器分组：横条（名称 + 最新版本状态 + 展开箭头）+ 可收起的候选版本列表。

    原版分组 ``is_vanilla=True``：不展开、不挂版本列表，横条点击即选回原版。
    """

    headerClicked = Signal(str)
    versionChosen = Signal(str, str)

    def __init__(self, loader_key: str, title: str, is_vanilla: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loaderSection")
        self._key = loader_key
        self._is_vanilla = is_vanilla
        self._available = True
        self._group_selected = False
        self._expanded = False
        self._versions: list[dict] = []
        self._selected_version = ""
        self._rows: list[_VersionRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 横条 ----
        self._header = QFrame(self)
        self._header.setObjectName("loaderSectionHeader")
        self._header.setCursor(Qt.PointingHandCursor)
        header_row = QHBoxLayout(self._header)
        header_row.setContentsMargins(16, 12, 16, 12)
        header_row.setSpacing(10)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("loaderCardTitle")
        header_row.addWidget(self._title_label)
        header_row.addStretch(1)

        self._status_label = QLabel(C.LOADER_PROBING_TEXT)
        self._status_label.setObjectName("loaderCardStatus")
        header_row.addWidget(self._status_label)

        self._arrow_label = QLabel("›" if not is_vanilla else "")
        self._arrow_label.setObjectName("loaderCardArrow")
        header_row.addWidget(self._arrow_label)

        for child in (self._title_label, self._status_label, self._arrow_label):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        outer.addWidget(self._header)

        # ---- 展开区（原版不创建）----
        self._body_host: QWidget | None = None
        self._rows_host: QWidget | None = None
        self._count_label: QLabel | None = None
        self._expand_anim: QPropertyAnimation | None = None
        if not is_vanilla:
            self._body_host = QWidget(self)
            self._body_host.setObjectName("loaderSectionBody")
            body_layout = QVBoxLayout(self._body_host)
            body_layout.setContentsMargins(10, 0, 10, 10)
            body_layout.setSpacing(6)

            self._count_label = QLabel("")
            self._count_label.setObjectName("loaderVersionCount")
            body_layout.addWidget(self._count_label)

            self._rows_host = QWidget(self._body_host)
            self._rows_host.setObjectName("loaderVersionRows")
            self._rows_layout = QVBoxLayout(self._rows_host)
            self._rows_layout.setContentsMargins(0, 0, 0, 0)
            self._rows_layout.setSpacing(6)
            body_layout.addWidget(self._rows_host)

            # 收起态：maximumHeight 钉 0，配合 set_expanded 的高度动画实现平滑手风琴。
            self._body_host.setMaximumHeight(0)
            self._body_host.setVisible(False)
            outer.addWidget(self._body_host)

        # 横条点击事件挂在 header 上；标签已穿透，事件落到 header。
        self._header.mousePressEvent = self._on_header_press  # type: ignore[method-assign]

    # ------------------------------------------------------------------ #
    # 状态回填
    # ------------------------------------------------------------------ #
    def _on_header_press(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._available:
            self.headerClicked.emit(self._key)
        super().mousePressEvent(event)

    @property
    def key(self) -> str:
        return self._key

    @property
    def available(self) -> bool:
        return self._available

    def selected_version(self) -> str:
        return self._selected_version

    def set_state(self, available: bool, status_text: str, detail_version: str = "",
                  versions: list[dict] | None = None) -> None:
        """回填探测结果：可用 / 不可用 / 探测中三态；不可用时收起并取消选中。

        v1.2.12.21：加载器可用但未选版本时状态显示「无」，不自动预选最新稳定版；
        用户在展开列表里点选具体版本后才显示选中的版本号。
        """
        self._available = available
        self.setEnabled(available)
        version = str(detail_version or "").strip()
        self._versions = [dict(item) for item in (versions or [])]

        if not available:
            self._status_label.setText(status_text)
            self._status_label.setProperty("unavailable", True)
            self._selected_version = ""
            self.set_expanded(False)
            self.set_group_selected(False)
            self._rebuild_rows()
        elif self._is_vanilla:
            # 原版：右侧显示当前 MC 版本号，默认选中
            self._status_label.setText(version)
            self._status_label.setProperty("unavailable", False)
            self._selected_version = ""  # 原版不需要具体版本号
            self.set_group_selected(True)
            self._rebuild_rows()
        else:
            # 第三方加载器：默认可用但未选版本，显示「无」，不选中
            self._status_label.setText("无")
            self._status_label.setProperty("unavailable", False)
            self._selected_version = ""  # 不自动预选，等用户展开选
            self.set_group_selected(False)
            self._rebuild_rows()
        self._refresh_style()

    def reset_probing(self) -> None:
        """重新进入版本 / 重启探测：回到探测中待回填态、收起展开区。"""
        self._available = True
        self.setEnabled(True)
        self._status_label.setText(C.LOADER_PROBING_TEXT)
        self._status_label.setProperty("unavailable", False)
        self._selected_version = ""
        self._versions = []
        self.set_expanded(False)
        self.set_group_selected(False)
        self._rebuild_rows()
        self._refresh_style()

    # ------------------------------------------------------------------ #
    # 展开 / 选中
    # ------------------------------------------------------------------ #
    def set_expanded(self, expanded: bool) -> None:
        """展开 / 收起：用 maximumHeight 手风琴动画，避免内容瞬间顶出挤压感。"""
        self._expanded = expanded
        self._arrow_label.setText("∧" if expanded else "›")
        if self._body_host is None:
            return
        # 停掉上一轮动画，避免方向打架。
        if self._expand_anim is not None:
            try:
                self._expand_anim.stop()
            except RuntimeError:
                pass
            self._expand_anim = None

        target = self._body_host
        if not appearance.animations_enabled:
            # 总开关关闭：瞬时展开/收起，不播放手风琴动画。
            if expanded:
                target.setVisible(True)
                target.adjustSize()
                target.setMaximumHeight(_MAX_HEIGHT_INF)
            else:
                target.setMaximumHeight(0)
                target.setVisible(False)
            return
        if expanded:
            target.setVisible(True)
            # 先让布局算一遍真实高度，再从 0 平滑长出来。
            target.adjustSize()
            end_h = max(target.sizeHint().height(), 1)
            anim = QPropertyAnimation(target, b"maximumHeight", self)
            anim.setDuration(_EXPAND_MS)
            anim.setStartValue(target.maximumHeight())
            anim.setEndValue(end_h)
            anim.setEasingCurve(QEasingCurve.OutCubic)

            def _done_open() -> None:
                target.setMaximumHeight(_MAX_HEIGHT_INF)
                self._expand_anim = None

            anim.finished.connect(_done_open)
            self._expand_anim = anim
            anim.start()
        else:
            # 从当前可视高度平滑收回到 0，动画结束再隐藏。
            start_h = target.height()
            anim = QPropertyAnimation(target, b"maximumHeight", self)
            anim.setDuration(_COLLAPSE_MS)
            anim.setStartValue(start_h)
            anim.setEndValue(0)
            anim.setEasingCurve(QEasingCurve.InOutCubic)

            def _done_close() -> None:
                target.setVisible(False)
                target.setMaximumHeight(_MAX_HEIGHT_INF)
                self._expand_anim = None

            anim.finished.connect(_done_close)
            self._expand_anim = anim
            anim.start()

    def is_expanded(self) -> bool:
        return self._expanded

    def set_group_selected(self, selected: bool) -> None:
        self._group_selected = selected
        self._header.setProperty("selected", selected)
        self._header.style().unpolish(self._header)
        self._header.style().polish(self._header)
        self._header.update()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        """分组整块（横条 + 展开列表）片内局部磨砂背板，覆盖高饱和壁纸保证标题可读。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if not self.isEnabled():
            # 不可用分组：压暗一档、边框变淡，文字由既有置灰样式承担。
            top, mid, bottom, border = (
                C.COLOR_DETAIL_GLASS_TOP_RGBA[0:3] + (150,),
                C.COLOR_DETAIL_GLASS_MID_RGBA[0:3] + (108,),
                C.COLOR_DETAIL_GLASS_BOTTOM_RGBA[0:3] + (78,),
                C.COLOR_DETAIL_BORDER_RGBA[0:3] + (110,),
            )
        else:
            # 所有可用分组统一磨砂玻璃效果，选中态只靠文字颜色/加粗区分，不换背景色
            top, mid, bottom, border = (
                C.COLOR_DETAIL_GLASS_TOP_RGBA,
                C.COLOR_DETAIL_GLASS_MID_RGBA,
                C.COLOR_DETAIL_GLASS_BOTTOM_RGBA,
                C.COLOR_DETAIL_BORDER_RGBA,
            )
        paint_frosted_panel(
            painter, self, C.COLOR_DETAIL_SECTION_RADIUS, top, mid, bottom, border
        )
        painter.end()

    def highlight_version(self, version: str) -> None:
        self._selected_version = version
        for row in self._rows:
            row.set_selected(row.version == version)

    def _rebuild_rows(self) -> None:
        if self._rows_host is None:
            return
        # 清空旧行
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

        if self._count_label is not None:
            total = len(self._versions)
            self._count_label.setText(f"全部版本（{total}）" if total else "")

        # 加载器列表最上面加一个「无」选项，选错了可以直接退回去
        if not self._is_vanilla:
            none_row = _VersionRow("无", "", self._rows_host)
            none_row.chosen.connect(lambda _: self.versionChosen.emit(self._key, ""))
            none_row.set_selected(self._selected_version == "")
            self._rows_layout.addWidget(none_row)
            self._rows.append(none_row)

        for item in self._versions:
            ver = str(item.get("version") or "")
            if not ver:
                continue
            row = _VersionRow(ver, _format_release_time(str(item.get("time") or "")), self._rows_host)
            row.chosen.connect(lambda _, v=ver: self.versionChosen.emit(self._key, v))
            row.set_selected(ver == self._selected_version)
            self._rows_layout.addWidget(row)
            self._rows.append(row)

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self.update()


class VersionDetailView(QWidget):
    """版本详情页：头部返回 + 别名输入、中部加载器分组列表、底部开始下载胶囊。"""

    #: 点返回箭头，回到版本列表。
    backRequested = Signal()
    #: 点击开始下载：回传 (mc_version, alias, loader, loader_version)。
    startDownloadRequested = Signal(str, str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("versionDetailView")
        self._mc_version = ""
        self._selected_loader = C.LOADER_VANILLA
        self._loader_version: dict[str, str] = {}
        self._probe_worker: LoaderProbeWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(16)

        # ---- 顶部：返回箭头 + 版本别名输入框 ----
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._back_button = QPushButton("←")
        self._back_button.setObjectName("detailBackBtn")
        self._back_button.setFixedWidth(44)
        self._back_button.setFixedHeight(40)
        self._back_button.setCursor(Qt.PointingHandCursor)
        self._back_button.clicked.connect(self.backRequested.emit)
        header.addWidget(self._back_button)

        self._alias_input = QLineEdit()
        self._alias_input.setObjectName("detailAliasInput")
        self._alias_input.setPlaceholderText("输入版本别名")
        self._alias_input.setFixedHeight(40)
        header.addWidget(self._alias_input, 1)
        root.addLayout(header)

        # ---- 中部分组列表（本视图自身可滚，与外层页面滚动条隔离）----
        scroll = QScrollArea()
        scroll.setObjectName("detail-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        # v1.2.12.11：彻底隐藏垂直滚动条（原生宽度压不住，见 download_page 注释）
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll = scroll

        card_host = QWidget()
        card_host.setObjectName("detailCardHost")
        card_col = QVBoxLayout(card_host)
        card_col.setContentsMargins(0, 0, 0, 0)
        card_col.setSpacing(12)

        self._cards: dict[str, _LoaderSection] = {}
        # 原版分组固定在最前、始终可用、默认选中、不可展开。
        vanilla_section = _LoaderSection(
            C.LOADER_VANILLA, C.LOADER_LABELS[C.LOADER_VANILLA],
            is_vanilla=True, parent=self,
        )
        vanilla_section.set_state(True, "", detail_version="")
        vanilla_section.headerClicked.connect(self._on_section_header_clicked)
        self._cards[C.LOADER_VANILLA] = vanilla_section
        card_col.addWidget(vanilla_section)

        for loader_key in C.LOADER_CARD_ORDER:
            section = _LoaderSection(
                loader_key, C.LOADER_LABELS[loader_key], parent=self,
            )
            section.headerClicked.connect(self._on_section_header_clicked)
            section.versionChosen.connect(self._on_version_chosen)
            self._cards[loader_key] = section
            card_col.addWidget(section)

        card_col.addStretch(1)
        scroll.setWidget(card_host)
        root.addWidget(scroll, 1)

        # ---- 底部居中开始下载胶囊 ----
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addStretch(1)
        self._start_button = QPushButton(C.DETAIL_START_DOWNLOAD_TEXT)
        self._start_button.setObjectName("detailStartDownloadBtn")
        self._start_button.setFixedHeight(44)
        self._start_button.setMinimumWidth(220)
        self._start_button.setCursor(Qt.PointingHandCursor)
        self._start_button.clicked.connect(self._emit_start)
        bottom_row.addWidget(self._start_button)
        bottom_row.addStretch(1)
        root.addLayout(bottom_row)

        self._select_loader(C.LOADER_VANILLA)

    # ------------------------------------------------------------------ #
    # 对外状态控制
    # ------------------------------------------------------------------ #
    def open_for(self, mc_version: str) -> None:
        """重置视图到指定 MC 版本：别名默认填版本号、分组回探测态、后台启动兼容性扫描。"""
        self._mc_version = str(mc_version or "").strip()
        self._alias_input.setText(self._mc_version)
        self._loader_version = {}
        self._selected_loader = C.LOADER_VANILLA
        for section in self._cards.values():
            section.reset_probing()
        self._select_loader(C.LOADER_VANILLA)
        self._start_probe()

    def focus_alias_input(self) -> None:
        """v1.3.2.0：撞名 / 别名为空弹框后，聚焦别名输入框并选中当前文字，方便立刻改名。"""
        self._alias_input.setFocus()
        self._alias_input.selectAll()

    def shutdown(self) -> None:
        """退出页面 / 关闭窗口时中断探测线程，等待收尾避免原生层崩溃。

        中断信号只在两次网络请求之间生效；阻塞在 ``urlopen`` 内的当前请求要等单次超时
        （META_PROBE_TIMEOUT）返回后才会检查中断并退出，因此等待窗口覆盖一次超时余量。
        等待超时仍未结束时保留线程引用，不把成员置空，避免 Python 回收仍在运行的 QThread
        触发原生层 0xC0000409。
        """
        worker = self._probe_worker
        if worker is None:
            return
        try:
            if worker.isRunning():
                worker.requestInterruption()
                finished = worker.wait(C.META_PROBE_TIMEOUT * 1000 + 2000)
                if finished:
                    self._probe_worker = None
                # 未结束：保留引用，由父对象生命周期托管，线程自然收尾。
            else:
                self._probe_worker = None
        except RuntimeError:
            self._probe_worker = None

    # ------------------------------------------------------------------ #
    # 探测线程
    # ------------------------------------------------------------------ #
    def _start_probe(self) -> None:
        self.shutdown()
        if not self._mc_version:
            return
        worker = LoaderProbeWorker(self._mc_version, self)
        worker.succeeded.connect(self._on_probe_succeeded)
        worker.failed.connect(self._on_probe_failed)
        self._probe_worker = worker
        worker.start()

    def _on_probe_succeeded(self, result: dict) -> None:
        for loader_key, info in (result or {}).items():
            section = self._cards.get(loader_key)
            if section is None:
                continue
            available = bool(info.get("available"))
            version = str(info.get("version") or "")
            versions = info.get("versions") or []
            self._loader_version[loader_key] = version
            section.set_state(
                available,
                C.LOADER_AVAILABLE_TEXT if available else C.LOADER_UNAVAILABLE_TEXT,
                detail_version=version,
                versions=versions,
            )
        # 原版不参与第三方探测，探测结束后回填为始终可用态（open_for 时统一重置过文案）。
        self._cards[C.LOADER_VANILLA].set_state(True, "", detail_version=self._mc_version)
        # 探测完成后强制重置选中态：只有原版选中，所有加载器都是白底
        self._select_loader(C.LOADER_VANILLA, "")
        # 探测完成后若当前选中的加载器恰好不可用，退回原版。
        if not self._cards[self._selected_loader].available:
            self._select_loader(C.LOADER_VANILLA)

    def _on_probe_failed(self, _reason: str) -> None:
        # 探测整体失败：四张第三方分组按不可用兜底，原版仍可选。
        for loader_key in C.LOADER_CARD_ORDER:
            section = self._cards[loader_key]
            section.set_state(False, C.LOADER_UNAVAILABLE_TEXT)
        self._cards[C.LOADER_VANILLA].set_state(True, "", detail_version=self._mc_version)

    # ------------------------------------------------------------------ #
    # 交互
    # ------------------------------------------------------------------ #
    def _close_other_sections(self, keep_key: str) -> None:
        for key, section in self._cards.items():
            if key != keep_key:
                section.set_expanded(False)

    def _select_loader(self, loader_key: str, version: str = "") -> None:
        self._selected_loader = loader_key
        for key, section in self._cards.items():
            section.set_group_selected(key == loader_key)
        if version:
            self._loader_version[loader_key] = version

    def _on_section_header_clicked(self, loader_key: str) -> None:
        section = self._cards[loader_key]
        if not section.available:
            return

        if loader_key == C.LOADER_VANILLA:
            self._close_other_sections(loader_key)
            self._select_loader(C.LOADER_VANILLA)
            return

        # 再次点击已展开分组 → 收起；否则展开本分组、收起其余，并默认选中最新版本。
        if section.is_expanded():
            section.set_expanded(False)
            return

        self._close_other_sections(loader_key)
        section.set_expanded(True)
        latest = section.selected_version()
        self._select_loader(loader_key, latest)
        section.highlight_version(latest)
        # 动画期间布局高度在变，等动画收尾再把整个分组滚到可视区，避免版本列表被顶出屏幕。
        QTimer.singleShot(_EXPAND_MS + 40, lambda s=section: self._scroll.ensureWidgetVisible(s, 60, 240))

    def _on_version_chosen(self, loader_key: str, version: str) -> None:
        section = self._cards[loader_key]
        if not version:
            # 选了「无」：切回原版
            self._select_loader(C.LOADER_VANILLA, "")
            section.highlight_version("")
            section._status_label.setText("无")
            section._status_label.style().unpolish(section._status_label)
            section._status_label.style().polish(section._status_label)
            return
        self._select_loader(loader_key, version)
        section.highlight_version(version)
        # 选中版本后横条右侧状态更新为选中的版本号
        section._status_label.setText(version)
        section._status_label.style().unpolish(section._status_label)
        section._status_label.style().polish(section._status_label)

    def _emit_start(self) -> None:
        alias = self._alias_input.text().strip() or self._mc_version
        loader_version = self._loader_version.get(self._selected_loader, "")
        self.startDownloadRequested.emit(
            self._mc_version, alias, self._selected_loader, loader_version
        )
