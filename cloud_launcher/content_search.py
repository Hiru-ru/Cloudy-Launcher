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

"""v1.3.4.0 内容搜索数据模块：Modrinth 搜索 + 图标下载 + 本地缓存落盘。

v1.3.6.0 起图标改为多线程并发下载（仍只用标准库），避免首次进入某分类时
20 张图标串行下载把首屏拖到一分钟以上。

仅做「搜索 + 图文展示」，不下载 mod / 整合包 / 光影 / 资源 / 数据包本体
（真实下载由 ``content_install`` 负责）。

- 数据源 Modrinth REST（免 API key）：``GET /v2/search``，facets 按 project_type
  过滤；五类 project_type 与下载页分类一一对应；
- 结果标准化为统一 dict 列表；图标从 Modrinth CDN 下载到本地缓存目录并复用，
  单个图标失败不阻断整体搜索，返回 ``icon_local=None`` 由界面显示占位图；
- 每次搜索的元数据 JSON 与全部图标均落盘到
  ``CLY/content_search/``（v1.3.10.0 起平铺在数据目录），满足「搜索来的东西放文件夹里」；
- 纯标准库 urllib / json / threading，UA 纯 ASCII，不引入第三方 HTTP / 图像库。
"""
import concurrent.futures
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from . import constants as C
from .resources import data_dir

# 搜索接口与本地缓存子目录（位于 yd 之下）。
SEARCH_API = "https://api.modrinth.com/v2/search"
CONTENT_CACHE_DIRNAME = "content_search"
ICONS_DIRNAME = "icons"
DEFAULT_LIMIT = 20
SEARCH_TIMEOUT = 20
ICON_TIMEOUT = 20
ICON_WORKERS = 8

# 下载页分类内部 key → Modrinth project_type。
PROJECT_TYPES = {
    "mod": "mod",
    "modpack": "modpack",
    "shader": "shader",
    "resourcepack": "resourcepack",
    "datapack": "datapack",
}

# 正式版（release）形如 1.21 / 1.21.1；快照、预发布、远古版不匹配。
_RELEASE_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def release_versions(versions) -> list[str]:
    """从版本数组里挑出正式版（过滤快照 / pre / rc / 远古版）。"""
    out = []
    for ver in versions or []:
        if isinstance(ver, str) and _RELEASE_RE.match(ver):
            out.append(ver)
    return out


def version_key(ver: str) -> tuple:
    """版本号转可比较元组，保证 1.21.10 > 1.21.9（字符串比较会错）。"""
    parts = []
    for piece in str(ver or "").split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def latest_releases(versions, count: int = 3) -> list[str]:
    """最新的若干正式版（最新在前），用于卡片「支持版本」展示。"""
    rels = sorted(set(release_versions(versions)), key=version_key)
    return rels[-count:][::-1]


# v1.3.8.0：Modrinth categories 里属于 mod 加载器的 slug → 卡片显示名。
# categories 里还混着内容分类（optimization / utility / library 等），只挑下列加载器。
LOADER_DISPLAY = {
    "fabric": "Fabric",
    "quilt": "Quilt",
    "neoforge": "NeoForge",
    "forge": "Forge",
    "optifine": "OptiFine",
    "modloader": "ModLoader",
    "liteloader": "LiteLoader",
    "rift": "Rift",
    "babric": "Babric",
}
# 卡片上加载器的展示顺序（主流加载器在前，其余兜底）。
_LOADER_ORDER = ("fabric", "quilt", "neoforge", "forge", "optifine",
                 "modloader", "liteloader", "rift", "babric")


def mod_loaders(categories) -> list[str]:
    """从项目 categories 里挑出 mod 加载器，按固定顺序返回显示名（去重）。"""
    cats = [c for c in (categories or []) if isinstance(c, str)]
    cat_set = set(cats)
    found = [slug for slug in _LOADER_ORDER if slug in cat_set]
    # 兜底：映射表里存在但未列入顺序的新 slug，按其在 categories 中的出现顺序补上。
    for c in cats:
        if c in LOADER_DISPLAY and c not in found:
            found.append(c)
    return [LOADER_DISPLAY[slug] for slug in found]



def _ua_header() -> dict:
    return {"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"}


def cache_root() -> str:
    """内容搜索缓存根目录（v1.3.10.0 起平铺为 ``CLY/content_search``）。"""
    return os.path.join(data_dir(), CONTENT_CACHE_DIRNAME)


def icons_dir() -> str:
    """图标缓存目录。"""
    return os.path.join(cache_root(), ICONS_DIRNAME)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _build_search_url(kind: str, query: str, limit: int, offset: int) -> str:
    project_type = PROJECT_TYPES[kind]
    facets = urllib.parse.quote('[["project_type:' + project_type + '"]]')
    params = ["limit=" + str(limit), "offset=" + str(offset), "facets=" + facets]
    if query:
        params.append("query=" + urllib.parse.quote(query))
    return SEARCH_API + "?" + "&".join(params)


