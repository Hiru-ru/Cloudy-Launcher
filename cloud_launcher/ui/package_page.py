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

"""v1.3.22.0 整合包打包（导出）页。

按手绘线框三段式自上而下：

1. 选择要导出的已安装版本（下拉复用实例扫描结果）；
2. 选择打包格式（离线完整包 / Modrinth / MultiMC-Prism / CurseForge / MCBBS）；
3. 开始打包：弹保存对话框，后台 :class:`~cloud_launcher.ui.export_worker.ExportPackWorker`
   跑 :func:`~cloud_launcher.modpack_export.export_instance`，统一进度卡片回传阶段与进度。

纯 PySide6 + 标准库；导出只读本地实例，不修改任何本地文件。
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from .. import game_dirs
from .. import modpack_export as mpe
from .. import modpack_format as mpf
from .card_widget import Card
from .export_worker import ExportPackWorker
from .launch_settings_page import _GlassComboBox
from .spring_button import SpringPushButton
from .task_progress_dialog import TaskProgressDialog

# 各格式在选择后展示的简短说明。
_FORMAT_HINTS = {
    mpf.FORMAT_OFFLINE: "把模组、配置、资源包、光影等完整打成压缩包，不联网，可在任意启动器解压使用。",
    mpf.FORMAT_MODRINTH: "生成标准 .mrpack；联网按文件哈希匹配 Modrinth 模组，未收录的随覆盖文件带出。",
    mpf.FORMAT_MULTIMC: "生成 MultiMC / Prism 实例压缩包，内含实例清单与游戏文件，可直接导入。",
    mpf.FORMAT_CURSEFORGE: "生成 CurseForge 风格压缩包；本地无法回溯模组平台 ID，模组随 overrides 打包带出。",
    mpf.FORMAT_MCBBS: "生成 MCBBS 风格压缩包；本地无法回溯模组 ID，模组随 overrides 打包带出。",
}

_GENERAL_HINT = "存档（saves）、日志与运行缓存不会打包；导出过程不会修改本地实例。"


def _default_dir() -> str:
    """默认保存目录：桌面，不存在时退回用户主目录。"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    return desktop if os.path.isdir(desktop) else os.path.expanduser("~")


def _format_size(num_bytes: int) -> str:
    if num_bytes >= 1024.0 * 1024.0:
        return "%.2f MB" % (num_bytes / (1024.0 * 1024.0))
    if num_bytes >= 1024.0:
        return "%.1f KB" % (num_bytes / 1024.0)
    return "%d B" % int(num_bytes)


