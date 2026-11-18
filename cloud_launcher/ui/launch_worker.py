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

    def __init__(self, alias, session, config, parent=None) -> None:
        super().__init__(parent)
        self._alias = alias
        self._session = session
        self._config = config

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
        java = java_runtime.resolve_java(self._config.java_path)
        if not java.get("ok"):
            self.failed.emit(C.JAVA_MISSING_MESSAGE)
            return

        # v1.3.1.8：版本 JSON 声明 javaVersion.majorVersion 时，先按主版本比对，
        # 版本过低直接给明确提示，别让 JVM 抛一行类版本错误或类找不到的误导信息。
        required_major = java_runtime.required_java_major(profile)
        current_major = java_runtime.java_major_version(str(java.get("version") or ""))
        if required_major and current_major and current_major < required_major:
            self.failed.emit(
                C.JAVA_VERSION_LOW_MESSAGE.format(
                    required=required_major, current=current_major, path=java.get("path", "")
                )
            )
            return

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
