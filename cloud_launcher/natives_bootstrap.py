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

"""v1.3.2.0 原生库（natives）自动准备。

外部版本（PCL2 / 官方启动器等安装的标准版本）natives 目录为空或缺失时，从对应的
``natives-windows`` Jar 解压原生库；本地缺失的 Jar 先按官方源 + BMCL 镜像下载到全局
``libraries``（同时进入 classpath）。

两种 profile 布局都支持：

- **现代版本（1.19+ / 26.3）**：natives 是独立库条目，Maven 坐标第四段为
  ``natives-windows``（如 ``org.lwjgl:lwjgl:3.4.3:natives-windows``），经
  ``downloads.artifact`` 下载，没有 ``classifiers``；
- **老版本**：原生库在 ``downloads.classifiers['natives-windows']`` 中。

解压目标沿用 :func:`game_dirs.find_natives_dir` 返回值，与 ``java_runtime`` 传给 JVM 的
``natives_directory`` 保持一致；解压采用 basename 平铺（老版本 ``-Djava.library.path``
即平铺口径；现代版本 LWJGL 运行时仍会从 classpath 自行解压，平铺文件不影响其行为）。
纯 Python 标准库实现，不引入新依赖。
"""
from __future__ import annotations

import os

from . import constants as C
from . import download_engine as engine
from . import game_dirs
from . import version_profile

_NATIVES_WINDOWS = "natives-windows"
_NATIVE_LIB_SUFFIXES = (".dll",)


def _coordinate_classifier(lib: dict) -> str:
    """读取库 Maven 坐标第四段（classifier）；不足四段返回空串。"""
    parts = str(lib.get("name") or "").split(":")
    return parts[3] if len(parts) >= 4 else ""


def _is_modern_natives_entry(lib: dict) -> bool:
    """现代布局 natives 条目：坐标第四段精确等于 ``natives-windows``。

    显式排除 ``natives-windows-arm64``（本机为 x64，ARM64 原生库不需要）。
    """
    return _coordinate_classifier(lib) == _NATIVES_WINDOWS


def _native_sources(profile: dict) -> list[dict]:
    """收集 profile 内全部 Windows natives 源描述，按 Maven 相对路径去重。

    每项含 ``name / relative_path / url / sha1 / size / layout``；规则不允许在当前
    Windows 环境使用的库跳过。
    """
    sources: list[dict] = []
    seen_paths: set[str] = set()

    def add(relative_path, url, sha1, size, layout, name) -> None:
        rel = str(relative_path or "").strip()
        if not rel or rel in seen_paths:
            return
        seen_paths.add(rel)
        sources.append({
            "name": str(name or ""),
            "relative_path": rel,
            "url": str(url or "").strip(),
            "sha1": str(sha1 or "").strip(),
            "size": int(size or 0),
            "layout": layout,
        })

    for lib in profile.get("libraries") or []:
        if not engine.library_rule_allows(lib):
            continue
        name = str(lib.get("name") or "")
        if _is_modern_natives_entry(lib):
            artifact = (lib.get("downloads") or {}).get("artifact") or {}
            rel = version_profile.library_relative_path(lib)
            url = artifact.get("url") or C.BMCL_MAVEN_URL.format(path=rel)
            add(rel, url, artifact.get("sha1"), artifact.get("size"), "modern", name)
            continue
        classifiers = ((lib.get("downloads") or {}).get("classifiers") or {})
        classifier = classifiers.get(_NATIVES_WINDOWS) or {}
        if not classifier:
            continue
        rel = str(classifier.get("path") or "").strip()
        if not rel:
            continue
        url = classifier.get("url") or C.BMCL_MAVEN_URL.format(path=rel)
        add(rel, url, classifier.get("sha1"), classifier.get("size"), "legacy", name)
    return sources


def _count_dll(natives_dir: str) -> int:
    """递归统计目录内 ``.dll`` 原生库数量（含子目录）。"""
    if not os.path.isdir(natives_dir):
        return 0
    count = 0
    for _root, _dirs, files in os.walk(natives_dir):
        for filename in files:
            if filename.lower().endswith(_NATIVE_LIB_SUFFIXES):
                count += 1
    return count


def _natives_already_present(natives_dir: str) -> bool:
    """目录内已存在任意 ``.dll`` 即视为原生库就位，跳过重复解压（幂等）。"""
    return _count_dll(natives_dir) > 0


def _build_download_task(source: dict) -> engine.DownloadTask:
    """为缺失的 natives Jar 构造下载任务，目标为全局 ``libraries``（外部启动器口径）。

    落到全局库后 ``game_dirs.find_library`` 的全局回退即可命中，Jar 同时进入 classpath。
    """
    rel_path = source["relative_path"].replace("/", os.sep)
    local_path = os.path.join(game_dirs.global_libraries_dir(), rel_path)
    mirror = C.BMCL_MAVEN_URL.format(path=source["relative_path"])
    url = source["url"] or mirror
    return engine.DownloadTask(
        url=url,
        local_path=local_path,
        size=source["size"],
        sha1=source["sha1"],
        mirror_url=mirror if url != mirror else None,
        label=source["name"] or os.path.basename(local_path),
    )


def ensure_natives(profile: dict, alias: str, should_cancel=None) -> dict:
    """确保版本 natives 目录就位并含原生库。

    返回 ``{"status", "message", "dll_count", "sources"}``：

    - ``skipped``：目录已有原生库，无需处理；
    - ``ready``：本次解压完成（或 profile 无 natives 条目，已兜底创建默认目录）；
    - ``failed``：下载 / 解压出错，``message`` 为中文原因。
    """
    natives_dir = game_dirs.find_natives_dir(alias)
    if _natives_already_present(natives_dir):
        return {
            "status": "skipped",
            "message": "",
            "dll_count": _count_dll(natives_dir),
            "sources": 0,
        }

    sources = _native_sources(profile)
    tracker = engine.ProgressTracker()

    if not sources:
        # 无 natives 条目的版本：确保默认目录存在，现代 LWJGL 会自行解压到子目录。
        try:
            os.makedirs(natives_dir, exist_ok=True)
        except OSError as exc:
            return {
                "status": "failed",
                "message": f"原生库目录创建失败：{exc}",
                "dll_count": 0,
                "sources": 0,
            }
        return {"status": "ready", "message": "", "dll_count": 0, "sources": 0}

    try:
        for source in sources:
            if callable(should_cancel) and should_cancel():
                return {
                    "status": "failed",
                    "message": "原生库准备已被取消。",
                    "dll_count": 0,
                    "sources": len(sources),
                }
            rel = source["relative_path"]
            jar_path = game_dirs.find_library(alias, rel)
            if not jar_path:
                task = _build_download_task(source)
                ok, reason = engine.download_one(task, tracker, should_cancel)
                if not ok:
                    return {
                        "status": "failed",
                        "message": f"原生库 Jar 下载失败：{reason}",
                        "dll_count": 0,
                        "sources": len(sources),
                    }
                jar_path = task.local_path
            if not engine.unpack_natives_jar(jar_path, natives_dir, should_cancel):
                return {
                    "status": "failed",
                    "message": f"原生库解压失败：{source['name'] or rel}",
                    "dll_count": 0,
                    "sources": len(sources),
                }
    except Exception as exc:  # 兜底：未预期异常统一转中文失败，不把异常抛到 UI 层
        return {
            "status": "failed",
            "message": f"原生库准备异常：{exc}",
            "dll_count": 0,
            "sources": len(sources),
        }

    return {
        "status": "ready",
        "message": "",
        "dll_count": _count_dll(natives_dir),
        "sources": len(sources),
    }
