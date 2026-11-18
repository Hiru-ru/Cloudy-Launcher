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

"""个人页：玩家昵称、当前账号状态、角色 3D 预览、游玩统计、版本占位行、加载条与开始游戏按钮。

账号管理（v1.3.17.0 起）：主页不再放置「离线 / 正版」分段按钮，账号的添加、类型选择
（离线 / 正版）、切换与移除统一到 设置 → 启动 → 账号管理（多账号列表 + 加号弹窗）。
本页只按当前会话状态展示：离线对应本地昵称 + 内置史蒂夫 / 艾利克斯随机角色；正版显示
微软昵称、UUID，并在后台下载正版全身皮肤替换 3D 预览。刷新令牌与公开身份由
``AccountStore`` 持久化，下次启动后台静默续期恢复正版；短期访问令牌只存进程内存、
不落盘；退出登录即清空内存会话并删除本地账号文件。

1.2.1.13 布局按用户提供的参考原型重构：主体为一条两列水平行——左列上下叠放玩家
名称卡（上）与游玩统计卡（下，三格纵向竖列：总游戏时长 → 启动次数 → 最近游玩日期）；
右列玩家人物 3D 预览卡整列撑高，与左列两行总高度顶部、底部对齐。游戏版本占位行从
统计卡内部移出，作为主体下方一条独立的通长横条（全页仅此一条，置灰下拉，仅占位，
真实版本列表后续接入）；最底部保持加载进度条 + 开始游戏椭圆胶囊按钮。窗口尺寸保持
980×660 不变。

v1.2.4.2：右侧玩家人物卡移除原先内嵌的 ``QFrame#preview-pane`` 白玻璃小窗包装（preview_box /
pane / pane_layout 与内边距、白描边），``SkinPreview`` 直接加入外层 ``Card`` 的 body，四周留白
由卡片自身边距提供；不再与外层磨砂叠成两层玻璃。两列权重、统计三格、独立版本占位行与底部
进度条 / 开始游戏按钮布局保持不变。

v1.2.4.3：3D 预览控件背景彻底透明（见 ``skin_preview.py``）——GL 帧缓冲保留 alpha、透明背景
属性 + ``WA_AlwaysStackOnTop`` 压到合成顺序最上层、清屏 alpha=0，角色轮廓之外不写任何底色，透出
外层卡片局部磨砂与壁纸，不再压出独立白 / 灰矩形，也不会退化成黑底；卡片布局、两列权重与其余控件
保持不变。

v1.2.4.4：离线、正版、开始游戏三个按钮换用 ``SpringPushButton``（橡皮筋拉扯 + 松开弹簧回弹
控制器，见 ``spring_button.py``），按钮本体 QSS 外观、尺寸与几何沿用 v1.2.4.3 旧样式不改动；
退出登录文字按钮不在本轮范围内，保持普通 ``QPushButton``。卡片、分段与主按钮外观未做整窗改动。

v1.2.4.5：离线、正版、开始游戏三个按钮与导航、标题栏两按钮统一 iOS 白色半透明胶囊语言；
选中态只靠更亮填充 + 亮描边 + 加粗深色字区分，不再出现蓝色块；拉扯向量改用全局光标映射，
指针拖出按钮仍持续跟随，沿拉扯方向轻微果冻形变。退出登录文字按钮仍不在范围内。

v1.2.4.6：返工收窄透明范围——只有这六个功能键做半透明玻璃，背景、卡片、侧栏、进度条、
输入框等其余区域全部回退 v1.2.4.5 基线，不做整窗 / 全页面模糊毛玻璃。六按钮填充透明度
按真实窗口像素明度差下调，开始游戏主按钮单独一组更淡的玻璃色（身后是较暗浅蓝壁纸 / 罩层，
不与分段、导航共用一档白），不再压成不透明白板；拖拽彻底取消硬限幅与 painter 矩形裁剪，
指针拖到任意方向都持续跟随、不被边界挡住，松开弹簧回弹复位。退出登录文字按钮仍不在范围内。

v1.2.5.1：本页由主窗口挂到「启动」导航、作为程序启动后的默认可见页；主窗口创建本页
实例并接入页面栈，启动静默恢复成功回调仍调 ``refresh()``；昵称 / 皮肤 / 3D 预览 /
离线 / 正版 / 统计 / 加载条 / 账号持久化全部代码与对外接口原样保留、不删不退化。
本页布局、控件与交互逻辑相对 v1.2.4.6 基线无任何改动。

记录时机：启动次数与最近游玩日期改为「真正启动游戏」后才记录——点击开始游戏、
模拟加载到 100%（本次启动游戏事件）后才启动次数 +1、写入当天日期；只打开启动器、
进入个人页不再计数、不写日期。游戏总时长同样只在游戏运行会话内累计，打开启动器不
计时；真实 Minecraft 进程接入后按会话结算时长。开始游戏按钮、3D 角色预览、离线 /
正版分段按钮与加载进度条外观保持不变。
"""
import random
from datetime import date

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import game_dirs
from ..account_session import AccountSession
from ..account_store import AccountStore
from ..config_store import ConfigStore
from ..version_launch_config import VersionLaunchConfig
from .card_widget import Card
from .capsule_progress_bar import CapsuleProgressBar
from .appearance import appearance
from .launch_worker import LaunchWorker
from .skin_fetch_worker import SkinFetchWorker
from .skin_preview import SkinPreview
from .spring_button import SpringPushButton


