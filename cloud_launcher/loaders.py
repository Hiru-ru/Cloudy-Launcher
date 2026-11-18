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

"""Forge / NeoForge / Fabric / OptiFine 四个加载器的支持性探测、结果缓存与安装 profile 构建。

v1.2.12.0 新增。纯 Python 标准库 ``urllib`` + ``json`` + ``xml.etree.ElementTree`` +
``zipfile``，不引入第三方 HTTP / 解析库；User-Agent 保持纯 ASCII。

支持性探测口径（2026-11-02 本机端点实测；v1.2.12.1 修正新年度版本号误判）：

- **Fabric**：官方 ``meta.fabricmc.net`` 与 BMCLAPI 镜像双端点；loader 列表非空，
  且对应 ``profile/json`` 双端点能拉回有效合并层（含 mainClass / inheritsFrom）才算
  支持。新年度版本号列表里 ``intermediary.version`` 为 ``0.0.0`` 占位，不再用它等值判定；
- **Forge**：BMCLAPI ``/forge/minecraft/<mc>`` 列表；空列表或 404 即不支持；
- **NeoForge**：官方 maven 本机不可达，走 BMCLAPI ``/maven/net/neoforged/neoforge/
  maven-metadata.xml``；旧版本号走内置「前缀 ↔ MC 版本」映射表，新年度版本号（两段纯数字，
  如 ``26.3``）与 NeoForge 前缀同名直配；快照号不做同名匹配；
- **OptiFine**：BMCLAPI ``/optifine/<mc>`` 列表；空数组即不支持；BMCLAPI 不托管 jar 二进制，
  真实下载地址由官方站广告中转页解析得到。

探测结果按 MC 版本精确键缓存到 ``yd/loader_support_cache.json``：同一版本下次打开直接读缓存、
不重新联网；只有清单中出现缓存里没有的新版本才重新探测对应加载器。
"""
from __future__ import annotations

import io
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone

from . import constants as C
from .resources import data_dir

_BEIJING_TZ = timezone(timedelta(hours=8))
_PROBE_TIMEOUT = C.META_PROBE_TIMEOUT
_UNAVAILABLE = C.LOADER_UNAVAILABLE_TEXT
# NeoForge 安装包可用性校验：最多探这么多个候选版本，最多保留这么多个已验证可用的。
_NEOFORGE_PROBE_LIMIT = 12
_NEOFORGE_VERIFIED_KEEP = 5


# --------------------------------------------------------------------------- #
# 结果模型与缓存
# --------------------------------------------------------------------------- #
def _result(available: bool, version: str = "", detail: str = "",
            label: str = "", versions: list[dict] | None = None) -> dict:
    return {
        "available": bool(available),
        "version": str(version or ""),
        "detail": str(detail or ""),
        "label": str(label or C.LOADER_LABELS.get(C.LOADER_VANILLA, "")),
        # 可展开的全部候选版本：``[{"version": str, "time": str}]``，新 → 旧排序；
        # time 端点缺失时留空串，由界面只展示版本号。
        "versions": [dict(item) for item in (versions or [])],
    }


def _sort_key(version: str) -> tuple:
    """版本号按段数值降序比较；非数字段记 0，兜底不抛异常。"""
    return tuple(int(part) if part.isdigit() else 0 for part in str(version).split("."))


def _cache_path() -> str:
    return os.path.join(data_dir(), C.LOADER_SUPPORT_CACHE_FILENAME)


def _load_cache() -> dict:
    path = _cache_path()
    if not os.path.isfile(path):
        return {"schema": C.LOADER_CACHE_SCHEMA, "versions": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # schema 不匹配（旧版本落盘的误判结果口径已变）时整体作废，按空缓存重建。
        if not isinstance(saved, dict) or saved.get("schema") != C.LOADER_CACHE_SCHEMA:
            return {"schema": C.LOADER_CACHE_SCHEMA, "versions": {}}
        if not isinstance(saved.get("versions"), dict):
            return {"schema": C.LOADER_CACHE_SCHEMA, "versions": {}}
        return saved
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"schema": C.LOADER_CACHE_SCHEMA, "versions": {}}


def _save_cache(cache: dict) -> None:
    directory = os.path.dirname(_cache_path())
    os.makedirs(directory, exist_ok=True)
    cache["schema"] = C.LOADER_CACHE_SCHEMA
    cache["fetched_at"] = datetime.now(_BEIJING_TZ).isoformat(timespec="seconds")
    tmp = _cache_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _cache_path())


