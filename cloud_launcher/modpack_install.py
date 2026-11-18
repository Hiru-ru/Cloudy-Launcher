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

"""v1.3.22.0 整合包安装模块（在线 Modrinth + 本地多格式导入）。

本模块把一个整合包安装成**全新的、可启动的版本隔离实例**，目录名即用户给的别名
（界面负责命名与撞名拦截）。两条入口：

- :func:`install_modpack`：在线 Modrinth 链路（下载页点整合包卡片），先下载 ``.mrpack``
  再安装；对外签名保持不变，供现有 worker 调用；
- :func:`install_local_pack`：本地任意格式整合包（全局拖拽最终调用），先由
  :mod:`modpack_format` 探测格式并解析成统一 :class:`~modpack_format.ModpackPlan`，
  再由通用核心 :func:`_install_plan` 安装。

通用核心负责底座（合并 profile / 原版库 / 资源 / 客户端 / 加载器库，阶段 1-5），
再落地计划内的联网下载文件（阶段 6）与包内自带文件（阶段 7），最后写
``install_meta.json``。全程复用 :mod:`version_profile` / :mod:`download_engine` /
:mod:`loaders` / :mod:`forge_install`，不重写下载与处理器逻辑；所有落盘路径都做
目录内校验，防止路径 / 压缩条目写出实例目录（zip slip）。纯标准库，UA 纯 ASCII。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from . import constants as C
from . import forge_install, game_dirs, java_runtime, loaders, version_profile
from . import modpack_format as mpf
from .download_engine import (
    DownloadTask,
    ProgressTracker,
    download_batch,
    download_one,
    maven_relative_path,
    rescue_tasks,
    unpack_natives_jar,
)

VERSION_API = "https://api.modrinth.com/v2/project/{project_id}/version"
VERSION_TIMEOUT = 25
MRPACK_EXT = ".mrpack"
INDEX_NAME = "modrinth.index.json"
WORK_DIRNAME = "modpack_work"
MRPACK_BASENAME = "pack.mrpack"

# 八个阶段的全局进度权重（合计 1.0），按各阶段实际下载体量粗估。
PHASE_WEIGHTS = (0.02, 0.05, 0.26, 0.24, 0.08, 0.13, 0.20, 0.02)
PHASE_LABELS = (
    "下载整合包文件",
    "解析依赖并准备版本",
    "下载原版支持库",
    "下载游戏资源",
    "下载客户端核心",
    "下载加载器支持库",
    "下载整合包内容",
    "应用配置并收尾",
)


class ModpackError(Exception):
    """整合包安装链路统一异常（消息直接用于界面提示）。"""


def _ua_header() -> dict:
    return {"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"}


# --------------------------------------------------------------------------- #
# 版本列表（供界面先选版本）
# --------------------------------------------------------------------------- #
def _request_json(url: str, should_cancel=None) -> list:
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("已取消")
    req = urllib.request.Request(url, headers=_ua_header())
    with urllib.request.urlopen(req, timeout=VERSION_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, list):
        raise ModpackError("整合包版本接口返回格式异常")
    return data


def _pick_mrpack(version: dict) -> dict | None:
    """从一个版本条目里挑出 .mrpack 文件：primary 优先，其次取首个 .mrpack。"""
    files = version.get("files") or []
    mrpack = [f for f in files
              if str(f.get("filename") or "").lower().endswith(MRPACK_EXT)]
    if not mrpack:
        return None
    primary = [f for f in mrpack if f.get("primary")]
    return (primary or mrpack)[0]


def fetch_modpack_versions(project_id: str, should_cancel=None) -> list[dict]:
    """拉取某整合包项目所有带 ``.mrpack`` 的版本，按发布时间新→旧返回。

    每条：``{"version_id","version_number","version_name","game_versions","loaders",
    "filename","url","size","date_published"}``。
    """
    url = VERSION_API.format(
        project_id=urllib.parse.quote(project_id, safe=""))
    try:
        raw_versions = _request_json(url, should_cancel)
    except urllib.error.HTTPError as exc:
        raise ModpackError("查询整合包版本失败（HTTP %s）" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise ModpackError("查询整合包版本失败，请检查网络") from exc
    except (TimeoutError, OSError) as exc:
        raise ModpackError("查询整合包版本超时，请稍后重试") from exc
    except ValueError as exc:
        raise ModpackError("整合包版本返回内容解析失败") from exc

    result: list[dict] = []
    for version in raw_versions:
        chosen = _pick_mrpack(version)
        if not chosen or not chosen.get("url"):
            continue
        result.append({
            "version_id": str(version.get("id") or ""),
            "version_number": str(version.get("version_number") or ""),
            "version_name": str(version.get("name") or ""),
            "game_versions": list(version.get("game_versions") or []),
            "loaders": list(version.get("loaders") or []),
            "filename": str(chosen.get("filename") or ""),
            "url": str(chosen.get("url") or ""),
            "size": int(chosen.get("size") or 0),
            "date_published": str(version.get("date_published") or ""),
        })
    return result


# --------------------------------------------------------------------------- #
# 路径安全
# --------------------------------------------------------------------------- #
def _safe_inside(root: str, rel_path: str) -> str:
    """把相对路径拼到 root 内并校验结果不越界；非法（绝对路径 / 含 ``..`` 逃逸）抛错。"""
    raw = str(rel_path or "").replace("\\", "/")
    if not raw.strip("/"):
        raise ModpackError("整合包内存在空路径条目")
    # 显式绝对路径（POSIX 以 / 开头、Windows 盘符如 C:）属于非法条目，直接拒绝而非改写。
    if raw.startswith("/") or (len(raw) >= 2 and raw[1] == ":"):
        raise ModpackError("整合包内存在绝对路径，已中止：%s" % rel_path)
    clean = raw.strip("/")
    target = os.path.normpath(os.path.join(root, *clean.split("/")))
    root_norm = os.path.normpath(root)
    if target != root_norm and not target.startswith(root_norm + os.sep):
        raise ModpackError("整合包内路径越界，已中止：%s" % rel_path)
    return target


def _prepare_alias(alias: str) -> str:
    alias = str(alias or "").strip()
    if not alias:
        raise ModpackError("请先给整合包命名")
    if game_dirs.alias_exists(alias):
        # 界面已做撞名拦截，这里再兜底一次，绝不覆盖已有实例。
        raise ModpackError("名字「%s」已被占用，请换一个" % alias)
    return alias


# --------------------------------------------------------------------------- #
# 入口一：在线 Modrinth
# --------------------------------------------------------------------------- #
def install_modpack(chosen: dict, alias: str, should_cancel=None,
                    on_phase=None, on_progress=None) -> dict:
    """在线 Modrinth：先下载/复制 .mrpack（阶段0），再用通用核心安装。"""
    alias = _prepare_alias(alias)
    game_dirs.ensure_base_dirs()
    game_dirs.ensure_version_dirs(alias)
    instance_dir = game_dirs.version_dir(alias)
    work_dir = os.path.join(instance_dir, WORK_DIRNAME)
    os.makedirs(work_dir, exist_ok=True)
    mrpack_path = os.path.join(work_dir, MRPACK_BASENAME)

    local_src = str(chosen.get("local_path") or "")
    if local_src:
        if callable(on_phase):
            on_phase(0, "读取本地整合包文件")
        if not os.path.isfile(local_src):
            raise ModpackError("本地整合包文件不存在：%s" % local_src)
        shutil.copy2(local_src, mrpack_path)
    else:
        if callable(on_phase):
            on_phase(0, PHASE_LABELS[0])
        pack_task = DownloadTask(
            url=str(chosen.get("url") or ""),
            local_path=mrpack_path,
            size=int(chosen.get("size") or 0),
            label=chosen.get("filename") or MRPACK_BASENAME,
        )
        ok, reason = _download_phase0(pack_task, ProgressTracker(),
                                      should_cancel, on_progress)
        if not ok:
            raise ModpackError("整合包文件下载失败：%s" % reason)

    plan = mpf.build_plan(mrpack_path, mpf.FORMAT_MODRINTH, should_cancel)
    plan.meta_extra.update({
        "modpack_project": str(chosen.get("project_id") or ""),
        "modpack_version": str(chosen.get("version_id") or ""),
        "modpack_name": str(chosen.get("modpack_name") or ""),
    })
    return _install_plan(
        plan, alias, mrpack_path, should_cancel, on_phase, on_progress,
        weight_offset=PHASE_WEIGHTS[0], work_dir=work_dir)


def _download_phase0(task: DownloadTask, tracker: ProgressTracker,
                     should_cancel, on_progress) -> tuple[bool, str]:
    """下载 .mrpack 并把进度映射到阶段0权重区间（0 ~ PHASE_WEIGHTS[0]）。"""
    stop = threading.Event()

    def _sample() -> None:
        while not stop.wait(0.3):
            stats = tracker.snapshot()
            if stats.total_files > 0:
                ratio = stats.done_files / stats.total_files
            elif stats.total_bytes > 0:
                ratio = stats.done_bytes / stats.total_bytes
            else:
                ratio = 0.0
            pct = min(100.0, PHASE_WEIGHTS[0] * ratio * 100.0)
            if callable(on_progress):
                on_progress(round(pct, 2), stats.done_bytes,
                            stats.total_bytes, stats.speed_bps,
                            stats.remaining_files)

    sampler = threading.Thread(target=_sample, daemon=True)
    sampler.start()
    ok, reason = download_one(task, tracker, should_cancel)
    stop.set()
    sampler.join(1.0)
    return ok, reason


# --------------------------------------------------------------------------- #
# 入口二：本地任意格式（全局拖拽）
# --------------------------------------------------------------------------- #
def install_local_pack(path: str, alias: str, should_cancel=None,
                       on_phase=None, on_progress=None,
                       on_resolve=None) -> dict:
    """本地整合包：探测格式 → 统一计划 → 通用核心。"""
    alias = _prepare_alias(alias)
    if not os.path.isfile(path):
        raise ModpackError("整合包文件不存在：%s" % path)
    fmt = mpf.detect_format(path)
    plan = mpf.build_plan(path, fmt, should_cancel, on_resolve)
    game_dirs.ensure_base_dirs()
    game_dirs.ensure_version_dirs(alias)
    return _install_plan(
        plan, alias, path, should_cancel, on_phase, on_progress,
        weight_offset=0.0, work_dir=None)


# 核心阶段（1-7）权重合计，用于把核心内部进度归一化到 0-100%。
_CORE_SPAN = sum(PHASE_WEIGHTS[1:])


def _install_plan(plan: mpf.ModpackPlan, alias: str, source_archive: str,
                  should_cancel, on_phase, on_progress,
                  weight_offset: float, work_dir: str | None) -> dict:
    """通用核心：底座（阶段1-5）+ 计划下载（阶段6）+ 包内解压（阶段7）+ 元数据。"""
    instance_dir = game_dirs.version_dir(alias)
    tracker = ProgressTracker()
    state = {"phase": 1}
    stop_sampler = threading.Event()

    def _set_phase(index: int, label: str | None = None) -> None:
        state["phase"] = index
        tracker.reset_counters()
        if callable(on_phase):
            on_phase(index, label or PHASE_LABELS[index])

    def _sample() -> None:
        while not stop_sampler.wait(0.3):
            if callable(should_cancel) and should_cancel():
                return
            stats = tracker.snapshot()
            phase = state["phase"]
            if stats.total_files > 0:
                ratio = stats.done_files / stats.total_files
            elif stats.total_bytes > 0:
                ratio = stats.done_bytes / stats.total_bytes
            else:
                ratio = 0.0
            # 核心内部（阶段1-7）归一化，再映射到 [weight_offset, 1]。
            core_base = sum(PHASE_WEIGHTS[1:phase]) / _CORE_SPAN
            core_ratio = core_base + (PHASE_WEIGHTS[phase] / _CORE_SPAN) * ratio
            percent = (weight_offset + (1.0 - weight_offset) * core_ratio) * 100.0
            if callable(on_progress):
                on_progress(round(min(100.0, percent), 2), stats.done_bytes,
                            stats.total_bytes, stats.speed_bps,
                            stats.remaining_files)

    sampler = threading.Thread(target=_sample, daemon=True)
    sampler.start()

    file_count = 0
    mc = plan.mc_version
    loader_key = plan.loader_key
    resolved_loader = plan.loader_version
    try:
        _resolve_download_paths(plan, instance_dir)
        extra_profile = None
        if mc:
            # ---- 阶段 1：构建合并 profile、落盘版本 JSON ----
            _set_phase(1)
            vanilla_profile = version_profile.load_merged_profile(
                mc, should_cancel=should_cancel)
            extra_profile, resolved_loader = _build_loader_profile(
                mc, loader_key, plan.loader_version, should_cancel,
                tracker, instance_dir)
            if extra_profile:
                merged = version_profile.merge_profiles(
                    vanilla_profile, extra_profile)
            else:
                merged = vanilla_profile
            json_path = game_dirs.version_json_path(alias)
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(merged, fh, ensure_ascii=False, indent=2)

            # ---- 阶段 2：原版支持库 + natives ----
            _set_phase(2)
            library_tasks = version_profile.collect_library_tasks(
                vanilla_profile, alias)
            natives_tasks, natives_pairs = _collect_natives(
                vanilla_profile, alias)
            _run_batch(library_tasks + natives_tasks, tracker, should_cancel)
            for jar_path, natives_target in natives_pairs:
                if callable(should_cancel) and should_cancel():
                    raise InterruptedError("下载已被取消")
                unpack_natives_jar(jar_path, natives_target, should_cancel)

            # ---- 阶段 3：原版资源 ----
            _set_phase(3)
            asset_tasks = version_profile.collect_asset_tasks(
                vanilla_profile, should_cancel=should_cancel)
            _run_batch(asset_tasks, tracker, should_cancel)

            # ---- 阶段 4：客户端核心 client.jar ----
            _set_phase(4)
            jar_task = version_profile.client_jar_task(
                vanilla_profile, alias, mc)
            ok, reason = download_one(jar_task, tracker, should_cancel)
            if not ok:
                raise ModpackError("客户端核心下载失败：%s" % reason)

            # ---- 阶段 5：加载器专属库 ----
            if extra_profile and loader_key == C.LOADER_FORGE:
                _set_phase(5)
                _run_forge_step(mc, resolved_loader, alias, extra_profile,
                                tracker, should_cancel)
            elif extra_profile:
                _set_phase(5)
                loader_tasks = version_profile.collect_library_tasks(
                    extra_profile, alias)
                _run_batch(loader_tasks, tracker, should_cancel)
                for jar_path, natives_target in version_profile.collect_natives_jars(
                        extra_profile, alias):
                    unpack_natives_jar(jar_path, natives_target, should_cancel)
            else:
                _set_phase(5)  # 无加载器，该阶段直接通过。

        # ---- 阶段 6：计划内联网下载文件 ----
        _set_phase(6)
        file_count = len(plan.downloads)
        _run_batch(plan.downloads, tracker, should_cancel)

        # ---- 阶段 7：包内文件解压 + 图标 + install_meta ----
        _set_phase(7)
        with zipfile.ZipFile(source_archive) as archive:
            _apply_archive_copies(archive, plan.archive_copies, instance_dir)
            has_icon = _ensure_modpack_icon(archive, instance_dir)
        meta_extra = dict(plan.meta_extra)
        if has_icon:
            meta_extra["avatar"] = "modpack"
        meta_mc = mc or game_dirs.local_version_base(alias)
        game_dirs.write_install_meta(
            alias, meta_mc, loader_key, resolved_loader, extra=meta_extra)
    except InterruptedError:
        stop_sampler.set()
        sampler.join(1.0)
        # 本次新建实例，取消即整目录移除，不留半成品。
        game_dirs.remove_version_dir(alias)
        raise
    except ModpackError:
        stop_sampler.set()
        sampler.join(1.0)
        game_dirs.remove_version_dir(alias)
        raise
    except Exception as exc:  # noqa: BLE001 网络 / 磁盘 / 处理器统一兜底
        stop_sampler.set()
        sampler.join(1.0)
        game_dirs.remove_version_dir(alias)
        raise ModpackError(f"安装失败：{type(exc).__name__}: {exc}") from exc
    finally:
        stop_sampler.set()
        sampler.join(1.0)

    if work_dir is not None:
        _remove_work_dir(work_dir)
    if callable(on_progress):
        on_progress(100.0, 0, 0, 0.0, 0)
    return {
        "alias": alias,
        "mc_version": mc,
        "loader": loader_key,
        "loader_version": resolved_loader,
        "dir": instance_dir,
        "file_count": file_count,
    }


# --------------------------------------------------------------------------- #
# 阶段内部辅助
# --------------------------------------------------------------------------- #
def _build_loader_profile(mc: str, loader_key: str, loader_version: str,
                          should_cancel, tracker: ProgressTracker,
                          instance_dir: str) -> tuple[dict | None, str]:
    """按加载器构建合并层 profile，返回 ``(profile, 实际加载器版本)``；原版返回 ``(None, "")``。"""
    if loader_key == C.LOADER_VANILLA:
        return None, ""
    if loader_key == C.LOADER_FABRIC:
        return loaders.build_fabric_profile(
            mc, loader_version, should_cancel=should_cancel)
    if loader_key == C.LOADER_NEOFORGE:
        return loaders.build_neoforge_profile(
            loader_version, should_cancel=should_cancel)
    if loader_key == C.LOADER_FORGE:
        installer_dir = os.path.join(instance_dir, "forge_work")
        return loaders.build_forge_profile(
            mc, loader_version, should_cancel=should_cancel,
            installer_dir=installer_dir, tracker=tracker)
    raise ModpackError("暂不支持这个加载器的整合包")


def _run_batch(tasks: list[DownloadTask], tracker: ProgressTracker,
               should_cancel) -> None:
    """并发跑一批任务，失败先串行救援，救不回来即中止，避免半成品被判定已安装。"""
    if not tasks:
        return
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("下载已被取消")
    results = download_batch(tasks, tracker, should_cancel)
    failures = [task for task, (ok, _r) in zip(tasks, results) if not ok]
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("下载已被取消")
    if failures:
        leftover = rescue_tasks(failures, tracker, should_cancel)
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("下载已被取消")
        if leftover:
            raise ModpackError("部分内容下载失败，已中止安装")


def _collect_natives(profile: dict, alias: str) -> tuple[list[DownloadTask], list[tuple[str, str]]]:
    """为老版本 ``natives-windows`` classifier Jar 生成下载任务并返回解压配对表。"""
    tasks: list[DownloadTask] = []
    pairs: list[tuple[str, str]] = []
    natives_target = game_dirs.natives_dir(alias)
    for lib in profile.get("libraries") or []:
        classifiers = (lib.get("downloads") or {}).get("classifiers") or {}
        classifier = classifiers.get("natives-windows")
        if not classifier:
            continue
        path = str(classifier.get("path") or "").strip()
        if not path:
            path = maven_relative_path(
                str(lib.get("name") or ""), "natives-windows")
        local = os.path.join(
            game_dirs.libraries_dir(alias), path.replace("/", os.sep))
        tasks.append(DownloadTask(
            url=str(classifier.get("url") or C.BMCL_MAVEN_URL.format(path=path)),
            local_path=local,
            size=int(classifier.get("size") or 0),
            sha1=str(classifier.get("sha1") or ""),
            mirror_url=C.BMCL_MAVEN_URL.format(path=path),
            label=f"natives {lib.get('name', path)}",
        ))
        pairs.append((local, natives_target))
    return tasks, pairs


def _run_forge_step(mc: str, forge_version: str, alias: str,
                    extra_profile: dict, tracker: ProgressTracker,
                    should_cancel) -> None:
    """Forge 阶段：先并发下载非处理器生成的库，再用本机 Java 跑处理器链。"""
    generated = set()
    for lib in extra_profile.get("libraries") or []:
        if forge_install.is_processor_generated(lib):
            generated.add(
                version_profile.library_local_path(lib, alias))
    all_tasks = version_profile.collect_library_tasks(extra_profile, alias)
    downloadable = [t for t in all_tasks if t.local_path not in generated]
    _run_batch(downloadable, tracker, should_cancel)

    java = java_runtime.detect_java()
    if not java.get("ok"):
        raise ModpackError("安装 Forge 整合包需要 Java，请先安装 Java 后重试")
    forge_install.run_forge_install(
        mc, forge_version, alias, java["path"],
        should_cancel=should_cancel, tracker=tracker, log=lambda msg: None)
    forge_install.cleanup_work_dir(alias)


def _resolve_download_paths(plan: mpf.ModpackPlan, instance_dir: str) -> None:
    """把计划内下载任务的相对 ``local_path`` 统一解析为实例内绝对路径（含越界校验）。"""
    for task in plan.downloads:
        task.local_path = _safe_inside(instance_dir, task.local_path)


def _apply_archive_copies(archive: zipfile.ZipFile,
                          copies: list[tuple[str, str]],
                          instance_dir: str) -> None:
    """按 ``(zip 条目, 实例内相对路径)`` 把包内自带文件安全解压进实例。"""
    for entry_name, rel in copies:
        key = entry_name.replace("\\", "/").lstrip("/")
        try:
            info = archive.getinfo(key)
        except KeyError:
            try:
                info = archive.getinfo(entry_name.lstrip("/"))
            except KeyError:
                continue
        if info.is_dir():
            continue
        target = _safe_inside(instance_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with archive.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out, C.DOWNLOAD_CHUNK_SIZE)


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MODPACK_ICON_NAME = "pack.png"


def _is_png(path: str) -> bool:
    """读文件头判断是否为有效 PNG（纯标准库，不依赖 PIL）；文件缺失返回 False。"""
    try:
        with open(path, "rb") as fh:
            return fh.read(8) == _PNG_SIGNATURE
    except OSError:
        return False


def _ensure_modpack_icon(archive: zipfile.ZipFile, instance_dir: str) -> bool:
    """确保实例根目录有整合包图标 ``pack.png``，返回是否成功。

    绝大多数整合包把图标放在自带文件里（已由 :func:`_apply_archive_copies` 解到根目录）；
    若根目录没有，再在归档内任意路径找名为 pack.png 的条目解到根目录。只认可有效 PNG。
    """
    icon_target = os.path.join(instance_dir, _MODPACK_ICON_NAME)
    if _is_png(icon_target):
        return True
    for name in archive.namelist():
        normalized = name.replace("\\", "/")
        if os.path.basename(normalized).lower() != _MODPACK_ICON_NAME:
            continue
        try:
            data = archive.read(name)
        except (KeyError, OSError):
            continue
        if not data:
            continue
        try:
            with open(icon_target, "wb") as out:
                out.write(data)
        except OSError:
            continue
        if _is_png(icon_target):
            return True
    return False


def _remove_work_dir(work_dir: str) -> None:
    shutil.rmtree(work_dir, ignore_errors=True)
