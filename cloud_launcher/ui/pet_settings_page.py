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

"""设置页「桌宠」标签：导入独立桌宠 APP、皮肤口径与桌宠启停。

三张局部磨砂卡片：

1. 桌宠程序：通过文件选择导入桌宠 .exe 或其 .zip 发布包（复制到 ``CLY/pet``），
   未导入不可启用；可移除或重新导入；
2. 桌宠皮肤：正版账号锁定正版皮肤、导入按钮禁用；离线账号可导入 / 移除自定义皮肤，
   无自定义时用内置史蒂夫 / 艾利克斯；
3. 启用桌宠：启动 / 关闭桌宠子进程。正版先异步下载皮肤落盘再启动，离线直接启动。

文件对话框 / 消息框只负责取路径与提示，核心动作拆成独立方法以便离屏回归直接调用。
"""
import os
import shutil

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import pet_controller as pc
from .. import pet_features as PF
from .card_widget import Card
from .toggle_switch import ToggleSwitch
from .skin_fetch_worker import SkinFetchWorker

CUSTOM_SKIN_DIR = "custom_skins"


class PetSettingsPage(QWidget):
    """桌宠设置页（独立 APP 导入 + 皮肤口径 + 启停）。"""

    def __init__(self, config, host, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("pet-settings-page")
        self._config = config
        self._host = host

        self._pet_process = None
        self._skin_worker: SkinFetchWorker | None = None

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

        self._build_app_section()
        self._build_skin_section()
        self._build_features_section()
        self._build_toggle_section()
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

        # 进程状态轮询：桌宠被外部关闭时把按钮恢复为「启动」。
        self._proc_timer = QTimer(self)
        self._proc_timer.setInterval(500)
        self._proc_timer.timeout.connect(self._poll_process)
        self._proc_timer.start()

    # ------------------------------------------------------------------
    # 卡片 1：桌宠程序导入
    # ------------------------------------------------------------------
    def _build_app_section(self) -> None:
        card = Card("桌宠程序")
        self._app_status = QLabel()
        self._app_status.setProperty("hintLabel", True)
        self._app_status.setWordWrap(True)
        card.add_widget(self._app_status)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._import_btn = QPushButton("导入桌宠")
        self._import_btn.setProperty("ghostAction", True)
        self._import_btn.setCursor(Qt.PointingHandCursor)
        self._import_btn.clicked.connect(self._on_choose_app)
        self._remove_btn = QPushButton("移除")
        self._remove_btn.setProperty("ghostAction", True)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.clicked.connect(self._on_remove_app)
        layout.addWidget(self._import_btn)
        layout.addWidget(self._remove_btn)
        layout.addStretch(1)
        card.add_widget(row)
        self._list_layout.addWidget(card)

    def _on_choose_app(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, "选择桌宠程序", "", "桌宠程序 (*.exe *.zip)"
        )
        if not src:
            return
        self.import_app(src)

    def import_app(self, src: str) -> bool:
        """核心导入动作：复制/解压到固定路径并写 config；成功返回 True。"""
        try:
            path = pc.import_pet_app(src)
        except (OSError, ValueError, shutil.Error) as exc:
            QMessageBox.warning(self, "Cloudy Launcher", f"桌宠导入失败：{exc}")
            return False
        self._config.pet_app_path = path
        self._config.save()
        self.refresh()
        return True

    def _on_remove_app(self) -> None:
        # 先强制关闭本次记录的进程与同路径孤儿（含 onefile 子进程），再删除。
        app_path = self._config.pet_app_path
        if self._pet_process is not None:
            pc.stop_pet(self._pet_process)
            self._pet_process = None
        if app_path:
            pc.stop_all_pet_processes(app_path)
        try:
            pc.remove_pet_app()
        except OSError as exc:
            QMessageBox.warning(self, "Cloudy Launcher",
                                f"桌宠仍被占用，移除失败：{exc}")
            return
        self._config.pet_app_path = ""
        self._config.save()
        self.refresh()

    # ------------------------------------------------------------------
    # 卡片 2：皮肤口径
    # ------------------------------------------------------------------
    def _build_skin_section(self) -> None:
        card = Card("桌宠皮肤")
        self._skin_status = QLabel()
        self._skin_status.setProperty("hintLabel", True)
        self._skin_status.setWordWrap(True)
        card.add_widget(self._skin_status)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._skin_import_btn = QPushButton("导入皮肤")
        self._skin_import_btn.setProperty("ghostAction", True)
        self._skin_import_btn.setCursor(Qt.PointingHandCursor)
        self._skin_import_btn.clicked.connect(self._on_choose_skin)
        self._skin_remove_btn = QPushButton("移除皮肤")
        self._skin_remove_btn.setProperty("ghostAction", True)
        self._skin_remove_btn.setCursor(Qt.PointingHandCursor)
        self._skin_remove_btn.clicked.connect(self._on_remove_skin)
        layout.addWidget(self._skin_import_btn)
        layout.addWidget(self._skin_remove_btn)
        layout.addStretch(1)
        card.add_widget(row)
        self._list_layout.addWidget(card)

    def _custom_skin_dir(self) -> str:
        path = os.path.join(self._host_path_data(), CUSTOM_SKIN_DIR)
        os.makedirs(path, exist_ok=True)
        return path

    def _host_path_data(self) -> str:
        from ..resources import data_dir
        return data_dir()

    def _on_choose_skin(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, "选择皮肤图片", "", "皮肤图片 (*.png *.jpg *.jpeg)"
        )
        if not src:
            return
        self.import_skin(src)

    def import_skin(self, src: str) -> bool:
        """离线皮肤导入：复制到 custom_skins 并写 config.custom_skin。"""
        try:
            dst = os.path.join(self._custom_skin_dir(), os.path.basename(src))
            shutil.copyfile(src, dst)
        except OSError as exc:
            QMessageBox.warning(self, "Cloudy Launcher", f"皮肤导入失败：{exc}")
            return False
        self._config.custom_skin = dst
        self._config.save()
        self.refresh()
        return True

    def _on_remove_skin(self) -> None:
        self._config.custom_skin = ""
        self._config.save()
        self.refresh()

    # ------------------------------------------------------------------
    # 卡片 3：功能开关（一键全开/全关 + 独立滑块；仅在启动器配置，不进桌宠）
    # ------------------------------------------------------------------
    def _build_features_section(self) -> None:
        card = Card("功能开关")

        # 一键全开 / 全关。
        head = QWidget()
        hlayout = QHBoxLayout(head)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(8)
        self._all_on_btn = QPushButton("全部开启")
        self._all_off_btn = QPushButton("全部关闭")
        for btn in (self._all_on_btn, self._all_off_btn):
            btn.setProperty("ghostAction", True)
            btn.setCursor(Qt.PointingHandCursor)
        self._all_on_btn.clicked.connect(lambda: self._set_all_features(True))
        self._all_off_btn.clicked.connect(lambda: self._set_all_features(False))
        hlayout.addWidget(self._all_on_btn)
        hlayout.addWidget(self._all_off_btn)
        hlayout.addStretch(1)
        card.add_widget(head)

        # 5 个独立滑块。
        self._feature_switches = {}
        features = self._config.pet_features
        for key, label in PF.FEATURE_ITEMS:
            frow = QWidget()
            flayout = QHBoxLayout(frow)
            flayout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(label)
            switch = ToggleSwitch(features.get(key, True))
            switch.toggled.connect(
                lambda checked, k=key: self._on_feature_toggle(k, checked))
            flayout.addWidget(name)
            flayout.addStretch(1)
            flayout.addWidget(switch)
            card.add_widget(frow)
            self._feature_switches[key] = switch
        self._list_layout.addWidget(card)

    def _on_feature_toggle(self, key: str, checked: bool) -> None:
        self._config.set_pet_feature(key, checked)

    def _set_all_features(self, flag: bool) -> None:
        features = self._config.pet_features
        for key in PF.FEATURE_KEYS:
            features[key] = flag
        self._config.pet_features = features
        self._config.save()
        # 同步滑块；值相同则 setChecked 内部不发信号，避免重复写盘。
        for switch in self._feature_switches.values():
            switch.setChecked(flag)

    # ------------------------------------------------------------------
    # 卡片 4：启停
    # ------------------------------------------------------------------
    def _build_toggle_section(self) -> None:
        card = Card("启用桌宠")
        self._toggle_btn = QPushButton("启动桌宠")
        self._toggle_btn.setProperty("primaryButton", True)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        card.add_widget(self._toggle_btn)
        self._list_layout.addWidget(card)

    @property
    def is_running(self) -> bool:
        return self._pet_process is not None and self._pet_process.poll() is None

    def _on_toggle(self) -> None:
        if self.is_running:
            self.stop_pet()
        else:
            self.start_pet()

    def start_pet(self) -> None:
        """启动桌宠；正版先异步下载皮肤，离线直接解析本地皮肤。"""
        app_path = self._config.pet_app_path
        if not app_path or not os.path.isfile(app_path):
            QMessageBox.information(self, "Cloudy Launcher", "请先导入桌宠程序。")
            return
        session = getattr(self._host, "session", None)
        if session is not None and session.is_microsoft:
            self._fetch_official_then_launch(app_path)
        else:
            skin, slim = pc.offline_skin_path(self._config)
            self._do_launch(app_path, skin, slim)

    def _fetch_official_then_launch(self, app_path: str) -> None:
        url = self._host.session.skin_url
        if not url:
            # 无皮肤地址：回退内置皮肤启动，不阻断桌宠使用。
            skin, slim = pc.offline_skin_path(self._config)
            self._do_launch(app_path, skin, slim)
            return
        self._app_path_pending = app_path
        self._skin_worker = SkinFetchWorker(url, self._host.session.slim, self)
        self._skin_worker.succeeded.connect(self._on_official_skin)
        self._skin_worker.failed.connect(self._on_official_failed)
        self._skin_worker.start()

    def _on_official_skin(self, image, slim: bool) -> None:
        try:
            skin = pc.save_official_skin(image)
        except OSError as exc:
            QMessageBox.warning(self, "Cloudy Launcher", f"正版皮肤缓存失败：{exc}")
            return
        self._do_launch(self._app_path_pending, skin, slim)

    def _on_official_failed(self, message: str) -> None:
        # 下载失败不阻断：回退内置皮肤启动，并提示原因。
        QMessageBox.information(self, "Cloudy Launcher",
                                f"{message}\n已使用内置皮肤启动桌宠。")
        skin, slim = pc.offline_skin_path(self._config)
        self._do_launch(self._app_path_pending, skin, slim)

    def _do_launch(self, app_path: str, skin_path: str, slim: bool) -> None:
        # 单实例：先终止本次记录的进程与同路径的历史孤儿，再启动，避免重复堆叠。
        if self._pet_process is not None:
            pc.stop_pet(self._pet_process)
            self._pet_process = None
        pc.stop_all_pet_processes(app_path)
        try:
            self._pet_process = pc.launch_pet(
                app_path, skin_path, slim,
                self._config.pet_window_x, self._config.pet_window_y,
                self._config.pet_features,
            )
        except OSError as exc:
            QMessageBox.warning(self, "Cloudy Launcher", f"桌宠启动失败：{exc}")
            return
        self.refresh()

    def stop_pet(self) -> None:
        app_path = self._config.pet_app_path
        if self._pet_process is not None:
            pc.stop_pet(self._pet_process)
            self._pet_process = None
        # 兜底：按 exe 路径清理历史孤儿（含 onefile 残留子进程）。
        if app_path:
            pc.stop_all_pet_processes(app_path)
        self.refresh()

    def _poll_process(self) -> None:
        if self._pet_process is not None and self._pet_process.poll() is not None:
            self._pet_process = None
            self.refresh()

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        app_path = self._config.pet_app_path
        if app_path and os.path.isfile(app_path):
            self._app_status.setText("已导入：" + os.path.basename(app_path))
            self._remove_btn.setEnabled(True)
        else:
            self._app_status.setText("尚未导入桌宠程序，请先导入后再启用。")
            self._remove_btn.setEnabled(False)

        session = getattr(self._host, "session", None)
        is_official = session is not None and session.is_microsoft
        if is_official:
            self._skin_status.setText("正版账号使用正版皮肤，不可导入皮肤。")
            self._skin_import_btn.setEnabled(False)
            self._skin_remove_btn.setEnabled(False)
        else:
            custom = self._config.custom_skin
            if custom and os.path.isfile(custom):
                self._skin_status.setText("自定义皮肤：" + os.path.basename(custom))
                self._skin_remove_btn.setEnabled(True)
            else:
                self._skin_status.setText("使用内置皮肤，可导入本地皮肤图片。")
                self._skin_remove_btn.setEnabled(False)
            self._skin_import_btn.setEnabled(True)

        if self.is_running:
            self._toggle_btn.setText("关闭桌宠")
            self._toggle_btn.setEnabled(True)
        else:
            self._toggle_btn.setText("启动桌宠")
            self._toggle_btn.setEnabled(bool(app_path and os.path.isfile(app_path)))

    def shutdown(self) -> None:
        """启动器退出：停止本次桌宠进程（整树）并等待皮肤线程收尾。"""
        self._proc_timer.stop()
        if self._skin_worker is not None and self._skin_worker.isRunning():
            self._skin_worker.wait(2000)
        app_path = self._config.pet_app_path
        if self._pet_process is not None:
            pc.stop_pet(self._pet_process)
            self._pet_process = None
        if app_path:
            pc.stop_all_pet_processes(app_path)
