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

"""版本下载后台线程：五步全真实安装编排 + 并发下载引擎 + 实时进度信号。

v1.2.12.0 重写。线程模型对齐本工程既有 ``VersionMetaWorker`` / ``AccountRestoreWorker``：
网络与磁盘工作全部放在独立 ``QThread``，不阻塞主界面；主线程通过信号更新单例下载面板。

安装编排顺序：

1. **下载原版 json 文件**：拉取原版版本 JSON、按所选加载器构建合并层 profile，落盘合并后的
   最终版本 JSON；
2. **下载原版支持库文件**：原版底座依赖库（含老版本 natives classifier Jar）下载到位并解压；
3. **下载原版资源文件**：拉取资源索引、并发下载全部对象到全局 ``assets`` 目录；
4. **安装游戏**：下载原版客户端 ``client.jar``；
5. **下载游戏支持库文件**：所选加载器（Fabric / Forge / NeoForge / OptiFine）专属依赖库。

中途取消：``QThread.requestInterruption()`` 设置中断标志，引擎逐块检查、立即停止并发任务，
worker 清理 ``.part`` 半成品分片后退出；不弹错误窗、不伪造成功。

纯标准库网络请求（经 :mod:`cloud_launcher.download_engine` 封装），不引入第三方 HTTP 库。
"""
from __future__ import annotations

import json
import os
import threading
import time

from PySide6.QtCore import QThread, Signal

from .. import constants as C
from .. import forge_install, game_dirs, java_runtime, loaders, version_profile
from ..download_engine import (
    DownloadTask,
    ProgressTracker,
    download_batch,
    download_one,
    rescue_tasks,
    unpack_natives_jar,
)


# 五步全局进度权重（合计 1.0）：JSON 准备 / 原版库 / 资源 / 客户端 Jar / 加载器库。
_STEP_WEIGHTS = (0.06, 0.30, 0.28, 0.24, 0.12)

# 诊断日志：设置环境变量 CLY_DIAG_LOG 为文件路径后，安装过程逐条落盘（默认关闭）。
_DIAG_PATH = os.environ.get("CLY_DIAG_LOG") or ""