# 版本选择列表：一屏最多可视三行，高度固定不撑高整个界面；更多版本靠组内滑块 / 滚轮滚动。
_VERSION_OPTION_ROW_HEIGHT = 32
_VERSION_LIST_HEIGHT = _VERSION_OPTION_ROW_HEIGHT * 3 + 14


def format_play_time(seconds: int) -> str:
    """将累计秒数按小时计时法格式化：“X 小时”。"""
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    return f"{hours} 小时"


def format_uuid(dashed: str) -> str:
    """把无横杠 32 位 UUID 格式化为 8-4-4-4-12；长度不符时原样返回。"""
    raw = (dashed or "").replace("-", "")
    if len(raw) != 32:
        return dashed or ""
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


class _VersionMoreButton(QPushButton):
    """版本横条右侧的三点设置入口：自绘浅玻璃圆 + 三个圆点，点开版本设置页。

    v1.3.5.0：不做常驻按钮，只在鼠标进入「游戏版本」横条时显现、移出后收起；自绘是为了
    保证三点在 26px 小圆里的位置与大小稳定，不受字体度量影响（与标题栏圆形按钮同一做法）。
    """

    _SIZE = 26
    _DOT_RADIUS = 1.7
    _DOT_GAP = 5.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("versionMoreBtn")
        self.setFixedSize(self._SIZE, self._SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("版本设置")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._hovered = False

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QPen(QColor(255, 255, 255, 150 if self._hovered else 120), 1.0))
        painter.setBrush(QColor(255, 255, 255, 120 if self._hovered else 84))
        painter.drawEllipse(rect)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(43, 71, 89, 220))
        dot = int(self._DOT_RADIUS * 2)
        center_y = int(self.height() / 2.0) - int(self._DOT_RADIUS)
        for index in (-1, 0, 1):
            center_x = int(self.width() / 2.0 + index * self._DOT_GAP) - int(self._DOT_RADIUS)
            painter.drawEllipse(center_x, center_y, dot, dot)
        painter.end()


