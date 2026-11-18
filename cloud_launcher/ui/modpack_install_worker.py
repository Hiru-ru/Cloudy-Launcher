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

"""v1.3.11.0 整合包安装后台线程。

两个线程，分别对应整合包安装链路的两段网络操作：

- :class:`ModpackVersionListWorker`：点卡片下载后，先拉取该整合包的 ``.mrpack`` 版本
  列表，供弹窗让用户选版本；
- :class:`ModpackInstallWorker`：用户选好版本、命名确认后，跑
  :func:`cloud_launcher.modpack_install.install_modpack` 全流程，实时回传阶段与进度。

进度回调由安装模块内部的采样线程触发，这里以 Qt 信号转发到主线程；跨线程发信号在
Qt 里走队列连接，安全。
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .. import modpack_format as mpf
from ..modpack_install import (
    ModpackError,
    fetch_modpack_versions,
    install_local_pack,
    install_modpack,
)


class ModpackVersionListWorker(QThread):
    """拉取整合包版本列表；成功发 list，失败发中文错误。"""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, project_id: str, parent=None) -> None:
        super().__init__(parent)
        self._project_id = project_id

    def run(self) -> None:
        try:
            versions = fetch_modpack_versions(
                self._project_id, self.isInterruptionRequested)
        except ModpackError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 兜底，避免线程静默退出
            if not self.isInterruptionRequested():
                self.failed.emit(f"查询整合包版本失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(versions)


class ModpackInstallWorker(QThread):
    """跑整合包安装；阶段、进度、成功、失败分别以信号回传。"""

    phaseChanged = Signal(int, str)
    #: (总进度%, 已下载字节, 总字节, 速度B/s, 剩余文件数)。
    progress = Signal(float, int, int, float, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, chosen: dict, alias: str, parent=None) -> None:
        super().__init__(parent)
        self._chosen = chosen
        self._alias = alias

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = install_modpack(
                self._chosen,
                self._alias,
                should_cancel=self.isInterruptionRequested,
                on_phase=lambda index, label: self.phaseChanged.emit(index, label),
                on_progress=lambda pct, done, total, speed, remaining: (
                    self.progress.emit(pct, done, total, speed, remaining)),
            )
        except ModpackError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 兜底
            if not self.isInterruptionRequested():
                self.failed.emit(f"安装失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)


class LocalModpackInstallWorker(QThread):
    """本地整合包（全局拖拽）安装线程；阶段、进度、成功、失败信号与在线 worker 一致。"""

    phaseChanged = Signal(int, str)
    #: (总进度%, 已下载字节, 总字节, 速度B/s, 剩余文件数)。
    progress = Signal(float, int, int, float, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, path: str, alias: str, parent=None) -> None:
        super().__init__(parent)
        self._path = path
        self._alias = alias

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = install_local_pack(
                self._path,
                self._alias,
                should_cancel=self.isInterruptionRequested,
                on_phase=lambda index, label: self.phaseChanged.emit(index, label),
                on_progress=lambda pct, done, total, speed, remaining: (
                    self.progress.emit(pct, done, total, speed, remaining)),
            )
        except ModpackError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 兜底
            if not self.isInterruptionRequested():
                self.failed.emit(f"安装失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)


class LocalModpackPlanWorker(QThread):
    """本地整合包解析线程：探测格式并构建统一计划，避免在主线程做联网/解压。"""

    succeeded = Signal(str, object)  # (文件路径, ModpackPlan)
    failed = Signal(str)

    def __init__(self, path: str, parent=None) -> None:
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            fmt = mpf.detect_format(self._path)
            plan = mpf.build_plan(
                self._path, fmt, should_cancel=self.isInterruptionRequested)
        except mpf.ModpackFormatError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 兜底
            if not self.isInterruptionRequested():
                self.failed.emit(f"解析整合包失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(self._path, plan)
