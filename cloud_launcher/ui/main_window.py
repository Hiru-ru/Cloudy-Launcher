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

"""主窗口：无边框、自定义标题栏、左侧导航 + 页面栈。

v1.2.5.1：按 PCL 式参考骨架接入五导航页面栈——启动 / 下载 / 设置 / 打包 / 关于。
归属口径（用户最终确认方案 A）：「启动」导航显示旧 ``ProfilePage`` 个人页（3D 预览、
昵称、离线 / 正版登录、游玩统计、开始游戏），作为默认可见页；「下载」导航显示
``DownloadPage`` 参考图骨架（六分类标签 + 五张版本卡片）；设置 / 打包 / 关于为通用
占位页。16ms 指针轮询定时器仅在当前可见为个人页（启动导航）时才转发给 GL 预览，
静默恢复成功回调仍调 ``profile_page.refresh()``。
"""
import os
import time

from PySide6.QtCore import Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import (
    QColor,
    QCursor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import brand
from .. import constants as C
from ..account_session import AccountSession
from ..account_store import AccountStore
from ..config_store import ConfigStore
from ..music_player import (
    MusicPlayer,
    current_music_path,
    delete_music,
    import_music,
)
from ..resources import resource_path
from ..wallpaper import load_selected_wallpaper
from .account_restore_worker import AccountRestoreWorker
from .about_page import AboutPage
from .appearance import appearance
from .background_layer import BackgroundLayer
from .frosted_backdrop import backdrop
from .download_page import DownloadPage
from .nav_sidebar import NavSidebar
from .package_page import PackagePage
from .placeholder_page import PlaceholderPage
from .profile_page import ProfilePage
from .settings_page import SettingsPage
from .spring_button import SpringPushButton
from .version_settings_page import VersionSettingsPage
from .local_modpack_dialog import DragDropOverlay, LocalModpackNameDialog
from .modpack_install_worker import (
    LocalModpackInstallWorker,
    LocalModpackPlanWorker,
)
from .task_progress_dialog import STATE_DONE, TaskProgressDialog
from ..modpack_install import PHASE_LABELS
from .. import modpack_format


class TitleCircleButton(SpringPushButton):
    """标题栏最小化 / 关闭圆形按钮。

    v1.2.4.6：与导航 / 分段 / 主按钮同属仅有的六个半透明玻璃功能键——白圆 + 细亮边 + 深色
    符号，透明度下调到浅色玻璃档透出标题栏后方背景，不再是不透明白实圆；关闭 hover 叠一层
    浅红反馈；继承 ``SpringPushButton``，左键按住拖动几何真实跟随、不被边界挡住，松开弹簧
    回弹复位。外形由 paintEvent 自绘，不走 QSS 背景，避免透明标题栏上出现直角方块。
    """

    _DIAMETER = 28
    # 28px 小圆按钮拉扯幅度收小，避免被拽出成组浅玻璃框。
    PULL_MAX_PX = 6.0
    PULL_DAMPING = 0.22

    def __init__(self, kind: str, parent=None) -> None:
        super().__init__("", parent)
        self._kind = kind  # "min" | "close"
        self._hover = False
        self.setFixedSize(self._DIAMETER, self._DIAMETER)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._spring.apply_transform(painter)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        radius = 11.5

        # 1) 一层很淡的底部投影（扁平 iOS 胶囊语言，不再叠两层厚重浮层阴影）。
        shadow = QPainterPath()
        shadow.addEllipse(QRectF(cx - radius, cy - radius + 1.4, radius * 2, radius * 2))
        painter.fillPath(shadow, QColor(70, 95, 115, 8))

        # 2) 白色玻璃圆主体；关闭按钮 hover 时叠一层浅红反馈底。
        # v1.2.4.6：白圆透明度下调到与其余五颗按钮同一档浅色玻璃，透出标题栏后方背景，
        # 不再是不透明白实圆；绿色 / 较暗壁纸顶部再收一档，避免在成组浅框之上压成亮白圆。
        body = QPainterPath()
        body.addEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
        if self._kind == "close" and self._hover:
            painter.fillPath(body, QColor(232, 96, 86, 30))
        else:
            painter.fillPath(body, QColor(255, 255, 255, 54))

        pen = QPen(QColor(255, 255, 255, 110))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(body, pen)

        # 3) 符号：最小化为横线，关闭为 ✕；关闭 hover 转红色。
        symbol_color = QColor(0xD2, 0x56, 0x4B) if (self._kind == "close" and self._hover) \
            else QColor(0x2B, 0x47, 0x59)
        symbol_pen = QPen(symbol_color)
        symbol_pen.setWidthF(2.0)
        symbol_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(symbol_pen)

        if self._kind == "min":
            painter.drawLine(9.5, cy, 18.5, cy)
        else:
            painter.drawLine(10.5, 10.5, 17.5, 17.5)
            painter.drawLine(17.5, 10.5, 10.5, 17.5)

        painter.end()


class TitleButtonGroup(QFrame):
    """标题栏最小化 / 关闭按钮的成组大圆角浅玻璃框（两个圆形按钮收进同一个框内）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleButtonGroup")
        self.setFixedHeight(34)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        self.min_btn = TitleCircleButton("min")
        self.close_btn = TitleCircleButton("close")
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 17.0, 17.0)
        painter.fillPath(path, QColor(255, 255, 255, 64))
        pen = QPen(QColor(255, 255, 255, 120))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.strokePath(path, pen)
        painter.end()


class MainWindow(QWidget):
    """应用主窗口。"""

    def __init__(self, config: ConfigStore):
        super().__init__()
        self.config = config
        # 正版会话存内存；刷新令牌与公开身份由独立账号文件持久化，启动时后台静默续期
        self.session = AccountSession()
        self.account_store = AccountStore()
        self._restore_worker: AccountRestoreWorker | None = None
        self._drag_pos: QPoint | None = None

        self.setWindowTitle(brand.window_title(config))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        # 全局指针跟随：主窗口也开启鼠标追踪，指针移到窗口任意位置都转发给角色预览
        self.setMouseTracking(True)
        self.resize(C.WINDOW_WIDTH, C.WINDOW_HEIGHT)
        self.setMinimumSize(C.WINDOW_MIN_WIDTH, C.WINDOW_MIN_HEIGHT)

        icon_path = resource_path("app_icon.ico")
        self.setWindowIcon(QIcon(icon_path))

        # v1.3.9.0：从 config 恢复外观状态（玻璃模式 + 七色染色）。
        appearance.set_glass_mode(config.get("glass_mode"))
        appearance.set_bg_tint(config.get("bg_tint"))
        appearance.set_nav_tint(config.get("nav_tint"))
        # v1.3.9.2：苹果动画总开关。
        appearance.set_animations_enabled(
            config.get("animations_enabled", C.ANIMATIONS_ENABLED_DEFAULT)
        )

        # 最底层背景层：按 config 选择加载壁纸（缺失 / 损坏静默回退默认渐变）。
        self.background = BackgroundLayer(self)
        wallpaper_pixmap, wallpaper_brightness = load_selected_wallpaper(config)
        self.background.set_wallpaper(wallpaper_pixmap, wallpaper_brightness)

        # 背景音乐播放器（单曲无限循环）；先建实例，UI 构建完再按 config 加载。
        self.music_player = MusicPlayer()

        self._build_ui()
        self._restore_window_state()
        self.music_player.load_from_config(config)

        # 全局指针跟随：定时轮询真实光标位置（鼠标事件不会从子控件冒泡到主窗口），
        # 指针落在窗口任意位置都把归一化坐标转发给角色预览；移出窗口则回正。
        # 16ms 与渲染帧同频采样，避免 33ms 离散采样造成的跟随阶梯卡顿。
        self._pointer_timer = QTimer(self)
        self._pointer_timer.setInterval(16)
        self._pointer_timer.timeout.connect(self._poll_global_pointer)
        self._pointer_timer.start()

        # 有本地账号存档时，后台静默续期恢复正版；无存档保持离线，不发起网络请求
        self._start_silent_restore()

    # ---------- 启动静默恢复正版会话 ----------
    def _start_silent_restore(self) -> None:
        saved = self.account_store.load()
        if not saved:
            return
        self._restore_worker = AccountRestoreWorker(saved["refresh_token"], parent=self)
        self._restore_worker.succeeded.connect(self._on_restore_succeeded)
        self._restore_worker.failed.connect(self._on_restore_failed)
        self._restore_worker.start()

    def _on_restore_succeeded(self, profile: dict) -> None:
        """静默续期成功：切正版内存会话，回写轮换后的新刷新令牌，刷新个人页。"""
        self.session.set_microsoft(profile)
        self.account_store.save(profile)
        self.profile_page.refresh()

    def _on_restore_failed(self, message: str) -> None:
        """静默续期失败：清除本地失效凭据，保持离线界面，不弹窗打扰用户。"""
        self.account_store.clear()

    def _on_version_installed(self, alias: str) -> None:
        """下载页安装完成一个版本后，刷新个人页列表并自动选中刚装好的别名。"""
        self.profile_page.refresh_version_list(preferred=str(alias or ""))

    def _on_content_installed(self, alias: str) -> None:
        """内容/整合包安装完成：立即刷新版本列表与版本设置页计数，免重启。"""
        self.profile_page.refresh_version_list(preferred=str(alias or ""))
        self.version_settings_page.refresh_for_alias(str(alias or ""))

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.setObjectName("root")
        # 根窗口背景渐变与圆角统一写进 app 全局样式表（QWidget#root）；
        # 这里不再调用本地 setStyleSheet——祖先本地表会切断全局表中后代控件的
        # 属性选择器规则（如 QPushButton[primaryButton="true"]），导致主按钮圆角/渐变失效。

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        self._build_title_bar(root)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.sidebar = NavSidebar()
        self.sidebar.navigateRequested.connect(self._switch_page)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()

        # v1.2.5.1：五导航页面栈。「启动」= 个人页 ProfilePage（默认可见）；
        # 「下载」= DownloadPage 参考图骨架（六分类标签 + 五版本卡片）；
        # 设置 / 打包 / 关于为通用占位页，本轮不接真实功能。
        self.profile_page = ProfilePage(self.config, self.session, self.account_store)
        self.download_page = DownloadPage()
        # 下载页某版本安装完成后，刷新个人页两行滚轮版本列表（新增选项 / 选中态）。
        self.download_page.versionInstalled.connect(self._on_version_installed)
        self.settings_page = SettingsPage(self.config, self)
        self.package_page = PackagePage(self)
        # v1.3.3.0：关于页改为真实页面，展示 LOGO、英文全名与版本号。
        self.about_page = AboutPage(self.config)

        self._pages: dict[str, QWidget] = {
            "launch": self.profile_page,
            "download": self.download_page,
            "settings": self.settings_page,
            "package": self.package_page,
            "about": self.about_page,
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        # v1.3.5.0：版本设置页是「启动」个人页的下级页面（不进侧栏五项），
        # 由个人页版本横条的三点按钮进入，左上返回按钮回到个人页。
        self.version_settings_page = VersionSettingsPage(self.config)
        self.version_settings_page.closed.connect(self._close_version_settings)
        self.profile_page.versionSettingsRequested.connect(self._open_version_settings)
        self.download_page.contentInstalled.connect(self._on_content_installed)
        self.stack.addWidget(self.version_settings_page)

        body.addWidget(self.stack, 1)

        # 默认进入「启动」个人页。
        self._switch_page("launch")

        root.addLayout(body, 1)

        # 背景层压到最底层并铺满整窗；上层布局控件自然叠在它之上。
        self.background.resize(self.size())
        self.background.lower()
        # 构建与主窗口同尺寸的清晰 cover 缓存，供卡片 / 侧栏截取自身后方小块做局部磨砂。
        self._refresh_backdrop()

        # 全局拖拽导入：主窗口接受文件拖入；遮罩与命名浮层作为顶层子控件手动定位。
        self.setAcceptDrops(True)
        self._drag_overlay = DragDropOverlay(self)
        self._local_name_dialog = LocalModpackNameDialog(self)
        self._local_name_dialog.confirmed.connect(self._on_local_name_confirmed)
        self._local_name_dialog.cancelled.connect(self._on_local_name_cancelled)
        self._plan_worker: LocalModpackPlanWorker | None = None
        self._local_worker: LocalModpackInstallWorker | None = None
        self._local_progress_dialog: TaskProgressDialog | None = None
        self._pending_pack_path = ""

    def _refresh_backdrop(self) -> None:
        """重建共享清晰壁纸缓存，并通知各玻璃片重绘局部磨砂块。"""
        backdrop.render_window(self.width(), self.height())
        for panel in self.findChildren(QFrame):
            panel.update()

    # ---------- v1.3.9.0 个性化 host 方法 ----------
    def set_glass_mode(self, mode: str) -> None:
        appearance.set_glass_mode(mode)
        self.config.set("glass_mode", appearance.glass_mode)
        self.config.save()
        for panel in self.findChildren(QFrame):
            panel.update()

    def set_bg_tint(self, key: str) -> None:
        appearance.set_bg_tint(key)
        self.config.set("bg_tint", appearance.bg_tint)
        self.config.save()
        self.background.update()
        # 普通档下染色叠在各面板内，需主动刷新所有面板与玻璃预览图。
        for panel in self.findChildren(QFrame):
            panel.update()
        self.settings_page.refresh_previews()

    def set_nav_tint(self, key: str) -> None:
        appearance.set_nav_tint(key)
        self.config.set("nav_tint", appearance.nav_tint)
        self.config.save()
        self.sidebar.update()

    def set_wallpaper_selection(self, key: str) -> None:
        self.config.set("wallpaper_file", key)
        self.config.save()
        pix, bright = load_selected_wallpaper(self.config)
        self.background.set_wallpaper(pix, bright)
        self._refresh_backdrop()
        self.settings_page.refresh_wallpaper()

    def import_wallpaper_file(self, src_path: str) -> str | None:
        from ..wallpaper import import_wallpaper

        try:
            filename = import_wallpaper(src_path)
        except ValueError:
            return None
        # 导入后自动选中新壁纸。
        self.config.set("wallpaper_file", filename)
        self.config.save()
        pix, bright = load_selected_wallpaper(self.config)
        self.background.set_wallpaper(pix, bright)
        self._refresh_backdrop()
        return filename

    def set_logo_visible(self, visible: bool) -> None:
        """Logo 开关：关闭即整个隐藏 Logo。"""
        self.config.set("logo_visible", bool(visible))
        self.config.save()
        self._apply_brand()

    def set_name_visible(self, visible: bool) -> None:
        """名字开关：关闭即隐藏名字。"""
        self.config.set("name_visible", bool(visible))
        self.config.save()
        self._apply_brand()

    def import_logo_file(self, src_path: str) -> bool:
        try:
            filename = brand.import_custom_logo(src_path)
        except ValueError:
            return False
        self.config.set("custom_logo", filename)
        self.config.save()
        self._apply_brand()
        self.settings_page.refresh_brand()
        return True

    def set_custom_name(self, text: str) -> None:
        self.config.set("custom_name", text.strip())
        self.config.save()
        self._apply_brand()

    def _apply_brand(self) -> None:
        self.sidebar.refresh_brand(self.config)
        self.about_page.refresh_brand(self.config)
        self.setWindowTitle(brand.window_title(self.config))

    def _pump_events(self, seconds: float) -> None:
        """驱动事件循环指定时长，让 QtMultimedia 后端异步完成加载 / 释放文件句柄。"""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.02)

    def add_music_file(self, src_path: str) -> None:
        # 先释放对旧文件的占用并等待后端真正关闭句柄，避免 Windows 下旧文件被锁删不掉。
        self.music_player.release_source()
        self._pump_events(0.4)
        # 记录导入前的原始文件名（磁盘上统一改存 bgm.<ext>，原始名用于歌名展示）。
        original_name = os.path.basename(src_path)
        try:
            path = import_music(src_path)
        except ValueError:
            return
        self.config.set("music_file", original_name)
        self.config.save()
        self.music_player.refresh_source()
        self.settings_page.refresh_music()

    def remove_music_file(self) -> None:
        # 先停止并清空 source 释放文件句柄，再轮询删除，直到文件真正消失（Windows 下
        # 句柄释放是异步的，立刻 os.remove 会静默失败）。
        self.music_player.release_source()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            QApplication.processEvents()
            delete_music()
            if not current_music_path():
                break
            time.sleep(0.05)
        self.config.set("music_file", "")
        self.config.save()
        self.music_player.refresh_source()
        self.settings_page.refresh_music()

    def set_music_enabled(self, value: bool) -> None:
        self.config.set("music_enabled", bool(value))
        self.config.save()
        self.music_player.set_enabled(bool(value))
        self.settings_page.refresh_music()

    def set_music_autoplay(self, value: bool) -> None:
        self.config.set("music_autoplay", bool(value))
        self.config.save()

    def toggle_music_play(self) -> None:
        if self.music_player.is_playing():
            self.music_player.pause()
        else:
            self.music_player.play()
        self.settings_page.refresh_music()

    def is_music_playing(self) -> bool:
        return self.music_player.is_playing()

    # ---------- v1.3.9.2 动画总开关 ----------
    def set_animations_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        appearance.set_animations_enabled(enabled)
        self.config.set("animations_enabled", enabled)
        self.config.save()
        self.settings_page.refresh_animations()

    def _build_title_bar(self, root: QVBoxLayout) -> None:
        bar = QWidget()
        bar.setObjectName("title-bar")
        bar.setFixedHeight(42)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10, 0, 10, 0)
        bar_layout.setSpacing(10)

        # 标题栏不再显示 LOGO 与应用名称，只保留右侧最小化 / 关闭按钮；
        # 左侧空白区域仍可按住拖动窗口。
        bar_layout.addStretch(1)

        # 最小化 / 关闭两个 iOS 白色圆形凸起按钮，统一收进同一个大圆角浅玻璃框内。
        self._title_group = TitleButtonGroup()
        self._title_group.min_btn.clicked.connect(self.showMinimized)
        self._title_group.close_btn.clicked.connect(self.close)
        bar_layout.addWidget(self._title_group)

        root.addWidget(bar)
        self._title_bar = bar

    # ---------- 页面切换 ----------
    def _switch_page(self, page_key: str) -> None:
        page = self._pages.get(page_key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        # 五个导航 key 全部同步侧栏选中态（「启动」对应的就是个人页实例）。
        if page_key in ("launch", "download", "settings", "package", "about"):
            # 从铺满整窗的版本设置页返回普通页面时，恢复主侧栏显示。
            self.sidebar.show()
            self.sidebar.set_active(page_key)
        if page_key == "package":
            # 进入打包页时重扫已安装版本，保证下拉与本地实例一致。
            self.package_page.refresh_versions()

    def _close_version_settings(self) -> None:
        """版本设置页左上返回：先重扫已安装版本再切回个人页。

        改名 / 删除版本后，个人页横条右侧别名与版本选项列表需要即时反映，否则会一直
        显示旧名字、要重启才更新；这里统一在返回前重扫一次，覆盖改名与删除两类改动。
        """
        self.profile_page.refresh_version_list()
        self._switch_page("launch")

    def _open_version_settings(self, alias: str) -> None:
        """个人页版本横条三点入口：按别名打开版本设置页，版本设置页铺满整个窗口。

        v1.3.5.1：按用户要求隐藏主侧栏（启动/下载/设置/打包/关于），版本设置页
        不再只占右侧一半，而是铺满整个窗口客户区；返回时由 ``_switch_page`` 恢复侧栏。
        """
        alias = str(alias or "").strip()
        if not alias:
            return
        self.version_settings_page.show_version(alias)
        self.stack.setCurrentWidget(self.version_settings_page)
        self.sidebar.set_active("launch")
        self.sidebar.hide()

    # ---------- 窗口拖动 ----------
    def resizeEvent(self, event):  # noqa: N802 (Qt 重写约定)
        # 窗口尺寸变化时同步最底层背景层，并重建共享清晰壁纸缓存、刷新各玻璃片局部磨砂。
        self.background.resize(self.size())
        self._refresh_backdrop()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._title_bar.geometry().contains(event.position().toPoint()):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _poll_global_pointer(self) -> None:
        """轮询全局光标，仅在「启动」个人页可见时转发给角色预览做指针跟随。"""
        if self._drag_pos is not None:
            return
        # v1.2.5.1：默认显示启动个人页；切到下载骨架或占位页时不再向 GL 预览转发坐标。
        if self.stack.currentWidget() is not self.profile_page:
            return
        geo = self.geometry()
        cursor = QCursor.pos()
        if geo.contains(cursor):
            nx = (cursor.x() - geo.left()) / max(1, geo.width()) * 2.0 - 1.0
            ny = (1.0 - (cursor.y() - geo.top()) / max(1, geo.height())) * 2.0 - 1.0
            self.profile_page.preview.on_global_pointer(nx, ny)
        else:
            self.profile_page.preview.reset_target()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ---------- 全局拖拽导入整合包 ----------
    def _extract_dropped_pack(self, event) -> str | None:
        """从拖放事件里找出第一个本地整合包文件（.mrpack/.zip）；没有则返回 None。"""
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            local = url.toLocalFile()
            if local.lower().endswith(modpack_format.PACK_EXTENSIONS):
                return local
        return None

    def dragEnterEvent(self, event):  # noqa: N802
        if self._extract_dropped_pack(event) is not None:
            event.acceptProposedAction()
            self._drag_overlay.show_overlay()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if self._extract_dropped_pack(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        # 解析中遮罩由流程控制，拖出窗口只在普通拖拽态隐藏。
        if not self._drag_overlay._resolving:
            self._drag_overlay.hide()
        event.accept()

    def dropEvent(self, event):  # noqa: N802
        path = self._extract_dropped_pack(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self._handle_dropped_pack(path)

    def _handle_dropped_pack(self, path: str) -> None:
        """放下后后台解析格式与计划，期间遮罩显示「正在解析」。"""
        self._pending_pack_path = path
        self._drag_overlay.show_resolving()
        worker = LocalModpackPlanWorker(path, self)
        worker.succeeded.connect(self._on_plan_succeeded)
        worker.failed.connect(self._on_plan_failed)
        self._plan_worker = worker
        worker.start()

    def _on_plan_succeeded(self, path: str, plan) -> None:
        self._plan_worker = None
        self._drag_overlay.hide()
        self._local_name_dialog.open_for(path, plan)

    def _on_plan_failed(self, reason: str) -> None:
        self._plan_worker = None
        self._pending_pack_path = ""
        self._drag_overlay.hide()
        QMessageBox.warning(self, C.APP_FULL_NAME, str(reason))

    def _on_local_name_cancelled(self) -> None:
        self._pending_pack_path = ""

    def _on_local_name_confirmed(self, alias: str) -> None:
        """命名确认后启动后台安装，并用统一进度卡片展示阶段 1-7。"""
        path = self._pending_pack_path
        if not path:
            return
        worker = LocalModpackInstallWorker(path, alias, self)
        worker.phaseChanged.connect(self._on_local_phase)
        worker.progress.connect(self._on_local_progress)
        worker.succeeded.connect(self._on_local_succeeded)
        worker.failed.connect(self._on_local_failed)
        self._local_worker = worker

        dialog = TaskProgressDialog(
            "%s 安装中" % alias, list(PHASE_LABELS), self)
        self._local_progress_dialog = dialog
        # 解析在命名前已完成，把阶段0标记为已完成，核心从阶段1开始。
        dialog.set_phase_state(0, STATE_DONE)
        dialog.mark_phase_running(1)
        dialog.cancelRequested.connect(worker.requestInterruption)
        worker.start()
        dialog.exec()

        self._local_progress_dialog = None
        if self._local_worker is not None and self._local_worker.isRunning():
            self._local_worker.wait(3000)
        self._local_worker = None
        self._pending_pack_path = ""

    def _on_local_phase(self, index: int, label: str) -> None:
        if self._local_progress_dialog is not None:
            self._local_progress_dialog.mark_phase_running(index)

    def _on_local_progress(self, percent: float, done: int,
                           total: int, speed: float, remaining: int) -> None:
        if self._local_progress_dialog is not None:
            self._local_progress_dialog.set_progress(
                float(percent), float(speed), int(remaining))

    def _on_local_succeeded(self, result: dict) -> None:
        self._local_worker = None
        dialog = self._local_progress_dialog
        if dialog is not None:
            dialog.finish_success()
            dialog.hide_cancel()
            dialog.accept()
        self._pending_pack_path = ""
        alias = str(result.get("alias") or "") if isinstance(result, dict) else ""
        self.profile_page.refresh_version_list(preferred=alias)
        self.version_settings_page.refresh_for_alias(alias)

    def _on_local_failed(self, reason: str) -> None:
        self._local_worker = None
        dialog = self._local_progress_dialog
        if dialog is not None:
            dialog.reject()
        self._pending_pack_path = ""
        QMessageBox.warning(self, C.APP_FULL_NAME, str(reason))

    # ---------- 窗口状态持久化 ----------
    def _restore_window_state(self) -> None:
        x = self.config.get("window_x")
        y = self.config.get("window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)
        if self.config.get("window_maximized", False):
            self.showMaximized()

    def shutdown(self) -> None:
        """等待全部后台线程收尾；不经过 closeEvent 的脚本 / 测试退出前显式调用，避免
        线程在主线程控件析构后才 emit 信号触发槽函数，造成原生层访问已销毁对象崩溃。"""
        if self._restore_worker is not None and self._restore_worker.isRunning():
            self._restore_worker.requestInterruption()
            # 等待时长覆盖静默恢复的单跳超时（8s）并留余量，保证阻塞在 urlopen 的线程能
            # 自行收尾，避免 QThread 未结束即被析构触发原生层 0xC0000409。
            self._restore_worker.wait(int(C.RESTORE_HTTP_TIMEOUT * 1000) + 2000)
        profile = getattr(self, "profile_page", None)
        if profile is not None:
            # 先置位关闭标志并等待在途皮肤线程；排队的恢复成功回调即使随后才执行，也会
            # 因该标志而不再启动新的皮肤下载线程。
            profile.shutdown()
        download = getattr(self, "download_page", None)
        if download is not None:
            download.shutdown()
        music = getattr(self, "music_player", None)
        if music is not None:
            music.shutdown()
        version_settings = getattr(self, "version_settings_page", None)
        if version_settings is not None:
            version_settings.shutdown()
        settings = getattr(self, "settings_page", None)
        if settings is not None:
            launch = getattr(settings, "launch_page", None)
            if launch is not None and hasattr(launch, "shutdown"):
                launch.shutdown()
            pet = getattr(settings, "pet_page", None)
            if pet is not None and hasattr(pet, "shutdown"):
                # 关闭本次启动的桌宠子进程并等待皮肤下载线程收尾。
                pet.shutdown()
        plan_worker = getattr(self, "_plan_worker", None)
        if plan_worker is not None and plan_worker.isRunning():
            plan_worker.requestInterruption()
            plan_worker.wait(3000)
        local_worker = getattr(self, "_local_worker", None)
        if local_worker is not None and local_worker.isRunning():
            local_worker.requestInterruption()
            local_worker.wait(5000)

    def closeEvent(self, event):
        self.shutdown()
        self.config.set("window_x", self.x())
        self.config.set("window_y", self.y())
        self.config.set("window_maximized", self.isMaximized())
        self.config.save()
        super().closeEvent(event)
