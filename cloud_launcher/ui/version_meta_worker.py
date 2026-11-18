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

"""下载页版本元数据后台线程：两类独立 QThread，信号回主线程更新分组。

- ``VersionMetaWorker``：启动加载全量清单。先读本地 ``yd/`` 缓存，有缓存直接回传（不联网、
  不刷新列表）；无缓存 / 缓存损坏才走国内镜像 → 官方轮询联网拉取，成功后由主线程落盘缓存。
- ``VersionCheckWorker``：已有缓存渲染完成后的后台轻量检查，只联网比对最新正式 / 预览版号；
  发现差异由主线程弹淡入淡出提示窗并静默覆盖缓存，当前界面列表保持不重建。

纯标准库网络请求在子线程完成；主线程接收「最新两行 + 四个全量分组列表」字典，离线 / 失败时
界面保持既有占位态，不弹窗、不阻塞主窗口。
"""
from PySide6.QtCore import QThread, Signal

from ..version_meta import (
    fetch_manifest_groups,
    load_cached_manifest,
)


class VersionMetaWorker(QThread):
    """启动全量加载：缓存优先，缺缓存才联网；成功回传 ``{"manifest", "source"}``。"""

    succeeded = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        cached = load_cached_manifest()
        if cached is not None:
            # 本地缓存命中：不重新联网拉全量，直接把缓存清单交回主线程渲染。
            if not self.isInterruptionRequested():
                self.succeeded.emit({"manifest": cached, "source": "cache"})
            return

        try:
            manifest = fetch_manifest_groups(should_cancel=self.isInterruptionRequested)
        except InterruptedError:
            return
        except Exception as exc:  # 网络 / 超时 / JSON 解析统一兜底，界面静默回退
            self.failed.emit(f"版本信息拉取失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit({"manifest": manifest, "source": "network"})


class VersionCheckWorker(QThread):
    """后台轻量检查：仅拉取最新清单供主线程比对 latest 正式 / 预览版号。"""

    succeeded = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            manifest = fetch_manifest_groups(should_cancel=self.isInterruptionRequested)
        except InterruptedError:
            return
        except Exception as exc:  # 断连静默：本次不提示、不打扰用户
            self.failed.emit(f"版本更新检查失败：{exc}")
            return
        if self.isInterruptionRequested():
            return
        self.succeeded.emit(manifest)
