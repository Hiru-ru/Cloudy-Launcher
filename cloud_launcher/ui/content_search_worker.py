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

"""v1.3.4.0 内容搜索后台线程：子线程执行搜索与图标下载，信号回主线程刷新结果。

网络请求与图标落盘全部在 QThread 内完成，避免阻塞主窗口；中断通过
``requestInterruption`` 取消，``InterruptedError`` 静默退出。
"""
from PySide6.QtCore import QThread, Signal

from ..content_search import DEFAULT_LIMIT, search_content


class ContentSearchWorker(QThread):
    """单次搜索任务：成功回传 ``{items,total_hits,saved_to}``，失败回传中文原因。"""

    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, kind: str, query: str = "",
                 limit: int = DEFAULT_LIMIT, offset: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._query = query
        self._limit = limit
        self._offset = offset

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = search_content(
                self._kind,
                query=self._query,
                limit=self._limit,
                offset=self._offset,
                should_cancel=self.isInterruptionRequested,
                on_progress=lambda done, total: self.progress.emit(done, total),
            )
        except InterruptedError:
            return
        except Exception as exc:  # 网络 / 超时 / 解析统一兜底，界面显示失败提示
            self.failed.emit(f"搜索失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)
