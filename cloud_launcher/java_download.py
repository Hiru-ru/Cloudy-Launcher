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

"""Java 运行环境自动下载与安装（v1.4.5.1 新增）。

按本机网络环境智能选择下载源，并保留全部候选源做自动切换：

- 国内（UTC+8 等）：清华 TUNA 主源 → 华为云镜像兜底 → Adoptium 标准源；
- 国外：Adoptium 标准 latest API 优先 → 清华 / 华为镜像兜底。

清华目录页原始 HTML 含具体 zip 文件名（带构建号，如 8u512b09），先正则解析；
华为目录页是 JS 单页、文件名异步加载，故复用清华解析出的同名文件（两镜像同步同一套
Adoptium 产物，已实测同名可达）。下载复用 :mod:`download_engine` 的多候选自动切换、
断点续传，再用 :mod:`zipfile` 解压到云朵运行时目录，带 zip-slip 路径防护。
"""
from __future__ import annotations

import os
import re
import urllib.request
import zipfile

from . import constants as C
from . import download_engine
from .resources import data_dir

_ZIP_NAME_PATTERN = re.compile(r"OpenJDK[0-9A-Za-z._-]*?\.zip")
# 中国及周边 UTC+8 时区偏移（秒）。
_CHINA_GMT_OFFSET = 8 * 3600


def runtime_root() -> str:
    """云朵 Java 运行时根目录：``<数据目录>/runtime/java``。"""
    return os.path.join(data_dir(), C.JAVA_RUNTIME_DIR_NAME)


def _major_dir(major: int) -> str:
    return os.path.join(runtime_root(), str(major))


def is_domestic_network() -> bool:
    """判断是否优先走国内镜像。

    轻量口径：本地时区偏移为 UTC+8 即判国内（覆盖中国及新加坡、马来西亚等，这些地区
    地理上也更适合走国内镜像）。这一判断只决定候选源的默认顺序，实际下载仍保留全部
    候选源、任一失败自动切换，因此即使判断有偏差也不会导致下载失败。
    """
    try:
        return int(time_localtime_gmtoff()) == _CHINA_GMT_OFFSET
    except (TypeError, ValueError):
        # 拿不准时默认国内：国内镜像在国内更快，在国外通常也能连通。
        return True


def time_localtime_gmtoff() -> int:
    """包装 ``time.localtime().tm_gmtoff``，单独成函数便于测试 monkeypatch。"""
    import time

    return int(time.localtime().tm_gmtoff)


def _open_url(url: str, timeout: int = 20):
    req = urllib.request.Request(
        url, headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"}
    )
    return urllib.request.urlopen(req, timeout=timeout)


def _resolve_mirror_zip_name(major: int) -> str:
    """从清华目录页解析最新 JRE zip 文件名（带构建号）；解析失败返回空串。"""
    dir_url = f"{C.TUNA_ADOPTIUM_BASE}/{major}/jre/x64/windows/"
    try:
        with _open_url(dir_url) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    names = sorted(set(_ZIP_NAME_PATTERN.findall(html)))
    return names[-1] if names else ""


def build_candidate_urls(major: int, domestic: bool | None = None) -> list[str]:
    """构造按网络环境排序的全部候选下载 URL（去重、保持顺序）。

    镜像文件名解析失败时，国内也会退回 Adoptium 标准源，保证至少有一个可用地址。
    """
    if domestic is None:
        domestic = is_domestic_network()
    adoptium = C.ADOPTIUM_LATEST_API.format(major=major)

    mirror_name = _resolve_mirror_zip_name(major)
    mirror_urls: list[str] = []
    if mirror_name:
        mirror_urls = [
            f"{C.TUNA_ADOPTIUM_BASE}/{major}/jre/x64/windows/{mirror_name}",
            f"{C.HUAWEI_ADOPTIUM_BASE}/{major}/jre/x64/windows/{mirror_name}",
        ]

    if domestic:
        ordered = mirror_urls + [adoptium]
    else:
        ordered = [adoptium] + mirror_urls

    result: list[str] = []
    for url in ordered:
        if url and url not in result:
            result.append(url)
    return result


def download_zip(major: int, tracker: download_engine.ProgressTracker,
                 cancel_check=None) -> str:
    """下载指定主版本的 JRE zip，返回本地 zip 路径；失败抛异常。

    复用 :func:`download_engine.download_one`，多候选源自动切换、断点续传。
    """
    urls = build_candidate_urls(major)
    if not urls:
        raise RuntimeError("无法确定 Java 下载地址")

    target_dir = _major_dir(major)
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, f"jre-{major}.zip")

    task = download_engine.DownloadTask(
        url=urls[0],
        local_path=zip_path,
        mirror_url=urls[1] if len(urls) > 1 else None,
        extra_urls=urls[2:],
        label=f"Java {major}",
    )
    ok, reason = download_engine.download_one(task, tracker, cancel_check)
    if not ok:
        raise RuntimeError(reason)
    return zip_path


def _is_within(base_dir: str, target_path: str) -> bool:
    """判断 ``target_path`` 解析后是否仍位于 ``base_dir`` 内（zip-slip 防护）。"""
    base_real = os.path.realpath(base_dir)
    target_real = os.path.realpath(target_path)
    try:
        return os.path.commonpath([base_real, target_real]) == base_real
    except ValueError:
        return False


def _find_java_exe(target_dir: str) -> str:
    """在解压目录下定位 ``bin/java.exe``；找不到返回空串。"""
    for root, _dirs, files in os.walk(target_dir):
        if os.path.basename(root).lower() == "bin" and "java.exe" in files:
            return os.path.join(root, "java.exe")
    return ""


def extract_zip(major: int, zip_path: str, cancel_check=None) -> str:
    """解压 JRE zip 到运行时目录并返回 ``java.exe`` 路径；失败抛异常。

    解压前清理该主版本目录下的旧解压内容（保留 zip），逐个成员做 zip-slip 校验。
    """
    target_dir = _major_dir(major)
    os.makedirs(target_dir, exist_ok=True)

    # 清理旧的解压顶层目录 / 文件，但保留本次要使用的 zip，避免重复安装残留。
    zip_name = os.path.basename(zip_path)
    for entry in os.listdir(target_dir):
        if entry == zip_name:
            continue
        old_path = os.path.join(target_dir, entry)
        if not _is_within(target_dir, old_path):
            continue
        try:
            if os.path.isdir(old_path):
                import shutil

                shutil.rmtree(old_path, ignore_errors=True)
            else:
                os.remove(old_path)
        except OSError:
            continue

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            if callable(cancel_check) and cancel_check():
                raise InterruptedError("安装已取消")
            destination = os.path.join(target_dir, member)
            if not _is_within(target_dir, destination):
                raise RuntimeError(f"压缩包含非法路径：{member}")
        archive.extractall(target_dir)

    java_exe = _find_java_exe(target_dir)
    if not java_exe:
        raise RuntimeError("解压完成后未找到 java.exe")
    return java_exe
