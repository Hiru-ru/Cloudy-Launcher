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

"""版本修改后台线程：在已有版本上重跑加载器安装 / 处理器链并更新版本。

v1.3.12.0 新增。对应第三张参考图的“开始修改”，也承担概览页“补齐文件”。与全新安装的
:class:`~cloud_launcher.ui.download_worker.VersionDownloadWorker` 复用同一套 version_profile /
loaders / download_engine / forge_install 函数，区别在于：

- 目标目录已存在，下载引擎按 ``_already_complete`` 幂等跳过已存在文件，只补缺失部分；
- 重新合并并落盘最终版本 JSON，再按需补齐原版库 / 资源 / 客户端 / 加载器库；
- 完成后改写 install_meta，使版本加载器与实际安装一致。

网络与磁盘工作全部在独立 QThread，主线程通过 progress 信号更新进度。
"""
from __future__ import annotations

import json
import os
import threading

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

# 五个阶段权重（合计 1.0）：JSON / 原版库 / 资源 / 客户端 / 加载器库。
_PHASE_WEIGHTS = (0.08, 0.30, 0.22, 0.12, 0.28)
_PHASE_LABELS = (
    "准备版本设置",
    "补齐原版支持库",
    "补齐游戏资源",
    "补齐客户端核心",
    "安装加载器支持库",
)


