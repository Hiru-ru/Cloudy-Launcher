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

"""后台工作线程：扫描 → 启动模型 → 多线并行翻译 → 生成资源包。

所有耗时操作放在 QThread 中，通过信号向界面反馈阶段与进度。翻译阶段把待翻译条目
展开后用线程池按 ``worker_lines`` 决定的并行线数并发请求 llama-server（其 slot 数
在启动时对应设置），进度经锁汇总后发出。用户点「取消」时置位标志，工作线程在检查
点安全退出并停止 server，已翻译内容仍写入资源包，未处理 / 失败条目保留英文原文，
不丢数据。
"""
import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QThread, Signal

import ai_constants as C
from ai_server import LlamaServer, ServerError
from ai_translator import Translator, TranslateError
import jar_scanner
import resourcepack


class AiWorker(QThread):
    phase = Signal(str)
    scan_progress = Signal(int, int, str)
    translate_progress = Signal(int, int, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, scan_root: str, server_exe: str, model_path: str,
                 output_dir: str, pack_name: str, parent=None):
        super().__init__(parent)
        self.scan_root = scan_root
        self.server_exe = server_exe
        self.model_path = model_path
        self.output_dir = output_dir
        self.pack_name = pack_name
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    def _cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        server = None
        try:
            self.phase.emit("正在扫描 jar 文件…")
            tasks = jar_scanner.scan_dir(
                self.scan_root,
                progress=lambda d, t, p: self.scan_progress.emit(d, t, p),
                should_cancel=self._cancelled)
            if self._cancelled():
                self.finished_ok.emit({"cancelled": True, "reason": "已取消扫描"})
                return
            pending = jar_scanner.count_pending(tasks)
            if not tasks or pending == 0:
                self.finished_ok.emit(
                    {"cancelled": False, "reason": "未发现需要翻译的英文条目"})
                return

            n_lines = C.worker_lines(pending)
            self.phase.emit("正在加载本地模型（首次约需几秒）…")
            server = LlamaServer(self.server_exe, self.model_path,
                                 n_parallel=n_lines)
            server.start()
            if self._cancelled():
                self.finished_ok.emit({"cancelled": True, "reason": "已取消"})
                return

            # 展开全部待翻译单元：(task 索引, key, 英文)。
            units = []
            for ti, task in enumerate(tasks):
                for key, en in task.to_translate.items():
                    units.append((ti, key, en))

            translator = Translator(server.base_url)
            results: list[dict] = [dict() for _ in tasks]
            lock = threading.Lock()
            state = {"done": 0}

            def work(unit):
                ti, key, en = unit
                # 已取消：未开始的单元直接跳过，不写结果、不计数、不刷新进度，
                # 避免取消后进度被快速推到 100% 并算出异常速度。
                if self._cancelled():
                    return
                try:
                    zh = translator.translate_one(en)
                except TranslateError:
                    # 单条失败保留英文：不写入译文，最终游戏回退英文原文。
                    zh = None
                # 翻译期间被取消：丢弃这条结果。
                if self._cancelled():
                    return
                if zh:
                    results[ti][key] = zh
                with lock:
                    state["done"] += 1
                    done = state["done"]
                self.translate_progress.emit(done, pending, key)

            self.phase.emit("正在并行翻译（%d 条翻译线）…" % n_lines)
            with ThreadPoolExecutor(max_workers=n_lines) as pool:
                list(pool.map(work, units))

            items = [(task, results[ti]) for ti, task in enumerate(tasks)
                     if results[ti]]
            if not items:
                self.finished_ok.emit({"cancelled": True, "reason": "已取消翻译"})
                return

            self.phase.emit("正在生成汉化资源包…")
            pack_dir = os.path.join(self.output_dir, self.pack_name)
            resourcepack.build_pack(pack_dir, items)
            zip_path = resourcepack.zip_pack(
                pack_dir, os.path.join(self.output_dir, self.pack_name + ".zip"))
            translated_count = sum(len(z) for _t, z in items)
            self.finished_ok.emit({
                "cancelled": self._cancelled(),
                "pack_dir": pack_dir,
                "zip_path": zip_path,
                "jars": len({t.jar_path for t, _ in items}),
                "namespaces": len(items),
                "translated": translated_count,
                "lines": n_lines,
                "disclaimer": C.TRANSLATION_DISCLAIMER,
            })
        except ServerError as e:
            self.failed.emit(str(e))
        except Exception:  # noqa: BLE001（兜底，把异常送回界面，避免线程静默崩溃）
            self.failed.emit("发生未预期错误：\n" + traceback.format_exc())
        finally:
            if server is not None:
                server.stop()
