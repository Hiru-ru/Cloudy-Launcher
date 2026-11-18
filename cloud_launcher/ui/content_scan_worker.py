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

"""版本内容扫描后台线程：把 jar / zip 元数据读取移出主线程。

v1.3.12.0 新增。点击概览四个计数按钮时启动，扫描完成后回传条目列表（含图标字节），
避免在主线程逐个解 jar 造成界面卡顿。
"""
from PySide6.QtCore import QThread, Signal

from .. import version_content


class ContentScanWorker(QThread):
    """扫描某版本某分类的条目，结果回主线程填充展开列表。"""

    #: 扫描完成：回传 entry 列表。
    succeeded = Signal(object)
    #: 扫描失败：回传中文原因。
    failed = Signal(str)

    def __init__(self, alias: str, kind: str, parent=None) -> None:
        super().__init__(parent)
        self._alias = str(alias or "")
        self._kind = str(kind or "")

    def run(self) -> None:
        if self.isInterruptionRequested() or not self._alias:
            return
        try:
            entries = version_content.scan_content(
                self._alias, self._kind,
                should_cancel=self.isInterruptionRequested,
            )
        except InterruptedError:
            return
        except Exception as exc:  # 兜底，界面静默提示
            self.failed.emit("读取内容失败：%s" % type(exc).__name__)
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(entries)
