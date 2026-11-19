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

"""游戏启动后台线程：在独立线程完成 Java 探测、命令组装、进程拉起，并持续监控直到
Minecraft 窗口真正出现。

进度条不再是摆设：每个阶段通过 phase 信号回传真实百分比与文案；进程拉起后不立即报成功，
而是等待游戏窗口实际可见才置 100%。进程若提前退出则读取启动日志并如实上报，绝不伪造成功。
"""
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

from PySide6.QtCore import QThread, Signal

from .. import constants as C
from .. import download_engine
from .. import game_dirs
from .. import java_runtime
from .. import natives_bootstrap

# 等待游戏窗口出现的最大秒数；超时但进程仍存活则保守判定为已启动。
WINDOW_WAIT_SECONDS = 40.0
# 等待窗口期间，进度从 75% 推进到 95% 所对应的预计秒数。
PROGRESS_FULL_SECONDS = 20.0
# 失败时回传的日志尾部最大字符数。
LOG_TAIL_CHARS = 1500


def _minecraft_window_handles() -> set:
    """返回当前可见、标题以 Minecraft 开头（且非 RenderPearl 辅助窗口）的顶层窗口句柄集合。"""
    user32 = ctypes.windll.user32
    handles = set()
    proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            lowered = title.lower()
            if title and lowered.startswith("minecraft") and "renderpearl" not in lowered:
                handles.add(int(hwnd))
        return True

    user32.EnumWindows(proc_type(callback), 0)
    return handles


def _find_game_window(exclude: set | None = None) -> list:
    """返回标题以 Minecraft 开头的可见窗口标题列表，可排除启动前就已存在的窗口。

    启动前已经存在的 Minecraft 窗口（例如上一个会话没关掉）不能算本次启动成功，否则
    用户点开始游戏会秒判成功、但实际进程可能已经崩了。
    """
    user32 = ctypes.windll.user32
    found = []
    proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    skip = exclude or set()

    def callback(hwnd, _lparam):
        if int(hwnd) in skip:
            return True
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            lowered = title.lower()
            if (
                title
                and lowered.startswith("minecraft")
                and "renderpearl" not in lowered
            ):
                found.append(title)
        return True

    user32.EnumWindows(proc_type(callback), 0)
    return found