class _VersionHeader(QPushButton):
    """「游戏版本」手风琴横条：指针移入时显现右侧三点入口，移出后收起。"""

    def __init__(self, parent=None) -> None:
        super().__init__("", parent)
        self.setProperty("versionAccordionHeader", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self._more_button: QPushButton | None = None
        self._more_enabled = False

    def bind_more_button(self, button: QPushButton) -> None:
        """挂上要随悬停显隐的三点按钮（按钮由横条内部布局摆放）。"""
        self._more_button = button
        button.hide()

    def set_more_enabled(self, enabled: bool) -> None:
        """没有选中版本时不提供设置入口，避免进入无意义的设置页。"""
        self._more_enabled = enabled
        if self._more_button is not None and not enabled:
            self._more_button.hide()

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._apply_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        self._apply_hover(False)
        super().leaveEvent(event)

    def _apply_hover(self, entered: bool) -> None:
        button = self._more_button
        if button is None:
            return
        if not self._more_enabled:
            button.hide()
            return
        if entered:
            button.show()
            return
        # 指针移入子按钮时父按钮同样会收到 Leave；按全局坐标复核是否仍落在横条内。
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            button.show()
        else:
            button.hide()


class ProfilePage(QWidget):
    """个人主页。"""

    startGameRequested = Signal()
    # v1.3.5.0：版本横条三点入口被点击，携带当前选中别名请求主窗口打开版本设置页。
    versionSettingsRequested = Signal(str)

    def __init__(self, config: ConfigStore, session: AccountSession,
                 account_store: AccountStore, parent=None):
        super().__init__(parent)
        self.config = config
        self.session = session
        self.account_store = account_store

        self._loading = False
        self._progress = 0
        self._version_entries: list[dict] = []
        self._skin_worker: SkinFetchWorker | None = None
        # 关闭阶段置位：禁止再启动新的皮肤下载线程，并等待在途线程收尾，避免子控件随主
        # 窗口析构时把运行中的 QThread 一并销毁而触发 0xC0000409。
        self._shutting_down = False

        self._build_ui()
        self.refresh()

    # ---------- UI 搭建 ----------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("page-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        # v1.2.12.11：彻底隐藏垂直滚动条（原生宽度压不住，见 download_page 注释），滚轮仍可滚
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("page-container")
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(12)

        # v1.3.17.0：主页顶部「离线 / 正版」分段按钮已移除，账号统一到
        # 设置 → 启动 → 账号管理（多账号列表 + 加号弹窗）。
        self._build_main_row(root)
        # 游戏版本手风琴：默认收起一条横条，点一下展开版本列表
        root.addWidget(self._build_version_row())
        self._build_launch_row(root)

    def _build_main_row(self, root: QVBoxLayout) -> None:
        """主体一条两列水平行（对齐参考原型）：

        - 左列上下叠放：玩家名称卡（上，自然高度）+ 游玩统计卡（下，弹性撑满）；
        - 右列玩家人物 3D 预览卡，整列撑高，与左列两行总高度顶部、底部对齐；
        - 游戏版本占位行不在本卡内，作为主体下方独立通长一行（见 _build_version_row）。
        窗口尺寸保持 980×660 不变。
        """
        row = QHBoxLayout()
        row.setSpacing(16)

        # 左列：昵称卡在上、统计卡在下，纵向叠放；统计卡占左列剩余弹性高度。
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.addWidget(self._build_name_card())
        left_col.addWidget(self._build_stats_card(), 1)
        row.addLayout(left_col, 6)

        # 右侧：角色预览卡片，仅保留 3D 预览。v1.2.4.2 移除原先内嵌的 preview-pane 白玻璃
        # 小窗（避免与外层磨砂叠成两层玻璃）；v1.2.4.3 起 GL 预览背景彻底透明，轮廓之外
        # 透出外层卡片磨砂，不再压出独立白板。四周留白由卡片自身边距提供，不另起内框 /
        # 描边。随水平行整列撑满等高。
        avatar_card = Card("玩家人物")
        self.preview = SkinPreview()
        avatar_card.body.addWidget(self.preview, 1)
        row.addWidget(avatar_card, 4)

        root.addLayout(row, 1)

    def _build_stats_card(self) -> Card:
        """左列下方游玩统计卡片：三格纵向竖列（总游戏时长 → 启动次数 → 最近游玩）。

        版本占位行已移出本卡，作为主体下方独立通长一行；本卡内部仅保留三格统计，
        竖列上方与下方由弹性间距撑开，保证三行在卡内均匀分布。
        """
        stats_card = Card(None)
        stats_body = QVBoxLayout()
        stats_body.setContentsMargins(0, 0, 0, 0)
        stats_body.setSpacing(12)

        stats_col = QVBoxLayout()
        stats_col.setSpacing(12)
        self.play_time_label = self._add_stat_row(stats_col, "总游戏时长")
        self.launch_count_label = self._add_stat_row(stats_col, "启动次数")
        self.last_played_label = self._add_stat_row(stats_col, "最近游玩", date_value=True)
        stats_body.addLayout(stats_col)
        stats_body.addStretch(1)

        stats_card.add_layout(stats_body)
        return stats_card

    def _build_name_card(self) -> Card:
        """玩家名称卡片：昵称输入框 + 正版账号信息行（UUID 小字、退出登录，默认隐藏）。

        输入框在卡片内垂直居中；正版登录成功后昵称框锁定为微软昵称，第二行显示 UUID
        与退出登录按钮；切回离线后该行隐藏、输入框恢复可编辑。
        """
        card = Card()
        card.body.addStretch(1)

        name_row = QHBoxLayout()
        name_row.setSpacing(10)

        name_label = QLabel("玩家名称")
        name_label.setProperty("hintLabel", True)
        name_label.setFixedWidth(70)
        name_row.addWidget(name_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入游戏昵称")
        # 字号 10px、高度 24px，能看清昵称即可。
        self.name_edit.setMinimumHeight(24)
        self.name_edit.setStyleSheet("font-size: 10px;")
        self.name_edit.editingFinished.connect(self._save_name)
        name_row.addWidget(self.name_edit, 1)
        card.body.addLayout(name_row)

        # 正版账号信息行：UUID 小字 + 退出登录按钮；默认隐藏，登录成功后显示。
        account_row = QHBoxLayout()
        account_row.setContentsMargins(80, 0, 0, 0)
        account_row.setSpacing(10)
        self.uuid_label = QLabel("")
        self.uuid_label.setProperty("uuidLabel", True)
        self.uuid_label.hide()
        account_row.addWidget(self.uuid_label, 1)

        self.logout_button = QPushButton("退出登录")
        self.logout_button.setProperty("logoutButton", True)
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.hide()
        self.logout_button.clicked.connect(self._logout_official)
        account_row.addWidget(self.logout_button)
        card.body.addLayout(account_row)

        card.body.addStretch(1)
        return card

    def _build_version_row(self) -> Card:
        """游戏版本选择手风琴：收起时一条横条，点一下展开版本列表。"""
        card = Card()
        card.body_layout.setContentsMargins(0, 0, 0, 0)
        card.body_layout.setSpacing(0)

        # --- 横条（header，可点击切换展开/收起） ---
        header = _VersionHeader()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(10)
        self._version_header = header

        version_label = QLabel("游戏版本")
        version_label.setProperty("hintLabel", True)
        header_layout.addWidget(version_label)

        self._version_current_label = QLabel("尚未安装")
        self._version_current_label.setProperty("versionCurrentLabel", True)
        header_layout.addWidget(self._version_current_label, 1)

        # 三点版本设置入口：装在固定宽度的空槽里，显隐只切换子按钮，横条几何不跳动。
        more_slot = QWidget()
        more_slot.setFixedSize(_VersionMoreButton._SIZE, _VersionMoreButton._SIZE)
        more_layout = QHBoxLayout(more_slot)
        more_layout.setContentsMargins(0, 0, 0, 0)
        more_layout.setSpacing(0)
        self._version_more_button = _VersionMoreButton()
        self._version_more_button.clicked.connect(self._request_version_settings)
        more_layout.addWidget(self._version_more_button)
        header_layout.addWidget(more_slot, 0)
        header.bind_more_button(self._version_more_button)

        self._version_arrow = QLabel("›")
        self._version_arrow.setProperty("versionArrow", True)
        header_layout.addWidget(self._version_arrow, 0)

        # 文字标签默认会接走鼠标事件，导致指针停在文字上时横条收不到 Enter（三点不出现）；
        # 让它们对鼠标透明，整条横条的悬停都由 header 自己处理。
        for child in (version_label, self._version_current_label, self._version_arrow):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        card.body_layout.addWidget(header)

        # --- 展开区域（body，默认收起高度 0） ---
        self._version_body = QWidget()
        self._version_body.setMaximumHeight(0)
        self._version_body.setMinimumHeight(0)
        body_layout = QVBoxLayout(self._version_body)
        body_layout.setContentsMargins(8, 0, 8, 6)
        body_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("version-list-scroll")
        scroll.setFixedHeight(_VERSION_LIST_HEIGHT)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 超出三行时显示垂直滑块（可见样式在 theme.py 单独定义，覆盖全局透明滚动条）。
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.viewport().setAutoFillBackground(False)
        # Windows 上 QSS width 对 QScrollBar 不生效（会回落原生 ~17px），用 API 钉成 6px，
        # 并在事件循环下一轮补一次，防止 show 时 QSS polish 把 fixedWidth 冲掉。
        vbar = scroll.verticalScrollBar()
        vbar.setFixedWidth(6)
        QTimer.singleShot(0, lambda sb=vbar: sb.setFixedWidth(6))
        self._version_scroll = scroll

        container = QWidget()
        container.setObjectName("version-list-container")
        self._version_list_layout = QVBoxLayout(container)
        self._version_list_layout.setContentsMargins(2, 2, 2, 2)
        self._version_list_layout.setSpacing(6)
        scroll.setWidget(container)

        self._version_options: list[QPushButton] = []
        self._version_entries: list[dict] = []
        self._version_placeholder = QLabel("尚未安装游戏版本，请先到下载页下载")
        self._version_placeholder.setProperty("versionListPlaceholder", True)
        self._version_placeholder.setAlignment(Qt.AlignCenter)
        self._version_list_layout.addWidget(self._version_placeholder)

        body_layout.addWidget(scroll)
        card.body_layout.addWidget(self._version_body)

        # 展开/收起动画
        self._version_expanded = False
        self._version_anim = QPropertyAnimation(self._version_body, b"maximumHeight")
        self._version_anim.setDuration(220)
        self._version_anim.setEasingCurve(QEasingCurve.OutCubic)
        header.clicked.connect(self._toggle_version_accordion)

        return card

    def _toggle_version_accordion(self) -> None:
        """点击横条切换版本列表展开/收起。"""
        self._version_expanded = not self._version_expanded
        if self._version_expanded:
            target_h = _VERSION_LIST_HEIGHT + 12
            self._version_arrow.setText("⌄")
        else:
            target_h = 0
            self._version_arrow.setText("›")
        if not appearance.animations_enabled:
            # 总开关关闭：高度瞬时到位，不播放手风琴动画。
            self._version_anim.stop()
            self._version_body.setMaximumHeight(target_h)
            return
        self._version_anim.setStartValue(self._version_body.maximumHeight())
        self._version_anim.setEndValue(target_h)
        self._version_anim.start()

    # ---------- 已安装版本两行滚轮列表 ----------
    def _clear_version_options(self) -> None:
        """清空旧版本选项按钮与末尾弹簧，占位标签保留复用。"""
        while self._version_list_layout.count():
            item = self._version_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._version_placeholder:
                widget.setParent(None)
        self._version_options = []

    def refresh_version_list(self, preferred: str = "") -> None:
        """重新扫描本地已安装版本并重建两行滚轮列表；下载成功后由主窗口调用刷新。

        v1.2.12.0：目录名即别名，原生 MC 版本 / 加载器类型 / 版本记录在 ``install_meta.json``；
        列表按钮显示别名，悬浮提示标注「MC 版本 · 加载器」。

        preferred：本次刚安装完成的别名，存在时优先选中。无有效选中但列表非空时，自动选中
        第一个版本兜底，避免「列表里有版本却因没选中而打不开」。
        """
        entries = game_dirs.scan_installed_entries()
        self._clear_version_options()
        self._version_entries = entries

        aliases = [str(entry.get("alias") or "") for entry in entries]
        current = self.config.selected_version
        # 有效选中优先级：本次安装的 preferred > 已保存的 current > 列表第一个兜底。
        chosen = ""
        if preferred and preferred in aliases:
            chosen = preferred
        elif current and current in aliases:
            chosen = current
        elif aliases:
            chosen = aliases[0]
        if chosen != current:
            # 覆盖失效选中（被删除）或首次自动选中，统一在这里落盘。
            self.config.selected_version = chosen
            self.config.save()

        if not entries:
            self._version_placeholder.setVisible(True)
            self._version_list_layout.addWidget(self._version_placeholder)
            self._sync_current_label()
            return

        self._version_placeholder.setVisible(False)
        current_btn: QPushButton | None = None
        for entry in entries:
            alias = str(entry.get("alias") or "")
            loader_label = C.LOADER_LABELS.get(entry.get("loader") or C.LOADER_VANILLA, "")
            tip = f"{entry.get('mc_version', alias)} · {loader_label}"
            if entry.get("loader_version"):
                tip = f"{tip} {entry['loader_version']}"
            btn = QPushButton(alias)
            btn.setProperty("versionOption", True)
            btn.setCheckable(True)
            btn.setFixedHeight(_VERSION_OPTION_ROW_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setChecked(alias == chosen)
            if alias == chosen:
                current_btn = btn
            btn.clicked.connect(
                lambda _checked=False, v=alias: self._select_version(v)
            )
            self._version_list_layout.addWidget(btn)
            self._version_options.append(btn)
        # 条目少时顶在列表上方，不被拉伸均分。
        self._version_list_layout.addStretch(1)
        # 刷新后把已选中版本滚动到两行可视区，避免选中项被裁切在视口外。
        if current_btn is not None:
            self._version_scroll.ensureWidgetVisible(current_btn)
        self._sync_current_label()

    def showEvent(self, event):  # noqa: N802 (Qt 重写约定)
        # 从版本设置页返回时，指针多半不在版本横条上，但横条没收到 Leave，
        # 三点会残留显示；页面重新出现时按真实指针位置复核一次显隐。
        super().showEvent(event)
        self._version_header._apply_hover(False)

    def _sync_current_label(self) -> None:
        """横条右侧显示当前选中别名；无有效选中时显示「尚未安装」。"""
        selected = self.config.selected_version
        self._version_current_label.setText(selected or "尚未安装")
        # 没有选中版本就进不了设置页，三点入口一并隐藏。
        self._version_header.set_more_enabled(bool(selected))

    def _request_version_settings(self) -> None:
        """三点按钮：把当前选中别名交给主窗口，由后者切到版本设置页。"""
        alias = str(self.config.selected_version or "")
        if alias:
            self.versionSettingsRequested.emit(alias)

    def _find_entry(self, alias: str) -> dict | None:
        """按别名在本地扫描结果里找安装元数据；未找到返回 ``None``。"""
        for entry in getattr(self, "_version_entries", []):
            if entry.get("alias") == alias:
                return entry
        return None

    def _select_version(self, alias: str) -> None:
        """选中某已安装版本：持久化别名到配置，并刷新互斥选中态。"""
        self.config.selected_version = alias
        self.config.save()
        for btn in self._version_options:
            btn.setChecked(btn.text() == alias)
            if btn.text() == alias:
                self._version_scroll.ensureWidgetVisible(btn)
        self._sync_current_label()

    def _add_stat_row(self, col: QVBoxLayout, caption: str, date_value: bool = False) -> QLabel:
        """在统计竖列追加一行：左侧固定宽小标签、右侧大数值，返回大数值标签供刷新。

        三行自上而下依次为总游戏时长、启动次数、最近游玩；date_value=True 时数值为
        年月日字符串，使用较小字号保证 ``YYYY-MM-DD`` 不换行、不溢出。
        """
        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(caption)
        label.setProperty("statLabel", True)
        label.setFixedWidth(96)
        row.addWidget(label)

        value = QLabel("—")
        value.setProperty("statValueDate" if date_value else "statValue", True)
        row.addWidget(value, 1)

        col.addLayout(row)
        return value

    def _build_launch_row(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)

        self.progress_bar = CapsuleProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待启动")
        row.addWidget(self.progress_bar, 4)

        self.launch_button = SpringPushButton("开始游戏")
        self.launch_button.setProperty("primaryButton", True)
        self.launch_button.setFixedHeight(44)
        self.launch_button.setFixedWidth(146)
        self.launch_button.setCursor(Qt.PointingHandCursor)
        self.launch_button.clicked.connect(self._on_launch_clicked)
        row.addWidget(self.launch_button, 0)

        root.addLayout(row)

    # ---------- 数据刷新 ----------
    def refresh(self) -> None:
        """按当前会话模式回填昵称、统计与角色；打开启动器本身不计数、不写最近游玩日期。

        启动次数与最近游玩日期只在真正启动游戏（加载完成事件）后记录，见
        ``_finish_loading``；游戏总时长同样只在游戏运行会话内累计，打开启动器不计时。
        启动时主窗口先尝试用本地账号文件静默恢复正版会话；恢复成功后会话切正版并由
        本方法回填，失败则保持离线。
        """
        self.play_time_label.setText(format_play_time(self.config.play_time_seconds))
        self.launch_count_label.setText(str(self.config.launch_count))
        self.last_played_label.setText(self.config.last_played or "—")

        if self.session.is_microsoft:
            self._apply_official_state()
        else:
            self._apply_offline_state(randomize=True)

        # 回填本地已安装版本两行滚轮列表，恢复上次选中的版本号。
        self.refresh_version_list()

    # ---------- 账号状态应用（切换/登录入口在设置 → 启动 → 账号管理） ----------
    def _apply_offline_state(self, randomize: bool) -> None:
        """切回离线：清空正版界面元素，昵称框恢复可编辑，回退内置离线角色。"""
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.config.player_name)
        self.name_edit.blockSignals(False)
        self.name_edit.setReadOnly(False)
        self.uuid_label.hide()
        self.logout_button.hide()

        if randomize:
            skin_id = random.choice(list(C.SKIN_CHOICES.keys()))
            self.config.skin = skin_id
            self.config.save()
        else:
            skin_id = self.config.skin
        self._apply_skin(skin_id)

    def _apply_official_state(self) -> None:
        """进入正版：昵称框锁定为微软昵称，显示 UUID，后台下载正版皮肤替换预览。"""
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.session.name)
        self.name_edit.blockSignals(False)
        self.name_edit.setReadOnly(True)
        self.uuid_label.setText("UUID：" + format_uuid(self.session.uuid))
        self.uuid_label.show()
        self.logout_button.show()
        self._fetch_official_skin()

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
        self.session.switch_offline()
        # 退出登录同时删除本地账号文件，清除可续期的刷新令牌
        self.account_store.clear()
        self._apply_offline_state(randomize=False)

    def _save_name(self) -> None:
        # 正版昵称来自微软账户、不可编辑；只读状态下不响应保存
        if self.session.is_microsoft:
            return
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setText(self.config.player_name)
            return
        self.config.player_name = name
        self.config.save()

    # ---------- 角色 ----------
    def _apply_skin(self, skin_id: str) -> None:
        self.preview.set_skin(skin_id)

    def _fetch_official_skin(self) -> None:
        """后台下载正版全身皮肤；无皮肤地址或下载失败时回退内置离线角色。"""
        if self._shutting_down:
            # 窗口已在关闭，不再启动新的下载线程；皮肤是否加载对退出无意义。
            return
        if self._skin_worker is not None:
            if self._skin_worker.isRunning():
                self._skin_worker.wait(1000)
            self._skin_worker = None

        skin_url = self.session.skin_url
        if not skin_url:
            self._apply_skin(self.config.skin)
            return

        self._skin_worker = SkinFetchWorker(skin_url, self.session.slim, parent=self)
        self._skin_worker.succeeded.connect(self._on_skin_loaded)
        self._skin_worker.failed.connect(self._on_skin_failed)
        self._skin_worker.start()

    def _on_skin_loaded(self, image, slim: bool) -> None:
        self.preview.set_external_skin(image, slim)

    def _on_skin_failed(self, message: str) -> None:
        # 皮肤拉取失败不影响登录态，回退内置史蒂夫 / 艾利克斯
        self._apply_skin(self.config.skin)

    def shutdown(self) -> None:
        """主窗口关闭时调用：置位禁止再启动皮肤线程，并等待在途皮肤下载收尾。

        ProfilePage 是嵌入主窗口的子控件，自身的 closeEvent 不会被触发，因此必须由
        MainWindow.shutdown 显式调用，否则运行中的 SkinFetchWorker 会随父控件析构而
        触发「QThread: Destroyed while thread is still running」原生崩溃。"""
        self._shutting_down = True
        if self._skin_worker is not None and self._skin_worker.isRunning():
            self._skin_worker.requestInterruption()
            self._skin_worker.wait(int(C.SKIN_FETCH_TIMEOUT * 1000) + 2000)

    # ---------- 真实启动游戏（后台线程：Java 探测 + 命令组装 + 进程拉起 + 存活监控） ----------
    def _on_launch_clicked(self) -> None:
        if self._loading:
            return
        alias = self.config.selected_version
        entry = self._find_entry(alias)
        if entry is None:
            QMessageBox.warning(
                self, C.APP_FULL_NAME, "请先在下方选择一个已安装的游戏版本。"
            )
            return

        self._loading = True
        self.launch_button.setEnabled(False)
        self.launch_button.setText("启动中…")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("正在准备游戏环境…")

        # 后台线程执行完整启动链路，避免阻塞界面；phase 信号实时回传真实阶段。
        # v1.3.21.0：传入该版本独立的启动配置（覆盖 + 默认兜底），不再直接用全局 config。
        launch_cfg = VersionLaunchConfig(self.config, alias)
        self._launch_worker = LaunchWorker(alias, self.session, launch_cfg, self)
        self._launch_worker.phase.connect(self._on_launch_phase)
        self._launch_worker.succeeded.connect(self._on_launch_succeeded)
        self._launch_worker.failed.connect(self._launch_failed)
        self._launch_worker.start()

    def _on_launch_phase(self, percent: int, text: str) -> None:
        """后台启动阶段回调：进度条真实反映环境准备→进程拉起→等待窗口。"""
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(text)

    def _on_launch_succeeded(self, process) -> None:
        """进程已确认稳定存活：本次启动计数 +1、记录当天日期并持久化。"""
        self.config.launch_count = self.config.launch_count + 1
        self.config.last_played = date.today().isoformat()
        self.config.save()
        self.launch_count_label.setText(str(self.config.launch_count))
        self.last_played_label.setText(self.config.last_played or "—")

        self._loading = False
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("游戏已启动")
        self.launch_button.setEnabled(True)
        self.launch_button.setText("开始游戏")

    def _launch_failed(self, reason: str) -> None:
        """启动失败：复位按钮 / 进度条并弹出引导提示；不伪造启动成功、不写启动计数。"""
        self._loading = False
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待启动")
        self.launch_button.setEnabled(True)
        self.launch_button.setText("开始游戏")
        # Java 相关失败分别给对应标题：缺 Java / Java 版本过低，其余沿用软件名。
        if reason.startswith(C.JAVA_MISSING_MESSAGE[:12]):
            title = C.JAVA_MISSING_TITLE
        elif "需要 Java" in reason:
            title = C.JAVA_VERSION_LOW_TITLE
        else:
            title = C.APP_FULL_NAME
        QMessageBox.warning(self, title, reason)

