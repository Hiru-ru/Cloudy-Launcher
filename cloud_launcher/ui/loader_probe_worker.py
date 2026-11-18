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

"""加载器支持性探测后台线程：进入版本详情页后在子线程扫描四个加载器兼容性。

v1.2.12.0 新增。探测逻辑与 ``yd/loader_support_cache.json`` 缓存读写封装在
:mod:`cloud_launcher.loaders`；本线程只负责把阻塞联网探测移出主线程，避免详情界面卡顿。
缓存命中时线程几乎瞬时返回；缺哪个加载器键才重新联网补探并写回缓存。
"""
from PySide6.QtCore import QThread, Signal

from .. import loaders


class LoaderProbeWorker(QThread):
    """按 MC 版本探测 Forge / NeoForge / Fabric / OptiFine 支持性，结果回主线程回填卡片。"""

    #: 探测完成：回传 ``{loader_key: {"available", "version", "detail", "label"}}``。
    succeeded = Signal(object)
    #: 探测整体失败（网络异常兜底后结果仍按不可用返回，一般不会走到 failed）。
    failed = Signal(str)

    def __init__(self, mc_version: str, parent=None) -> None:
        super().__init__(parent)
        self._mc_version = str(mc_version or "").strip()

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = loaders.probe_all(
                self._mc_version, should_cancel=self.isInterruptionRequested
            )
        except InterruptedError:
            return
        except Exception as exc:  # 网络 / 解析异常静默兜底，界面按不可用渲染
            self.failed.emit(f"加载器支持性探测失败：{type(exc).__name__}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(result)