class PackagePage(QWidget):
    """整合包打包页：选版本 → 选格式 → 开始打包。"""

    def __init__(self, host, parent=None) -> None:
        super().__init__(parent)
        self._host = host
        self._worker: ExportPackWorker | None = None
        self._progress_dialog: TaskProgressDialog | None = None
        self._entries: list[dict] = []

        self.setObjectName("package-page")

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

        self._build_version_card()
        self._build_format_card()
        self._build_action_card()
        self._list_layout.addStretch(1)

        scroll.setWidget(list_widget)
        outer.addWidget(scroll)

        self.refresh_versions()

    # ------------------------------------------------------------------ #
    # 卡片构建
    # ------------------------------------------------------------------ #
    def _build_version_card(self) -> None:
        card = Card("选择版本")
        caption = QLabel("要导出的已安装版本")
        caption.setProperty("fieldLabel", True)
        card.add_widget(caption)

        self._version_combo = _GlassComboBox()
        self._version_combo.setProperty("versionPicker", True)
        card.add_widget(self._version_combo)

        self._version_hint = QLabel("")
        self._version_hint.setProperty("sectionHint", True)
        self._version_hint.setWordWrap(True)
        card.add_widget(self._version_hint)
        self._list_layout.addWidget(card)

    def _build_format_card(self) -> None:
        card = Card("打包的格式")
        caption = QLabel("导出为哪种整合包格式")
        caption.setProperty("fieldLabel", True)
        card.add_widget(caption)

        self._format_combo = _GlassComboBox()
        self._format_combo.setProperty("versionPicker", True)
        for fmt, label in mpe.EXPORT_FORMAT_LABELS.items():
            self._format_combo.addItem(label, fmt)
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)
        card.add_widget(self._format_combo)

        self._format_hint = QLabel("")
        self._format_hint.setProperty("sectionHint", True)
        self._format_hint.setWordWrap(True)
        card.add_widget(self._format_hint)
        self._list_layout.addWidget(card)

    def _build_action_card(self) -> None:
        card = Card("开始打包")
        row = QHBoxLayout()
        row.setSpacing(12)
        self._export_btn = SpringPushButton("开始打包")
        self._export_btn.setProperty("primaryButton", True)
        self._export_btn.setFixedHeight(44)
        self._export_btn.setMinimumWidth(160)
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.clicked.connect(self._on_export_clicked)
        row.addWidget(self._export_btn)
        row.addStretch(1)
        card.add_layout(row)

        general = QLabel(_GENERAL_HINT)
        general.setProperty("sectionHint", True)
        general.setWordWrap(True)
        card.add_widget(general)
        self._list_layout.addWidget(card)

    # ------------------------------------------------------------------ #
    # 数据回填
    # ------------------------------------------------------------------ #
    def refresh_versions(self) -> None:
        """重扫已安装实例并回填版本下拉；无实例时禁用打包按钮。"""
        self._entries = game_dirs.scan_installed_entries()
        self._version_combo.blockSignals(True)
        self._version_combo.clear()
        for entry in self._entries:
            alias = entry["alias"]
            mc = entry.get("mc_version") or ""
            loader_label = C.LOADER_LABELS.get(entry.get("loader") or "", "")
            text = alias if not mc else f"{alias}（{mc} · {loader_label}）"
            self._version_combo.addItem(text, alias)
        self._version_combo.blockSignals(False)

        if self._entries:
            self._version_hint.setText("共 %d 个已安装版本可选。" % len(self._entries))
            self._export_btn.setEnabled(True)
        else:
            self._version_hint.setText("当前没有已安装版本，请先在「启动」页安装一个版本。")
            self._export_btn.setEnabled(False)

        self._on_format_changed()

    def _current_alias(self) -> str:
        alias = self._version_combo.currentData()
        return str(alias or "").strip()

    def _current_format(self) -> str:
        fmt = self._format_combo.currentData()
        return str(fmt or "").strip()

    def _on_format_changed(self) -> None:
        fmt = self._current_format()
        self._format_hint.setText(_FORMAT_HINTS.get(fmt, ""))

    # ------------------------------------------------------------------ #
    # 打包流程
    # ------------------------------------------------------------------ #
    def _on_export_clicked(self) -> None:
        alias = self._current_alias()
        fmt = self._current_format()
        if not alias:
            QMessageBox.information(self._host, C.APP_FULL_NAME, "请先选择要导出的版本。")
            return
        if fmt not in mpe.EXPORT_FORMAT_LABELS:
            QMessageBox.information(self._host, C.APP_FULL_NAME, "请先选择打包格式。")
            return

        ext = mpe.EXPORT_EXTENSIONS[fmt]
        default_name = game_dirs.sanitize_version_id(alias) + ext
        filter_text = {
            mpf.FORMAT_MODRINTH: "Modrinth 整合包 (*.mrpack)",
            mpf.FORMAT_OFFLINE: "离线完整包 (*.zip)",
            mpf.FORMAT_MULTIMC: "MultiMC / Prism 整合包 (*.zip)",
            mpf.FORMAT_CURSEFORGE: "CurseForge 整合包 (*.zip)",
            mpf.FORMAT_MCBBS: "MCBBS 整合包 (*.zip)",
        }.get(fmt, "整合包 (*.zip *.mrpack)")
        output_path, _ = QFileDialog.getSaveFileName(
            self._host, "保存整合包",
            os.path.join(_default_dir(), default_name), filter_text)
        if not output_path:
            return
        if not output_path.lower().endswith(ext):
            output_path += ext

        worker = ExportPackWorker(alias, fmt, output_path, self._host)
        worker.phaseChanged.connect(self._on_phase)
        worker.progress.connect(self._on_progress)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self._on_failed)
        self._worker = worker

        dialog = TaskProgressDialog(
            "%s 打包中" % alias, list(mpe.PHASE_LABELS.values()), self._host)
        self._progress_dialog = dialog
        dialog.cancelRequested.connect(worker.requestInterruption)
        worker.start()
        dialog.exec()

        self._progress_dialog = None
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(3000)
        self._worker = None

    def _on_phase(self, index: int, label: str) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.mark_phase_running(index)

    def _on_progress(self, percent: float, done: int,
                     total: int, speed: float, remaining: int) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.set_progress(
                float(percent), float(speed), int(remaining))

    def _on_succeeded(self, result) -> None:
        self._worker = None
        dialog = self._progress_dialog
        if dialog is not None:
            dialog.finish_success()
            dialog.hide_cancel()
            dialog.accept()

        lines = [
            "打包完成：%s" % os.path.basename(result.output_path),
            "共 %d 个文件，%s。" % (result.file_count, _format_size(result.size_bytes)),
        ]
        if result.mapped_mods:
            lines.append("已匹配 Modrinth 模组 %d 个。" % result.mapped_mods)
        lines.extend(result.notes)
        QMessageBox.information(self._host, C.APP_FULL_NAME, "\n".join(lines))

    def _on_failed(self, reason: str) -> None:
        self._worker = None
        dialog = self._progress_dialog
        if dialog is not None:
            dialog.reject()
        QMessageBox.warning(self._host, C.APP_FULL_NAME, str(reason))
