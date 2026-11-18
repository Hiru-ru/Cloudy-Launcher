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

"""Minecraft 官方版本清单只读拉取、全量分类与本地缓存。

下载页五个分组的数据口径（v1.2.9.1 起取代此前「每组只放一条代表版本」的旧口径）：

- 「最新版本」分组固定两行：最新正式版（``latest.release``）、最新预览版
  （``latest.snapshot``），只保留这两条；
- 「正式版」分组：清单中 ``type == "release"`` 的全部版本；
- 「预览版」分组：清单中 ``type == "snapshot"`` 且不在愚人节白名单内的全部版本；
- 「远古版」分组：``type == "old_beta"`` 与 ``type == "old_alpha"`` 合并，按发布
  时间统一倒序（新 → 旧）；
- 「愚人节版」分组：``APRIL_FOOL_IDS`` 精确 id 白名单命中的全部特殊版本（线上清单
  里它们的 type 都是 snapshot，必须先从预览版剔除再单独成组）。

v1.2.10.0 缓存与镜像口径：

- 只拉版本号与发布日期文本，**不下载游戏客户端、不解析完整版本文件清单、不绑定下载 /
  启动动作**。纯标准库 ``urllib`` + ``json`` + ``datetime``，User-Agent 保持纯 ASCII；
  网络 / 超时 / JSON 异常统一向上抛出，由界面层后台线程静默回退到「不显示版本信息」状态，
  不弹窗、不崩溃。
- 清单分类结果缓存到 ``yd/version_manifest_cache.json``：首次无缓存才联网全量拉取，之后
  启动直接读缓存渲染、不重新刷新列表；后台轻量比对最新版号时静默覆盖本缓存。
- 联网按国内 BMCLAPI2 镜像 → 官方 piston-meta 顺序轮询兜底，任一成功即用，全部失败才抛错。
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from . import constants as C
from .resources import data_dir

# 官方 releaseTime 为 UTC（+00:00）；界面按北京时间（UTC+8）展示。
_BEIJING_TZ = timezone(timedelta(hours=8))
# 无时间戳条目排序时使用的最小可比较时刻（UTC），保证排序键不会因 None 抛 TypeError。
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)

# 四个全量分组的内部键，与下载页分组一一对应。
KEY_RELEASE = "release"
KEY_SNAPSHOT = "snapshot"
KEY_ANCIENT = "ancient"
KEY_APRIL = "april"
GROUP_KEYS = (KEY_RELEASE, KEY_SNAPSHOT, KEY_ANCIENT, KEY_APRIL)


def _parse_moment(item: dict | None) -> datetime | None:
    """解析条目发布时间为带时区 datetime；优先 releaseTime、回退 time；失败返回 None。"""
    if not item:
        return None
    raw = item.get("releaseTime") or item.get("time")
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(str(raw))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment
    except (ValueError, TypeError, OverflowError):
        return None


def _format_moment(moment: datetime | None) -> str:
    """把带时区时刻格式化为北京时间 ``YYYY/MM/DD HH:MM``；空值返回空串。"""
    if moment is None:
        return ""
    return moment.astimezone(_BEIJING_TZ).strftime("%Y/%m/%d %H:%M")


def _format_release_time(raw: str | None) -> str:
    """把 ISO8601 发布时间格式化为北京时间 ``YYYY/MM/DD HH:MM``；解析失败返回空串。"""
    if not raw:
        return ""
    try:
        moment = datetime.fromisoformat(raw)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(_BEIJING_TZ).strftime("%Y/%m/%d %H:%M")
    except (ValueError, TypeError, OverflowError):
        return ""


def _normalize(item: dict | None) -> dict | None:
    """把清单条目标准化为 ``{"id", "time", "_moment"}``；无 id 或空 id 返回 None。"""
    if not item:
        return None
    vid = str(item.get("id") or "").strip()
    if not vid:
        return None
    moment = _parse_moment(item)
    return {"id": vid, "time": _format_moment(moment), "_moment": moment}


def classify_versions(versions: list[dict]) -> dict[str, list[dict]]:
    """把原始 versions 数组归类到四个全量分组（纯函数，可离线单测，不发网络请求）。

    返回 ``{"release": [{"id", "time"}, ...], "snapshot": [...], "ancient": [...],
    "april": [...]}``；release / snapshot / april 保持清单原有顺序（线上清单本身已按
    releaseTime 新 → 旧倒序）；ancient 由 old_beta 与 old_alpha 两段合并后统一按时间
    倒序。未知 / 未来新增 type 兜底归入预览版，不静默吞掉、不抛错。
    """
    groups: dict[str, list[dict]] = {key: [] for key in GROUP_KEYS}
    april_ids = set(C.APRIL_FOOL_IDS)

    for item in versions:
        norm = _normalize(item)
        if norm is None:
            continue
        vid = norm["id"]
        vtype = str(item.get("type") or "").strip()

        if vid in april_ids:
            groups[KEY_APRIL].append(norm)
        elif vtype == "release":
            groups[KEY_RELEASE].append(norm)
        elif vtype in ("old_beta", "old_alpha"):
            groups[KEY_ANCIENT].append(norm)
        elif vtype == "snapshot":
            groups[KEY_SNAPSHOT].append(norm)
        else:
            # 清单未来新增未知类型时兜底进预览版，避免条目丢失或分类崩溃。
            groups[KEY_SNAPSHOT].append(norm)

    # 远古版两段合并后统一按发布时间倒序；无时间戳条目排在本组末尾（保持清单原序稳定）。
    groups[KEY_ANCIENT].sort(
        key=lambda entry: entry["_moment"] or _EPOCH, reverse=True
    )

    # 排序完成后移除仅用于内部比较的时刻字段，对外只暴露 id 与展示时间。
    for group in groups.values():
        for entry in group:
            entry.pop("_moment", None)
    return groups


def _latest_entry(versions: list[dict], by_id: dict[str, dict], vid: str) -> dict:
    """按 id 取最新条目标准化结果；分组字典未命中时回退原始 versions 再找一次。"""
    if vid in by_id:
        return dict(by_id[vid])
    for item in versions:
        if str(item.get("id") or "").strip() == vid:
            norm = _normalize(item)
            if norm is not None:
                norm.pop("_moment", None)
                return norm
    return {"id": vid, "time": ""}


def _fetch_payload(url: str, should_cancel=None) -> dict:
    """请求单个清单端点并解析 JSON；瞬时断连按常量重试，仍失败向上抛出最后一个异常。

    ``should_cancel`` 返回真时立即抛 ``InterruptedError``，让关闭窗口的后台线程尽快退出。
    """
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"},
    )
    payload: dict | None = None
    last_error: Exception | None = None
    for attempt in range(C.META_FETCH_RETRIES):
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("版本清单拉取已被取消")
        try:
            with urllib.request.urlopen(request, timeout=C.META_HTTP_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            last_error = None
            break
        except Exception as exc:  # 网络 / 超时 / JSON 解析统一兜底，留给上层决定占位
            last_error = exc
            if attempt < C.META_FETCH_RETRIES - 1:
                # 重试间隔分段等待，期间响应取消信号，不被 sleep 整段卡住。
                waited = 0.0
                step = 0.1
                while waited < C.META_RETRY_DELAY:
                    if callable(should_cancel) and should_cancel():
                        raise InterruptedError("版本清单拉取已被取消")
                    time.sleep(step)
                    waited += step
    if last_error is not None:
        raise last_error
    return payload


def fetch_manifest_groups(
    urls: tuple[str, ...] | list[str] | None = None,
    should_cancel=None,
) -> dict:
    """拉取清单并解析为最新两行 + 四个全量分组列表；按镜像顺序轮询兜底。

    ``urls`` 缺省时取常量 ``MC_VERSION_MANIFEST_URLS``（国内 BMCLAPI2 → 官方 piston-meta）；
    逐个尝试，任一成功即用，全部失败抛出最后一个异常，由界面层静默回退占位。
    ``should_cancel`` 为可选无参回调，在每个镜像尝试前调用；返回真表示后台线程已被请求
    中断，立即抛 ``InterruptedError`` 退出轮询，避免关闭窗口后线程继续联网。

    返回结构::

        {
            "latest_release": {"id": ..., "time": ...},
            "latest_snapshot": {"id": ..., "time": ...},
            "release":  [{"id", "time"}, ...],
            "snapshot": [{"id", "time"}, ...],
            "ancient":  [{"id", "time"}, ...],
            "april":    [{"id", "time"}, ...],
        }

    任一全量分组缺失时对应空列表；latest 条目缺失时 ``id`` 为空串，由界面留空展示。
    """
    endpoints = tuple(urls) if urls else tuple(C.MC_VERSION_MANIFEST_URLS)
    payload: dict | None = None
    last_error: Exception | None = None
    for endpoint in endpoints:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("版本清单拉取已被取消")
        try:
            payload = _fetch_payload(endpoint, should_cancel=should_cancel)
            last_error = None
            break
        except Exception as exc:  # 当前镜像不可用就试下一个镜像，不中断其余轮询
            last_error = exc
    if last_error is not None:
        raise last_error

    latest = payload.get("latest") or {}
    release_id = str(latest.get("release") or "").strip()
    snapshot_id = str(latest.get("snapshot") or "").strip()
    if not release_id and not snapshot_id:
        raise ValueError("版本清单缺少 latest.release / latest.snapshot 字段")

    versions = payload.get("versions") or []
    groups = classify_versions(versions)

    by_id: dict[str, dict] = {}
    for group in groups.values():
        for entry in group:
            by_id[entry["id"]] = entry

    return {
        "latest_release": _latest_entry(versions, by_id, release_id),
        "latest_snapshot": _latest_entry(versions, by_id, snapshot_id),
        **groups,
    }


# --------------------------------------------------------------------------- #
# 本地清单缓存（yd/version_manifest_cache.json）
# --------------------------------------------------------------------------- #
_CACHE_SCHEMA = 1


def _cache_path() -> str:
    return os.path.join(data_dir(), C.META_CACHE_FILENAME)


def _manifest_is_valid(manifest: object) -> bool:
    """校验缓存里的清单字典结构完整，防止半损坏 JSON 被当成可用数据回填界面。"""
    if not isinstance(manifest, dict):
        return False
    if not isinstance(manifest.get("latest_release"), dict):
        return False
    if not isinstance(manifest.get("latest_snapshot"), dict):
        return False
    return all(isinstance(manifest.get(key), list) for key in GROUP_KEYS)


def load_cached_manifest() -> dict | None:
    """读取本地清单缓存；缺失 / 损坏 / 结构不完整时返回 ``None``，由调用方回退联网拉取。"""
    path = _cache_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(saved, dict) or saved.get("schema") != _CACHE_SCHEMA:
        return None
    manifest = saved.get("manifest")
    if not _manifest_is_valid(manifest):
        return None
    return manifest


def save_cached_manifest(manifest: dict) -> None:
    """把分类后的清单原子写入缓存目录；只落盘版本号与日期文本，不存下载链接。"""
    if not _manifest_is_valid(manifest):
        return
    directory = os.path.dirname(_cache_path())
    os.makedirs(directory, exist_ok=True)
    payload = {
        "schema": _CACHE_SCHEMA,
        "fetched_at": datetime.now(_BEIJING_TZ).isoformat(timespec="seconds"),
        "manifest": manifest,
    }
    tmp = _cache_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _cache_path())


def fetch_latest_versions() -> tuple[str, str, str, str]:
    """兼容旧接口：返回 ``(正式版号, 正式版发布日期, 预览版号, 预览版发布日期)``。

    版本号任一缺失时抛出异常由调用方兜底；发布日期解析失败仅留空，不影响版本号展示。
    """
    manifest = fetch_manifest_groups()
    release = manifest["latest_release"]
    snapshot = manifest["latest_snapshot"]
    return release["id"], release["time"], snapshot["id"], snapshot["time"]


def fetch_version_item(version_id: str, should_cancel=None) -> dict:
    """拉取清单并按 ``id`` 返回原始 versions 条目（含 ``url`` / ``type``）。

    v1.2.11.0 下载骨架新增：分类缓存只保存 id 与日期文本、不保存 version JSON 地址，
    下载某个版本时重新走镜像轮询定位该条目。找不到 id、清单拉取失败均向上抛出，由
    下载 worker 静默回退，不弹窗、不阻塞主线程。
    """
    payload: dict | None = None
    last_error: Exception | None = None
    for endpoint in C.MC_VERSION_MANIFEST_URLS:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("版本定位已被取消")
        try:
            payload = _fetch_payload(endpoint, should_cancel=should_cancel)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
    if payload is None:
        raise last_error if last_error is not None else RuntimeError("版本清单不可用")

    target = str(version_id or "").strip()
    for item in payload.get("versions", []):
        if str(item.get("id") or "").strip() == target:
            return item
    raise KeyError(f"清单中找不到版本 {target}")