# --------------------------------------------------------------------------- #
# 通用 HTTP
# --------------------------------------------------------------------------- #
def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"},
    )


def _fetch_json(url: str, should_cancel=None) -> dict | list:
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("加载器探测已被取消")
    with urllib.request.urlopen(_request(url), timeout=_PROBE_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str, should_cancel=None) -> str:
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("加载器探测已被取消")
    with urllib.request.urlopen(_request(url), timeout=_PROBE_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def _artifact_available(url: str, timeout: float | None = None,
                        should_cancel=None, attempts: int = 2) -> bool:
    """HEAD 探测远端工件是否真实存在。

    镜像站对「已发布为新年度版本号、但尚未同步二进制」的加载器版本只会返回 404
    （例如 BMCL 对 NeoForge 26.3.0.x 的 metadata 有条目、installer 却全部 404）。
    探测阶段先确认安装包真能拿到，才不会出现「卡片写可以添加、下载必然失败」。
    """
    for _ in range(max(1, attempts)):
        if callable(should_cancel) and should_cancel():
            return False
        try:
            request = _request(url)
            request.method = "HEAD"
            with urllib.request.urlopen(request, timeout=timeout or _PROBE_TIMEOUT) as response:
                status = int(getattr(response, "status", 200) or 200)
                if 200 <= status < 400:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError, ValueError):
            continue
    return False


# --------------------------------------------------------------------------- #
# Fabric
# --------------------------------------------------------------------------- #
def _probe_fabric(mc: str, should_cancel=None) -> dict:
    """探测 Fabric 支持性：loader 列表非空，且对应 profile/json 能真实拉取成功才算支持。

    v1.2.12.1 修正：新年度版本号（如 26.3）列表里 ``intermediary.version`` 为 ``0.0.0``
    占位，不再用它做严格等值判定；改为以 profile/json 双端点能否返回有效合并层为准。
    旧版本端点 400 / 404 / 空列表 / profile 拉取失败仍按不支持兜底。

    v1.3.3.3 起新增第三个回退源 Legacy Fabric：标准 Fabric 与 BMCL 对 1.12.2 等
    老版本返回空（400/500），Legacy Fabric 独立 meta 提供同一套 loader 的延续支持。
    """
    # (列表端点模板, 对应 profile 端点模板)；前面的源优先，逐个回退。
    source_templates = (
        (C.FABRIC_LIST_OFFICIAL, C.FABRIC_PROFILE_OFFICIAL),
        (C.FABRIC_LIST_MIRROR, C.FABRIC_PROFILE_MIRROR),
        (C.LEGACYFABRIC_LIST_URL, C.LEGACYFABRIC_PROFILE_URL),
    )
    for list_tpl, profile_tpl in source_templates:
        list_url = list_tpl.format(mc=mc)
        try:
            data = _fetch_json(list_url, should_cancel=should_cancel)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
                json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, list) or not data:
            continue

        # 稳定 loader 优先；列表顺序即新 → 旧。仅稳定版本进可选列表，避免数百条
        # 实验版塞满详情页；稳定集合为空时再退回全量兜底。
        stable_entries = [e for e in data if (e.get("loader") or {}).get("stable")]
        ordered_entries = stable_entries or data
        versions: list[dict] = []
        for entry in ordered_entries:
            ver = str((entry.get("loader") or {}).get("version") or "")
            if ver:
                versions.append({"version": ver, "time": ""})
        if not versions:
            continue

        # 取最新 stable loader 版本；profile/json 真实拉取成功才确认支持。
        loader_version = versions[0]["version"]
        profile_url = profile_tpl.format(mc=mc, loader=loader_version)
        try:
            profile = _fetch_json(profile_url, should_cancel=should_cancel)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
                json.JSONDecodeError, ValueError):
            continue
        if isinstance(profile, dict) and (
            profile.get("mainClass") or profile.get("inheritsFrom")
        ):
            return _result(True, loader_version, C.LOADER_AVAILABLE_TEXT,
                           C.LOADER_LABELS[C.LOADER_FABRIC], versions=versions)
    return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FABRIC])


