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

"""v1.2.12.0 下载页：列表态 ↔ 版本详情态双层栈；分类标签 + 可折叠分组 + 单例下载浮层。

页面归属沿用方案 A：「启动」导航显示个人页，「下载」导航显示本骨架页。

- 顶层 ``QStackedWidget``：index 0 为原有分组列表，index 1 为 ``VersionDetailView``
  版本详情视图；条目下载按钮先切进详情页，选好加载器、填好别名后再发起下载；
- 顶部分类标签：原版游戏 / mod / 整合包 / 光影包 / 资源包 / 数据包，点击只切换
  选中高亮视觉态，不接真实分类拉取；
- 五个分组：最新版本 / 正式版 / 预览版 / 远古版 / 愚人节版。分组标题横条最左侧挂本组
  分类方块图标；点击标题横条平滑展开 / 收起；
- 「最新版本」分组固定两行实时条目：最新正式版、最新预览版；
- 四个全量分组承载清单内全量分类版本：点开分组才懒加载构建条目、收起即释放；分组内
  不再开设独立滚动区，垂直滚动全部交给最外侧一条极细透明滚动条；条目为「分组小方块
  图标 + 版本号 + 发布日期 + 下载按钮」轻量玻璃行；
- v1.2.12.0 下载接线：未安装 / 已安装条目点击都进入版本详情页，可对同一版本重复下载；
  同时只允许一个下载任务（单任务单例），详情页点「开始下载」后弹出复用同一实例的
  ``DownloadPanel`` 单例浮层：顶部居中铺开 / 5 秒无操作自动收回右下角小胶囊、总进度 /
  速度 / 剩余文件 + 五步分步清单，底部居中大叉可中途取消；下载成功后更新已安装集合、
  刷新全部条目按钮态，并对外发 ``versionInstalled`` 信号供个人页刷新版本选择列表；
- v1.3.2.0：条目按钮不再有「已安装」置灰态，所有版本（含已装）按钮恒为「下载」且可点；
  点「开始下载」时若别名目录已存在，不再静默自动改名，弹中文提示框要求立刻重新命名，
  改名后才放行下载；
- 清单缓存（v1.2.10.0）：分类结果落盘 ``yd/version_manifest_cache.json``，首次无缓存才
  联网全量拉取，之后启动直接读缓存渲染；后台轻量检查发现新版本时弹淡入淡出提示窗；
- 下载编排覆盖原版 profile、依赖库、natives、资源对象、client.jar 与加载器专属库；
  离线 / 超时 / 解析失败静默回退不弹窗、不崩溃；
- 配色沿用既有浅蓝白 iOS 玻璃体系，不引入不透明实色块；不挂 QGraphicsBlurEffect、
  不引第三方模糊库，片内磨砂复用 ``frosted_backdrop.paint_frosted_panel``。
"""
from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import game_dirs
from ..resources import resource_path
from ..version_meta import (
    load_cached_manifest,
    save_cached_manifest,
)
from .download_panel import DownloadPanel
from .download_worker import VersionDownloadWorker
from .content_search_view import ContentSearchView
from .appearance import appearance
from .frosted_backdrop import paint_frosted_panel
from .version_detail_view import VersionDetailView
from .version_meta_worker import VersionCheckWorker, VersionMetaWorker

# 分组横条 / 条目尺寸（较 v1.2.6.1 再整体缩小一档）。
_SECTION_RADIUS = 12.0
_HEADER_HEIGHT = 36
_ICON_SIZE = 28
_HEADER_GAP = 10
_ROW_GAP = 8
_BODY_PAD = 12
_TAB_HEIGHT = 38
# 分类标签行上下间距：顶部留白让标签不贴窗口顶，底部留白让下方搜索框 / 分组不紧贴标签。
_TAB_TOP_MARGIN = 12
_TAB_BOTTOM_MARGIN = 10
_ANIM_MS = 260

# 顶部分类标签顺序（与参考图一致）。
CATEGORY_TABS = ("原版游戏", "mod", "整合包", "光影包", "资源包", "数据包")

# 分组定义：(内部 key, 标题, 分组类型, 占位方块贴图(None=无), 是否默认展开)。
# v1.3.1.7：移除与正式版 / 预览版首条重复的「最新版本」分组，只保留四个全量分组。
# list 分组 = 点开展开全量列表（数据到达即后台分批预建，展开即时显示）。
SECTIONS = (
    ("release", "正式版", "list", "grass_block.png", False),
    ("snapshot", "预览版", "list", "diamond_block.png", False),
    ("ancient", "远古版", "list", "command_block.png", False),
    ("april", "愚人节版", "list", "gold_block.png", False),
)

# 四个全量分组在 version_meta 返回字典里的键，顺序与 cards 一致。
LIST_SECTION_KEYS = ("release", "snapshot", "ancient", "april")

# 分组分类方块缩放缓存：同一个分组在横条 / 数百条条目里共享同一张缩放后的 QPixmap，
# 避免每条条目重复解码 256×256 原图与重复缩放（预览版 748 条性能关键）。
_PIXMAP_CACHE: dict[tuple[str, int], QPixmap] = {}