def _fetch_json(url: str, timeout: int, should_cancel=None) -> dict:
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("搜索已取消")
    req = urllib.request.Request(url, headers=_ua_header())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _icon_extension(icon_url: str) -> str:
    path = urllib.parse.urlparse(icon_url).path
    ext = os.path.splitext(path)[1].lower()
    # 仅允许常见图像扩展名，避免异常 URL 造成奇怪文件名。
    return ext if ext in (".png", ".webp", ".jpg", ".jpeg", ".gif") else ".png"


def _download_icon(icon_url: str, project_id: str, should_cancel=None):
    """下载图标到本地并返回绝对路径；已存在则复用，失败返回 None。"""
    if not icon_url:
        return None
    _ensure_dir(icons_dir())
    local = os.path.join(icons_dir(), project_id + _icon_extension(icon_url))
    if os.path.isfile(local) and os.path.getsize(local) > 0:
        return local
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("搜索已取消")
    req = urllib.request.Request(icon_url, headers=_ua_header())
    tmp = local + ".part"
    with urllib.request.urlopen(req, timeout=ICON_TIMEOUT) as resp:
        data = resp.read()
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, local)
    return local


def _fetch_icon_bytes(icon_url: str, should_cancel=None):
    """下载图标到内存（bytes），不落盘；供第一页以外的分页浏览使用。"""
    if not icon_url:
        return None
    if callable(should_cancel) and should_cancel():
        raise InterruptedError("搜索已取消")
    req = urllib.request.Request(icon_url, headers=_ua_header())
    with urllib.request.urlopen(req, timeout=ICON_TIMEOUT) as resp:
        return resp.read()


def _normalize_hit(hit: dict) -> dict:
    return {
        "project_id": hit.get("project_id", ""),
        "slug": hit.get("slug", ""),
        "title": hit.get("title", ""),
        "description": hit.get("description", ""),
        "author": hit.get("author", ""),
        "downloads": int(hit.get("downloads", 0) or 0),
        "follows": int(hit.get("follows", 0) or 0),
        "icon_url": hit.get("icon_url") or "",
        "project_type": hit.get("project_type", ""),
        "supported_versions": list(hit.get("versions") or []),
        "loaders": mod_loaders(hit.get("categories")),
        "icon_local": None,
        "icon_bytes": None,
    }


def _save_result(kind: str, query: str, items: list[dict], total: int) -> str:
    """把本次搜索的元数据 JSON 落盘到分类目录（最近一次结果）。"""
    kind_dir = os.path.join(cache_root(), kind)
    _ensure_dir(kind_dir)
    payload = {
        "kind": kind,
        "query": query,
        "total_hits": total,
        "saved_at": int(time.time()),
        "items": items,
    }
    out = os.path.join(kind_dir, "last.json")
    tmp = out + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, out)
    return out


def search_content(kind: str, query: str = "", limit: int = DEFAULT_LIMIT,
                   offset: int = 0, should_cancel=None,
                   on_progress=None) -> dict:
    """执行一次搜索并下载图标，返回 ``{items,total_hits,saved_to}``。

    每个 item 含本地化后的 ``icon_local``（可能为 None，界面用占位图）。
    搜索请求失败会抛异常，由后台线程捕获回传；图标单条失败不影响整体。
    """
    if kind not in PROJECT_TYPES:
        raise KeyError("未知内容分类: " + kind)
    # v1.3.7.0：只有第一页（offset=0）写缓存（last.json + 图标落盘）；翻到后续页
    # 只在内存里持有图标，yd 目录不产生任何缓存文件。下载落盘不受影响，所有页都能下载。
    persist = offset == 0
    url = _build_search_url(kind, query, limit, offset)
    obj = _fetch_json(url, SEARCH_TIMEOUT, should_cancel)
    total = int(obj.get("total_hits", 0) or 0)
    items = [_normalize_hit(h) for h in obj.get("hits", [])]
    _fill_icons(items, should_cancel, on_progress, persist=persist)

    saved_to = ""
    if persist:
        _ensure_dir(cache_root())
        saved_to = _save_result(kind, query, items, total)
    return {"items": items, "total_hits": total, "saved_to": saved_to}


def _fill_icons(items: list[dict], should_cancel=None, on_progress=None,
                persist: bool = True) -> None:
    """并发补齐 items 的图标：persist=True 落盘复用，False 只进内存、不写缓存。"""
    pending = [item for item in items if item.get("icon_url")]
    total = len(pending)
    if not total:
        return

    def fetch(item):
        try:
            if persist:
                return ("path",
                        _download_icon(item["icon_url"], item["project_id"],
                                       should_cancel))
            return ("bytes", _fetch_icon_bytes(item["icon_url"], should_cancel))
        except (urllib.error.URLError, OSError, TimeoutError, ValueError):
            return None

    finished = 0
    workers = min(ICON_WORKERS, total)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                kind_key, value = res
                if kind_key == "path":
                    futures[future]["icon_local"] = value
                else:
                    futures[future]["icon_bytes"] = value
            finished += 1
            if callable(on_progress):
                on_progress(finished, total)