# --------------------------------------------------------------------------- #
# Forge
# --------------------------------------------------------------------------- #
def _probe_forge(mc: str, should_cancel=None) -> dict:
    url = C.FORGE_LIST_URL.format(mc=mc)
    try:
        data = _fetch_json(url, should_cancel=should_cancel)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FORGE])
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FORGE])
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError):
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FORGE])

    if not isinstance(data, list) or not data:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FORGE])

    def _build_number(entry: dict) -> int:
        try:
            return int(entry.get("build") or 0)
        except (TypeError, ValueError):
            return 0

    ordered = sorted(data, key=_build_number, reverse=True)
    versions: list[dict] = []
    for entry in ordered:
        ver = str(entry.get("version") or "")
        if ver:
            versions.append({"version": ver, "time": str(entry.get("modified") or "")})
    if not versions:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_FORGE])
    latest = versions[0]["version"]
    return _result(True, latest, C.LOADER_AVAILABLE_TEXT,
                   C.LOADER_LABELS[C.LOADER_FORGE], versions=versions)


# --------------------------------------------------------------------------- #
# NeoForge
# --------------------------------------------------------------------------- #
def _neoforge_prefix(version: str) -> str:
    """取 NeoForge 版本号前两段（``21.1.172`` → ``21.1``）。"""
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


def _neoforge_is_stable(version: str) -> bool:
    lowered = version.lower()
    return not any(token in lowered for token in ("alpha", "beta", "snapshot", "pre", "rc", "-"))


def _neoforge_mc_prefixes(mc: str) -> list[str]:
    """返回该 MC 版本可能对应的 NeoForge 版本前缀列表。

    旧版本号体系（1.21.1 ↔ 21.1）走内置映射表反查；新年度版本号（两段纯数字，
    如 ``26.3``）与 NeoForge 前缀同名直配（``26.3`` ↔ ``26.3.x``）。快照号
    （``26.4-snapshot-6``、``25w51a``）不做同名匹配，仅保留映射表命中结果。
    """
    mapped = [prefix for prefix, target in C.NEOFORGE_MC_PREFIX_MAP.items() if target == mc]
    if mapped:
        return mapped
    if re.fullmatch(r"\d+\.\d+", mc or ""):
        return [mc]
    return []


def _probe_neoforge(mc: str, should_cancel=None) -> dict:
    try:
        text = _fetch_text(C.NEOFORGE_MAVEN_META_URL, should_cancel=should_cancel)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_NEOFORGE])

    versions: list[str] = []
    try:
        root = ET.fromstring(text)
        for node in root.iter("version"):
            if node.text:
                versions.append(node.text.strip())
    except ET.ParseError:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_NEOFORGE])

    matched_prefixes = _neoforge_mc_prefixes(mc)
    if not matched_prefixes:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_NEOFORGE])

    candidates = [
        v for v in versions
        if _neoforge_prefix(v) in matched_prefixes and _neoforge_is_stable(v)
    ]
    if not candidates:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_NEOFORGE])

    # 版本号按段数值降序取最新稳定版；全量稳定候选进可选版本列表。
    ordered = sorted(candidates, key=_sort_key, reverse=True)
    # 镜像可能只有 metadata 条目而没有安装包（NeoForge 26.3.0.x 实测全部 404）：
    # 逐个 HEAD 校验真实存在的安装包，只把验证通过的版本交给界面，避免下载必失败。
    verified: list[str] = []
    for ver in ordered[:_NEOFORGE_PROBE_LIMIT]:
        if callable(should_cancel) and should_cancel():
            return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_NEOFORGE])
        if _artifact_available(C.NEOFORGE_INSTALLER_URL.format(ver=ver),
                               should_cancel=should_cancel):
            verified.append(ver)
        if len(verified) >= _NEOFORGE_VERIFIED_KEEP:
            break
    if not verified:
        return _result(False, "", C.LOADER_MIRROR_MISSING_TEXT,
                       C.LOADER_LABELS[C.LOADER_NEOFORGE])
    versions = [{"version": v, "time": ""} for v in verified]
    latest = versions[0]["version"]
    return _result(True, latest, C.LOADER_AVAILABLE_TEXT,
                   C.LOADER_LABELS[C.LOADER_NEOFORGE], versions=versions)


