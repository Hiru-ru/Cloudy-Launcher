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

"""分块并发下载引擎：纯 Python 标准库 ``urllib`` + ``concurrent.futures`` + ``threading``。

v1.2.11.0 新增。红线：不引入 ``requests`` / ``aiohttp`` 等第三方 HTTP 库；HTTP 请求头
User-Agent 保持纯 ASCII（urllib 按 latin-1 编码请求头，中文会直接抛 UnicodeEncodeError）。

职责边界：
- 负责任务级下载、并发调度、进度 / 速度 / 剩余文件统计、主镜像 → 兜底镜像切换、SHA1 校验、
  原子落盘与中断响应；不解析版本清单、不拼装版本隔离目录（由 ``game_dirs`` 与 worker 负责）。
- 本轮骨架只承载「版本 JSON」与「客户端 Jar」两类任务；依赖库 / 资源文件任务模型已预留，
  后续轮次直接构造 :class:`DownloadTask` 投喂即可。

线程数口径（用户要求）：默认 20 线程；预估总内容大于 1GB 自动切 30 线程。
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import constants as C


# --------------------------------------------------------------------------- #
# 任务与统计模型
# --------------------------------------------------------------------------- #
@dataclass
class DownloadTask:
    """单个待下载文件任务。

    ``mirror_url`` 可选：主 ``url`` 失败时切换到兜底镜像；``size`` 用于预估总进度，
    ``sha1`` 非空时下载完成后做完整性校验。
    """

    url: str
    local_path: str
    size: int = 0
    sha1: str = ""
    mirror_url: str | None = None
    extra_urls: list[str] = field(default_factory=list)
    label: str = ""


@dataclass
class DownloadStats:
    """实时进度快照（线程安全读取，由 :class:`ProgressTracker` 产出）。"""

    total_files: int = 0
    done_files: int = 0
    failed_files: int = 0
    total_bytes: int = 0
    done_bytes: int = 0
    remaining_files: int = 0
    speed_bps: float = 0.0


def choose_thread_count(estimated_bytes: int) -> int:
    """按预估总内容选择并发线程数：大于 1GB 用大文件档 30，否则默认 20。"""
    try:
        size = int(estimated_bytes or 0)
    except (TypeError, ValueError):
        size = 0
    return C.DOWNLOAD_THREADS_LARGE if size > C.DOWNLOAD_LARGE_BYTES else C.DOWNLOAD_THREADS_DEFAULT


class ProgressTracker:
    """线程安全的下载进度 / 速度统计器。

    多线程下载时由各工作线程调用 :meth:`record_chunk` / :meth:`record_file_done` /
    :meth:`record_file_failed`；主线程（worker）周期性调用 :meth:`snapshot` 取快照推给界面。
    速度取最近 ``DOWNLOAD_SPEED_WINDOW_SEC`` 秒窗口内累计字节差，避免瞬时抖动。
    """

    def __init__(self, total_files: int = 0, total_bytes: int = 0) -> None:
        self._lock = threading.Lock()
        self.total_files = max(0, int(total_files))
        self.total_bytes = max(0, int(total_bytes))
        self.done_files = 0
        self.failed_files = 0
        self.done_bytes = 0
        # 采样点 (monotonic 秒, 累计字节)，环形保留最近窗口。
        self._samples: list[tuple[float, int]] = []

    def set_total(self, total_files: int, total_bytes: int) -> None:
        with self._lock:
            self.total_files = max(0, int(total_files))
            self.total_bytes = max(0, int(total_bytes))

    def reset_counters(self) -> None:
        """每一步下载开始前清零已完成 / 失败文件与累计字节、速度采样。

        全局 tracker 在五步之间复用；若不清零，下一步 ``set_total`` 只更新总数，
        已完成计数仍沿用上一步，步内文件 / 字节占比会跨步失真（直接顶到 100%）。
        """
        with self._lock:
            self.done_files = 0
            self.failed_files = 0
            self.done_bytes = 0
            self._samples.clear()

    def record_chunk(self, nbytes: int) -> None:
        if nbytes <= 0:
            return
        now = time.monotonic()
        with self._lock:
            self.done_bytes += nbytes
            self._samples.append((now, self.done_bytes))
            self._prune_samples(now)

    def record_file_done(self) -> None:
        with self._lock:
            self.done_files += 1

    def record_file_failed(self) -> None:
        with self._lock:
            self.failed_files += 1

    def record_file_recovered(self) -> None:
        """救援重试把先前记过失败的文件救回来：只回退失败计数（完成计数由下载本身记）。

        并发池里失败常常是源站瞬时限流（同一时刻大量连接被拒），串行再试一次通常就能成功；
        若不回退失败计数，面板会一直显示「失败 N」，与实际结果不符。
        """
        with self._lock:
            if self.failed_files > 0:
                self.failed_files -= 1

    def _prune_samples(self, now: float) -> None:
        cutoff = now - C.DOWNLOAD_SPEED_WINDOW_SEC
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.pop(0)

    def _speed_bps(self) -> float:
        now = time.monotonic()
        self._prune_samples(now)
        if len(self._samples) < 2:
            return 0.0
        first_t, first_b = self._samples[0]
        last_t, last_b = self._samples[-1]
        elapsed = last_t - first_t
        if elapsed <= 1e-3:
            return 0.0
        return max(0.0, (last_b - first_b) / elapsed)

    def snapshot(self) -> DownloadStats:
        with self._lock:
            remaining = max(0, self.total_files - self.done_files - self.failed_files)
            return DownloadStats(
                total_files=self.total_files,
                done_files=self.done_files,
                failed_files=self.failed_files,
                total_bytes=self.total_bytes,
                done_bytes=self.done_bytes,
                remaining_files=remaining,
                speed_bps=self._speed_bps(),
            )


# --------------------------------------------------------------------------- #
# 单文件下载
# --------------------------------------------------------------------------- #
def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"},
    )


def _sha1_of_file(path: str) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            block = f.read(C.DOWNLOAD_CHUNK_SIZE)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _probe_size(url: str) -> int:
    """HEAD 探测远端文件大小；失败返回 0（调用方回落单连接）。"""
    request = _build_request(url)
    request.method = "HEAD"
    try:
        with urllib.request.urlopen(request, timeout=C.DOWNLOAD_STALL_TIMEOUT) as response:
            length = response.headers.get("Content-Length")
            return int(length) if length and length.isdigit() else 0
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return 0


def _already_complete(task: DownloadTask) -> bool:
    """目标文件已存在、大小 / SHA1 匹配则视为已完成，跳过重复下载（幂等）。"""
    if not os.path.isfile(task.local_path):
        return False
    try:
        if task.size > 0 and os.path.getsize(task.local_path) != task.size:
            return False
        if task.sha1:
            return _sha1_of_file(task.local_path) == task.sha1.lower()
        return os.path.getsize(task.local_path) > 0
    except OSError:
        return False


# 同一时刻最多允许几个文件走分片并发：批量下载里大文件若同时开分片，连接数会叠加触发源站限流。
_SPLIT_SEMAPHORE = threading.Semaphore(2)
# 分片遇到 429 时的退避秒数（源站限流阈值较低，8 并发会直接拒）。
_SPLIT_BACKOFF_SECONDS = 4.0


class _RangeUnsupported(Exception):
    """服务器不支持 Range 分片（返回 200 而非 206）；调用方回落单连接下载。"""


def _fast_timeout() -> int:
    """分片 / 单连接读取用的短 socket 超时：靠循环重试累计判断停滞，而不是靠一次长阻塞。"""
    return min(3, max(1, int(C.DOWNLOAD_STALL_TIMEOUT)))


def _stream_response(resp, out, tracker: ProgressTracker, cancel_check,
                      stall_limit: float, expect: int = -1) -> int:
    """把响应体裁流式写入 ``out``，返回写入字节数。

    用 ``read1`` + 短 socket 超时做「停滞检测」：源站在限流时会滴灌（每 1~2 秒给几个 KB），
    单次 12 秒超时永远不会触发，表现为「速度 0 B/s、进度不动」的假卡死。这里累计无数据
    时长超过 ``stall_limit`` 就主动放弃本次连接，让调用方换新连接重取（新连接常能拿到
    快通道）。``expect > 0`` 时读满即返回，避免末尾多读。
    """
    got = 0
    last_data = time.time()
    while True:
        if callable(cancel_check) and cancel_check():
            raise InterruptedError("下载已被取消")
        try:
            if expect > 0:
                block = resp.read1(min(C.DOWNLOAD_CHUNK_SIZE, expect - got))
            else:
                block = resp.read1(C.DOWNLOAD_CHUNK_SIZE)
        except (TimeoutError, OSError) as exc:
            if time.time() - last_data >= stall_limit:
                raise TimeoutError(f"读取停滞超过 {stall_limit:.0f} 秒") from exc
            continue
        if not block:
            return got
        out.write(block)
        got += len(block)
        last_data = time.time()
        tracker.record_chunk(len(block))
        if expect > 0 and got >= expect:
            return got


def _download_split(url: str, task: DownloadTask, tracker: ProgressTracker,
                    cancel_check) -> None:
    """把大文件按 ``Range`` 分片、多线程并发下载，全部完成后按序拼成 ``.part``。

    背景（2026-11-07 实测）：``maven.minecraftforge.net`` 单连接经 ``urllib`` 只有
    8~35 KB/s（8 MB 要 5~15 分钟），面板长时间无字节推进，用户判定为卡死；同一文件
    8 路 Range 并发可到 340~510 KB/s（23 秒下完）。并发过高会被源站 429 限流，因此
    单文件分片数上限取 4，遇到 429 退避后重试该片，且全局最多 2 个文件同时分片。
    """
    total = task.size
    if total <= 0:
        raise _RangeUnsupported("未知文件大小")
    parts = max(2, min(C.DOWNLOAD_SPLIT_MAX_PARTS,
                       int(total // C.DOWNLOAD_SPLIT_PART_BYTES)))
    chunk = (total + parts - 1) // parts
    part_path = task.local_path + ".part"
    os.makedirs(os.path.dirname(os.path.abspath(task.local_path)), exist_ok=True)

    # 清理无法校验归属的残留：上一轮尺寸对不上的分片、以及旧的整文件 .part。
    for index in range(parts):
        piece = f"{part_path}.{index}"
        start = index * chunk
        end = min(total - 1, start + chunk - 1)
        try:
            if os.path.getsize(piece) == end - start + 1:
                continue  # 完整分片保留，重试时不必重下
            os.remove(piece)
        except OSError:
            pass
    try:
        os.remove(part_path)
    except OSError:
        pass

    # 停滞上限：单片连续这么久没有任何新字节，就放弃这条连接换新连接重取。
    stall_limit = max(20.0, float(C.DOWNLOAD_STALL_TIMEOUT) * 2)
    errors: list[BaseException] = []
    errors_lock = threading.Lock()

    def fetch_piece(index: int, start: int, end: int) -> None:
        piece = f"{part_path}.{index}"
        expect = end - start + 1
        if os.path.isfile(piece) and os.path.getsize(piece) == expect:
            return
        attempts = 4
        last_exc: BaseException = ValueError("分片下载失败")
        for attempt in range(attempts):
            try:
                request = _build_request(url)
                request.add_header("Range", f"bytes={start}-{end}")
                with urllib.request.urlopen(request, timeout=_fast_timeout()) as resp:
                    if getattr(resp, "status", 200) != 206:
                        raise _RangeUnsupported("服务器未接受 Range 请求")
                    with open(piece, "wb") as out:
                        got = _stream_response(resp, out, tracker, cancel_check,
                                               stall_limit, expect)
                if got == expect:
                    return
                raise ValueError(f"分片字节数不足 {got}/{expect}")
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code == 429 and attempt + 1 < attempts:
                    time.sleep(_SPLIT_BACKOFF_SECONDS * (attempt + 1))
                    continue
                raise
            except InterruptedError:
                raise
            except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
                # 分片被限速 / 断流：换新连接重取本片，不整文件重来。
                last_exc = exc
                if attempt + 1 < attempts:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise
        raise last_exc

    def fetch(index: int, start: int, end: int) -> None:
        try:
            fetch_piece(index, start, end)
        except BaseException as exc:  # noqa: BLE001 - 统一收集后由主线程判定
            with errors_lock:
                errors.append(exc)

    threads: list[threading.Thread] = []
    for index in range(parts):
        start = index * chunk
        end = min(total - 1, start + chunk - 1)
        if start > end:
            continue
        thread = threading.Thread(target=fetch, args=(index, start, end), daemon=True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    def _cleanup_pieces(drop_merged: bool = False) -> None:
        """删除分片文件；``drop_merged`` 时连已拼接的整文件 ``.part`` 一起删。

        注意：拼接成功后**不能**删 ``.part``——它就是交给 ``_finalize_part`` 校验 / 落盘的
        成品，早前在这里无条件删掉曾导致「下载成功却被判定失败、整文件反复重下」。
        """
        for i in range(parts):
            try:
                os.remove(f"{part_path}.{i}")
            except OSError:
                pass
        if drop_merged:
            try:
                os.remove(part_path)
            except OSError:
                pass

    if errors:
        _cleanup_pieces(drop_merged=True)
        for exc in errors:
            if isinstance(exc, _RangeUnsupported):
                raise exc
        raise errors[0]

    # 拼接：任何一片缺失都视为失败，避免落盘半截文件。
    for index in range(parts):
        piece = f"{part_path}.{index}"
        start = index * chunk
        end = min(total - 1, start + chunk - 1)
        expect = end - start + 1
        if not os.path.isfile(piece) or os.path.getsize(piece) != expect:
            _cleanup_pieces(drop_merged=True)
            raise ValueError("分片下载不完整")

    with open(part_path, "wb") as out:
        for index in range(parts):
            with open(f"{part_path}.{index}", "rb") as source:
                shutil.copyfileobj(source, out, C.DOWNLOAD_CHUNK_SIZE)
    _cleanup_pieces()


def _finalize_part(task: DownloadTask) -> None:
    """校验 ``.part`` 的 SHA1（有要求时）并原子替换为正式文件。"""
    part_path = task.local_path + ".part"
    if task.sha1:
        if _sha1_of_file(part_path) != task.sha1.lower():
            try:
                os.remove(part_path)
            except OSError:
                pass
            raise ValueError("文件 SHA1 校验不匹配")
    os.replace(part_path, task.local_path)


def _download_from(url: str, task: DownloadTask, tracker: ProgressTracker,
                    cancel_check) -> None:
    """从单个 URL 流式分块下载到 ``<local_path>.part``；中断 / 网络异常向上抛出。

    - 支持断点续传：已有 ``.part`` 时带 ``Range`` 头续传，服务器不支持则自动重下。
    - 读取停滞保护：socket 超时设为 ``DOWNLOAD_STALL_TIMEOUT``，只要数据在流动，每次
      recv 都会在超时前返回；连续这么久一个字节都收不到，socket 直接抛 TimeoutError，
      由 ``download_one`` 切换下一候选源。这比跨线程 close/shutdown 可靠——后者在
      Windows 上无法保证唤醒另一线程阻塞的 recv。
    - 大文件（体积已知且 ≥ ``DOWNLOAD_SPLIT_MIN_BYTES``）先尝试 Range 分片并发，服务器
      不支持 Range 时回落单连接；分片对弱网 / 限速源能提速一个量级。
    """
    part_path = task.local_path + ".part"
    os.makedirs(os.path.dirname(os.path.abspath(task.local_path)), exist_ok=True)

    if task.size >= C.DOWNLOAD_SPLIT_MIN_BYTES and _SPLIT_SEMAPHORE.acquire(blocking=False):
        try:
            try:
                _download_split(url, task, tracker, cancel_check)
            except _RangeUnsupported:
                pass  # 服务器不支持分片，走下面的单连接逻辑
            else:
                _finalize_part(task)
                return
        finally:
            _SPLIT_SEMAPHORE.release()

    # 断点续传起点：已有 .part 的大小。
    resume_pos = 0
    if os.path.isfile(part_path):
        try:
            resume_pos = os.path.getsize(part_path)
        except OSError:
            resume_pos = 0

    request = _build_request(url)
    if resume_pos > 0:
        request.add_header("Range", f"bytes={resume_pos}-")

    with urllib.request.urlopen(request, timeout=_fast_timeout()) as response:
        # 206 = 服务器接受续传，追加写；200 = 不支持 Range，从头覆盖写。
        resumed = getattr(response, "status", 200) == 206 and resume_pos > 0
        mode = "ab" if resumed else "wb"
        if not resumed:
            resume_pos = 0

        with open(part_path, mode) as out:
            _stream_response(response, out, tracker, cancel_check,
                             max(30.0, float(C.DOWNLOAD_STALL_TIMEOUT) * 3))

    # SHA1 校验（有要求时），不匹配抛错触发镜像兜底；通过后原子替换。
    _finalize_part(task)


def download_one(task: DownloadTask, tracker: ProgressTracker,
                  cancel_check=None) -> tuple[bool, str]:
    """下载单个任务：依次尝试全部候选源；成功返回 ``(True, "")``，失败返回 ``(False, 原因)``。

    已完整存在的文件直接跳过；所有网络 / 校验异常统一捕获，不抛到并发池导致线程崩溃。
    网络中断 / 停滞时保留 ``.part``，下一源通过 ``Range`` 断点续传，不重复下载；
    SHA1 不匹配由 ``_download_from`` 删除脏文件，最终仍有完整性校验兜底。
    """
    if _already_complete(task):
        tracker.record_file_done()
        return True, ""

    # 体积未知时先 HEAD 探测一次：有大小才能走 Range 分片并发（大文件在弱网源上快一个量级）。
    if task.size <= 0:
        probed = _probe_size(task.url)
        if probed > 0:
            task.size = probed

    # 汇总全部候选源并去重，保持传入顺序（主源 → mirror → extra）。
    candidates: list[str] = []
    for u in [task.url, task.mirror_url, *task.extra_urls]:
        if u and u not in candidates:
            candidates.append(u)

    last_error = ""
    # 整轮重试：所有候选源一轮都失败后，若仍有重试配额，退避后再从头轮询。
    # 已下载的 .part 会在后续候选上通过 Range 续传，重试不会重复下载。
    for attempt in range(C.DOWNLOAD_RETRIES + 1):
        for url in candidates:
            if callable(cancel_check) and cancel_check():
                return False, "下载已被取消"
            try:
                _download_from(url, task, tracker, cancel_check)
                tracker.record_file_done()
                return True, ""
            except InterruptedError:
                return False, "下载已被取消"
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError,
                    TimeoutError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                # 网络 / 停滞错误：保留 .part 供下一源断点续传；SHA1 错误已在下层删除。
                continue

        if callable(cancel_check) and cancel_check():
            break
        if attempt < C.DOWNLOAD_RETRIES:
            time.sleep(C.DOWNLOAD_RETRY_BACKOFF * (attempt + 1))

    tracker.record_file_failed()
    return False, last_error or "下载失败"


def rescue_tasks(tasks: list[DownloadTask], tracker: ProgressTracker,
                 cancel_check=None, rounds: int = 3,
                 delay: float = 3.0) -> list[DownloadTask]:
    """串行救援：对并发批量里失败的文件逐个低速重试，返回仍失败的列表。

    并发池里失败往往是「同一瞬间几十条连接打同一个源站被限流 / TLS 抖动」的瞬态问题，
    并发重试只会重复撞墙。这里改为一次只下一个文件、每次失败后指数退避，
    已下载的 ``.part`` 通过 Range 续传继续，不必从头再下。

    ``rounds`` 是单个文件的最大尝试次数；成功的文件回退一次失败计数（完成计数由
    下载本身记录，避免重复累加）。
    """
    leftover: list[DownloadTask] = []
    for task in tasks:
        recovered = False
        for attempt in range(max(1, int(rounds))):
            if callable(cancel_check) and cancel_check():
                leftover.append(task)
                continue
            ok, _reason = download_one(task, tracker, cancel_check)
            if ok:
                tracker.record_file_recovered()
                recovered = True
                break
            if attempt + 1 < rounds:
                time.sleep(delay * (attempt + 1))
        if not recovered:
            leftover.append(task)
    return leftover


def download_batch(tasks: list[DownloadTask], tracker: ProgressTracker,
                   cancel_check=None) -> list[tuple[bool, str]]:
    """并发执行一批任务，返回与 ``tasks`` 顺序一致的 ``(成功, 原因)`` 结果列表。

    线程数由 :func:`choose_thread_count` 按任务预估总字节选择；任务内部逐块检查取消信号。
    单个任务失败不影响其余任务；全部失败 / 取消由调用方根据结果列表判定。
    """
    if not tasks:
        return []

    estimated = sum(max(0, t.size) for t in tasks)
    workers = choose_thread_count(estimated)
    tracker.set_total(len(tasks), estimated)

    results: list[tuple[bool, str]] = [(False, "未执行")] * len(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(download_one, task, tracker, cancel_check): index
            for index, task in enumerate(tasks)
        }
        for future in concurrent.futures.as_completed(future_map):
            index = future_map[future]
            try:
                results[index] = future.result()
            except Exception as exc:  # 兜底：工作线程内未预期异常不拖垮整池
                results[index] = (False, f"{type(exc).__name__}: {exc}")
                tracker.record_file_failed()
    return results


# --------------------------------------------------------------------------- #
# v1.2.12.0：Maven 坐标 / 库规则 / natives 解压 / 资源落盘辅助（纯标准库，不引入第三方）
# --------------------------------------------------------------------------- #
import zipfile


def maven_coordinate(name: str) -> tuple[str, str, str, str]:
    """把 ``group:artifact:version[:classifier]`` 拆成 ``(group, artifact, version, classifier)``。

    段数不足时缺失段回退空串；坐标格式异常不抛错，由调用方按空段兜底。
    """
    parts = str(name or "").split(":")
    group = parts[0] if len(parts) >= 1 else ""
    artifact = parts[1] if len(parts) >= 2 else ""
    version = parts[2] if len(parts) >= 3 else ""
    classifier = parts[3] if len(parts) >= 4 else ""
    return group, artifact, version, classifier


def maven_relative_path(name: str, classifier: str = "") -> str:
    """把 Maven 坐标转换为仓库内相对路径 ``group/path/artifact-version[-classifier].jar``。

    group 的 ``.`` 转为目录分隔符；classifier 非空时文件名追加 ``-classifier``。
    """
    group, artifact, version, coord_classifier = maven_coordinate(name)
    classifier = classifier or coord_classifier
    group_path = group.replace(".", "/")
    suffix = f"-{classifier}" if classifier else ""
    filename = f"{artifact}-{version}{suffix}.jar" if version else f"{artifact}{suffix}.jar"
    return f"{group_path}/{artifact}/{version}/{filename}" if version else f"{group_path}/{artifact}/{filename}"


def library_rule_allows(library: dict) -> bool:
    """判定某依赖库在当前操作系统 / 特性条件下是否需要下载。

    原版 / 加载器版本 JSON 里的 ``rules`` 支持 ``os.name``（本工程只运行 Windows，``windows``
    允许、其余拒绝）与 ``features``（特征要求默认拒绝，本启动器不提供对应特性环境）；
    无 rules 字段视为允许。allow 规则命中即放行，未命中的拒绝规则才排除。
    """
    rules = library.get("rules")
    if not rules:
        return True
    allowed = False
    for rule in rules:
        action = str(rule.get("action") or "allow")
        os_match = True
        os_block = rule.get("os")
        if isinstance(os_block, dict):
            os_name = str(os_block.get("name") or "").lower()
            # 本工程运行环境固定 Windows；未指定 name 的规则不按操作系统排除。
            os_match = (not os_name) or os_name == "windows"
        feature_block = rule.get("features")
        feature_match = not feature_block
        if os_match and feature_match:
            allowed = action == "allow"
    return allowed


def unpack_natives_jar(jar_path: str, natives_dir: str, cancel_check=None) -> bool:
    """把 natives classifier Jar 内的原生库解压到 ``natives_dir``；跳过目录条目与 META-INF。

    已存在且非空的同名原生库覆盖前不重复解压；解压异常返回 ``False``，由编排层记录失败。
    """
    if not jar_path or not os.path.isfile(jar_path):
        return False
    os.makedirs(natives_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(jar_path) as archive:
            for info in archive.infolist():
                if callable(cancel_check) and cancel_check():
                    return False
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if name.startswith("META-INF/") or name.endswith("/"):
                    continue
                target = os.path.join(natives_dir, os.path.basename(name))
                if os.path.isfile(target) and os.path.getsize(target) > 0:
                    continue
                with archive.open(info) as source, open(target, "wb") as out:
                    out.write(source.read())
        return True
    except (OSError, zipfile.BadZipFile):
        return False


def object_asset_path(asset_hash: str, legacy: bool) -> str:
    """资源对象落盘路径；现代版本走 ``objects/<hash[:2]>/<hash>``，旧版 legacy 走
    ``virtual/legacy/<name>``（文件名由调用层另行拼接，本函数只返回目录口径）。"""
    prefix = asset_hash[:2]
    if legacy:
        from . import game_dirs
        return game_dirs.assets_virtual_legacy_dir()
    from . import game_dirs
    return os.path.join(game_dirs.assets_objects_dir(), prefix, asset_hash)