def _scaled_block_pixmap(block_file: str | None, size: int) -> QPixmap | None:
    """按 ``(贴图名, 尺寸)`` 取共享缩放方块贴图；文件缺失 / 解码失败返回 ``None``。"""
    if not block_file:
        return None
    key = (block_file, size)
    cached = _PIXMAP_CACHE.get(key)
    if cached is not None:
        return cached
    pix = QPixmap(resource_path(f"blocks/{block_file}"))
    if pix.isNull():
        return None
    scaled = pix.scaled(
        size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    _PIXMAP_CACHE[key] = scaled
    return scaled


class VersionRow(QFrame):
    """最新版本分组内一行条目：方块图标 + 竖排版本号标题 / 发布日期副标题 + 下载按钮。"""

    #: 点击下载按钮，回传版本号给下载页统一调度。
    downloadRequested = Signal(str)

    def __init__(
        self,
        block_file: str | None = None,
        title: str = "",
        subtitle: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("versionRow")
        self._version_id = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(_HEADER_GAP)

        icon = QLabel()
        icon.setProperty("versionRowIcon", True)
        icon.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        icon.setAlignment(Qt.AlignCenter)
        pix = _scaled_block_pixmap(block_file, _ICON_SIZE)
        if pix is not None:
            icon.setPixmap(pix)
        self._icon_label = icon
        row.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        title_label = QLabel(title)
        title_label.setProperty("versionRowTitle", True)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._title_label = title_label
        text_col.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setProperty("versionRowSubtitle", True)
        sub_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sub_label.setVisible(bool(subtitle))
        self._subtitle_label = sub_label
        text_col.addWidget(sub_label)

        row.addLayout(text_col, 1)

        self._download_btn = QPushButton("下载")
        self._download_btn.setObjectName("versionDownloadBtn")
        self._download_btn.setFixedSize(64, 26)
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_btn.clicked.connect(self._emit_download)
        row.addWidget(self._download_btn)

    def set_meta(self, title: str, subtitle: str = "", version_id: str = "") -> None:
        self._title_label.setText(title or "")
        self._subtitle_label.setText(subtitle or "")
        self._subtitle_label.setVisible(bool(subtitle))
        self._version_id = str(version_id or "").strip()

    def _emit_download(self) -> None:
        if self._version_id:
            self.downloadRequested.emit(self._version_id)

    def set_installed(self, installed: bool) -> None:
        """v1.3.2.0：下载页不再显示「已安装」态。

        无论该版本是否已安装，按钮始终可点、文案恒为「下载」，允许对同一版本重复下载；
        是否已安装仍由 ``DownloadPage._is_installed`` 判定，用于「开始下载」时的撞名提示。
        保留本方法签名以兼容条目构建 / 刷新链路，内部只保证按钮处于正常可点状态。
        """
        btn = self._download_btn
        btn.setProperty("installed", False)
        btn.setEnabled(True)
        btn.setText("下载")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()


class VersionEntry(QFrame):
    """全量分组内一条轻量条目：左侧分组小方块图标 + 版本号 + 右侧日期 + 下载按钮。

    支持滑入 / 淡入显现动画；分组内多条条目共享同一张缩放后的分类方块贴图。
    """

    #: 点击下载按钮，回传版本号给下载页统一调度。
    downloadRequested = Signal(str)

    def __init__(
        self,
        entry: dict,
        block_file: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("versionEntry")
        self._version_id = str(entry.get("id") or "").strip()

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(8)

        icon = QLabel()
        icon.setProperty("versionEntryIcon", True)
        icon.setFixedSize(C.ENTRY_ICON_SIZE, C.ENTRY_ICON_SIZE)
        icon.setAlignment(Qt.AlignCenter)
        pix = _scaled_block_pixmap(block_file, C.ENTRY_ICON_SIZE)
        if pix is not None:
            icon.setPixmap(pix)
        self._icon_label = icon
        row.addWidget(icon)

        title = QLabel(str(entry.get("id") or ""))
        title.setProperty("versionEntryTitle", True)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._title_label = title
        row.addWidget(title, 1)

        time_label = QLabel(str(entry.get("time") or ""))
        time_label.setProperty("versionEntryTime", True)
        time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label = time_label
        row.addWidget(time_label)

        self._download_btn = QPushButton("下载")
        self._download_btn.setObjectName("versionDownloadBtn")
        self._download_btn.setFixedSize(58, 24)
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_btn.clicked.connect(self._emit_download)
        row.addWidget(self._download_btn)

        # 显现状态：未显现时透明并偏移到 home 位置一侧；进入视口后动画到 home 位置。
        # 透明度特效按需创建：只有需要滑入 / 隐藏动画的首屏与缓冲带条目才挂 effect，
        # 非首屏条目保持默认不透明，避免数百条各自持有 QGraphicsOpacityEffect 的开销。
        self._revealed = False
        self._home_x: int | None = None
        self._cached_top: int | None = None
        self._anim_group: QParallelAnimationGroup | None = None
        self._opacity_effect: QGraphicsOpacityEffect | None = None

    def _emit_download(self) -> None:
        if self._version_id:
            self.downloadRequested.emit(self._version_id)

    def set_installed(self, installed: bool) -> None:
        """v1.3.2.0：下载页不再显示「已安装」态，按钮恒为「下载」且可点，支持重复下载。

        保留方法签名兼容条目刷新链路；已安装与否的判断仍由下载页保留，用于撞名提示。
        """
        btn = self._download_btn
        btn.setProperty("installed", False)
        btn.setEnabled(True)
        btn.setText("下载")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    def _ensure_effect(self) -> QGraphicsOpacityEffect:
        if self._opacity_effect is None:
            self._opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self._opacity_effect)
        return self._opacity_effect

    # ---------- 显现 / 复位 ----------
    def place_directly(self) -> None:
        """非首屏缓冲带内条目直接就位：不透明、不播动画、不保留隐藏偏移、不挂特效。
        垂直位置完全交给布局，不主动 move y，避免把尚未布局的 y=0 固化到容器顶部。"""
        self._stop_anim()
        self._revealed = True
        if self._home_x is None:
            self._home_x = self.x()
        if self._opacity_effect is not None:
            self._opacity_effect.setOpacity(1.0)
        if self.x() != self._home_x:
            self.move(self._home_x, self.y())

    def reset_hidden(self, direction: int) -> None:
        """复位到未显现状态：透明 + 按滚动方向偏移到一侧，供反向滚回时重新显现。

        direction: 1 = 向下滚（条目从左侧滑入，隐藏时偏左）；-1 = 向上滚（从右侧滑入，
        隐藏时偏右）。
        """
        self._stop_anim()
        self._revealed = False
        self._ensure_effect().setOpacity(0.0)
        if self._home_x is None:
            self._home_x = self.x()
        offset = C.ENTRY_SLIDE_DISTANCE * (-direction)
        self.move(self._home_x + offset, self.y())

    def reveal(self, direction: int, duration_ms: int, start_delay: int = 0) -> None:
        """播放从一侧滑入 + 淡入到就位的显现动画。

        direction: 1 向下滚 → 从左往右；-1 向上滚 → 从右往左。
        """
        if self._revealed:
            return
        self._stop_anim()
        if self._home_x is None:
            self._home_x = self.x()
        home_x = self._home_x
        home_y = self.y()
        offset = C.ENTRY_SLIDE_DISTANCE * (-direction)
        self.move(home_x + offset, home_y)

        if not appearance.animations_enabled:
            # 总开关关闭：瞬时就位、不滑入淡入。
            self._anim_group = None
            self._ensure_effect().setOpacity(1.0)
            self.move(home_x, home_y)
            self._revealed = True
            return

        effect = self._ensure_effect()
        group = QParallelAnimationGroup(self)

        pos_anim = QPropertyAnimation(self, b"pos", self)
        pos_anim.setDuration(duration_ms)
        pos_anim.setStartValue(QPoint(home_x + offset, home_y))
        pos_anim.setEndValue(QPoint(home_x, home_y))
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        fade_anim = QPropertyAnimation(effect, b"opacity", self)
        fade_anim.setDuration(duration_ms)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        group.addAnimation(pos_anim)
        group.addAnimation(fade_anim)
        pos_anim.startDelay = start_delay
        fade_anim.startDelay = start_delay
        group.finished.connect(self._on_reveal_finished)
        self._anim_group = group
        group.start()

    def _stop_anim(self) -> None:
        if self._anim_group is not None:
            try:
                try:
                    self._anim_group.finished.disconnect()
                except RuntimeError:
                    pass
                self._anim_group.stop()
                self._anim_group.deleteLater()
            except RuntimeError:
                pass
            self._anim_group = None

    def _on_reveal_finished(self) -> None:
        self._revealed = True
        if self._opacity_effect is not None:
            self._opacity_effect.setOpacity(1.0)
        self.move(self._home_x if self._home_x is not None else self.x(), self.y())
        self._anim_group = None


class UpdateNoticePopup(QFrame):
    """后台检查发现新版本时的非模态小提示窗：淡入停留，点「知道了」淡出后销毁。

    作为下载页直接子控件浮层，不弹模态、不阻断主窗口操作；当前已渲染的缓存列表
    保持不重建，新清单仅静默覆盖本地缓存，下次启动自动生效。
    """

    def __init__(self, parent: QWidget, changes: list[dict]) -> None:
        super().__init__(parent)
        self.setObjectName("updateNoticePopup")
        self._changes = changes
        self._closed = False
        self._fade_anim: QPropertyAnimation | None = None

        # 淡入 / 淡出由 QGraphicsOpacityEffect 驱动（工程红线：不挂 QGraphicsBlurEffect）。
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        title = QLabel("发现新版本")
        title.setProperty("updateNoticeTitle", True)
        root.addWidget(title)

        intro = QLabel("检测到 Minecraft 版本更新，已加入最新版本。")
        intro.setProperty("updateNoticeHint", True)
        intro.setWordWrap(True)
        root.addWidget(intro)

        body = QVBoxLayout()
        body.setContentsMargins(0, 2, 0, 0)
        body.setSpacing(8)
        for change in changes:
            body.addWidget(self._build_change_row(change))
        root.addLayout(body)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 4, 0, 0)
        buttons.addStretch(1)
        ok = QPushButton("知道了")
        ok.setObjectName("updateNoticeOk")
        ok.setFixedHeight(34)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.dismiss)
        buttons.addWidget(ok)
        root.addLayout(buttons)

        self.setFixedWidth(350)
        # 弹窗作为下载页直接子浮层、不参与父布局，show() 不会自动按 sizeHint 撑开；
        # 必须手动按 sizeHint 调整并锁定高度，否则高度停在默认 30px、子控件挤压重叠；
        # 锁定高度也避免垂直布局把各行拉高出多余空白。
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())
        QTimer.singleShot(0, self._center_on_parent)
        self.raise_()

    # ---------- 变化项行 ----------
    @staticmethod
    def _build_change_row(change: dict) -> QFrame:
        row = QFrame()
        row.setObjectName("updateNoticeRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setProperty("updateNoticeRowIcon", True)
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignCenter)
        pix = _scaled_block_pixmap(change.get("block_file"), 20)
        if pix is not None:
            icon.setPixmap(pix)
        layout.addWidget(icon)

        label = QLabel(str(change.get("label") or ""))
        label.setProperty("updateNoticeRowLabel", True)
        layout.addWidget(label)
        layout.addStretch(1)

        version = QLabel(str(change.get("new") or ""))
        version.setProperty("updateNoticeRowVersion", True)
        layout.addWidget(version)
        return row

    # ---------- 定位与淡入淡出 ----------
    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        parent_rect = parent.rect()
        x = max(12, (parent_rect.width() - self.width()) // 2)
        y = max(24, int(parent_rect.height() * 0.22) - self.height() // 2)
        self.move(x, y)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        super().showEvent(event)
        # 布局激活后再按 sizeHint 撑开并锁定高度、重新居中，避免初始几何停在默认小尺寸。
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())
        self._center_on_parent()
        self._fade(C.UPDATE_NOTICE_FADE_MS, 0.0, 1.0, QEasingCurve.OutCubic)

    def _fade(
        self,
        duration_ms: int,
        start: float,
        end: float,
        easing: QEasingCurve.Type,
    ) -> None:
        if self._fade_anim is not None:
            try:
                self._fade_anim.stop()
            except RuntimeError:
                pass
        if not appearance.animations_enabled:
            # 总开关关闭：透明度瞬时到位，不淡入淡出。
            self._fade_anim = None
            self._opacity_effect.setOpacity(end)
            return
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing)
        self._fade_anim = anim
        anim.start()

    def dismiss(self) -> None:
        if self._closed:
            return
        self._closed = True
        if not appearance.animations_enabled:
            # 总开关关闭：瞬时消失并销毁，不播放淡出。
            self._fade_anim = None
            self._opacity_effect.setOpacity(0.0)
            self.deleteLater()
            return
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(C.UPDATE_NOTICE_FADE_MS)
        anim.setStartValue(self._opacity_effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.deleteLater)
        self._fade_anim = anim
        anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        inner = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(inner, 18, 18)
        painter.fillPath(path, QColor(255, 255, 255, 242))
        pen = painter.pen()
        pen.setColor(QColor(190, 222, 238, 150))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(path, pen)
        painter.end()