# --------------------------------------------------------------------------- #
# OptiFine
# --------------------------------------------------------------------------- #
def _probe_optifine(mc: str, should_cancel=None) -> dict:
    url = C.OPTIFINE_LIST_URL.format(mc=mc)
    try:
        data = _fetch_json(url, should_cancel=should_cancel)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
            json.JSONDecodeError, ValueError):
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_OPTIFINE])

    if not isinstance(data, list) or not data:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_OPTIFINE])

    # 优先正式版（文件名不以 preview_ 开头），预览版排后面；全量进可选版本列表。
    stable = [e for e in data if not str(e.get("filename") or "").startswith("preview_")]
    previews = [e for e in data if str(e.get("filename") or "").startswith("preview_")]
    ordered = stable + previews
    versions: list[dict] = []
    for entry in ordered:
        filename = str(entry.get("filename") or "")
        if filename:
            versions.append({"version": filename, "time": ""})
    if not versions:
        return _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[C.LOADER_OPTIFINE])
    chosen = versions[0]["version"]
    return _result(True, chosen, C.LOADER_AVAILABLE_TEXT,
                   C.LOADER_LABELS[C.LOADER_OPTIFINE], versions=versions)


_PROBES = {
    C.LOADER_FORGE: _probe_forge,
    C.LOADER_NEOFORGE: _probe_neoforge,
    C.LOADER_FABRIC: _probe_fabric,
    C.LOADER_OPTIFINE: _probe_optifine,
}


def probe_all(mc_version: str, should_cancel=None) -> dict[str, dict]:
    """探测某 MC 版本对四个第三方加载器的支持性；缓存命中直接返回，缺键才联网补探。

    返回 ``{loader_key: {"available", "version", "detail", "label"}}``；原版始终可选，
    不在本结果内（由界面固定渲染）。网络失败的加载器按不可用兜底，不抛到界面线程。
    """
    mc = str(mc_version or "").strip()
    cache = _load_cache()
    versions_cache: dict = cache.setdefault("versions", {})
    cached_entry: dict = versions_cache.get(mc, {})

    result: dict[str, dict] = {}
    for key in C.LOADER_CARD_ORDER:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("加载器探测已被取消")
        if key in cached_entry and isinstance(cached_entry[key], dict):
            result[key] = dict(cached_entry[key])
            continue
        try:
            result[key] = _PROBES[key](mc, should_cancel=should_cancel)
        except InterruptedError:
            raise
        except Exception:
            result[key] = _result(False, "", _UNAVAILABLE, C.LOADER_LABELS[key])
        cached_entry[key] = result[key]

    versions_cache[mc] = cached_entry
    try:
        _save_cache(cache)
    except OSError:
        pass
    return result