class VersionModifyWorker(QThread):
    """在已有版本上应用目标加载器（或补齐文件），驱动阶段进度。"""

    #: 进度快照：{"phase","phase_label","percent","message"}。
    progress = Signal(object)
    #: 完成：回传 {"alias","mc_version","loader","loader_version"}。
    succeeded = Signal(object)
    #: 失败：回传中文原因。
    failed = Signal(str)

    def __init__(self, alias: str, mc_version: str,
                 target_loader: str, target_loader_version: str = "",
                 parent=None) -> None:
        super().__init__(parent)
        self._alias = str(alias or "").strip()
        self._mc_version = str(mc_version or "").strip()
        self._loader = str(target_loader or C.LOADER_VANILLA)
        self._loader_version = str(target_loader_version or "").strip()
        self._resolved_loader_version = self._loader_version
        self._tracker = ProgressTracker()
        self._stop_sampling = threading.Event()
        self._sampler: threading.Thread | None = None
        self._current_phase = -1
        self._phase_before = 0.0
        self._phase_sub_base = 0.0
        self._phase_sub_span = 1.0
        self._global_percent = 0.0

    # ------------------------------------------------------------------ #
    # 进度
    # ------------------------------------------------------------------ #
    def _refresh_global(self) -> None:
        if self._current_phase < 0:
            return
        stats = self._tracker.snapshot()
        if stats.total_files > 0:
            ratio = stats.done_files / stats.total_files
        elif stats.total_bytes > 0:
            ratio = stats.done_bytes / stats.total_bytes
        else:
            ratio = 0.0
        ratio = max(0.0, min(1.0, ratio))
        span = _PHASE_WEIGHTS[self._current_phase]
        ratio = self._phase_sub_base + self._phase_sub_span * ratio
        self._global_percent = min(
            100.0, (self._phase_before + span * ratio) * 100.0)

    def _emit_progress(self, message: str = "") -> None:
        self.progress.emit({
            "phase": self._current_phase,
            "phase_label": _PHASE_LABELS[self._current_phase]
            if 0 <= self._current_phase < len(_PHASE_LABELS) else "",
            "percent": round(self._global_percent, 2),
            "message": message,
        })

    def _start_sampler(self) -> None:
        self._stop_sampling.clear()

        def sample() -> None:
            while not self._stop_sampling.wait(0.3):
                if self.isInterruptionRequested():
                    return
                self._refresh_global()
                self._emit_progress()

        self._sampler = threading.Thread(target=sample, daemon=True)
        self._sampler.start()

    def _stop_sampler(self) -> None:
        self._stop_sampling.set()
        if self._sampler is not None:
            self._sampler.join(1.0)
            self._sampler = None

    def _begin_phase(self, index: int, sub_base: float = 0.0,
                     sub_span: float = 1.0) -> None:
        self._current_phase = index
        self._phase_before = sum(_PHASE_WEIGHTS[:index])
        self._phase_sub_base = sub_base
        self._phase_sub_span = sub_span
        self._tracker.reset_counters()
        self._global_percent = self._phase_before * 100.0
        self._emit_progress(_PHASE_LABELS[index])

    def _finish_phase(self, index: int) -> None:
        self._global_percent = min(
            100.0, (self._phase_before + _PHASE_WEIGHTS[index]) * 100.0)
        self._current_phase = -1
        self._emit_progress(_PHASE_LABELS[index])

    # ------------------------------------------------------------------ #
    # 主流程
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        if self.isInterruptionRequested() or not self._alias or not self._mc_version:
            return
        game_dirs.ensure_base_dirs()
        game_dirs.ensure_version_dirs(self._alias)
        self._start_sampler()
        try:
            self._run()
        except InterruptedError:
            game_dirs.cleanup_partial(self._alias)
            self.failed.emit("已取消修改")
        except Exception as exc:  # 网络 / 磁盘 / 处理器统一兜底
            game_dirs.cleanup_partial(self._alias)
            self.failed.emit("修改失败：%s: %s" % (type(exc).__name__, exc))
        finally:
            self._stop_sampler()

    def _run(self) -> None:
        alias = self._alias
        mc = self._mc_version
        cancel = self.isInterruptionRequested

        # ---- 阶段 0：加载原版 profile + 目标加载器，合并落盘 ----
        self._begin_phase(0)
        self._tracker.set_total(1, 0)
        vanilla_profile = version_profile.load_merged_profile(mc, should_cancel=cancel)
        extra_profile, resolved = self._build_loader_extra(vanilla_profile, cancel)
        self._resolved_loader_version = resolved
        merged = (version_profile.merge_profiles(vanilla_profile, extra_profile)
                  if extra_profile else vanilla_profile)
        json_path = game_dirs.version_json_path(alias)
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2)
        self._tracker.record_file_done()
        self._finish_phase(0)

        # ---- 阶段 1：原版支持库（幂等，已存在跳过）+ natives ----
        self._begin_phase(1)
        library_tasks = version_profile.collect_library_tasks(vanilla_profile, alias)
        natives_tasks, natives_pairs = self._collect_natives(vanilla_profile, alias)
        self._run_batch(library_tasks + natives_tasks)
        for jar_path, natives_dir in natives_pairs:
            if self.isInterruptionRequested():
                raise InterruptedError("已取消")
            unpack_natives_jar(jar_path, natives_dir, cancel_check=cancel)
        self._finish_phase(1)

        # ---- 阶段 2：游戏资源 ----
        self._begin_phase(2)
        asset_tasks = version_profile.collect_asset_tasks(
            vanilla_profile, should_cancel=cancel)
        self._run_batch(asset_tasks)
        self._finish_phase(2)

        # ---- 阶段 3：客户端核心 ----
        self._begin_phase(3)
        jar_task = version_profile.client_jar_task(vanilla_profile, alias, mc)
        self._tracker.set_total(1, max(0, int(jar_task.size or 0)))
        ok, reason = download_one(jar_task, self._tracker, cancel)
        if not ok:
            raise RuntimeError(reason or "客户端核心补齐失败")
        self._finish_phase(3)

        # ---- 阶段 4：加载器支持库（Forge 走处理器链）----
        self._begin_phase(4)
        if extra_profile and self._loader == C.LOADER_FORGE:
            self._run_forge_step(extra_profile)
        elif extra_profile:
            loader_tasks = version_profile.collect_library_tasks(extra_profile, alias)
            self._run_batch(loader_tasks)
            for jar_path, natives_dir in version_profile.collect_natives_jars(
                    extra_profile, alias):
                unpack_natives_jar(jar_path, natives_dir, cancel_check=cancel)
        else:
            self._tracker.set_total(0, 0)
        self._finish_phase(4)

        if self.isInterruptionRequested():
            raise InterruptedError("已取消")

        # 更新 install_meta：加载器与实际安装一致，保留 modpack 等既有字段。
        game_dirs.write_install_meta(
            alias, mc, self._loader, self._resolved_loader_version,
            extra=game_dirs.read_install_meta(alias),
        )
        self._global_percent = 100.0
        self.succeeded.emit({
            "alias": alias,
            "mc_version": mc,
            "loader": self._loader,
            "loader_version": self._resolved_loader_version,
        })

    # ------------------------------------------------------------------ #
    # 批量 / Forge / natives
    # ------------------------------------------------------------------ #
    def _run_batch(self, tasks: list[DownloadTask]) -> None:
        if not tasks:
            self._tracker.set_total(0, 0)
            return
        results = download_batch(tasks, self._tracker, self.isInterruptionRequested)
        failures = [task for task, (ok, _r) in zip(tasks, results) if not ok]
        if self.isInterruptionRequested():
            raise InterruptedError("已取消")
        if failures:
            leftover = rescue_tasks(failures, self._tracker, self.isInterruptionRequested)
            if self.isInterruptionRequested():
                raise InterruptedError("已取消")
            if leftover:
                raise RuntimeError("部分文件补齐失败：%s" % leftover[0].label)

    def _run_forge_step(self, extra_profile: dict) -> None:
        # 前 90%：可下载库；后 10%：处理器链。
        self._phase_sub_base = 0.0
        self._phase_sub_span = 0.90
        generated = set()
        for lib in extra_profile.get("libraries") or []:
            if forge_install.is_processor_generated(lib):
                generated.add(version_profile.library_local_path(lib, self._alias))
        all_tasks = version_profile.collect_library_tasks(extra_profile, self._alias)
        downloadable = [t for t in all_tasks if t.local_path not in generated]
        self._run_batch(downloadable)

        self._phase_sub_base = 0.90
        self._phase_sub_span = 0.10
        self._tracker.reset_counters()
        processor_count = forge_install.count_client_processors(
            self._alias, self._mc_version, self._resolved_loader_version)
        self._tracker.set_total((processor_count or 0) + 1, 0)
        java = java_runtime.detect_java()
        if not java.get("ok"):
            raise RuntimeError("安装 Forge 需要 Java，请先安装 Java 后重试")
        forge_install.run_forge_install(
            self._mc_version,
            self._resolved_loader_version,
            self._alias,
            java["path"],
            should_cancel=self.isInterruptionRequested,
            tracker=self._tracker,
            log=lambda msg: None,
        )
        forge_install.cleanup_work_dir(self._alias)

    def _collect_natives(self, profile: dict, alias: str):
        from ..download_engine import maven_relative_path

        tasks: list[DownloadTask] = []
        pairs: list[tuple[str, str]] = []
        target = game_dirs.natives_dir(alias)
        for lib in profile.get("libraries") or []:
            classifiers = (lib.get("downloads") or {}).get("classifiers") or {}
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
                label="natives %s" % lib.get("name", path),
            ))
            pairs.append((local, target))
        return tasks, pairs

    # ------------------------------------------------------------------ #
    # 加载器合并层
    # ------------------------------------------------------------------ #
    def _build_loader_extra(self, vanilla: dict, cancel):
        loader = self._loader
        ver = self._loader_version
        if loader == C.LOADER_VANILLA:
            return None, ""
        if loader == C.LOADER_FABRIC:
            return loaders.build_fabric_profile(self._mc_version, ver, should_cancel=cancel)
        if loader == C.LOADER_FORGE:
            profile, resolved = loaders.build_forge_profile(
                self._mc_version, ver, should_cancel=cancel,
                installer_dir=os.path.join(game_dirs.version_dir(self._alias), "forge_work"),
                tracker=self._tracker)
            return profile, resolved
        if loader == C.LOADER_NEOFORGE:
            return loaders.build_neoforge_profile(ver, should_cancel=cancel)
        if loader == C.LOADER_OPTIFINE:
            return self._build_optifine(cancel), ver
        raise RuntimeError("暂不支持这个加载器：%s" % loader)

    def _build_optifine(self, cancel) -> dict:
        url = loaders.resolve_optifine_download_url(self._loader_version, should_cancel=cancel)
        if not url:
            raise RuntimeError("OptiFine 下载源暂时不可用")
        target_dir = game_dirs.libraries_dir(self._alias)
        local = "%s%soptifine%sOptiFine%s%s" % (
            target_dir, os.sep, os.sep, os.sep, self._loader_version)
        task = DownloadTask(url=url, local_path=local, label=self._loader_version)
        ok, reason = download_one(task, self._tracker, cancel)
        if not ok:
            raise RuntimeError(reason or "OptiFine Jar 下载失败")
        return loaders.build_optifine_profile(local, self._mc_version)
