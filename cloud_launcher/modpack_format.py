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

"""v1.3.22.0 整合包格式识别与统一安装计划（本地导入）。

本模块把「一个本地整合包文件」解析成与具体格式无关的 :class:`ModpackPlan`，再由
:mod:`modpack_install` 的通用核心负责底座（原版库 / 资源 / 客户端 / 加载器）安装与
计划内文件落地，从而支持主流启动器 / 平台之间的整合包互导。

支持识别的格式（按 zip 根目录的清单文件判定）：

==========================  =========================  ==========================
格式                         清单文件                    文件来源
==========================  =========================  ==========================
Modrinth（``.mrpack``）      ``modrinth.index.json``     URL + 哈希，覆盖文件在包内
CurseForge（``.zip``）       ``manifest.json``          projectID/fileID，需解析
MultiMC / Prism（``.zip``）  ``mmc-pack.json``          自包含，文件在 ``minecraft/``
MCBBS（``.zip``）            ``mcbbs.packmeta``         fileApi + 哈希
离线完整包（``.zip``）       无清单，直接是游戏目录      全部文件在包内
==========================  =========================  ==========================

CurseForge 的 projectID/fileID 不直接给下载地址：官方 API 与网页均强制 API key，本模块
改用公开、免费、无需 key 的 CFWidget（``api.cfwidget.com``）按 projectID 取文件名，再
构造 ``edge.forgecdn.net`` 直链匿名下载（已实测可用）。纯标准库，UA 纯 ASCII。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field

from . import constants as C
from .download_engine import DownloadTask

# 格式键。
FORMAT_MODRINTH = "modrinth"
FORMAT_CURSEFORGE = "curseforge"
FORMAT_MULTIMC = "multimc"
FORMAT_MCBBS = "mcbbs"
FORMAT_OFFLINE = "offline"

# 各格式清单文件名。
MODRINTH_MANIFEST = "modrinth.index.json"
CURSEFORGE_MANIFEST = "manifest.json"
MULTIMC_MANIFEST = "mmc-pack.json"
MCBBS_MANIFEST = "mcbbs.packmeta"

# 可被识别为整合包的扩展名（均为 zip 容器）。
PACK_EXTENSIONS = (".mrpack", ".zip")

# CFWidget 与 CDN。
CFWIDGET_API = "https://api.cfwidget.com/{project_id}"
FORGECDN = "https://edge.forgecdn.net/files/{major}/{minor}/{name}"
CF_HTTP_TIMEOUT = 25
CF_MAX_RETRY = 6

# Modrinth 依赖字段 → 内部加载器键。
_LOADER_DEP_KEYS = (
    ("forge", C.LOADER_FORGE),
    ("neoforge", C.LOADER_NEOFORGE),
    ("fabric-loader", C.LOADER_FABRIC),
)

# MultiMC 组件 uid 前缀 → 内部加载器键。
_MMC_UID_LOADERS = (
    ("net.minecraftforge", C.LOADER_FORGE),
    ("net.neoforged", C.LOADER_NEOFORGE),
    ("net.fabricmc.fabric-loader", C.LOADER_FABRIC),
    ("org.quiltmc.quilt-loader", "quilt"),
)

# CurseForge modLoaders id 前缀 → 内部加载器键。
_CF_LOADER_PREFIXES = (
    ("forge", C.LOADER_FORGE),
    ("neoforge", C.LOADER_NEOFORGE),
    ("fabric", C.LOADER_FABRIC),
    ("quilt", "quilt"),
)


class ModpackFormatError(Exception):
    """整合包解析 / 格式识别统一异常（消息直接用于界面提示）。"""


@dataclass
class ModpackPlan:
    """与格式无关的统一安装计划。

    - ``downloads``：需要联网下载的文件，``local_path`` 已解析为实例内绝对路径；
    - ``archive_copies``：从包内直接解压的条目 ``(zip 内条目名, 实例内相对路径)``；
    - ``meta_extra``：写入 ``install_meta.json`` 的附加字段（来源 / 头像等）。
    """

    format: str
    suggested_name: str
    mc_version: str
    loader_key: str = C.LOADER_VANILLA
    loader_version: str = ""
    downloads: list[DownloadTask] = field(default_factory=list)
    archive_copies: list[tuple[str, str]] = field(default_factory=list)
    meta_extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 格式探测
# --------------------------------------------------------------------------- #
def _normalized_names(archive: zipfile.ZipFile) -> set[str]:
    return {n.replace("\\", "/").lstrip("/") for n in archive.namelist()}


def detect_format(path: str) -> str:
    """打开本地整合包（zip 容器），按根目录清单文件判定格式；无法识别回退离线包。"""
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ModpackFormatError("整合包文件损坏或无法打开，请检查文件") from exc
    with archive:
        names = _normalized_names(archive)
        if MODRINTH_MANIFEST in names:
            return FORMAT_MODRINTH
        if CURSEFORGE_MANIFEST in names:
            return _confirm_curseforge(archive, names)
        if MULTIMC_MANIFEST in names:
            return FORMAT_MULTIMC
        if MCBBS_MANIFEST in names:
            return FORMAT_MCBBS
        return FORMAT_OFFLINE


def _confirm_curseforge(archive: zipfile.ZipFile, names: set[str]) -> str:
    """根目录存在 ``manifest.json`` 时确认是 CurseForge 整合包（含 manifestType）。"""
    try:
        data = json.loads(archive.read(CURSEFORGE_MANIFEST).decode("utf-8"))
    except (ValueError, KeyError):
        # 结构不标准但确有 manifest.json，按 CurseForge 尝试解析。
        return FORMAT_CURSEFORGE
    if isinstance(data, dict) and data.get("manifestType") == "minecraftModpack":
        return FORMAT_CURSEFORGE
    # 没有 manifestType 的普通 manifest.json 也按 CurseForge 兼容处理。
    return FORMAT_CURSEFORGE


# --------------------------------------------------------------------------- #
# 入口：解析为统一计划
# --------------------------------------------------------------------------- #
def build_plan(path: str, fmt: str, should_cancel=None,
               on_phase=None) -> ModpackPlan:
    """把本地整合包按格式解析成 :class:`ModpackPlan`。"""
    if fmt == FORMAT_MODRINTH:
        return _plan_modrinth(path)
    if fmt == FORMAT_CURSEFORGE:
        return _plan_curseforge(path, should_cancel, on_phase)
    if fmt == FORMAT_MULTIMC:
        return _plan_multimc(path)
    if fmt == FORMAT_MCBBS:
        return _plan_mcbbs(path)
    if fmt == FORMAT_OFFLINE:
        return _plan_offline(path)
    raise ModpackFormatError("暂不支持这个整合包格式")


def _read_archive_json(archive: zipfile.ZipFile, name: str) -> dict:
    try:
        data = json.loads(archive.read(name).decode("utf-8"))
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise ModpackFormatError("整合包清单解析失败：%s" % name) from exc
    if not isinstance(data, dict):
        raise ModpackFormatError("整合包清单格式异常：%s" % name)
    return data


def _assert_loader_supported(loader_key: str) -> None:
    if loader_key == "quilt":
        raise ModpackFormatError(
            "暂不支持 Quilt 整合包，请选 Fabric / Forge / NeoForge 的整合包")


# --------------------------------------------------------------------------- #
# Modrinth
# --------------------------------------------------------------------------- #
def _plan_modrinth(path: str) -> ModpackPlan:
    with zipfile.ZipFile(path) as archive:
        names = _normalized_names(archive)
        index = _read_archive_json(archive, MODRINTH_MANIFEST)
    deps = index.get("dependencies") or {}
    mc = str(deps.get("minecraft") or "").strip()
    if not mc:
        raise ModpackFormatError("整合包未声明依赖的 Minecraft 版本")
    loader_key, loader_version = _resolve_modrinth_loader(deps)
    _assert_loader_supported(loader_key)

    downloads = _modrinth_downloads(index)
    copies = _prefixed_copies(names, ("overrides/", "client-overrides/"))
    plan = ModpackPlan(
        format=FORMAT_MODRINTH,
        suggested_name=str(index.get("name") or "").strip(),
        mc_version=mc,
        loader_key=loader_key,
        loader_version=loader_version,
        downloads=downloads,
        archive_copies=copies,
        meta_extra={"source": "modrinth"},
    )
    return plan


def _resolve_modrinth_loader(deps: dict) -> tuple[str, str]:
    if "quilt-loader" in deps:
        return "quilt", str(deps.get("quilt-loader") or "")
    for dep_key, loader_key in _LOADER_DEP_KEYS:
        value = str(deps.get(dep_key) or "").strip()
        if value:
            return loader_key, value
    return C.LOADER_VANILLA, ""


def _modrinth_downloads(index: dict) -> list[DownloadTask]:
    """把 index 里客户端需要的文件转成下载任务（占位 local_path，核心前补实例目录）。"""
    tasks: list[DownloadTask] = []
    for entry in index.get("files") or []:
        env = entry.get("env") or {}
        client_need = str(env.get("client") or "required").strip().lower()
        if client_need == "unsupported":
            continue
        downloads = [u for u in (entry.get("downloads") or []) if u]
        if not downloads:
            continue
        rel_path = str(entry.get("path") or "")
        hashes = entry.get("hashes") or {}
        tasks.append(DownloadTask(
            url=downloads[0],
            local_path=rel_path,  # 相对路径，核心安装前统一转实例内绝对路径
            size=int(entry.get("fileSize") or 0),
            sha1=str(hashes.get("sha1") or ""),
            mirror_url=downloads[1] if len(downloads) > 1 else None,
            extra_urls=downloads[2:],
            label=os.path.basename(rel_path),
        ))
    return tasks


# --------------------------------------------------------------------------- #
# CurseForge
# --------------------------------------------------------------------------- #
def _plan_curseforge(path: str, should_cancel, on_phase) -> ModpackPlan:
    with zipfile.ZipFile(path) as archive:
        names = _normalized_names(archive)
        manifest = _read_archive_json(archive, CURSEFORGE_MANIFEST)

    mc_block = manifest.get("minecraft") or {}
    mc = str(mc_block.get("version") or "").strip()
    if not mc:
        raise ModpackFormatError("CurseForge 整合包未声明 Minecraft 版本")
    loader_key, loader_version = _resolve_cf_loader(mc_block.get("modLoaders") or [])
    _assert_loader_supported(loader_key)

    refs = [f for f in (manifest.get("files") or [])
            if f.get("required", True)]
    # 按 projectID 调 CFWidget 解析 fileID → 文件名，构造 CDN 直链。
    downloads: list[DownloadTask] = []
    resolved = _resolve_cf_files(refs, should_cancel, on_phase)
    for rel_path, url, size in resolved:
        downloads.append(DownloadTask(
            url=url,
            local_path=rel_path,
            size=size,
            label=os.path.basename(rel_path),
        ))

    override_dir = str(manifest.get("overrides") or "overrides").replace("\\", "/")
    override_prefix = override_dir.strip("/") + "/"
    copies = _prefixed_copies(names, (override_prefix,))
    plan = ModpackPlan(
        format=FORMAT_CURSEFORGE,
        suggested_name=str(manifest.get("name") or "").strip(),
        mc_version=mc,
        loader_key=loader_key,
        loader_version=loader_version,
        downloads=downloads,
        archive_copies=copies,
        meta_extra={"source": "curseforge"},
    )
    return plan


def _resolve_cf_loader(mod_loaders: list) -> tuple[str, str]:
    primary = next((m for m in mod_loaders if m.get("primary")), None)
    chosen = primary or (mod_loaders[0] if mod_loaders else None)
    if not chosen:
        return C.LOADER_VANILLA, ""
    raw_id = str(chosen.get("id") or "").strip()
    if not raw_id:
        return C.LOADER_VANILLA, ""
    if raw_id.startswith("quilt"):
        return "quilt", raw_id.split("-", 1)[1] if "-" in raw_id else ""
    for prefix, loader_key in _CF_LOADER_PREFIXES:
        if raw_id.startswith(prefix + "-"):
            return loader_key, raw_id[len(prefix) + 1:]
    return C.LOADER_VANILLA, ""


def _resolve_cf_files(refs: list, should_cancel, on_phase) -> list[tuple[str, str, int]]:
    """对每个 projectID 拉一次 CFWidget，建立 fileID→文件名映射并构造 CDN 直链。"""
    grouped: dict[int, set[int]] = {}
    for ref in refs:
        try:
            pid = int(ref.get("projectID"))
            fid = int(ref.get("fileID"))
        except (TypeError, ValueError):
            continue
        grouped.setdefault(pid, set()).add(fid)

    result: list[tuple[str, str, int]] = []
    total = len(grouped)
    for index, (pid, file_ids) in enumerate(sorted(grouped.items()), start=1):
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("已取消")
        if callable(on_phase):
            on_phase(index, total, pid)
        name_map = _fetch_cfwidget_names(pid, should_cancel)
        for fid in file_ids:
            name, size = name_map.get(fid, ("", 0))
            if not name:
                raise ModpackFormatError(
                    "CurseForge 文件解析失败（project %s / file %s），"
                    "可能已被作者下架或禁止第三方下载" % (pid, fid))
            url = _forgecdn_url(fid, name)
            result.append(("mods/" + name, url, size))
    return result


def _ua_header() -> dict:
    return {"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)",
            "Accept": "application/json"}


def _fetch_cfwidget_names(project_id: int, should_cancel) -> dict[int, tuple[str, int]]:
    """拉取项目全部文件，返回 ``fileID → (文件名, 大小)``；处理 202 排队。"""
    url = CFWIDGET_API.format(project_id=project_id)
    body = _http_get_with_queue(url, should_cancel)
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError as exc:
        raise ModpackFormatError("CFWidget 返回内容解析失败") from exc
    files = data.get("files") or []
    mapping: dict[int, tuple[str, int]] = {}
    for item in files:
        try:
            fid = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            mapping[fid] = (name, int(item.get("filesize") or 0))
    return mapping


def _http_get_with_queue(url: str, should_cancel) -> bytes:
    last_msg = ""
    for attempt in range(CF_MAX_RETRY):
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("已取消")
        req = urllib.request.Request(url, headers=_ua_header())
        try:
            with urllib.request.urlopen(req, timeout=CF_HTTP_TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 202:
                # 项目不在本地库，已排队，几秒后重试。
                time.sleep(2.5)
                continue
            if exc.code == 301:
                loc = exc.headers.get("Location")
                if loc:
                    url = urllib.parse.urljoin(url, loc)
                    continue
            last_msg = "HTTP %s" % exc.code
        except urllib.error.URLError as exc:
            last_msg = str(exc.reason)
            time.sleep(2.0)
        except (TimeoutError, OSError) as exc:
            last_msg = type(exc).__name__
            time.sleep(2.0)
    raise ModpackFormatError("解析 CurseForge 项目超时或失败：%s" % last_msg)


def _forgecdn_url(file_id: int, name: str) -> str:
    return FORGECDN.format(
        major=file_id // 1000,
        minor="%03d" % (file_id % 1000),
        name=urllib.parse.quote(name),
    )


# --------------------------------------------------------------------------- #
# MultiMC / Prism
# --------------------------------------------------------------------------- #
def _plan_multimc(path: str) -> ModpackPlan:
    with zipfile.ZipFile(path) as archive:
        names = _normalized_names(archive)
        pack = _read_archive_json(archive, MULTIMC_MANIFEST)

    mc, loader_key, loader_version = _resolve_mmc_components(
        pack.get("components") or [])
    _assert_loader_supported(loader_key)

    # MultiMC/Prism 实例文件在 minecraft/ 下；个别导出直接在根，两种都兼容。
    has_mc_root = any(n.startswith("minecraft/") for n in names)
    prefixes = ("minecraft/",) if has_mc_root else ("",)
    copies = _prefixed_copies(names, prefixes,
                              skip=(MULTIMC_MANIFEST, "instance.cfg"))
    suggested = _multimc_instance_name(path)
    return ModpackPlan(
        format=FORMAT_MULTIMC,
        suggested_name=suggested,
        mc_version=mc,
        loader_key=loader_key,
        loader_version=loader_version,
        downloads=[],
        archive_copies=copies,
        meta_extra={"source": "multimc"},
    )


def _resolve_mmc_components(components: list) -> tuple[str, str, str]:
    mc = ""
    loader_key = C.LOADER_VANILLA
    loader_version = ""
    for comp in components:
        uid = str(comp.get("uid") or "")
        version = str(comp.get("version") or "").strip()
        if uid == "net.minecraft":
            mc = version
            continue
        for uid_prefix, mapped in _MMC_UID_LOADERS:
            if uid == uid_prefix or uid.startswith(uid_prefix + "."):
                loader_key = mapped
                loader_version = version
                break
    if not mc:
        raise ModpackFormatError("MultiMC 整合包未声明 net.minecraft 组件")
    return mc, loader_key, loader_version


def _multimc_instance_name(path: str) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            if "instance.cfg" in archive.namelist():
                raw = archive.read("instance.cfg").decode("utf-8", "ignore")
                for line in raw.splitlines():
                    if line.startswith("name="):
                        return line[5:].strip()
    except (zipfile.BadZipFile, OSError):
        pass
    return ""


# --------------------------------------------------------------------------- #
# MCBBS
# --------------------------------------------------------------------------- #
def _plan_mcbbs(path: str) -> ModpackPlan:
    with zipfile.ZipFile(path) as archive:
        names = _normalized_names(archive)
        meta = _read_archive_json(archive, MCBBS_MANIFEST)

    mc = str(meta.get("minecraft") or meta.get("gameVersion") or "").strip()
    loader_key, loader_version = _resolve_mcbbs_addons(meta.get("addons") or [])
    _assert_loader_supported(loader_key)
    file_api = str(meta.get("fileApi") or "").strip()
    downloads: list[DownloadTask] = []
    for item in meta.get("files") or []:
        rel_path = str(item.get("path") or "").strip()
        hash_value = str(item.get("hash") or "").strip()
        if not rel_path or not hash_value:
            continue
        url = (file_api + hash_value) if file_api else ""
        if not url:
            continue
        downloads.append(DownloadTask(
            url=url,
            local_path=rel_path,
            size=int(item.get("size") or 0),
            label=os.path.basename(rel_path),
        ))
    copies = _prefixed_copies(names, ("overrides/",))
    return ModpackPlan(
        format=FORMAT_MCBBS,
        suggested_name=str(meta.get("name") or "").strip(),
        mc_version=mc,
        loader_key=loader_key,
        loader_version=loader_version,
        downloads=downloads,
        archive_copies=copies,
        meta_extra={"source": "mcbbs"},
    )


def _resolve_mcbbs_addons(addons: list) -> tuple[str, str]:
    for addon in addons:
        addon_id = str(addon.get("id") or "")
        version = str(addon.get("version") or "").strip()
        if addon_id in ("forge", "neoforge", "fabric"):
            key = {"forge": C.LOADER_FORGE, "neoforge": C.LOADER_NEOFORGE,
                   "fabric": C.LOADER_FABRIC}[addon_id]
            return key, version
        if addon_id == "quilt":
            return "quilt", version
    return C.LOADER_VANILLA, ""


# --------------------------------------------------------------------------- #
# 离线完整包
# --------------------------------------------------------------------------- #
def _plan_offline(path: str) -> ModpackPlan:
    with zipfile.ZipFile(path) as archive:
        names = _normalized_names(archive)
    # 兼容两种打包：根目录直接是游戏目录，或外层包了 .minecraft/。
    has_dot_mc = any(n.startswith(".minecraft/") for n in names)
    prefixes = (".minecraft/",) if has_dot_mc else ("",)
    copies = _prefixed_copies(names, prefixes)
    # 离线包没有清单，无法可靠判定 MC/加载器，交由核心按目录内容推断 / 要求用户确认。
    return ModpackPlan(
        format=FORMAT_OFFLINE,
        suggested_name=os.path.splitext(os.path.basename(path))[0],
        mc_version="",
        loader_key=C.LOADER_VANILLA,
        loader_version="",
        downloads=[],
        archive_copies=copies,
        meta_extra={"source": "offline"},
    )


# --------------------------------------------------------------------------- #
# 覆盖文件收集（通用）
# --------------------------------------------------------------------------- #
def _prefixed_copies(names: set[str], prefixes: tuple[str, ...],
                     skip: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """把匹配前缀的条目转成 ``(原始条目, 去前缀后的相对路径)``，跳过目录与清单本身。"""
    copies: list[tuple[str, str]] = []
    for name in sorted(names):
        if name in skip or name.endswith("/"):
            continue
        prefix = next((p for p in prefixes if p and name.startswith(p)), "")
        if prefixes and not prefix and "" not in prefixes:
            continue
        rel = name[len(prefix):] if prefix else name
        if not rel:
            continue
        copies.append((name, rel))
    return copies