# --------------------------------------------------------------------------- #
# 安装 profile 构建（下载链路，供 worker 调用）
# --------------------------------------------------------------------------- #
def _download_bytes(url: str, should_cancel=None, mirror: str | None = None) -> bytes:
    """下载二进制到内存（installer Jar 体积数 MB，可接受；失败依次尝试镜像）。"""
    last_error: Exception | None = None
    for candidate in (url, mirror):
        if not candidate:
            continue
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("加载器安装包下载已被取消")
        try:
            with urllib.request.urlopen(_request(candidate), timeout=C.DOWNLOAD_HTTP_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("加载器安装包下载失败")


def _extract_installer_version_json(raw: bytes) -> dict:
    """从 Forge / NeoForge installer Jar 内提取 ``version.json`` 并解析为字典。"""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = "version.json"
        if name not in archive.namelist():
            raise RuntimeError("安装包内缺少 version.json")
        return json.loads(archive.read(name).decode("utf-8"))


def build_fabric_profile(mc: str, loader_version: str,
                         should_cancel=None) -> tuple[dict, str]:
    """拉取 Fabric profile JSON（官方优先，BMCL 镜像兜底），作为合并层返回。

    返回 ``(profile, 实际使用的 loader 版本号)``；版本号即所选版本，正常不变。
    """
    endpoints = (
        C.FABRIC_PROFILE_OFFICIAL.format(mc=mc, loader=loader_version),
        C.FABRIC_PROFILE_MIRROR.format(mc=mc, loader=loader_version),
        C.LEGACYFABRIC_PROFILE_URL.format(mc=mc, loader=loader_version),
    )
    last_error: Exception | None = None
    for url in endpoints:
        try:
            profile = _fetch_json(url, should_cancel=should_cancel)
            return profile, loader_version  # type: ignore[return-value]
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
                json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("Fabric profile 拉取失败")


def _forge_versions_for(mc: str, should_cancel=None) -> list[str]:
    """拉取某 MC 版本可用的 Forge 版本号（BMCL 列表，按 build 新 → 旧）。"""
    data = _fetch_json(C.FORGE_LIST_URL.format(mc=mc), should_cancel=should_cancel)
    if not isinstance(data, list) or not data:
        return []

    def _build_number(entry: dict) -> int:
        try:
            return int(entry.get("build") or 0)
        except (TypeError, ValueError):
            return 0

    ordered = sorted(data, key=_build_number, reverse=True)
    versions: list[str] = []
    for entry in ordered:
        ver = str(entry.get("version") or "").strip()
        if ver and ver not in versions:
            versions.append(ver)
    return versions


def _read_cached_installer(path: str) -> dict | None:
    """读本地已落盘的 installer 并取 ``version.json``；文件缺失 / 半截损坏返回 None 并清理。"""
    if not (os.path.isfile(path) and os.path.getsize(path) > 0):
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            if "version.json" not in archive.namelist():
                return None
            return json.loads(archive.read("version.json").decode("utf-8"))
    except (OSError, ValueError, zipfile.BadZipFile):
        try:
            os.remove(path)
        except OSError:
            pass
        return None


def build_forge_profile(mc: str, forge_version: str,
                        should_cancel=None,
                        installer_dir: str | None = None,
                        tracker=None) -> tuple[dict, str]:
    """下载 Forge installer Jar，提取内部 ``version.json`` 作为合并层 profile。

    官方 maven 主源、BMCL maven 镜像双源；若所选版本两源都失败，按同 MC 的旧版本
    从新到旧回退，直到 installer 真正下载成功。返回 ``(profile, 实际版本号)``。

    ``installer_dir`` 非空时把 installer 原样落盘为
    ``forge-{mc}-{ver}-installer.jar``（与 :func:`forge_install.installer_local_path`
    一致），供第 5 步处理器链直接复用，避免同一安装包下载两次。

    ``installer_dir`` 非空时改走 :func:`download_engine.download_one`：带 ``.part``
    断点续传、停滞超时切源与整轮重试，且 ``tracker`` 能上报字节进度——官方源实测
    8 MB 只能跑到 30~260 KB/s，``urllib`` 一次性 ``read()`` 会让面板长时间静止。
    """
    from .download_engine import DownloadTask, download_one

    requested = str(forge_version or "").strip()
    try:
        listed = _forge_versions_for(mc, should_cancel=should_cancel)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
            json.JSONDecodeError, ValueError):
        listed = []

    candidates = [requested]
    requested_key = _sort_key(requested)
    for ver in listed:
        if ver != requested and _sort_key(ver) <= requested_key:
            candidates.append(ver)
    candidates = list(dict.fromkeys(candidates))

    last_error: Exception | None = None
    for ver in candidates:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("加载器安装包下载已被取消")

        save_path = None
        if installer_dir:
            try:
                os.makedirs(installer_dir, exist_ok=True)
            except OSError:
                pass
            save_path = os.path.join(
                installer_dir, f"forge-{mc}-{ver}-installer.jar")
            cached = _read_cached_installer(save_path)
            if cached is not None:
                return cached, ver

        primary = C.FORGE_INSTALLER_URL.format(mc=mc, ver=ver)
        mirror = (
            f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/"
            f"{mc}-{ver}/forge-{mc}-{ver}-installer.jar"
        )
        try:
            if save_path:
                # 走下载引擎：断点续传 + 停滞检测 + 多源重试 + 进度上报。
                from .download_engine import ProgressTracker
                local_tracker = tracker if tracker is not None else ProgressTracker()
                task = DownloadTask(
                    url=primary,
                    local_path=save_path,
                    mirror_url=mirror,
                    label=os.path.basename(save_path),
                )
                ok, reason = download_one(task, local_tracker, should_cancel)
                if not ok:
                    last_error = RuntimeError(reason or "Forge 安装包下载失败")
                    continue
                profile = _read_cached_installer(save_path)
                if profile is None:
                    last_error = RuntimeError("Forge 安装包解析失败")
                    continue
                return profile, ver
            raw = _download_bytes(primary, should_cancel=should_cancel, mirror=mirror)
            return _extract_installer_version_json(raw), ver
        except InterruptedError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("Forge 安装包下载失败")


