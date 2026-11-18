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

"""v1.3.22.0 整合包导出后台线程。

跑 :func:`cloud_launcher.modpack_export.export_instance` 全流程，阶段、进度、成功、
失败分别以 Qt 信号转发到主线程；跨线程信号走队列连接，安全。范式与本地导入
``LocalModpackInstallWorker`` 一致，便于复用同一套进度卡片。
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..modpack_export import export_instance
from ..modpack_install import ModpackError


class ExportPackWorker(QThread):
    """把已安装实例按所选格式打包成整合包压缩包；信号回传阶段与进度。"""

    phaseChanged = Signal(int, str)
    #: (总进度%, 已写字节, 总字节, 速度B/s, 剩余文件数)。
    progress = Signal(float, int, int, float, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, alias: str, fmt: str, output_path: str, parent=None) -> None:
        super().__init__(parent)
        self._alias = alias
        self._fmt = fmt
        self._output_path = output_path

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = export_instance(
                self._alias,
                self._fmt,
                self._output_path,
                should_cancel=self.isInterruptionRequested,
                on_phase=lambda index, label: self.phaseChanged.emit(index, label),
                on_progress=lambda pct, done, total, speed, remaining: (
                    self.progress.emit(pct, done, total, speed, remaining)),
            )
        except ModpackError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except InterruptedError:
            return
        except Exception as exc:  # noqa: BLE001 兜底，避免线程静默退出
            if not self.isInterruptionRequested():
                self.failed.emit(f"打包失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)