class LaunchWorker(QThread):
    """后台执行完整启动链路，phase 回传真实阶段，succeeded/failed 给出最终结论。"""

    phase = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, alias, session, config, parent=None,
                 preset_java_path: str = "") -> None:
        super().__init__(parent)
        self._alias = alias
        self._session = session
        self._config = config
        # 主线程已完成 Java 选择 / 下载时直接传入，跳过线程内重复探测。
        self._preset_java_path = str(preset_java_path or "")

    def run(self) -> None:
        self.phase.emit(10, "正在准备游戏环境…")
        profile_path = game_dirs.version_json_path(self._alias)
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except Exception:
            self.failed.emit("该版本文件损坏，请重新下载该版本。")
            return

        # 客户端 Jar 是主类所在 jar，缺失时 JVM 必然报找不到主类，先给出明确原因。
        if not game_dirs.find_client_jar(self._alias):
            self.failed.emit(
                "该版本目录内找不到客户端 jar（client.jar 或 <版本号>.jar）。\n"
                "请用本启动器重新下载该版本，或确认版本目录未被外部工具改坏。"
            )
            return

        self.phase.emit(30, "正在检测 Java 环境…")
        if self._preset_java_path:
            probe = java_runtime._probe_java_executable(self._preset_java_path)
            if not probe:
                self.failed.emit(
                    "选定的 Java 已失效，请重新选择或重新下载对应版本。"
                )
                return
            java = {
                "path": probe["path"],
                "version": probe["version"],
                "major": java_runtime.java_major_version(probe["version"]),
            }
        else:
            # v1.4.5.1：按 profile 所需主版本精确匹配，不再简单取列表第一个（避免老版本
            # 误用 Java 25）。正常情况下主线程已处理缺失下载，这里走到 missing 属异常兜底。
            selection = java_runtime.select_java(profile, self._config.java_path)
            if selection.get("status") != "ready":
                self.failed.emit(C.JAVA_MISSING_MESSAGE)
                return
            java = selection

        # v1.3.2.0：natives 目录为空 / 缺失时，从 natives-windows Jar 自动解压原生库；
        # 本地缺失的 Jar 先下载到全局 libraries。已有原生库则跳过，不重复解压。
        self.phase.emit(45, "正在准备原生库…")
        try:
            natives_result = natives_bootstrap.ensure_natives(profile, self._alias)
        except Exception as exc:
            self.failed.emit(f"原生库准备失败：{exc}")
            return
        if natives_result["status"] == "failed":
            self.failed.emit(natives_result["message"])
            return

        self.phase.emit(55, "正在组装启动参数…")
        try:
            command = java_runtime.build_launch_command(
                profile, self._alias, self._session, self._config, java["path"]
            )
        except Exception as exc:
            self.failed.emit(f"启动参数组装失败：{exc}")
            return

        self.phase.emit(70, "正在拉起游戏进程…")
        log_path = game_dirs.launch_log_path(self._alias)
        cwd = java_runtime.resolve_game_dir(self._alias, self._config)
        # 启动前先记下已存在的 Minecraft 窗口，之后只认新出现的窗口，避免误判成功。
        baseline_windows = _minecraft_window_handles()
        log_file = None
        try:
            # v1.3.1.8：按二进制落盘，Java 在中文 Windows 上输出 GBK 字节，
            # 用文本模式按 UTF-8 写会把日志写坏（弹窗里成一串乱码）。
            log_file = open(log_path, "wb")
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            if log_file is not None:
                log_file.close()
            self.failed.emit(f"游戏进程启动失败：{exc}")
            return

        self.phase.emit(75, "正在加载游戏资源，窗口即将出现…")
        start = time.time()
        last_percent = 75
        while True:
            rc = process.poll()
            if rc is not None:
                log_file.flush()
                log_file.close()
                tail = self._read_tail(log_path)
                self.failed.emit(
                    f"游戏启动后异常退出（退出码 {rc}）。\n"
                    f"日志已保存到：{log_path}\n{tail}"
                )
                return

            if _find_game_window(exclude=baseline_windows):
                log_file.close()
                self.phase.emit(100, "游戏已启动")
                self.succeeded.emit(process)
                return

            elapsed = time.time() - start
            if elapsed >= WINDOW_WAIT_SECONDS:
                # 超时但进程仍存活，保守判定成功，避免无限等待。
                log_file.close()
                self.phase.emit(100, "游戏进程已启动")
                self.succeeded.emit(process)
                return

            percent = 75 + int(min(1.0, elapsed / PROGRESS_FULL_SECONDS) * 20)
            if percent != last_percent:
                self.phase.emit(percent, "正在加载游戏资源，窗口即将出现…")
                last_percent = percent
            self.msleep(300)

    @staticmethod
    def _read_tail(log_path: str) -> str:
        """读取启动日志尾部；Java 输出在中文 Windows 上是 GBK，先按 UTF-8 再按 GBK 解码。"""
        try:
            with open(log_path, "rb") as f:
                raw = f.read()
        except Exception:
            return ""
        text = ""
        for encoding in ("utf-8", "gbk", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if len(text) > LOG_TAIL_CHARS:
            return "…" + text[-LOG_TAIL_CHARS:]
        return text


class JavaDownloadWorker(QThread):
    """后台下载并安装指定主版本的 Java：下载阶段回传字节百分比，解压阶段单独提示。

    下载在内部子线程执行，本线程轮询 ``ProgressTracker`` 快照推进度，避免界面看不到进度。
    """

    progress = Signal(int, str)
    phase = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, major, parent=None) -> None:
        super().__init__(parent)
        self._major = int(major)
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True
        self.requestInterruption()

    def _cancel_check(self) -> bool:
        return self._cancel or self.isInterruptionRequested()

    def run(self) -> None:
        import threading

        from .. import java_download

        tracker = download_engine.ProgressTracker(total_files=1)
        box: dict = {}

        def do_download() -> None:
            try:
                box["zip"] = java_download.download_zip(
                    self._major, tracker, self._cancel_check
                )
            except InterruptedError:
                box["canceled"] = True
            except Exception as exc:  # noqa: BLE001 - 统一回传，线程内不抛
                box["download_error"] = exc

        thread = threading.Thread(target=do_download)
        thread.start()
        last_pct = -1
        while thread.is_alive():
            snapshot = tracker.snapshot()
            total = snapshot.total_bytes
            done = snapshot.done_bytes
            if total > 0:
                pct = max(0, min(99, int(done * 100 / total)))
                if pct != last_pct:
                    self.progress.emit(
                        pct, C.JAVA_DOWNLOADING_TEXT.format(major=self._major)
                    )
                    last_pct = pct
            self.msleep(200)
        thread.join()

        if box.get("canceled"):
            self.failed.emit("已取消")
            return
        if "download_error" in box:
            self.failed.emit(str(box["download_error"]))
            return

        self.phase.emit(C.JAVA_EXTRACTING_TEXT.format(major=self._major))
        try:
            java_path = java_download.extract_zip(
                self._major, box["zip"], self._cancel_check
            )
        except InterruptedError:
            self.failed.emit("已取消")
            return
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(java_path)