def _neoforge_all_versions(should_cancel=None) -> list[str]:
    """从 BMCL maven-metadata 拉取全部 NeoForge 版本号（新 → 旧顺序由调用方排序）。"""
    text = _fetch_text(C.NEOFORGE_MAVEN_META_URL, should_cancel=should_cancel)
    root = ET.fromstring(text)
    return [node.text.strip() for node in root.iter("version") if node.text]


def build_neoforge_profile(neoforge_version: str, should_cancel=None) -> tuple[dict, str]:
    """下载 NeoForge installer Jar（BMCL maven 镜像），提取内部 ``version.json``。

    官方 maven 本机不可达，BMCL 对最新若干版本可能尚未镜像（installer 404）。此时按
    同前缀（同一 MC 版本）稳定版从新到旧回退，直到某版本 installer 真正下载成功；
    返回 ``(profile, 实际使用的版本号)``，保证「没有就用旧版本试到成功」。
    """
    requested = str(neoforge_version or "").strip()
    prefix = _neoforge_prefix(requested)
    try:
        all_versions = _neoforge_all_versions(should_cancel=should_cancel)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError, ET.ParseError):
        all_versions = []

    requested_key = _sort_key(requested)
    candidates = [requested]
    for ver in all_versions:
        if ver == requested:
            continue
        if _neoforge_prefix(ver) != prefix or not _neoforge_is_stable(ver):
            continue
        # 只回退到不高于所选版本的旧版，不擅自升级。
        if _sort_key(ver) <= requested_key:
            candidates.append(ver)
    # 去重并按新 → 旧排序（requested 已在首位，排序后保持同序）。
    candidates = sorted(dict.fromkeys(candidates), key=_sort_key, reverse=True)
    # 回退只走前几个候选：镜像缺包时每个候选都要付 404 / 超时代价，全量回退会拖成几分钟。
    candidates = candidates[:_NEOFORGE_PROBE_LIMIT // 2]

    last_error: Exception | None = None
    for ver in candidates:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("加载器安装包下载已被取消")
        try:
            raw = _download_bytes(C.NEOFORGE_INSTALLER_URL.format(ver=ver),
                                  should_cancel=should_cancel,
                                  mirror=C.NEOFORGE_INSTALLER_OFFICIAL_URL.format(ver=ver))
            return _extract_installer_version_json(raw), ver
        except InterruptedError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
                zipfile.BadZipFile, RuntimeError) as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("NeoForge 安装包下载失败")


def resolve_optifine_download_url(filename: str, should_cancel=None) -> str | None:
    """解析 OptiFine 官方广告中转页，提取真实下载直链；解析失败返回 ``None``。

    中转页 HTML 内含 ``downloadx?f=<filename>&x=<token>`` 形式的相对 / 绝对链接；
    纯标准库正则提取，不依赖第三方 HTML 解析库。
    """
    url = C.OPTIFINE_ADLOAD_URL.format(filename=filename)
    try:
        html = _fetch_text(url, should_cancel=should_cancel)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return None
    match = re.search(r"downloadx\?f=[^'\"&\s]+&x=[A-Za-z0-9]+", html)
    if not match:
        return None
    return f"https://optifine.net/{match.group(0)}"


def build_optifine_profile(optifine_jar_local: str, mc: str) -> dict:
    """构造 OptiFine 独立运行合并层：继承原版、mainClass 保持原版、classpath 加入 OptiFine Jar。

    ``optifine_jar_local`` 为 worker 下载完成后的本地绝对路径；启动层把该 Jar 追加进
    classpath，不执行 OptiFine 安装器补丁流程（本机无 Java 时无法执行安装器）。
    """
    jar_name = os.path.basename(optifine_jar_local)
    return {
        "inheritsFrom": mc,
        "mainClass": "net.minecraft.client.main.Main",
        "libraries": [
            {
                "name": f"optifine:OptiFine:{jar_name}",
                "downloads": {
                    "artifact": {
                        "path": f"optifine/OptiFine/{jar_name}",
                        "url": "",
                    }
                },
                "_local_jar": optifine_jar_local,
            }
        ],
    }
