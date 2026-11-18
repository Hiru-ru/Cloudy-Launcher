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

"""原版 Minecraft 版本编排：版本 JSON 拉取、``inheritsFrom`` 继承链合并、依赖库 /
natives / 资源 / 客户端 Jar 下载任务收集。

v1.2.12.0 新增。纯 Python 标准库 ``urllib`` + ``json`` + ``os``，不引入第三方 HTTP 库；
User-Agent 保持纯 ASCII。本模块只负责「解析版本清单 → 合并 profile → 构造
:class:`~cloud_launcher.download_engine.DownloadTask`」，不直接发并发下载（由下载 worker
投喂引擎），不绑定界面控件。

目录口径（见 :mod:`cloud_launcher.game_dirs`）：
- 依赖库 jar → 版本隔离目录 ``libraries/``；
- natives classifier Jar 下载到 ``libraries/`` 后解压到 ``natives/``；
- 资源对象 → 全局 ``.minecraft/assets/objects/<hash[:2]>/<hash>``；1.12 及更早 legacy 资源
  落到 ``assets/virtual/legacy/<name>``；
- 客户端 Jar → 版本隔离目录 ``client.jar``。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from . import constants as C
from . import download_engine as engine
from . import game_dirs
from .version_meta import fetch_version_item


# --------------------------------------------------------------------------- #
# HTTP 拉取
# --------------------------------------------------------------------------- #
def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"},
    )


def _fetch_json(url: str, should_cancel=None, timeout: int = C.META_HTTP_TIMEOUT) -> dict:
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("版本 JSON 拉取已被取消")
    with urllib.request.urlopen(_request(url), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_version_json(version_id: str, should_cancel=None) -> dict:
    """按清单条目 ``url`` 拉取某版本原始 version JSON；清单定位失败 / 网络异常向上抛出。

    官方 piston-meta 不可达时，BMCLAPI 提供同构 ``/mc/version/<id>/json`` 兜底。
    """
    item = fetch_version_item(version_id, should_cancel=should_cancel)
    official_url = str(item.get("url") or "").strip()
    mirror_url = f"https://bmclapi2.bangbang93.com/mc/version/{version_id}/json"
    last_error: Exception | None = None
    for url in (official_url, mirror_url):
        if not url:
            continue
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("版本 JSON 拉取已被取消")
        try:
            return _fetch_json(url, should_cancel=should_cancel, timeout=C.DOWNLOAD_HTTP_TIMEOUT)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError,
                json.JSONDecodeError) as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError(f"版本 {version_id} 元数据不可用")


# --------------------------------------------------------------------------- #
# inheritsFrom 继承链合并
# --------------------------------------------------------------------------- #
def _merge_arguments(base: dict, child: dict) -> dict:
    """合并两段 ``arguments``（jvm / game 列表去重拼接，子 profile 追加在后）。"""
    merged: dict = {}
    for key in ("jvm", "game"):
        base_list = list((base.get("arguments") or {}).get(key) or [])
        child_list = list((child.get("arguments") or {}).get(key) or [])
        seen: set[str] = set()
        combined: list = []
        for entry in base_list + child_list:
            token = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            if token in seen:
                continue
            seen.add(token)
            combined.append(entry)
        merged[key] = combined
    return merged


def merge_profiles(base: dict, child: dict) -> dict:
    """公开包装：把子 profile 合并进父 profile（见 :func:`_merge_profiles`）。"""
    return _merge_profiles(base, child)


def _merge_profiles(base: dict, child: dict) -> dict:
    """把子 profile（加载器 / 继承层）合并进父 profile（原版底座），返回新字典。

    - 标量字段（mainClass / assetIndex / assets / javaVersion / logging /
      complianceLevel / type / id / minecraftArguments）子覆盖父；
    - libraries 按 ``name`` 去重，子条目覆盖父条目；
    - arguments.jvm / game 列表去重拼接；
    - downloads 子覆盖父（通常子 profile 不带 client 下载块，保留父原版块）。
    """
    merged = dict(base)
    for key, value in child.items():
        if key == "libraries":
            base_libs = {lib.get("name"): lib for lib in base.get("libraries") or []}
            for lib in value or []:
                base_libs[lib.get("name")] = lib
            merged["libraries"] = list(base_libs.values())
        elif key == "arguments":
            merged["arguments"] = _merge_arguments(base, child)
        elif key in ("downloads",):
            merged[key] = {**(base.get(key) or {}), **(value or {})}
        else:
            merged[key] = value
    return merged


def load_merged_profile(mc_version: str, should_cancel=None,
                        extra_profile: dict | None = None) -> dict:
    """加载原版版本 JSON 并沿 ``inheritsFrom`` 合并；``extra_profile``（加载器 profile）
    作为最上层子 profile 合并进原版底座。返回合并后的完整 profile 字典。
    """
    chain: list[dict] = []
    visited: set[str] = set()
    current = str(mc_version or "").strip()
    while current:
        if current in visited:
            break
        visited.add(current)
        profile = fetch_version_json(current, should_cancel=should_cancel)
        chain.append(profile)
        current = str(profile.get("inheritsFrom") or "").strip()

    if not chain:
        raise RuntimeError(f"版本 {mc_version} 元数据为空")

    # 链顺序：原版底座在最前，上层在后；合并时后段覆盖前段。
    merged = chain[-1]
    for profile in reversed(chain[:-1]):
        merged = _merge_profiles(profile, merged)
    if isinstance(extra_profile, dict) and extra_profile:
        merged = _merge_profiles(merged, extra_profile)
    return merged


# --------------------------------------------------------------------------- #
# 依赖库任务收集
# --------------------------------------------------------------------------- #
def library_relative_path(lib: dict) -> str:
    """依赖库在 ``libraries/`` 下的 Maven 相对路径；优先 downloads.artifact.path。"""
    artifact = (lib.get("downloads") or {}).get("artifact") or {}
    path = str(artifact.get("path") or "").strip()
    if not path:
        path = engine.maven_relative_path(str(lib.get("name") or ""))
    return path


def library_local_path(lib: dict, alias: str) -> str:
    """库 jar 在版本隔离 ``libraries/`` 下的本地路径；优先 downloads.artifact.path。"""
    return os.path.join(
        game_dirs.libraries_dir(alias), library_relative_path(lib).replace("/", os.sep)
    )


def _library_local_path(lib: dict, alias: str) -> str:
    return library_local_path(lib, alias)


def _legacy_natives_eff_lib(lib: dict) -> dict | None:
    """把老格式 natives 库规范化为带当前系统 artifact 的有效库。

    Legacy Fabric 等老版本 profile 里的平台库（如 ``lwjgl-platform``）没有
    ``downloads`` 段，只有 ``natives``（OS → classifier 后缀）与顶层 ``url``（Maven
    基址）。它没有主 Jar，当前系统要用的是 classifier Jar（Windows 取
    ``natives-windows``）。这里构造一个把该 classifier 当 artifact 的 eff_lib，
    使其落盘路径 / 源链与真实工件一致；非该格式返回 None。
    """
    if lib.get("downloads"):
        return None
    natives_map = lib.get("natives")
    if not isinstance(natives_map, dict):
        return None
    classifier_name = str(natives_map.get("windows") or "").strip()
    if not classifier_name:
        return None
    name = str(lib.get("name") or "").strip()
    if not name:
        return None
    rel = engine.maven_relative_path(name, classifier_name)
    base = str(lib.get("url") or "").strip().rstrip("/")
    eff = dict(lib)
    eff["downloads"] = {"artifact": {
        "path": rel,
        "url": (base + "/" + rel) if base else "",
    }}
    return eff


def _library_sources(lib: dict) -> list[str]:
    """返回该库的候选下载地址链（前面优先）。

    v1.3.3.3 起顺序为：阿里云公共 Maven → BMCL 映射 → 华为云公共 Maven → 官方源。
    实测 2026-11-07：``libraries.minecraft.net`` 对本机经常「HTTP 200 后挂住不回数据」，
    单个小 Jar 能拖到 6 分钟毫无进展，是「剩余文件 1、速度 0、面板一直进行中」的直接成因；
    同一批 Maven Central 工件走阿里云 / 华为云则秒级完成。Forge 专属工件
    （``net.minecraftforge:*``）三个国内镜像都 404（立即返回，代价很小），只有官方源可用。

    兼容两种库格式：
    - 现代 Mojang 格式：``downloads.artifact.url`` 给完整文件地址；
    - 旧式 / 加载器格式（Fabric / Forge 部分库）：无 ``downloads.artifact``，
      改用顶层 ``url``（Maven 基址）拼接 Maven 相对路径得到真实文件地址。
    """
    artifact = (lib.get("downloads") or {}).get("artifact") or {}
    path = str(artifact.get("path") or "").strip()
    if not path:
        path = engine.maven_relative_path(str(lib.get("name") or ""))
    official = str(artifact.get("url") or "").strip()
    if not official:
        # 无 artifact 直链时，加载器库通常带顶层 Maven 基址（以 / 结尾）。
        base = str(lib.get("url") or "").strip()
        if base:
            official = base.rstrip("/") + "/" + path

    ordered = [
        C.ALIYUN_MAVEN_URL.format(path=path),
        C.BMCL_MAVEN_URL.format(path=path),
        C.HUAWEI_MAVEN_URL.format(path=path),
        official,
    ]
    sources: list[str] = []
    for url in ordered:
        if url and url not in sources:
            sources.append(url)
    return sources


def collect_library_tasks(profile: dict, alias: str) -> list[engine.DownloadTask]:
    """遍历合并后 profile 的 libraries，按操作系统 / 特性规则过滤，生成下载任务列表。"""
    tasks: list[engine.DownloadTask] = []
    for lib in profile.get("libraries") or []:
        if not engine.library_rule_allows(lib):
            continue
        downloads = lib.get("downloads") or {}
        classifiers = downloads.get("classifiers") or {}
        native_classifier = classifiers.get("natives-windows") or {}
        # 老格式（Legacy Fabric 等）：无 downloads、只有 natives map 与顶层 url，
        # 先规范化为当前系统 classifier artifact；否则再处理带 downloads.classifiers
        # 的旧版 natives 库（1.12.2 等）。直接按 name 推无 classifier 路径会 404。
        legacy_eff = _legacy_natives_eff_lib(lib)
        if legacy_eff is not None:
            eff_lib = legacy_eff
        elif native_classifier and not downloads.get("artifact"):
            # 没有 downloads.artifact，只有按平台分的 classifiers；把当前系统的
            # natives-windows classifier 当作有效 artifact，落盘路径与 collect_natives_jars
            # 的解压输入保持一致。
            eff_lib = dict(lib)
            eff_downloads = dict(downloads)
            eff_downloads["artifact"] = native_classifier
            eff_lib["downloads"] = eff_downloads
        else:
            eff_lib = lib
        artifact = (eff_lib.get("downloads") or {}).get("artifact") or {}
        # 既无 artifact 下载块、也无可用坐标的库（纯指令占位）跳过。
        if not artifact and not str(eff_lib.get("name") or "").strip():
            continue
        sources = _library_sources(eff_lib)
        local = _library_local_path(eff_lib, alias)
        # 旧式加载器库的 size / sha1 在库顶层；现代格式在 artifact 内。
        size = int(artifact.get("size") or eff_lib.get("size") or 0)
        sha1 = str(artifact.get("sha1") or eff_lib.get("sha1") or "").strip()
        if not sources:
            continue
        tasks.append(engine.DownloadTask(
            url=sources[0],
            local_path=local,
            size=size,
            sha1=sha1,
            mirror_url=sources[1] if len(sources) > 1 else None,
            extra_urls=sources[2:],
            label=str(eff_lib.get("name") or os.path.basename(local)),
        ))
    return tasks


def collect_natives_jars(profile: dict, alias: str) -> list[tuple[str, str]]:
    """收集老版本 natives classifier Jar 本地路径与其解压目标目录。

    同时支持现代 ``downloads.classifiers`` 格式与老格式 ``natives`` map（Legacy Fabric
    等无 downloads 的平台库）。返回 ``[(jar_local_path, natives_dir), ...]``，
    没有 natives 工件时返回空列表。
    """
    pairs: list[tuple[str, str]] = []
    natives_target = game_dirs.natives_dir(alias)
    for lib in profile.get("libraries") or []:
        if not engine.library_rule_allows(lib):
            continue
        downloads = lib.get("downloads") or {}
        classifiers = downloads.get("classifiers") or {}
        classifier = classifiers.get("natives-windows") or {}
        path = str(classifier.get("path") or "").strip()
        # 老格式：无 downloads，按 natives map 的 windows classifier 推路径。
        if not path:
            natives_map = lib.get("natives")
            if isinstance(natives_map, dict) and not downloads:
                classifier_name = str(natives_map.get("windows") or "").strip()
                if classifier_name:
                    path = engine.maven_relative_path(
                        str(lib.get("name") or ""), classifier_name)
        if not path:
            continue
        local = os.path.join(game_dirs.libraries_dir(alias), path.replace("/", os.sep))
        pairs.append((local, natives_target))
    return pairs


# --------------------------------------------------------------------------- #
# 资源（assets）任务收集
# --------------------------------------------------------------------------- #
def _fetch_asset_index(asset_index: dict, should_cancel=None) -> dict:
    url = str(asset_index.get("url") or "").strip()
    if not url:
        return {"objects": {}}
    # BMCL 资源索引镜像兜底：按 sha1 路径不可镜像，仅官方端点可用；失败向上抛出由 worker 记录。
    return _fetch_json(url, should_cancel=should_cancel, timeout=C.DOWNLOAD_HTTP_TIMEOUT)


def collect_asset_tasks(profile: dict, should_cancel=None) -> list[engine.DownloadTask]:
    """拉取资源索引并为每个对象生成下载任务；现代版本落 objects，旧版 legacy 落 virtual。"""
    asset_index = profile.get("assetIndex") or {}
    if not asset_index:
        return []
    index = _fetch_asset_index(asset_index, should_cancel=should_cancel)
    objects = index.get("objects") or {}
    # 把资源索引 JSON 落盘到 assets/indexes/<id>.json，游戏运行时依赖它定位资源；
    # 旧实现只在内存使用索引、从不落盘，导致游戏报 Can't open resource index。
    index_id = str(asset_index.get("id") or profile.get("assets") or "")
    if index_id:
        index_path = game_dirs.assets_index_path(index_id)
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False)
    # 1.12 及更早版本 assets 索引版本号为数字 / 旧标识，需要 legacy 目录；现代版本走 objects。
    legacy = str(profile.get("assets") or asset_index.get("id") or "") in ("1.12", "1.11", "1.10",
                                                                          "1.9", "1.8", "1.7",
                                                                          "1.6", "1.5", "1.4",
                                                                          "1.3", "1.2", "1.1")
    tasks: list[engine.DownloadTask] = []
    for name, entry in objects.items():
        hash_value = str(entry.get("hash") or "")
        if not hash_value:
            continue
        size = int(entry.get("size") or 0)
        if legacy:
            local = os.path.join(game_dirs.assets_virtual_legacy_dir(), name.replace("/", os.sep))
            primary = C.BMCL_ASSET_URL.format(prefix=hash_value[:2], hash=hash_value)
            mirror = C.OFFICIAL_OBJECT_URL.format(hash=hash_value, name=hash_value)
        else:
            local = os.path.join(game_dirs.assets_objects_dir(),
                                 hash_value[:2], hash_value)
            primary = C.BMCL_ASSET_URL.format(prefix=hash_value[:2], hash=hash_value)
            mirror = C.OFFICIAL_OBJECT_URL.format(hash=hash_value, name=name)
        tasks.append(engine.DownloadTask(
            url=primary,
            local_path=local,
            size=size,
            sha1=hash_value,
            mirror_url=mirror,
            label=name,
        ))
    return tasks


# --------------------------------------------------------------------------- #
# 客户端 Jar 任务
# --------------------------------------------------------------------------- #
def client_jar_task(profile: dict, alias: str, mc_version: str) -> engine.DownloadTask:
    """生成原版客户端 Jar 下载任务；官方源优先，BMCL 镜像兜底，停滞自动切换。"""
    client = (profile.get("downloads") or {}).get("client") or {}
    official = str(client.get("url") or "").strip()
    mirror = C.BMCL_CLIENT_JAR_URL.format(version=mc_version)
    return engine.DownloadTask(
        url=official or mirror,
        local_path=game_dirs.client_jar_path(alias),
        size=int(client.get("size") or 0),
        sha1=str(client.get("sha1") or ""),
        mirror_url=mirror if official else None,
        label=f"{mc_version} client.jar",
    )