class AccordionSection(QFrame):
    """单个可折叠分组：标题横条（标题 + 计数 + 箭头）+ 可展开内容面板。"""

    #: 组内任意条目（含最新两行）点击下载时转发版本号，由下载页统一调度单例任务。
    entryDownloadRequested = Signal(str)

    def __init__(
        self,
        key: str,
        title: str,
        kind: str,
        block_file: str | None = None,
        expanded: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("versionSection")
        # 已安装判定回调：由下载页注入，条目构建时据此设置按钮初始态；默认全部未安装。
        self._install_check = lambda _vid: False
        # 收起态由 set_expanded 把分组自身高度锁回标题横条；展开态放开最小 / 最大高度，
        # 由内部布局按条目内容撑高，剩余垂直空间交给列表末尾弹簧，不被均分拉高。
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._key = key
        self._kind = kind
        self._block_file = block_file
        self._expanded = expanded
        self._anim: QPropertyAnimation | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 标题横条：点击切换展开 / 收起 ----
        header = QFrame()
        header.setObjectName("sectionHeader")
        header.setFixedHeight(_HEADER_HEIGHT)
        header.setCursor(Qt.PointingHandCursor)
        head_row = QHBoxLayout(header)
        head_row.setContentsMargins(14, 0, 14, 0)
        head_row.setSpacing(_HEADER_GAP)

        # 全量分组横条最左侧分类方块；最新版本分组两行自带图标，横条不再重复挂图。
        header_icon: QLabel | None = None
        if kind != "latest" and block_file:
            header_icon = QLabel()
            header_icon.setProperty("sectionHeaderIcon", True)
            header_icon.setFixedSize(C.SECTION_HEADER_ICON_SIZE, C.SECTION_HEADER_ICON_SIZE)
            header_icon.setAlignment(Qt.AlignCenter)
            pix = _scaled_block_pixmap(block_file, C.SECTION_HEADER_ICON_SIZE)
            if pix is not None:
                header_icon.setPixmap(pix)
            head_row.addWidget(header_icon)
        self._header_icon = header_icon

        name_label = QLabel(title)
        name_label.setProperty("sectionTitle", True)
        self._name_label = name_label
        head_row.addWidget(name_label, 1)

        count_label = QLabel("")
        count_label.setProperty("sectionCount", True)
        count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._count_label = count_label
        head_row.addWidget(count_label)

        arrow = QLabel("∧" if expanded else "∨")
        arrow.setProperty("sectionArrow", True)
        arrow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._arrow_label = arrow
        head_row.addWidget(arrow)

        header.mousePressEvent = self._on_header_press
        root.addWidget(header)

        # ---- 展开内容面板 ----
        self.rows: list[VersionRow] = []
        self.entries: list[VersionEntry] = []
        self._pending_entries: list[dict] = []
        self._list_container: QWidget | None = None
        self._list_layout: QVBoxLayout | None = None
        self._placeholder: QLabel | None = None
        self._last_scroll_value = 0
        # 超大列表分批构建状态：待建队列、游标、驱动下一批的定时器。
        self._pending_build: list[dict] = []
        self._batch_cursor = 0
        self._batch_timer: QTimer | None = None

        body = QWidget()
        body.setObjectName("sectionBody")
        body_col = QVBoxLayout(body)
        body_col.setContentsMargins(_BODY_PAD, 0, _BODY_PAD, _BODY_PAD)
        body_col.setSpacing(_ROW_GAP)

        if kind == "latest":
            release_row = VersionRow(block_file or "grass_block.png")
            snapshot_row = VersionRow("diamond_block.png")
            self.rows = [release_row, snapshot_row]
            for row in self.rows:
                row.downloadRequested.connect(self.entryDownloadRequested.emit)
                body_col.addWidget(row)
            self._count_label.setVisible(False)
        else:
            # v1.2.12.0：去掉分组内第二条滚动条，条目直接排在分组内容面板里，
            # 整个页面只由最外层 #page-scroll 一条细滚动条承载垂直滚动。
            list_container = QWidget()
            list_container.setObjectName("section-list-container")
            list_layout = QVBoxLayout(list_container)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.setSpacing(6)

            # 后台静默加载，不显示显眼的居中占位文字，加载完直接填内容
            placeholder = QLabel("")
            placeholder.setProperty("sectionPlaceholder", True)
            placeholder.setAlignment(Qt.AlignCenter)
            self._placeholder = placeholder
            list_layout.addWidget(placeholder)

            body_col.addWidget(list_container)
            self._list_container = list_container
            self._list_layout = list_layout

        self._body = body
        root.addWidget(body)

        self.set_expanded(expanded, animate=False)

    # ---------- 对外状态 ----------
    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self, animate: bool = True) -> None:
        self.set_expanded(not self._expanded, animate=animate)

    def set_count(self, count: int) -> None:
        """横条右侧条目计数；0 条时不显示计数文本。"""
        if self._kind == "latest":
            return
        self._count_label.setText(f"{count} 条" if count > 0 else "")

    def set_list_data(self, entries: list[dict]) -> None:
        """后台数据到达后暂存全量条目；立即后台分批预建，展开时直接动画不卡。"""
        self._pending_entries = list(entries or [])
        self.set_count(len(self._pending_entries))
        if self._kind != "latest":
            # v1.2.12.11：数据一到就分批预建条目，不等用户点展开。
            # 之前点展开才同步建 748 条会卡一下；现在用 QTimer 每 0ms 一批 50 条，
            # 在事件循环里慢慢建完，用户点展开时条目已就位。
            self._clear_entry_widgets()
            self._pending_build = list(self._pending_entries)
            self._batch_cursor = 0
            self._append_next_batch(first_pass=True)

    # ---------- 条目懒构建 / 释放 ----------
    def build_entries(self) -> None:
        """点击展开时调用：后台预建已完成则直接复用，否则同步补完剩余条目，不缺条。"""
        if self._kind == "latest" or self._list_layout is None:
            return
        # 先停止预建定时器，但保留 _pending_build / 游标，用于判断还剩多少没建。
        if self._batch_timer is not None:
            try:
                self._batch_timer.stop()
                self._batch_timer.deleteLater()
            except RuntimeError:
                pass
            self._batch_timer = None
        # 预建进行中：同步补完游标之后的剩余条目，避免动画时缺条。
        if self._pending_build:
            remaining = self._pending_build[self._batch_cursor:]
            if remaining:
                self._append_entries(remaining)
            self._pending_build = []
            self._batch_cursor = len(self._pending_entries)
            self._finalize_layout(first_pass=True)
            return
        # 完全没预建过：同步建全部（兜底）。
        if self._pending_entries and not self.entries:
            self._append_entries(self._pending_entries)
            self._finalize_layout(first_pass=True)
        # 预建已完成、条目已就位：无需重建，直接播展开动画即可即时显示。

    def _append_entries(self, raw_slice: list[dict]) -> None:
        for raw in raw_slice:
            entry = VersionEntry(raw, block_file=self._block_file, parent=self._list_container)
            entry.downloadRequested.connect(self.entryDownloadRequested.emit)
            entry.set_installed(self._install_check(entry._version_id))
            self._list_layout.addWidget(entry)
            self.entries.append(entry)

    def set_install_check(self, callback) -> None:
        """注入已安装判定回调 ``callback(version_id) -> bool``，供新条目初始化按钮态。"""
        self._install_check = callback

    def refresh_installed_states(self) -> None:
        """下载成功 / 本地扫描变化后，刷新组内所有可见条目的已安装按钮态。"""
        for row in self.rows:
            # 最新两行版本号在 set_meta 回填后才有 id；空 id 保持未安装态。
            row.set_installed(bool(row._version_id) and self._install_check(row._version_id))
        for entry in self.entries:
            entry.set_installed(self._install_check(entry._version_id))

    def _append_next_batch(self, first_pass: bool) -> None:
        # 收起态也照常分批预建（旧版在此直接 return，导致展开时同步一次性建数百条卡顿）。
        # 条目在隐藏的 body 内通过 QTimer 逐批建完，用户点展开时条目已就位、动画即时流畅。
        end = min(self._batch_cursor + C.ENTRY_BATCH_SIZE, len(self._pending_build))
        self._append_entries(self._pending_build[self._batch_cursor:end])
        self._batch_cursor = end
        finished = self._batch_cursor >= len(self._pending_build)
        if finished:
            self._pending_build = []
            # 无论第几批收尾，都按首屏路径 finalize：激活布局、清空坐标缓存、播放首屏
            # 交错入场，并注册下一轮事件循环的二次校验。中途批次 first_pass=False 只刷新
            # 几何；若最后一批也用 False 收尾，后建条目会在布局尚未分配几何时被直接判定，
            # y 坐标塌成 0 并被钉到容器顶部。
            self._finalize_layout(first_pass=True)
        else:
            # 分批中途只刷新几何，不跑可见性遍历：否则每批都重复扫描当时全部已建条目，
            # 形成 O(n²) 判定开销并给新条目重复挂入场动画。
            self._list_container.adjustSize()
            self._list_container.updateGeometry()
            self._batch_timer = QTimer(self)
            self._batch_timer.setSingleShot(True)
            self._batch_timer.timeout.connect(lambda: self._append_next_batch(first_pass=False))
            self._batch_timer.start(0)

    def _finalize_layout(self, first_pass: bool) -> None:
        # 末尾弹簧只在全部条目就位后挂一次，避免分批中途弹簧挤压已建条目。
        if self._list_layout is not None and self._batch_cursor >= len(self._pending_build):
            self._list_layout.addStretch(1)
        # 先让布局把条目几何位置计算出来，再刷新可见性缓存。
        self._list_container.adjustSize()
        self._list_container.updateGeometry()
        # 强制 invalidate 布局缓存，否则 addWidget 后 sizeHint() 仍返回旧值
        # （实测 103 条已建完，sizeHint 仍=12），导致动画 target_h 算错、结束后瞬间撑高。
        self._list_layout.invalidate()
        # 分批追加后布局几何已重排：清空上一轮（分批中途）缓存的坐标，避免后建条目
        # 缓存到尚未布局的 y=0，最终被误判进首屏并钉在容器顶部。
        for entry in self.entries:
            entry._cached_top = None
        self._refresh_visibility(first_pass=first_pass)

    def _cancel_batch(self) -> None:
        if self._batch_timer is not None:
            try:
                self._batch_timer.stop()
                self._batch_timer.deleteLater()
            except RuntimeError:
                pass
            self._batch_timer = None
        self._pending_build = []
        self._batch_cursor = 0

    def clear_entries(self) -> None:
        """收起分组时销毁全部条目控件释放内存；再次展开由 build_entries 重建。"""
        self._cancel_batch()
        self._clear_entry_widgets()

    def _clear_entry_widgets(self) -> None:
        if self._list_layout is None:
            return
        for entry in self.entries:
            entry._stop_anim()
            # 先把透明度特效从控件剥离并释放，再摘除父对象，避免退出清理阶段
            # 残留 QGraphicsOpacityEffect / 动画组访问已析构的原生控件。
            entry.setGraphicsEffect(None)
            entry.setParent(None)
        self.entries = []
        # 移除占位与弹簧等所有子控件后重新挂回占位（数据未到 / 列表为空时显示）。
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._placeholder:
                widget.setParent(None)
        if self._placeholder is not None:
            self._list_layout.addWidget(self._placeholder)

    # ---------- 可见性（v1.2.12.0：组内不再独立滚动，条目全部直接就位） ----------
    def _on_scroll_value(self, value: int) -> None:
        # 内层滚动条移除后保留空槽位兼容外部调用；不再参与显现动画。
        self._last_scroll_value = value

    def _refresh_visibility(self, first_pass: bool = False, scroll_delta: int = 0) -> None:
        # v1.2.12.0：分组内第二条滚动条已移除，垂直滚动完全交给外层页面滚动区；
        # 条目元素外形与现状保持不变，仅不再做组内视口滑入 / 隐藏双向显现动画。
        if self._list_container is None or not self.entries:
            return
        for entry in self.entries:
            entry.place_directly()

    # ---------- 展开 / 收起高度动画 ----------
    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        # 总开关关闭时强制走瞬时分支，不播放手风琴高度动画。
        if not appearance.animations_enabled:
            animate = False
        self._expanded = expanded
        self._arrow_label.setText("∧" if expanded else "∨")
        self.setProperty("sectionOpen", expanded)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        if self._anim is not None and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

        # 先放开最小高度（收起态 setFixedHeight 锁了 min=max=36），但暂不放开 maxH——
        # 动画期间由 self.maximumHeight 自己控制高度，否则下面一行 setMaximumHeight(16M)
        # 会让父 layout 在动画开始前瞬间把分组撑到全高，下面的分组被猛推。
        self.setMinimumHeight(0)

        if not animate:
            self._body.setVisible(expanded)
            self._body.setMinimumHeight(0)
            self._body.setMaximumHeight(16_777_215 if expanded else 0)
            if expanded:
                self.setMaximumHeight(16_777_215)
                self.build_entries()
            else:
                # 收起不销毁已建条目、也不打断后台预建，下次展开即时显示、不卡顿。
                self.setFixedHeight(_HEADER_HEIGHT)
            self._body.updateGeometry()
            self.updateGeometry()
            return

        self._body.setVisible(True)
        # 动画期间放开 body 高度上限，由 self.maximumHeight 统一裁剪总高度。
        self._body.setMaximumHeight(16_777_215)
        # 展开前同步建完全部条目（v1.2.12.8 起不再分批）。
        if expanded:
            self.build_entries()
        # 手动累加目标高度——Qt 的 body.sizeHint() 在 addWidget 后不可靠（实测 103 条
        # 已建完，sizeHint 仍返回 12），直接遍历可见条目累加 sizeHint + spacing。
        if expanded:
            items = self.rows if self._kind == "latest" else self.entries
            n = len(items)
            if n:
                sum_h = sum(it.sizeHint().height() for it in items)
                body_full = sum_h + _ROW_GAP * (n - 1) + _BODY_PAD
            else:
                body_full = _BODY_PAD
        else:
            body_full = 0
        start_h = self.height()
        target_h = (_HEADER_HEIGHT + body_full) if expanded else _HEADER_HEIGHT
        self._anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._anim.setDuration(_ANIM_MS)
        self._anim.setStartValue(start_h)
        self._anim.setEndValue(target_h)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        if expanded:
            self._anim.finished.connect(self._release_body_height)
        else:
            self._anim.finished.connect(self._hide_body_on_collapse)
        self._anim.start()

    def _release_body_height(self) -> None:
        """展开动画结束后放开分组最大高度，避免后续内容被限高裁剪。"""
        if self._expanded:
            self.setMaximumHeight(16_777_215)
            self.updateGeometry()

    def _hide_body_on_collapse(self) -> None:
        if not self._expanded:
            self._body.setVisible(False)
            # 保留已建条目、不打断后台预建，再次展开即时显示、不卡顿。
            self.setFixedHeight(_HEADER_HEIGHT)
            self._body.updateGeometry()
            self.updateGeometry()

    def _on_header_press(self, _event) -> None:
        self.toggle(animate=True)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # v1.2.12.6：展开后整块不再切"置顶档"更白的 TOP_GLASS（alpha 186 叠磨砂后接近不透明白板，
        # 真机实拍展开半屏被白边糊死、壁纸卡通人物透不出来）；展开 / 收起统一用普通半透磨砂色，
        # 整块都能透出底下壁纸。
        top, mid, bottom, border = (
            C.COLOR_VERSION_GLASS_TOP_RGBA,
            C.COLOR_VERSION_GLASS_MID_RGBA,
            C.COLOR_VERSION_GLASS_BOTTOM_RGBA,
            C.COLOR_VERSION_BORDER_RGBA,
        )
        paint_frosted_panel(painter, self, _SECTION_RADIUS, top, mid, bottom, border)
        painter.end()


