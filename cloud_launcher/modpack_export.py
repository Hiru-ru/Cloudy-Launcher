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

"""v1.3.22.0 整合包导出（打包）后端。

把一个已安装实例按所选格式打成标准整合包压缩包，纯标准库、不修改源实例目录：

==========================  ==================================================
格式                        包内结构
==========================  ==================================================
离线完整包（``.zip``）       根目录即游戏内容，无清单
Modrinth（``.mrpack``）     ``modrinth.index.json`` + ``client-overrides/``；
                            mod jar 按 sha1 反查 Modrinth，查不到的进 overrides
MultiMC / Prism（``.zip``） ``instance.cfg`` + ``mmc-pack.json`` + ``minecraft/``
CurseForge（``.zip``）      ``manifest.json`` + ``overrides/``
MCBBS（``.zip``）           ``mcbbs.packmeta`` + ``overrides/``
==========================  ==================================================

说明：本地实例元数据只记录 MC / 加载器 / 加载器版本，不保存每个 mod 的平台
projectID / fileID 或哈希映射。因此 CurseForge / MCBBS 无法回溯规范平台 ID，
对应清单的 ``files`` 留空，mod 文件随 ``overrides/`` 一并带出（退化壳）；界面结果
里会如实标注未能映射的模组。Modrinth 可按文件 sha1 在线反查，反查不到的同样兜底
进 ``client-overrides/``。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field

from . import constants as C
from . import game_dirs
from . import modpack_format as mpf
from .modpack_install import ModpackError

# --------------------------------------------------------------------------- #
# 阶段与常量
# --------------------------------------------------------------------------- #
PHASE_SCAN = 0
PHASE_RESOLVE = 1
PHASE_PACK = 2
PHASE_LABELS = {
    PHASE_SCAN: "正在扫描实例文件",
    PHASE_RESOLVE: "正在匹配 Modrinth 模组",
    PHASE_PACK: "正在写入压缩包",
}

MODRINTH_VERSION_FILE_API = (
    "https://api.modrinth.com/v2/version_file/{sha1}?algorithm=sha1")
MR_HTTP_TIMEOUT = 20

# 导出格式 → 界面标签 / 默认扩展名。
EXPORT_FORMAT_LABELS = {
    mpf.FORMAT_OFFLINE: "离线完整包 (.zip)",
    mpf.FORMAT_MODRINTH: "Modrinth (.mrpack)",
    mpf.FORMAT_MULTIMC: "MultiMC / Prism (.zip)",
    mpf.FORMAT_CURSEFORGE: "CurseForge (.zip)",
    mpf.FORMAT_MCBBS: "MCBBS (.zip)",
}
EXPORT_EXTENSIONS = {
    mpf.FORMAT_MODRINTH: ".mrpack",
    mpf.FORMAT_OFFLINE: ".zip",
    mpf.FORMAT_MULTIMC: ".zip",
    mpf.FORMAT_CURSEFORGE: ".zip",
    mpf.FORMAT_MCBBS: ".zip",
}

# 排除的顶层目录：底座库 / 原生库 / 安装临时 / 启动器自身配置 / 运行缓存 / 个人存档截图。
_EXCLUDED_TOP_DIRS = {
    "libraries", "natives", "forge_work", "modpack_work", "work", "pcl",
    "blob_cache", ".puzzle_cache", "cache", "crash_reports", "logs",
    "saves", "screenshots", "versions", "run", "tmp", "temp",
}
# 排除的顶层文件（底座 jar / 版本 profile / 启动器元数据 / 提取的图标）。
_EXCLUDED_TOP_FILES = {"install_meta.json", "pack.png"}

# 内部加载器键 → 各平台标识。
_MR_DEP_KEY = {
    C.LOADER_FABRIC: "fabric-loader",
    C.LOADER_FORGE: "forge",
    C.LOADER_NEOFORGE: "neoforge",
}
_MMC_UID = {
    C.LOADER_FABRIC: "net.fabricmc.fabric-loader",
    C.LOADER_FORGE: "net.minecraftforge",
    C.LOADER_NEOFORGE: "net.neoforged",
}
_CF_LOADER_PREFIX = {
    C.LOADER_FABRIC: "fabric",
    C.LOADER_FORGE: "forge",
    C.LOADER_NEOFORGE: "neoforge",
}


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class ExportFile:
    """待打包的单个实例文件。"""

    abs_path: str
    rel_path: str          # 相对实例目录，``/`` 分隔
    size: int
    sha1: str = ""


@dataclass
class ExportResult:
    """导出结果，供界面提示与复核。"""

    alias: str
    format: str
    output_path: str
    file_count: int
    size_bytes: int
    mapped_mods: int = 0
    fallback_mods: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 文件收集与分类
# --------------------------------------------------------------------------- #
def _is_excluded_rel(rel_path: str) -> bool:
    """判定实例内相对路径是否属于底座 / 运行时 / 个人数据，不应进包。"""
    top = rel_path.split("/", 1)[0]
    if top.lower() in _EXCLUDED_TOP_DIRS:
        return True
    if "/" not in rel_path:
        low = top.lower()
        if low in _EXCLUDED_TOP_FILES:
            return True
        # 根目录的 .jar 是客户端核心、.json 是版本 profile / 元数据，均不进包。
        if low.endswith(".jar") or low.endswith(".json"):
            return True
    return False


def _collect_files(alias: str) -> list[ExportFile]:
    """扫描实例目录，返回纳入打包的文件列表（按相对路径升序）。"""
    inst_dir = game_dirs.version_dir(alias)
    if not os.path.isdir(inst_dir):
        raise ModpackError("实例目录不存在：%s" % alias)

    files: list[ExportFile] = []
    for root, dirs, names in os.walk(inst_dir):
        # 原地过滤排除目录，避免下钻。
        dirs[:] = [d for d in dirs if d.lower() not in _EXCLUDED_TOP_DIRS]
        for name in names:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, inst_dir).replace("\\", "/")
            if _is_excluded_rel(rel_path):
                continue
            if not os.path.isfile(abs_path):
                continue
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                continue
            files.append(ExportFile(abs_path=abs_path, rel_path=rel_path, size=size))

    files.sort(key=lambda f: f.rel_path)
    return files


def _sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(256 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Modrinth 在线反查
# --------------------------------------------------------------------------- #
def _mr_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)",
            "Accept": "application/json",
        },
    )


def _resolve_modrinth(sha1: str) -> dict | None:
    """按 sha1 反查 Modrinth 版本；返回 ``{url, size, sha1}``，查不到 / 失败返回 ``None``。"""
    if not sha1:
        return None
    url = MODRINTH_VERSION_FILE_API.format(sha1=sha1)
    try:
        with urllib.request.urlopen(_mr_request(url), timeout=MR_HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 404 = 该文件未被 Modrinth 收录；其余状态码按兜底处理。
        if exc.code != 404:
            return None
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    if not isinstance(data, dict):
        return None
    files = data.get("files") or []
    chosen = next((f for f in files if f.get("primary")), None)
    chosen = chosen or (files[0] if files else None)
    if not isinstance(chosen, dict):
        return None
    download_url = str(chosen.get("url") or "").strip()
    if not download_url:
        return None
    hashes = chosen.get("hashes") or {}
    return {
        "url": download_url,
        "size": int(chosen.get("size") or 0),
        "sha1": str(hashes.get("sha1") or sha1),
    }


# --------------------------------------------------------------------------- #
# 清单构造
# --------------------------------------------------------------------------- #
def _mr_dependencies(mc: str, loader: str, loader_version: str) -> dict:
    deps: dict[str, str] = {"minecraft": mc}
    dep_key = _MR_DEP_KEY.get(loader)
    if dep_key and loader_version:
        deps[dep_key] = loader_version
    return deps


def _build_mr_index(name: str, mc: str, loader: str, loader_version: str,
                    mr_files: list[dict]) -> dict:
    return {
        "formatVersion": 1,
        "game": "minecraft",
        "name": name,
        "versionId": "export-" + time.strftime("%Y%m%d-%H%M%S"),
        "dependencies": _mr_dependencies(mc, loader, loader_version),
        "files": mr_files,
    }


def _build_cf_manifest(name: str, mc: str, loader: str, loader_version: str) -> dict:
    mod_loaders: list[dict] = []
    prefix = _CF_LOADER_PREFIX.get(loader)
    if prefix and loader_version:
        mod_loaders.append({"id": f"{prefix}-{loader_version}", "primary": True})
    return {
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": name,
        "version": "1.0.0",
        "author": C.APP_UA_NAME,
        "minecraft": {"version": mc, "modLoaders": mod_loaders},
        # 本地无平台 ID 可回溯，files 留空，mod 走 overrides 带出。
        "files": [],
        "overrides": "overrides",
    }


def _build_mmc_pack(mc: str, loader: str, loader_version: str) -> dict:
    components: list[dict] = [{
        "uid": "net.minecraft",
        "version": mc,
        "important": True,
        "cachedName": "Minecraft",
        "cachedVersion": mc,
    }]
    uid = _MMC_UID.get(loader)
    if uid and loader_version:
        components.append({
            "uid": uid,
            "version": loader_version,
            "important": True,
            "cachedName": C.LOADER_LABELS.get(loader, loader),
            "cachedVersion": loader_version,
        })
    return {"components": components, "formatVersion": 1}


def _build_mmc_instance_cfg(name: str) -> str:
    return f"InstanceType=OneSix\nname={name}\n"


def _build_mcbbs_meta(name: str, mc: str, loader: str, loader_version: str) -> dict:
    addons: list[dict] = []
    if loader != C.LOADER_VANILLA and loader_version:
        addons.append({"id": loader, "version": loader_version})
    return {"name": name, "minecraft": mc, "addons": addons, "files": []}


def _json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def export_instance(alias: str, fmt: str, output_path: str,
                    should_cancel=None, on_phase=None,
                    on_progress=None) -> ExportResult:
    """把实例 ``alias`` 按格式 ``fmt`` 打包到 ``output_path``。

    ``on_phase(index, label)`` 阶段回调；``on_progress(pct, done, total, speed,
    remaining)`` 进度回调。取消时抛 :class:`InterruptedError`，由 Worker 静默处理。
    """
    if fmt not in EXPORT_FORMAT_LABELS:
        raise ModpackError("暂不支持这个打包格式")

    def cancel_check() -> bool:
        return callable(should_cancel) and should_cancel()

    def emit_phase(index: int, label: str) -> None:
        if callable(on_phase):
            on_phase(index, label)

    # 1) 读取实例元数据。
    emit_phase(PHASE_SCAN, PHASE_LABELS[PHASE_SCAN])
    meta = game_dirs.read_install_meta(alias)
    mc = str(meta.get("mc_version") or "").strip()
    loader = str(meta.get("loader") or C.LOADER_VANILLA)
    loader_version = str(meta.get("loader_version") or "").strip()
    if not mc:
        mc = game_dirs.local_version_base(alias)

    files = _collect_files(alias)
    if not files:
        raise ModpackError("实例内没有可打包的游戏内容（mods / config 等为空）")

    notes: list[str] = []
    fallback_mods: list[str] = []
    mapped_mods = 0

    # 2) 按格式分流文件、构造清单条目。
    entries: list[tuple[str, str]] = []          # (zip 内名, 本地绝对路径)
    manifest_entries: list[tuple[str, bytes]] = []
    mr_files: list[dict] = []

    if fmt == mpf.FORMAT_MODRINTH:
        emit_phase(PHASE_RESOLVE, PHASE_LABELS[PHASE_RESOLVE])
        total = len(files)
        for index, f in enumerate(files, start=1):
            if cancel_check():
                raise InterruptedError("已取消")
            is_mod_jar = (f.rel_path.startswith("mods/")
                          and f.rel_path.lower().endswith(".jar"))
            if is_mod_jar:
                f.sha1 = _sha1_file(f.abs_path)
                resolved = _resolve_modrinth(f.sha1)
                if resolved:
                    mr_files.append({
                        "path": f.rel_path,
                        "hashes": {"sha1": resolved["sha1"]},
                        "downloads": [resolved["url"]],
                        "fileSize": resolved["size"] or f.size,
                        "env": {"client": "required"},
                    })
                    mapped_mods += 1
                else:
                    entries.append(("client-overrides/" + f.rel_path, f.abs_path))
                    fallback_mods.append(os.path.basename(f.rel_path))
            else:
                entries.append(("client-overrides/" + f.rel_path, f.abs_path))
            if callable(on_progress):
                on_progress(100.0 * index / max(total, 1), 0, 0, 0.0, total - index)
        if fallback_mods:
            notes.append("有 %d 个模组未在 Modrinth 收录，已随覆盖文件带出：%s"
                         % (len(fallback_mods), "、".join(fallback_mods[:5])
                            + (" 等" if len(fallback_mods) > 5 else "")))
        index_json = _build_mr_index(alias, mc, loader, loader_version, mr_files)
        manifest_entries.append((mpf.MODRINTH_MANIFEST, _json_bytes(index_json)))

    elif fmt == mpf.FORMAT_MULTIMC:
        prefix = "minecraft/"
        for f in files:
            entries.append((prefix + f.rel_path, f.abs_path))
        manifest_entries.append((
            mpf.MULTIMC_MANIFEST,
            _json_bytes(_build_mmc_pack(mc, loader, loader_version))))
        manifest_entries.append((
            "instance.cfg", _build_mmc_instance_cfg(alias).encode("utf-8")))

    elif fmt == mpf.FORMAT_CURSEFORGE:
        prefix = "overrides/"
        for f in files:
            entries.append((prefix + f.rel_path, f.abs_path))
        manifest_entries.append((
            mpf.CURSEFORGE_MANIFEST,
            _json_bytes(_build_cf_manifest(alias, mc, loader, loader_version))))
        notes.append("本地无法回溯 CurseForge 模组 ID，模组已随 overrides 带出，"
                     "清单未包含独立下载条目。")

    elif fmt == mpf.FORMAT_MCBBS:
        prefix = "overrides/"
        for f in files:
            entries.append((prefix + f.rel_path, f.abs_path))
        manifest_entries.append((
            mpf.MCBBS_MANIFEST,
            _json_bytes(_build_mcbbs_meta(alias, mc, loader, loader_version))))
        notes.append("本地无法回溯 MCBBS 模组 ID，模组已随 overrides 带出。")

    else:  # offline
        for f in files:
            entries.append((f.rel_path, f.abs_path))

    # 3) 写入压缩包。
    emit_phase(PHASE_PACK, PHASE_LABELS[PHASE_PACK])
    out_dir = os.path.dirname(os.path.abspath(output_path))
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        raise ModpackError("无法创建输出目录：%s" % exc) from exc

    total_bytes = sum(f.size for f in files)
    done_bytes = 0
    written = 0
    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in manifest_entries:
                if cancel_check():
                    raise InterruptedError("已取消")
                archive.writestr(name, data)
            for zip_name, abs_path in entries:
                if cancel_check():
                    raise InterruptedError("已取消")
                archive.write(abs_path, zip_name)
                done_bytes += os.path.getsize(abs_path)
                written += 1
                if callable(on_progress):
                    pct = 100.0 * done_bytes / max(total_bytes, 1)
                    on_progress(pct, done_bytes, total_bytes, 0.0,
                                len(entries) - written)
    except OSError as exc:
        raise ModpackError("写入压缩包失败：%s" % exc) from exc

    size_bytes = 0
    try:
        size_bytes = os.path.getsize(output_path)
    except OSError:
        pass

    return ExportResult(
        alias=alias,
        format=fmt,
        output_path=output_path,
        file_count=written + len(manifest_entries),
        size_bytes=size_bytes,
        mapped_mods=mapped_mods,
        fallback_mods=fallback_mods,
        notes=notes,
    )
