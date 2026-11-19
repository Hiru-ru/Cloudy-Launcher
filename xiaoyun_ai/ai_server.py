# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Xiaoyun AI / 小云 AI
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

"""llama-server 进程管理：启动、就绪检测与整树关闭。

模型在 server 启动时加载一次并常驻内存，后续翻译通过 HTTP 复用，避免每条都重新
加载 1GB 模型。启动参数固定带 ``--no-jinja`` 以绕过 R1 思考链，配合 completion
接口的停止序列拿到单条干净译文。
"""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import ai_constants as C


def pick_free_port() -> int:
    """让系统分配一个当前空闲的本地端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerError(RuntimeError):
    """llama-server 启动或就绪失败。"""


class LlamaServer:
    """llama-server 子进程的生命周期封装。"""

    def __init__(self, server_exe: str, model_path: str,
                 threads: int = C.DEFAULT_THREADS,
                 ctx: int = C.DEFAULT_CTX,
                 n_parallel: int = 1):
        self.server_exe = server_exe
        self.model_path = model_path
        self.threads = threads
        self.n_parallel = max(1, int(n_parallel or 1))
        # 多 slot 并行时总上下文按 slot 数分配，保证每个 slot 有独立上下文。
        self.ctx = (self.n_parallel * C.PER_SLOT_CTX
                    if self.n_parallel > 1 else ctx)
        self.port = pick_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._proc: subprocess.Popen | None = None

    def _argv(self) -> list[str]:
        return [
            self.server_exe,
            "-m", self.model_path,
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "-t", str(self.threads),
            "-ngl", "0",
            "-c", str(self.ctx),
            "--parallel", str(self.n_parallel),
            "--no-jinja",
        ]

    def start(self, ready_timeout: float = 90.0) -> None:
        """启动 server 并阻塞直到 /health 返回 200。"""
        if not os.path.isfile(self.server_exe):
            raise ServerError("找不到 llama-server 可执行文件。")
        if not os.path.isfile(self.model_path):
            raise ServerError("找不到模型文件（.gguf）。")
        self._proc = subprocess.Popen(  # noqa: S603（列表参数，无 shell 注入）
            self._argv(),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        if not self._wait_ready(ready_timeout):
            self.stop()
            raise ServerError("本地模型服务在限定时间内未就绪。")

    def _wait_ready(self, timeout: float) -> bool:
        t0 = time.monotonic()
        # 进程提前退出则直接失败，不必等满超时。
        while time.monotonic() - t0 < timeout:
            if self._proc is not None and self._proc.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(
                        self.base_url + "/health", timeout=2) as r:
                    if r.status == 200:
                        return True
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.7)
        return False

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self) -> None:
        """整树终止 server（含 onefile 子进程）；已退出则不处理。"""
        proc = self._proc
        if proc is None:
            return
        if proc.poll() is None and sys.platform == "win32":
            taskkill = os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"),
                "System32", "taskkill.exe")
            try:
                subprocess.run(
                    [taskkill, "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._proc = None
