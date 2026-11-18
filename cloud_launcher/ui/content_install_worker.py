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

"""v1.3.6.0 内容下载后台线程：解析目标文件并真实下载到版本隔离目录。

网络请求与落盘全部在 QThread 内完成，避免阻塞主窗口；中断通过
``requestInterruption`` 取消，``ContentInstallError`` 统一翻译成中文提示回主线程。
"""
from PySide6.QtCore import QThread, Signal

from ..content_install import (
    ContentFileExists,
    ContentInstallError,
    download_content,
)


class ContentInstallWorker(QThread):
    """单次内容下载：成功回传 ``{path,filename,version_number,size,dir}``。"""

    succeeded = Signal(object)
    failed = Signal(str)
    #: 已解析出目标文件（界面可提前显示文件名 / 版本号）。
    resolved = Signal(object)
    #: (已下载字节, 总字节)，总字节未知时为 0。
    progress = Signal(int, int)
    #: (第几次, 总次数)：线路不稳自动重试，界面提示用。
    retrying = Signal(int, int)
    #: 目标目录已有同名文件（界面弹框征询覆盖）。
    target_exists = Signal(str)

    def __init__(self, project_id: str, kind: str, alias: str, mc_version: str,
                 loader: str, overwrite: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._project_id = project_id
        self._kind = kind
        self._alias = alias
        self._mc_version = mc_version
        self._loader = loader
        self._overwrite = overwrite

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = download_content(
                self._project_id,
                self._kind,
                self._alias,
                self._mc_version,
                self._loader,
                overwrite=self._overwrite,
                should_cancel=self.isInterruptionRequested,
                on_progress=lambda done, total: self.progress.emit(done, total),
                on_retry=lambda n, total: self.retrying.emit(n, total),
                version_callback=lambda info: self.resolved.emit(info),
            )
        except ContentFileExists as exc:
            self.target_exists.emit(exc.path)
            return
        except ContentInstallError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 网络 / 磁盘异常统一兜底
            if not self.isInterruptionRequested():
                self.failed.emit(f"下载失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)
