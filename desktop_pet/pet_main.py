# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Cloudy Pet / 云朵桌宠
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

"""云朵桌宠（Cloudy Pet）独立 APP 入口。

命令行参数（由云朵启动器导入并启动时传入）：

- ``--skin <path>``：皮肤图片文件路径（png/jpg/jpeg）；
- ``--slim <0|1>``：是否细臂（Alex 风格）模型；
- ``--x <int>`` / ``--y <int>``：窗口左上角初始位置（可选，缺省放在屏幕右下角）。

运行后显示一个透明、无边框、置顶的小窗，角色身体静止，仅头部跟随鼠标转动。
"""
import argparse
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication, QMenu, QMessageBox, QWidget, QVBoxLayout,
)

import pet_actions as A
import pet_constants as P
import pet_features as F
from pet_bubble import SpeechBubble
from pet_feed_menu import FeedMenu
from pet_hover import HoverController
from pet_idle import IdleController
from pet_needs import HungerController
from pet_particles import ParticleLayer
from pet_preview import PetPreview
from pet_sleep import SleepController
from pet_wolf_event import WolfEventController


class PetWindow(QWidget):
    """透明置顶无边框桌宠窗。"""

    def __init__(self, skin_path: str, slim: bool, x: int | None,
                 y: int | None, features: dict | None = None):
        super().__init__()
        self._features = F.normalize(features)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(P.PET_WINDOW_WIDTH, P.PET_WINDOW_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.preview = PetPreview(self)
        layout.addWidget(self.preview)

        loaded = False
        if skin_path and os.path.isfile(skin_path):
            loaded = self.preview.set_skin_file(skin_path, slim)
        if not loaded:
            # 未传入有效皮肤时回退内置默认皮肤（经典模型）。
            self.preview.set_skin_file(P.default_skin_path(), False)

        self._place(x, y)

        # 头顶对话气泡（绝对定位子控件，不进布局）。
        self.bubble = SpeechBubble(self, P.PET_WINDOW_WIDTH)

        # 空闲检测：鼠标静止到阈值后随机播放动作，移动即打断；活动时同步隐藏气泡。
        self._idle = IdleController(self.preview, on_activity=self._on_user_activity)

        # 饥饿值：随时间下降，饿了冒泡「我饿了」并自动吃东西，吃完回满。
        self._hunger = HungerController(self.preview, say=self.bubble.show_text)

        # 喂食菜单 + 悬停检测：静止 1~3 秒弹出，选择喂什么。
        self.feed_menu = FeedMenu(on_pick=self._pick_food)
        self._hover = HoverController(self, self.feed_menu)

        # 小狗随机进场/退场：空闲时随机让驯服狼进场陪伴，陪伴后自动退场。
        self._wolf_event = WolfEventController(self.preview)

        # 情绪粒子覆盖层（爱心/音符/问号/Zzz），透明不挡交互。
        self.particles = ParticleLayer(self)
        self.particles.setGeometry(0, 0, P.PET_WINDOW_WIDTH, P.PET_WINDOW_HEIGHT)
        self.particles.show()
        self.particles.raise_()

        # 困倦 / 睡眠：持续空闲打哈欠、入睡，鼠标一动醒来。
        self._sleep = SleepController(
            self.preview, say=self.bubble.show_text,
            on_sleep_change=self._on_sleep_change)

        self._apply_features()

        self._poll = QTimer(self)
        self._poll.setInterval(P.POLL_INTERVAL_MS)
        self._poll.timeout.connect(self._poll_cursor)
        self._poll.start()

    def _apply_features(self) -> None:
        """把当前开关状态应用到各控制器（默认全开）。"""
        f = self._features
        self._idle.set_enabled(f[F.IDLE])
        self._hover.set_enabled(f[F.HOVER])
        self._hunger.set_enabled(f[F.HUNGER])
        self._wolf_event.set_enabled(f[F.WOLF])
        self._sleep.set_enabled(f[F.SLEEP])

    def _on_sleep_change(self, sleeping: bool) -> None:
        """入睡 / 醒来回调：入睡时持续冒 Zzz，醒来清空粒子。"""
        if sleeping:
            self._zzz_timer = QTimer(self)
            self._zzz_timer.setInterval(900)
            self._zzz_timer.timeout.connect(self._emit_zzz)
            self._zzz_timer.start()
            self._emit_zzz()
        else:
            timer = getattr(self, "_zzz_timer", None)
            if timer is not None:
                timer.stop()
                self._zzz_timer = None

    def _emit_zzz(self) -> None:
        self.particles.zzz(80, 40)

    def _place(self, x: int | None, y: int | None) -> None:
        if x is not None and y is not None:
            self.move(x, y)
            return
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        px = avail.right() - self.width() - 40
        py = avail.bottom() - self.height() - 40
        self.move(px, py)

    def _on_user_activity(self) -> None:
        """鼠标活动：隐藏气泡、醒来，并让小狗事件重置进场计时（狼在则继续陪伴）。"""
        self.bubble.hide_now()
        self._wolf_event.on_activity()
        self._sleep.on_activity()

    def _poll_cursor(self) -> None:
        center = self.geometry().center()
        cursor = QCursor.pos()
        dx = cursor.x() - center.x()
        dy = cursor.y() - center.y()
        nx = max(-1.0, min(1.0, dx / P.POINTER_RADIUS))
        # 屏幕坐标向下为正，转成 OpenGL 风格的“上正下负”再交给渲染组件。
        ny = max(-1.0, min(1.0, -dy / P.POINTER_RADIUS))
        self.preview.on_pointer(nx, ny)
        dt = P.POLL_INTERVAL_MS / 1000.0
        f = self._features
        menu_open = self._hover.is_open()
        sleeping = self._sleep.is_sleeping()

        # feature 开关与临时抑制（菜单/睡眠）合并，只在条件变化时实际 reset。
        self._idle.set_enabled(f[F.IDLE] and not menu_open and not sleeping)
        self._hover.set_enabled(f[F.HOVER] and not sleeping)
        self._hunger.set_enabled(f[F.HUNGER] and not sleeping)
        self._wolf_event.set_enabled(f[F.WOLF] and not menu_open)
        self._sleep.set_enabled(f[F.SLEEP] and not menu_open)

        # 空闲检测：传入鼠标位置与帧间隔，由其判断是否进入随机表演。
        self._idle.update((cursor.x(), cursor.y()), dt)
        # 饥饿值推进：饿了自动冒泡并吃东西。
        self._hunger.update(dt)
        # 悬停检测：窗口内静止 1~3 秒弹出喂食菜单。
        self._hover.update((cursor.x(), cursor.y()), dt)
        # 困倦 / 睡眠推进。
        self._sleep.update(dt)
        # 小狗随机进场/退场：依据当前是否空闲推进。
        self._wolf_event.update(self._idle.is_idle(), dt)

    def _pick_food(self, target: str, food_id: str) -> None:
        """菜单选择喂什么：关闭菜单，按目标（自己/小狗）执行对应反应。"""
        self._hover.close_menu()
        self.bubble.hide_now()
        if target == "pet":
            # 摸小狗：玩家摸头动作 + 狗被摸柔和反应 + 冒爱心。
            self.preview.trigger_action(A.PET)
            self.preview.pet_wolf()
            self.particles.heart(96, 92)
            return
        if target == "wolf":
            # 喂小狗：触发开心反应并冒泡，不影响玩家饥饿值。
            self.preview.feed_wolf()
            self.bubble.show_text("汪！谢谢主人~")
            self.particles.heart(96, 92)
            return
        # 喂自己：立即吃指定食物并把饥饿值回满。
        self.preview.trigger_action(A.EAT, food_id=food_id)
        self._hunger.hunger = P.HUNGER_RESTORE
        self._hunger._announced = False
        self._hunger._was_eating = False

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        """右键菜单：「做个动作」子菜单 + 直接退出入口。"""
        menu = QMenu(self)
        action_menu = menu.addMenu("做个动作")
        action_items = {}
        for aid, label in A.ACTION_LABELS:
            action_items[action_menu.addAction(label)] = aid
        menu.addSeparator()
        quit_action = menu.addAction("退出桌宠")
        chosen = menu.exec(event.globalPos())
        if chosen == quit_action:
            # Tool 类型窗口 close 不触发 lastWindowClosed，需显式退出应用，避免进程残留。
            self.close()
            QApplication.quit()
        elif chosen in action_items:
            self.preview.trigger_action(action_items[chosen])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cloudy Pet desktop companion")
    parser.add_argument("--skin", default="", help="skin image file path")
    parser.add_argument("--slim", type=int, default=0, choices=(0, 1), help="slim arm model")
    parser.add_argument("--x", type=int, default=None, help="window left position")
    parser.add_argument("--y", type=int, default=None, help="window top position")
    # 启动器握手标志：只有云朵启动器拉起时才会传入，直接双击不带此标志。
    parser.add_argument("--from-launcher", action="store_true",
                        help="internal handshake: launched by Cloudy Launcher")
    # 功能开关：逗号分隔 key=1/0，缺省（未传）全部开启。
    parser.add_argument("--features", default="",
                        help="feature toggles key=1,key=0; default all on")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication(sys.argv)
    app.setApplicationName(P.PET_APP_NAME)

    if not args.from_launcher:
        # 非启动器拉起（如直接双击）：不显示桌宠，提示后退出。
        QMessageBox.information(
            None,
            "云朵桌宠",
            "云朵桌宠无法单独运行。请打开云朵启动器，在「设置 · 桌宠」页导入并启动桌宠。",
        )
        return 0

    features = F.parse_features(args.features)
    window = PetWindow(args.skin, bool(args.slim), args.x, args.y, features)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