class DownloadPage(QWidget):
    """下载页：分类标签栏 + 可滚动分组列表；后台拉取最新两行与四个全量分组回填。"""

    #: 某版本下载完成并加入本地后对外通知，主窗口据此刷新个人页版本选择列表。
    versionInstalled = Signal(str)
    #: 内容（mod/光影/资源/数据包）或整合包安装完成，带目标版本别名，主窗口据此即时刷新。
    contentInstalled = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("download-page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # v1.3.4.0：分类内容栈。原版游戏=下面的版本列表/详情栈，其余 5 个分类=
        # 各自的内容搜索视图；分类标签由 _build_tabs 统一构建并在最后加入 outer。
        self._category_stack = QStackedWidget(self)

        # v1.2.12.0：列表态 ↔ 版本详情态双层栈（原版游戏分类内部），默认显示版本列表，
        # 点条目下载按钮进入详情页。
        self._stack = QStackedWidget(self)

        list_view = QWidget()
        list_view.setObjectName("download-list-view")
        list_root = QVBoxLayout(list_view)
        list_root.setContentsMargins(0, 0, 0, 0)
        list_root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("page-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # v1.2.12.11：彻底隐藏垂直滚动条。QSS width 和 setFixedWidth(2) 在 Windows 上
        # 都压不住原生滚动条宽度（实测仍渲染 ~17px 白色轨道），用户截图可见右侧白边。
        # AlwaysOff 完全不画滚动条控件，内容占满全宽，鼠标滚轮仍可正常滚动。
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)

        container = QWidget()
        container.setObjectName("download-container")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setAutoFillBackground(False)
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        section_list = QVBoxLayout()
        section_list.setSpacing(8)
        self.cards: list[AccordionSection] = []
        self._section_by_key: dict[str, AccordionSection] = {}

        # v1.3.1.7：仅四个全量分组（正式版 / 预览版 / 远古版 / 愚人节版），数据到达即
        # 后台分批预建，点展开即时显示；不再创建重复的「最新版本」分组。
        self._snapshot_card = None
        for key, name, kind, block_file, default_open in SECTIONS:
            section = AccordionSection(
                key, name, kind, block_file, expanded=default_open
            )
            section_list.addWidget(section)
            self.cards.append(section)
            self._section_by_key[key] = section
            if key == "snapshot":
                self._snapshot_card = section
        # 末尾弹簧吸收剩余垂直空间：分组按自身 sizeHint 排列在顶部，不被均分拉高。
        section_list.addStretch(1)
        root.addLayout(section_list, 1)

        scroll.setWidget(container)
        list_root.addWidget(scroll)

        self._detail_view = VersionDetailView(self)
        self._detail_view.backRequested.connect(self._back_to_list)
        self._detail_view.startDownloadRequested.connect(self._start_download_from_detail)

        self._stack.addWidget(list_view)
        self._stack.addWidget(self._detail_view)
        self._stack.setCurrentIndex(0)

        # 原版游戏分类（category_stack index 0）。
        self._category_stack.addWidget(self._stack)

        # 其余 5 个分类：内容搜索视图（搜索框 + 搜索按钮 + 带图结果），顺序与 tabs 对齐。
        self._search_views: dict[str, ContentSearchView] = {}
        for kind, hint in (
            ("mod", "搜索 mod（模组）…"),
            ("modpack", "搜索整合包…"),
            ("shader", "搜索光影包…"),
            ("resourcepack", "搜索资源包…"),
            ("datapack", "搜索数据包…"),
        ):
            view = ContentSearchView(kind, hint, self)
            view.contentChanged.connect(self.contentInstalled)
            self._category_stack.addWidget(view)
            self._search_views[kind] = view
        self._category_stack.setCurrentIndex(0)

        # 全局分类标签：置于内容栈之上，不随版本列表滚动；_build_tabs 内部默认选中
        # 第一项并切换 category_stack。
        self._build_tabs(outer)
        outer.addWidget(self._category_stack, 1)

        # ---- v1.2.12.0 本地已安装版本集合 + 单例下载面板 + 单任务下载 worker ----
        game_dirs.ensure_base_dirs()
        self._installed: set[str] = set(game_dirs.scan_installed_versions())
        self._download_worker: VersionDownloadWorker | None = None
        # 单例浮层：作为本页直接子控件、不参与父布局；整个页面生命周期只创建这一次。
        self._panel = DownloadPanel(self)
        self._panel.cancelRequested.connect(self._cancel_current_download)
        for section in self.cards:
            section.set_install_check(self._is_installed)
            section.entryDownloadRequested.connect(self._open_detail)

        # 清单缓存优先（v1.2.10.0）：本地有缓存直接渲染、不重新联网拉全量；随后起后台
        # 轻量检查线程扫描国内镜像 / 官方最新版号。首次无缓存才由全量线程联网拉取并落盘。
        self._current_manifest: dict | None = None
        self._meta_worker: VersionMetaWorker | None = None
        self._check_worker: VersionCheckWorker | None = None
        self._notice_popup: UpdateNoticePopup | None = None

        cached = load_cached_manifest()
        if cached is not None:
            self._apply_meta(cached)
            self._start_check_worker()
        else:
            self._meta_worker = VersionMetaWorker(self)
            self._meta_worker.succeeded.connect(self._on_meta_loaded)
            self._meta_worker.failed.connect(lambda _msg: None)
            self._meta_worker.start()

    # ---------- 元数据回填 ----------
    def _apply_meta(self, manifest: dict) -> None:
        """按本次清单刷新四个全量分组列表；缺失分类保留加载占位。"""
        self._current_manifest = manifest

        for key in LIST_SECTION_KEYS:
            section = self._section_by_key.get(key)
            if section is not None:
                section.set_list_data(manifest.get(key) or [])

        self.refresh_all_installed_states()

    # ---------- 清单缓存加载与后台版本检查 ----------
    def _on_meta_loaded(self, payload: dict) -> None:
        """首次无缓存全量拉取完成：渲染清单、落盘缓存；本次不重复起检查线程。"""
        manifest = payload.get("manifest") or {}
        source = payload.get("source") or "network"
        self._apply_meta(manifest)
        if source == "network":
            save_cached_manifest(manifest)

    def _start_check_worker(self) -> None:
        """启动后台轻量检查线程（已有缓存渲染完成后）；重复进入不重复启动。"""
        if self._check_worker is not None and self._check_worker.isRunning():
            return
        self._check_worker = VersionCheckWorker(self)
        self._check_worker.succeeded.connect(self._on_check_succeeded)
        self._check_worker.failed.connect(lambda _msg: None)
        self._check_worker.start()

    def _on_check_succeeded(self, new_manifest: dict) -> None:
        """后台比对最新正式 / 预览版号：列出一个或两个变化项，弹淡入淡出提示窗。

        新清单即时应用到内存并重绘分组（保留各分组展开态），同时覆盖本地缓存，
        新版本无需重启即出现在列表。
        """
        current = self._current_manifest or {}
        changes: list[dict] = []

        cur_release = str((current.get("latest_release") or {}).get("id") or "")
        new_release = str((new_manifest.get("latest_release") or {}).get("id") or "")
        if new_release and new_release != cur_release:
            changes.append({
                "label": "最新正式版",
                "block_file": "grass_block.png",
                "old": cur_release,
                "new": new_release,
                "time": str((new_manifest.get("latest_release") or {}).get("time") or ""),
            })

        cur_snapshot = str((current.get("latest_snapshot") or {}).get("id") or "")
        new_snapshot = str((new_manifest.get("latest_snapshot") or {}).get("id") or "")
        if new_snapshot and new_snapshot != cur_snapshot:
            changes.append({
                "label": "最新预览版",
                "block_file": "diamond_block.png",
                "old": cur_snapshot,
                "new": new_snapshot,
                "time": str((new_manifest.get("latest_snapshot") or {}).get("time") or ""),
            })

        # 即时刷新：把新清单应用到内存并重绘分组（set_list_data 保留各分组当前展开态），
        # 新版本无需重启即出现在列表；同时覆盖本地缓存。旧实现只存缓存、不重绘，导致
        # 必须重启才能看到新版本，与提示语「已加入最新版本」自相矛盾。
        self._apply_meta(new_manifest)
        save_cached_manifest(new_manifest)
        if changes:
            self._show_update_notice(changes)

    def _show_update_notice(self, changes: list[dict]) -> None:
        """同一时刻只保留一个提示窗；旧窗先淡出，再弹出新的淡入提示。"""
        if self._notice_popup is not None:
            self._notice_popup.dismiss()
        popup = UpdateNoticePopup(self, changes)
        self._notice_popup = popup
        popup.show()

    # ---------- v1.2.12.0 下载调度（详情页入口 + 单任务单例 + 单例面板 + 中途取消） ----------
    def _is_installed(self, version_id: str) -> bool:
        return version_id in self._installed

    def refresh_all_installed_states(self) -> None:
        """刷新全部分组可见条目的已安装按钮态；收起分组的条目重建时由 install_check 兜底。"""
        for section in self.cards:
            section.refresh_installed_states()

    def _open_detail(self, version_id: str) -> None:
        """条目下载按钮先进版本详情页（选加载器 / 自定义别名后再开始下载）。

        已安装版本同样允许进入详情重复下载（新别名另存一份隔离目录），不再拦截。
        """
        vid = str(version_id or "").strip()
        if not vid:
            return
        # 已有下载任务在跑时不打断当前任务，忽略后续详情入口点击。
        if self._download_worker is not None and self._download_worker.isRunning():
            return
        self._detail_view.open_for(vid)
        self._stack.setCurrentIndex(1)

    def _back_to_list(self) -> None:
        """详情页返回箭头：切回版本列表态。"""
        self._stack.setCurrentIndex(0)

    def _start_download_from_detail(self, mc_version: str, alias: str,
                                    loader: str, loader_version: str) -> None:
        """详情页「开始下载」：校验别名非空且不与现有目录冲突后，启动单例 worker。

        v1.3.2.0：别名目录已存在时不再静默自动改名，弹中文提示框要求用户立刻重新命名，
        并聚焦别名输入框；改成不冲突的新名字后才放行下载。同一 MC 版本可重复下载，
        只是必须以新别名另存一份隔离目录。
        """
        mc = str(mc_version or "").strip()
        if not mc:
            return
        # 单任务单例：已有下载任务在跑时忽略后续点击，面板复用、不重复弹出第二个。
        if self._download_worker is not None and self._download_worker.isRunning():
            return

        raw_alias = str(alias or "").strip()
        if not raw_alias:
            QMessageBox.warning(self, C.ALIAS_EMPTY_TITLE, C.ALIAS_EMPTY_MESSAGE)
            self._detail_view.focus_alias_input()
            return

        if game_dirs.alias_exists(raw_alias):
            safe_name = game_dirs.sanitize_version_id(raw_alias)
            QMessageBox.warning(
                self,
                C.ALIAS_DUPLICATE_TITLE,
                C.ALIAS_DUPLICATE_MESSAGE.format(alias=safe_name),
            )
            self._detail_view.focus_alias_input()
            return

        self._panel.start(raw_alias)
        worker = VersionDownloadWorker(
            mc, raw_alias, loader=loader, loader_version=loader_version, parent=self
        )
        worker.progress.connect(self._panel.update_progress)
        worker.stepChanged.connect(self._panel.set_step)
        worker.succeeded.connect(self._on_download_succeeded)
        worker.failed.connect(self._on_download_failed)
        worker.cancelled.connect(self._on_download_cancelled)
        self._download_worker = worker
        worker.start()

    def _cancel_current_download(self) -> None:
        """面板底部大叉：请求中断当前下载任务；worker 收尾后经 cancelled 信号复位面板。"""
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.requestInterruption()

    def _on_download_succeeded(self, payload: dict) -> None:
        payload = payload or {}
        mc_version = str(payload.get("mc_version") or "").strip()
        alias = str(payload.get("alias") or "").strip()
        if mc_version:
            self._installed.add(mc_version)
        self._panel.mark_success(alias or mc_version)
        self.refresh_all_installed_states()
        # 个人页按别名（隔离目录名）选中，多个同 MC 版本也能唯一定位，故优先发 alias。
        self.versionInstalled.emit(alias or mc_version)
        self._download_worker = None
        # 下载成功后回到列表态，让用户看到已安装标识刷新。
        self._back_to_list()

    def _on_download_failed(self, reason: str) -> None:
        self._panel.mark_failed(reason)
        self._download_worker = None

    def _on_download_cancelled(self) -> None:
        """用户中途取消：面板复位收起，不弹失败提示；半成品目录已由 worker 清理。"""
        self._panel.mark_cancelled()
        self._download_worker = None
        self._back_to_list()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        super().resizeEvent(event)
        self._panel.reposition()

    def shutdown(self) -> None:
        """中断并等待清单全量线程、后台检查线程、下载线程与详情探测线程收尾；不经过
        closeEvent 的脚本 / 测试退出前也应调用，避免进程析构顺序下线程结束后 emit 信号
        访问已销毁的主线程控件。"""
        for worker in (self._meta_worker, self._check_worker, self._download_worker):
            if worker is None:
                continue
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    # 等待时长覆盖单次 HTTP 超时（清单 6s / 下载 30s），保证阻塞在 urlopen
                    # 的线程能自行收尾，避免 QThread 未结束即被析构触发原生层 0xC0000409。
                    worker.wait(7000)
            except RuntimeError:
                pass
        if self._detail_view is not None:
            self._detail_view.shutdown()
        if self._panel is not None:
            self._panel.shutdown()
        for view in getattr(self, "_search_views", {}).values():
            view.shutdown()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self.shutdown()
        super().closeEvent(event)

    # ---------- 顶部分类标签 ----------
    def _build_tabs(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(10)
        # 只改上下间距、保留左右现状：标签整体下移，且与下方内容栈（搜索框 / 分组）拉开距离。
        side_margins = row.contentsMargins()
        row.setContentsMargins(side_margins.left(), _TAB_TOP_MARGIN,
                               side_margins.right(), _TAB_BOTTOM_MARGIN)
        self._tabs: list[QPushButton] = []
        for name in CATEGORY_TABS:
            btn = QPushButton(name)
            btn.setProperty("categoryTab", True)
            btn.setFixedHeight(_TAB_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, b=btn: self._select_tab(b))
            row.addWidget(btn, 1)
            self._tabs.append(btn)
        # 默认选中第一项「原版游戏」。
        self._select_tab(self._tabs[0])
        root.addLayout(row)

    def _select_tab(self, active: QPushButton) -> None:
        for index, btn in enumerate(self._tabs):
            btn.setProperty("categoryActive", btn is active)
            # 属性选择器状态切换后必须刷新样式，否则 QSS 不会重算。
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
            if btn is active:
                self._category_stack.setCurrentIndex(index)
        view = self._current_search_view()
        if view is not None:
            # 首次进入该分类自动拉一批热门内容；已有结果时不重复搜索。
            view.trigger_default_search()

    def _current_search_view(self):
        index = self._category_stack.currentIndex()
        if index <= 0:
            return None
        kinds = ("mod", "modpack", "shader", "resourcepack", "datapack")
        return self._search_views.get(kinds[index - 1])