def _diag(message: str) -> None:
    """把安装过程关键事件追加写入诊断日志；未开启诊断时静默返回。"""
    if not _DIAG_PATH:
        return
    try:
        with open(_DIAG_PATH, "a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))
    except OSError:
        pass


class VersionDownloadWorker(QThread):
    """下载并安装一个 Minecraft 版本（原版或所选加载器），驱动五步状态机与实时进度。"""

    #: 实时进度快照（dict）：总文件 / 已完成 / 剩余 / 总字节 / 已下载字节 / 速度 Bps / 总百分比。
    progress = Signal(object)
    #: 步骤状态变化：(步骤序号, 状态 pending|running|done|skipped, 步骤百分比 0-100)。
    stepChanged = Signal(int, str, float)
    #: 下载完成：回传 ``{"alias", "mc_version", "loader", "loader_version"}``。
    succeeded = Signal(object)
    #: 下载失败：回传中文原因（界面静默提示，不阻塞）。
    failed = Signal(str)
    #: 用户中途取消：清理完成后通知面板收起，不报失败。
    cancelled = Signal()

    def __init__(self, mc_version: str, alias: str,
                 loader: str = C.LOADER_VANILLA, loader_version: str = "",
                 parent=None) -> None:
        super().__init__(parent)
        self._mc_version = str(mc_version or "").strip()
        self._alias = str(alias or "").strip()
        self._loader = str(loader or C.LOADER_VANILLA)
        self._loader_version = str(loader_version or "").strip()
        # 实际使用的加载器版本：所选版本镜像缺失回退到旧版本时，记录真正下载成功的版本。
        self._resolved_loader_version = self._loader_version
        self._tracker = ProgressTracker()
        self._stop_sampling = threading.Event()
        self._sampler: threading.Thread | None = None
        self._global_percent = 0.0
        # v1.2.12.2：当前进行中的步骤与其全局权重基线；采样线程据此按实时文件 / 字节
        # 进度回填步内全局百分比，避免整批下载期间总进度长时间停在上一档不动。
        self._current_step = -1
        self._step_before = 0.0
        # v1.3.3.3：步内分段（下载 → 处理器）映射到该步权重的前后区间，
        # 让 Forge 处理器阶段仍能平滑推进，而不是整步停在 99.x%。
        self._step_sub_base = 0.0
        self._step_sub_span = 1.0

    # ------------------------------------------------------------------ #
    # 信号辅助
    # ------------------------------------------------------------------ #
    def _emit_step(self, index: int, state: str, percent: float = 0.0) -> None:
        self.stepChanged.emit(index, state, max(0.0, min(100.0, percent)))

    def _refresh_global_percent(self) -> None:
        """按当前进行中步骤的实时 tracker 快照回填全局加权百分比。

        整批并发下载期间，旧版要等整批完成才一次性跳到下一档，总进度长时间卡住不动；
        这里采样时先用已完成文件占比（无文件总数时退回已下载字节占比）估算步内进度，
        再叠加该步之前已完成步骤的权重基线，得到平滑推进的全局百分比。
        """
        if self._current_step < 0:
            return
        stats = self._tracker.snapshot()
        if stats.total_files > 0:
            ratio = stats.done_files / stats.total_files
        elif stats.total_bytes > 0:
            ratio = stats.done_bytes / stats.total_bytes
        else:
            ratio = 0.0
        ratio = max(0.0, min(1.0, ratio))
        span = _STEP_WEIGHTS[self._current_step]
        ratio = self._step_sub_base + self._step_sub_span * ratio
        self._global_percent = min(100.0, (self._step_before + span * ratio) * 100.0)

    def _emit_progress(self) -> None:
        stats = self._tracker.snapshot()
        self.progress.emit({
            "total_files": stats.total_files,
            "done_files": stats.done_files,
            "failed_files": stats.failed_files,
            "remaining_files": stats.remaining_files,
            "total_bytes": stats.total_bytes,
            "done_bytes": stats.done_bytes,
            "speed_bps": stats.speed_bps,
            "percent": round(self._global_percent, 2),
        })

    def _start_sampler(self) -> None:
        """独立采样线程：节流读取进度快照并发信号给主线程，下载阻塞期间面板仍实时刷新。"""
        self._stop_sampling.clear()

        def sample() -> None:
            while not self._stop_sampling.wait(0.3):
                if self.isInterruptionRequested():
                    return
                self._refresh_global_percent()
                self._emit_progress()

        self._sampler = threading.Thread(target=sample, daemon=True)
        self._sampler.start()

    def _stop_sampler(self) -> None:
        self._stop_sampling.set()
        if self._sampler is not None:
            self._sampler.join(1.0)
            self._sampler = None

    # ------------------------------------------------------------------ #
    # 主流程
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        if self.isInterruptionRequested() or not self._mc_version or not self._alias:
            return

        game_dirs.ensure_base_dirs()
        game_dirs.ensure_version_dirs(self._alias)
        self._start_sampler()

        try:
            self._run_pipeline()
        except InterruptedError:
            game_dirs.cleanup_partial(self._alias)
            self._stop_sampler()
            self.cancelled.emit()
            return
        except Exception as exc:  # 网络 / JSON / 文件系统统一兜底，界面静默回退
            _diag("PIPELINE FAIL %s: %s" % (type(exc).__name__, exc))
            self._stop_sampler()
            game_dirs.cleanup_partial(self._alias)
            self.failed.emit(f"下载 {self._mc_version} 失败：{type(exc).__name__}: {exc}")
            return
        finally:
            self._stop_sampler()
            self._emit_progress()

    def _cancel(self):
        return self.isInterruptionRequested

    # ------------------------------------------------------------------ #
    # 步骤执行辅助
    # ------------------------------------------------------------------ #
    def _run_batch(self, tasks: list[DownloadTask], step_index: int) -> None:
        """并发执行一批任务；任一失败且非取消即中止抛错。步内进度回填全局加权百分比。"""
        if self.isInterruptionRequested():
            raise InterruptedError("下载已被取消")
        self._current_step = step_index
        self._step_before = sum(_STEP_WEIGHTS[:step_index])
        self._step_sub_base = 0.0
        self._step_sub_span = 1.0
        # 每步开始清零全局 tracker 的已完成 / 失败计数与累计字节，避免上一步
        # 计数沿用到本步造成文件 / 字节占比跨步失真。
        self._tracker.reset_counters()
        self._emit_step(step_index, C.STEP_RUNNING, 0.0)
        if not tasks:
            self._tracker.set_total(0, 0)
            self._finish_step(step_index, 100.0)
            return

        results = download_batch(tasks, self._tracker, self._cancel())
        failures = [(reason, task) for task, (ok, reason) in zip(tasks, results) if not ok]
        if self.isInterruptionRequested():
            raise InterruptedError("下载已被取消")
        if failures:
            # 并发池里的失败多为源站瞬时限流：先串行低速救援，救不回来才中止安装，
            # 避免「只差最后一个文件」时整个安装直接失败。
            for _reason, task in failures:
                _diag("step=%d FAIL %s url=%s reason=%s"
                      % (step_index, task.label, task.url, _reason))
            leftover = rescue_tasks([task for _r, task in failures],
                                    self._tracker, self._cancel())
            if self.isInterruptionRequested():
                raise InterruptedError("下载已被取消")
            if leftover:
                _diag("step=%d STILL FAIL %s"
                      % (step_index, ", ".join(t.label for t in leftover)))
                # 首个失败原因上报；批量任务里部分文件失败即中止安装，避免半成品版本被判定已安装。
                raise RuntimeError(f"部分文件下载失败：{failures[0][0]}")

        stats = self._tracker.snapshot()
        step_percent = (
            stats.done_files / stats.total_files * 100.0 if stats.total_files > 0 else 100.0
        )
        self._finish_step(step_index, step_percent)

    def _run_forge_loader_step(self, extra_profile: dict) -> None:
        """Forge 第 4 步：先下载可直接下载的库，再用本机 Java 跑处理器链生成 client Jar。

        处理器生成的 ``:client`` 库无下载 URL，从普通批量任务里剔除；其余库并发下载后，
        调用 :mod:`forge_install` 执行 client 侧处理器，期间步骤保持「进行中」，全部成功才收尾。
        """
        step = C.DOWNLOAD_STEP_GAME_LIBS
        if self.isInterruptionRequested():
            raise InterruptedError("下载已被取消")
        self._current_step = step
        self._step_before = sum(_STEP_WEIGHTS[:step])
        # 本步分两段：并发下载库占 0~90%，installer 复用 + 处理器链占 90~100%。
        # 处理器阶段真实耗时数十秒到数分钟，必须让它继续推进，否则面板会停在 99.x% 像卡死。
        self._step_sub_base = 0.0
        self._step_sub_span = 0.90
        self._tracker.reset_counters()
        self._emit_step(step, C.STEP_RUNNING, 0.0)

        # 处理器生成库的本地路径集合，从批量任务中剔除。
        generated_paths = set()
        for lib in extra_profile.get("libraries") or []:
            if forge_install.is_processor_generated(lib):
                generated_paths.add(version_profile.library_local_path(lib, self._alias))
        all_tasks = version_profile.collect_library_tasks(extra_profile, self._alias)
        downloadable = [t for t in all_tasks if t.local_path not in generated_paths]

        results = download_batch(downloadable, self._tracker, self._cancel())
        failures = [(reason, task) for task, (ok, reason) in zip(downloadable, results) if not ok]
        if self.isInterruptionRequested():
            raise InterruptedError("下载已被取消")
        if failures:
            for _reason, task in failures:
                _diag("forge-libs FAIL %s url=%s reason=%s"
                      % (task.label, task.url, _reason))
            leftover = rescue_tasks([task for _r, task in failures],
                                    self._tracker, self._cancel())
            if self.isInterruptionRequested():
                raise InterruptedError("下载已被取消")
            if leftover:
                _diag("forge-libs STILL FAIL %s"
                      % ", ".join(t.label for t in leftover))
                raise RuntimeError(f"部分文件下载失败：{failures[0][0]}")

        # 库下载完成 → 切到处理器段：installer 槽位 + 每个 client 处理器各占一个槽位，
        # 让「剩余文件」随处理器推进递减、总百分比继续爬升。
        self._step_sub_base = 0.90
        self._step_sub_span = 0.10
        self._tracker.reset_counters()
        processor_count = forge_install.count_client_processors(
            self._alias, self._mc_version, self._resolved_loader_version)
        self._tracker.set_total((processor_count or 0) + 1, 0)

        # 运行 Forge 处理器链生成 client Jar（需要本机 Java），进度直接回填全局 tracker。
        java = java_runtime.detect_java()
        if not java.get("ok"):
            raise RuntimeError("安装 Forge 需要 Java 运行环境，请先安装 Java 后重试")
        forge_install.run_forge_install(
            self._mc_version,
            self._resolved_loader_version,
            self._alias,
            java["path"],
            should_cancel=self._cancel(),
            tracker=self._tracker,
            log=lambda msg: None,
        )
        forge_install.cleanup_work_dir(self._alias)
        self._finish_step(step, 100.0)

    def _finish_step(self, step_index: int, step_percent: float) -> None:
        """按五步权重刷新全局百分比并收尾当前步骤状态。"""
        before = sum(_STEP_WEIGHTS[:step_index])
        span = _STEP_WEIGHTS[step_index]
        self._global_percent = min(100.0, (before + span * step_percent / 100.0) * 100.0)
        self._current_step = -1
        self._step_before = 0.0
        self._emit_step(step_index, C.STEP_DONE, step_percent)
        self._emit_progress()

    # ------------------------------------------------------------------ #
    # 五步编排
    # ------------------------------------------------------------------ #
    def _run_pipeline(self) -> None:
        mc = self._mc_version
        alias = self._alias
        cancel = self._cancel()

        # ---- 第 0 步：下载 / 合并版本 JSON ----
        self._current_step = C.DOWNLOAD_STEP_JSON
        self._step_before = sum(_STEP_WEIGHTS[:C.DOWNLOAD_STEP_JSON])
        self._step_sub_base = 0.0
        self._step_sub_span = 1.0
        self._emit_step(C.DOWNLOAD_STEP_JSON, C.STEP_RUNNING)
        _diag("pipeline start mc=%s alias=%s loader=%s ver=%s"
              % (mc, alias, self._loader, self._loader_version))
        # Forge 的 installer 在这一步下载并落盘，用 1 个槽位让面板能反映其字节进度。
        self._tracker.reset_counters()
        self._tracker.set_total(1, 0)
        vanilla_profile = version_profile.load_merged_profile(mc, should_cancel=cancel)
        extra_profile, resolved_version = self._build_loader_extra_profile(
            vanilla_profile, cancel)
        self._resolved_loader_version = resolved_version
        if extra_profile:
            merged = version_profile.merge_profiles(vanilla_profile, extra_profile)
        else:
            merged = vanilla_profile
        # 落盘最终生效版本 JSON（目录名跟随别名）。
        json_path = game_dirs.version_json_path(alias)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        self._finish_step(C.DOWNLOAD_STEP_JSON, 100.0)

        # ---- 第 1 步：原版支持库（含老版本 natives classifier Jar 与解压）----
        library_tasks = version_profile.collect_library_tasks(vanilla_profile, alias)
        natives_tasks, natives_pairs = self._collect_natives(vanilla_profile, alias)
        _diag("step1 library_tasks=%d natives_tasks=%d"
              % (len(library_tasks), len(natives_tasks)))
        self._run_batch(library_tasks + natives_tasks, C.DOWNLOAD_STEP_LIBRARIES)
        for jar_path, natives_dir in natives_pairs:
            if self.isInterruptionRequested():
                raise InterruptedError("下载已被取消")
            unpack_natives_jar(jar_path, natives_dir, cancel_check=cancel)

        # ---- 第 2 步：原版资源文件 ----
        asset_tasks = version_profile.collect_asset_tasks(vanilla_profile, should_cancel=cancel)
        self._run_batch(asset_tasks, C.DOWNLOAD_STEP_ASSETS)

        # ---- 第 3 步：安装游戏（客户端 Jar）----
        self._current_step = C.DOWNLOAD_STEP_INSTALL
        self._step_before = sum(_STEP_WEIGHTS[:C.DOWNLOAD_STEP_INSTALL])
        self._emit_step(C.DOWNLOAD_STEP_INSTALL, C.STEP_RUNNING)
        jar_task = version_profile.client_jar_task(vanilla_profile, alias, mc)
        self._tracker.reset_counters()
        self._tracker.set_total(1, max(0, int(jar_task.size or 0)))
        ok, reason = download_one(jar_task, self._tracker, cancel)
        if not ok:
            raise RuntimeError(reason or "客户端 Jar 下载失败")
        self._finish_step(C.DOWNLOAD_STEP_INSTALL, 100.0)

        # ---- 第 4 步：加载器专属支持库 ----
        if extra_profile:
            if self._loader == C.LOADER_FORGE:
                # Forge 的 client 工件由处理器本地生成，走专用步骤。
                self._run_forge_loader_step(extra_profile)
            else:
                loader_tasks = version_profile.collect_library_tasks(extra_profile, alias)
                self._run_batch(loader_tasks, C.DOWNLOAD_STEP_GAME_LIBS)
                # 老格式平台库（Legacy Fabric 的 lwjgl-platform 等）以 classifier Jar
                # 落盘，需解压到 natives 目录；现代加载器无此类工件时配对为空。
                for jar_path, natives_dir in version_profile.collect_natives_jars(
                        extra_profile, alias):
                    unpack_natives_jar(jar_path, natives_dir, cancel_check=cancel)
        else:
            # 原版无加载器：该步跳过，但所有实际下载到此已全部完成。必须把全局百分比
            # 推到 100%，否则 run() finally 里的 _emit_progress 会用停在第 3 步的 88%
            # 覆盖成功面板（mark_success 已显示的 100%），表现为「安装完成却卡 88%」。
            self._global_percent = 100.0
            self._current_step = -1
            self._step_before = 0.0
            self._emit_step(C.DOWNLOAD_STEP_GAME_LIBS, C.STEP_SKIPPED)
            self._emit_progress()

        if self.isInterruptionRequested():
            raise InterruptedError("下载已被取消")

        # 安装元数据落盘：别名 ↔ 原生 MC 版本 ↔ 加载器类型 / 实际版本。
        game_dirs.write_install_meta(
            alias, mc, self._loader, self._resolved_loader_version,
            extra={"installed_at": ""},
        )
        self.succeeded.emit({
            "alias": alias,
            "mc_version": mc,
            "loader": self._loader,
            "loader_version": self._resolved_loader_version,
        })

    def _collect_natives(self, profile: dict, alias: str) -> tuple[list[DownloadTask], list[tuple[str, str]]]:
        """为老版本 natives classifier Jar 生成下载任务，并返回解压配对表。"""
        from ..download_engine import maven_relative_path

        tasks: list[DownloadTask] = []
        pairs: list[tuple[str, str]] = []
        natives_target = game_dirs.natives_dir(alias)
        for lib in profile.get("libraries") or []:
            downloads = lib.get("downloads") or {}
            classifiers = downloads.get("classifiers") or {}
            classifier = classifiers.get("natives-windows")
            if not classifier:
                continue
            path = str(classifier.get("path") or "").strip()
            if not path:
                path = maven_relative_path(str(lib.get("name") or ""), "natives-windows")
            local = game_dirs.libraries_dir(alias) + os.sep + path.replace("/", os.sep)
            primary = str(classifier.get("url") or "").strip()
            mirror = C.BMCL_MAVEN_URL.format(path=path)
            tasks.append(DownloadTask(
                url=primary or mirror,
                local_path=local,
                size=int(classifier.get("size") or 0),
                sha1=str(classifier.get("sha1") or ""),
                mirror_url=mirror if primary else None,
                label=f"natives {lib.get('name', path)}",
            ))
            pairs.append((local, natives_target))
        return tasks, pairs

    # ------------------------------------------------------------------ #
    # 加载器合并层构建
    # ------------------------------------------------------------------ #
    def _build_loader_extra_profile(self, vanilla: dict,
                                    cancel) -> tuple[dict | None, str]:
        """按所选加载器拉取 / 构建合并层 profile；返回 ``(profile, 实际加载器版本)``。

        原版返回 ``(None, "")``；Forge / NeoForge 镜像缺失回退旧版本时，实际版本
        可能与所选版本不同，由本方法一并回传。
        """
        mc = self._mc_version
        loader = self._loader
        loader_version = self._loader_version

        if loader == C.LOADER_VANILLA:
            return None, ""

        if loader == C.LOADER_FABRIC:
            profile, resolved = loaders.build_fabric_profile(
                mc, loader_version, should_cancel=cancel)
            return profile, resolved

        if loader == C.LOADER_FORGE:
            # 把 installer 一并落盘到该版本的 forge_work：第 5 步处理器链直接复用，
            # 不再二次下载数 MB 安装包（弱网下这一步会长时间无进度，曾表现为卡死）。
            # tracker 接入后，第 0 步下载 installer 时面板也能看到字节推进。
            profile, resolved = loaders.build_forge_profile(
                mc, loader_version, should_cancel=cancel,
                installer_dir=os.path.join(game_dirs.version_dir(self._alias), "forge_work"),
                tracker=self._tracker)
            return profile, resolved

        if loader == C.LOADER_NEOFORGE:
            profile, resolved = loaders.build_neoforge_profile(
                loader_version, should_cancel=cancel)
            return profile, resolved

        if loader == C.LOADER_OPTIFINE:
            return self._build_optifine_extra(mc, loader_version, cancel), loader_version

        return None, ""

    def _build_optifine_extra(self, mc: str, filename: str, cancel) -> dict:
        """解析 OptiFine 真实下载地址、下载 Jar 到加载器库目录，构造独立运行合并层。"""
        url = loaders.resolve_optifine_download_url(filename, should_cancel=cancel)
        if not url:
            raise RuntimeError("OptiFine 下载源暂时不可用")

        target_dir = game_dirs.libraries_dir(self._alias)
        local = f"{target_dir}{os.sep}optifine{os.sep}OptiFine{os.sep}{filename}"
        task = DownloadTask(
            url=url,
            local_path=local,
            label=filename,
        )
        ok, reason = download_one(task, self._tracker, cancel)
        if not ok:
            raise RuntimeError(reason or "OptiFine Jar 下载失败")
        return loaders.build_optifine_profile(local, mc)
