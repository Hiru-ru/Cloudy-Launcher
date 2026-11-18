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

"""v1.3.6.0 内容真实下载模块：Modrinth 版本文件解析 + 落盘到已安装版本目录。

在 v1.3.4.0「搜索 + 图文展示」基础上补上真实下载链路。按分类把项目文件下到目标
游戏版本自己的隔离目录（与 CLY 版本隔离口径一致）：

======  ==========================================  ====================
分类    落点                                        文件类型
======  ==========================================  ====================
mod     ``versions/<别名>/mods/``                   ``.jar``
shader  ``versions/<别名>/shaderpacks/``            ``.zip``
resourcepack ``versions/<别名>/resourcepacks/``     ``.zip``
datapack ``versions/<别名>/datapacks/``             ``.zip``
======  ==========================================  ====================

- 只按目标版本的真实 ``mc_version`` 与加载器筛选：mod 必须匹配加载器（原版版本不
  允许装 mod），光影 / 资源包 / 数据包只核对游戏版本；
- 单文件流式下载，``.part`` 半成品 + ``os.replace`` 原子落盘，失败不留残file；
- 目标同名文件已存在时抛 :class:`ContentFileExists`，由界面弹框征询，不静默改名
  （历史否决项）；
- 整合包（``.mrpack``）需要解包 + 依赖安装，不在本模块范围，界面明确提示；
- 纯标准库 urllib / json / os，UA 纯 ASCII，不引入第三方依赖。
"""
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import constants as C
from . import game_dirs

VERSION_API = "https://api.modrinth.com/v2/project/{project_id}/version"
VERSION_TIMEOUT = 25
# Modrinth CDN 走 Cloudflare，国内线路偶发长时间不吐字节；读超时放宽到 60s 并配合
# 多次重试，避免 2MB 左右的小文件因一次卡顿就被判失败。
DOWNLOAD_TIMEOUT = 60
CHUNK_SIZE = 256 * 1024
#: 单个文件下载最多尝试次数（清掉 .part 后重下）。
DOWNLOAD_ATTEMPTS = 3

#: 分类 → 版本隔离目录下的子目录名。
INSTALL_DIRS = {
    "mod": "mods",
    "shader": "shaderpacks",
    "resourcepack": "resourcepacks",
    "datapack": "datapacks",
}

#: 分类 → 期望文件扩展名（有多个候选 file 时按此优先）。
INSTALL_EXTENSIONS = {
    "mod": ".jar",
    "shader": ".zip",
    "resourcepack": ".zip",
    "datapack": ".zip",
}

#: 分类 → 界面提示用的中文名。
KIND_LABELS = {
    "mod": "mod",
    "shader": "光影包",
    "resourcepack": "资源包",
    "datapack": "数据包",
    "modpack": "整合包",
}

#: 需要解包安装、暂不支持一键落盘的分类。
UNSUPPORTED_KINDS = ("modpack",)

#: 加载器 → Modrinth ``loaders`` 查询值（mod 分类用；原版与 OptiFine 不能装 mod）。
MOD_LOADER_FILTERS = {
    C.LOADER_FABRIC: ("fabric",),
    C.LOADER_FORGE: ("forge",),
    C.LOADER_NEOFORGE: ("neoforge",),
}


class ContentInstallError(Exception):
    """内容下载链路统一异常基类（消息直接用于界面提示）。"""


class NoCompatibleFile(ContentInstallError):
    """目标版本没有可下载的兼容文件。"""


class ContentFileExists(ContentInstallError):
    """目标目录已存在同名文件（由界面征询覆盖）。"""

    def __init__(self, path: str) -> None:
        super().__init__("目标目录已存在同名文件")
        self.path = path


class _Incomplete(ContentInstallError):
    """收到的字节少于 Content-Length（线路断流），属可重试抖动，不对外暴露。"""


def _ua_header() -> dict:
    return {"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"}


def install_dir(kind: str, alias: str) -> str:
    """某分类在某版本隔离目录下的落点目录（不保证已创建）。"""
    sub = INSTALL_DIRS.get(kind)
    if not sub:
        raise ContentInstallError("这个分类暂不支持下载")
    return os.path.join(game_dirs.version_dir(alias), sub)


def _request_json(url: str, timeout: int, should_cancel=None) -> list:
    if callable(should_cancel) and should_cancel():
        raise ContentInstallError("已取消")
    req = urllib.request.Request(url, headers=_ua_header())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list):
        raise ContentInstallError("内容接口返回格式异常")
    return data


def _build_version_url(project_id: str, mc_version: str, loaders) -> str:
    params = {}
    if mc_version:
        params["game_versions"] = json.dumps([mc_version], separators=(",", ":"))
    if loaders:
        params["loaders"] = json.dumps(list(loaders), separators=(",", ":"))
    url = VERSION_API.format(project_id=urllib.parse.quote(project_id, safe=""))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def _pick_file(version: dict, kind: str) -> dict | None:
    """在一个版本条目里挑出要下载的文件：优先期望扩展名，其次 primary。"""
    files = version.get("files") or []
    if not files:
        return None
    want_ext = INSTALL_EXTENSIONS.get(kind, "")
    if want_ext:
        files = [f for f in files
                 if str(f.get("filename") or "").lower().endswith(want_ext)]
        if not files:
            # 扩展名不符（例如数据包项目只给了 jar 的 mod 版本）视为该版本不可用，
            # 不能把 jar 塞进 resourcepacks / datapacks 目录。
            return None
    primary = [f for f in files if f.get("primary")]
    return (primary or files)[0]


def resolve_target(project_id: str, kind: str, mc_version: str, loader: str,
                   timeout: int = VERSION_TIMEOUT,
                   should_cancel=None) -> dict:
    """解析「某项目在某游戏版本上应下载哪个文件」。

    返回 ``{"version_number","version_name","loaders","game_versions",
    "filename","url","size","published"}``；无兼容文件抛 :class:`NoCompatibleFile`。
    """
    if kind in UNSUPPORTED_KINDS:
        raise ContentInstallError(
            "整合包需要解包并安装依赖，暂不支持一键下载（后续版本支持）"
        )
    if kind not in INSTALL_DIRS:
        raise ContentInstallError("这个分类暂不支持下载")

    loaders = ()
    if kind == "mod":
        key = str(loader or "").strip().lower()
        loaders = MOD_LOADER_FILTERS.get(key, ())
        if not loaders:
            raise NoCompatibleFile(
                "当前版本是%s，不能装 mod；请选一个 Fabric / Forge / NeoForge 版本"
                % (C.LOADER_LABELS.get(key, "原版"))
            )

    url = _build_version_url(project_id, mc_version, loaders)
    try:
        versions = _request_json(url, timeout, should_cancel)
    except urllib.error.HTTPError as exc:
        raise ContentInstallError("查询版本失败（HTTP %s）" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise ContentInstallError("查询版本失败，请检查网络") from exc
    except (TimeoutError, OSError) as exc:
        raise ContentInstallError("查询版本超时，请稍后重试") from exc
    except ValueError as exc:
        raise ContentInstallError("查询版本返回内容解析失败") from exc

    if not versions:
        raise NoCompatibleFile(
            "这个项目没有适配 %s 的文件，无法下载" % (mc_version or "当前版本")
        )

    for version in versions:
        if callable(should_cancel) and should_cancel():
            raise ContentInstallError("已取消")
        chosen = _pick_file(version, kind)
        if not chosen or not chosen.get("url"):
            continue
        return {
            "version_number": str(version.get("version_number") or ""),
            "version_name": str(version.get("name") or ""),
            "loaders": list(version.get("loaders") or []),
            "game_versions": list(version.get("game_versions") or []),
            "filename": str(chosen.get("filename") or ""),
            "url": str(chosen.get("url") or ""),
            "size": int(chosen.get("size") or 0),
            "published": str(version.get("date_published") or ""),
        }
    raise NoCompatibleFile(
        "这个项目没有适配 %s 的可下载文件，无法下载" % (mc_version or "当前版本")
    )


def _safe_filename(name: str) -> str:
    """文件名只保留基名并清洗路径分隔符，防止写出目标目录。"""
    base = os.path.basename(str(name or "").strip().replace("\\", "/"))
    base = base.replace("/", "").replace("\\", "")
    return base or "download.bin"


def _download_file(url: str, dest: str, should_cancel=None, on_progress=None,
                   attempts: int = DOWNLOAD_ATTEMPTS, on_retry=None) -> int:
    """流式下载到 ``dest``（调用方已确保父目录存在）；返回写入字节数。

    网络抖动 / 读超时会清掉 ``.part`` 残片后重试，最多 ``attempts`` 次；用户取消
    立即抛出，不再重试。``on_retry`` 在每次重试开始前回调 ``(第几次, 总次数)``，
    界面据此提示「线路不稳，正在重试」，避免进度归零被误读成卡死。
    """
    tmp = dest + ".part"
    last_error = None
    for attempt in range(max(1, attempts)):
        if callable(should_cancel) and should_cancel():
            _remove_quiet(tmp)
            raise ContentInstallError("已取消")
        if attempt > 0:
            # 线性退避，给线路一点恢复时间。
            if callable(on_retry):
                on_retry(attempt + 1, max(1, attempts))
            time.sleep(1.5 * attempt)
        written = 0
        req = urllib.request.Request(url, headers=_ua_header())
        try:
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                with open(tmp, "wb") as fh:
                    while True:
                        if callable(should_cancel) and should_cancel():
                            raise ContentInstallError("已取消")
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        written += len(chunk)
                        if callable(on_progress):
                            on_progress(written, total)
            if written <= 0:
                raise ContentInstallError("下载到的文件是空的，请稍后重试")
            # 断流兜底：CDN 中途关连接时 read() 只返回 EOF、不抛异常，必须自己对
            # 账 Content-Length，否则半截文件会被当成成功落盘（坏 jar 进 mods）。
            if total > 0 and written != total:
                raise _Incomplete(
                    "只收到 %s/%s 字节" % (written, total))
            os.replace(tmp, dest)
            return written
        except _Incomplete as exc:
            _remove_quiet(tmp)
            last_error = exc
        except ContentInstallError:
            _remove_quiet(tmp)
            raise
        except urllib.error.HTTPError as exc:
            _remove_quiet(tmp)
            # 4xx 属确定性错误（文件被删 / 无权限），不重试。
            if 400 <= exc.code < 500:
                raise ContentInstallError("下载失败（HTTP %s）" % exc.code) from exc
            last_error = exc
        except urllib.error.URLError as exc:
            _remove_quiet(tmp)
            last_error = exc
        except (TimeoutError, OSError, http.client.IncompleteRead) as exc:
            # 断流（只下发半截就关连接）在 http.client 里是 IncompleteRead，
            # 属可重试的网络抖动，不能直接判失败。
            _remove_quiet(tmp)
            last_error = exc
    _remove_quiet(tmp)
    if isinstance(last_error, _Incomplete):
        raise ContentInstallError("下载屡次中断（线路不稳定），请稍后重试") from last_error
    if isinstance(last_error, urllib.error.URLError):
        raise ContentInstallError("下载失败，请检查网络后重试") from last_error
    if isinstance(last_error, urllib.error.HTTPError):
        raise ContentInstallError("下载失败（HTTP %s）" % last_error.code) from last_error
    raise ContentInstallError("下载中断，请稍后重试") from last_error


def _remove_quiet(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def download_content(project_id: str, kind: str, alias: str, mc_version: str,
                     loader: str, overwrite: bool = False,
                     should_cancel=None, on_progress=None,
                     version_callback=None, on_retry=None) -> dict:
    """把某项目适配目标版本的文件真实下载到该版本隔离目录。

    ``on_progress`` 回调 ``(read_bytes, total_bytes)``；``version_callback`` 在解析
    出目标文件后回调一次（界面可提前显示文件名 / 版本号）；``on_retry`` 在自动
    重试前回调 ``(第几次, 总次数)``。

    返回 ``{"path","filename","version_number","size","dir"}``。
    """
    if not alias:
        raise ContentInstallError("请先选择一个游戏版本")
    if not game_dirs.is_version_installed(alias):
        raise ContentInstallError(
            "版本目录「%s」还不完整，请先把它下载安装好" % alias
        )

    target = resolve_target(project_id, kind, mc_version, loader,
                            should_cancel=should_cancel)
    if callable(version_callback):
        version_callback(target)

    filename = _safe_filename(target["filename"])
    directory = install_dir(kind, alias)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        raise ContentInstallError("无法创建目录：%s" % directory) from exc

    dest = os.path.join(directory, filename)
    if os.path.isfile(dest) and not overwrite:
        raise ContentFileExists(dest)

    written = _download_file(target["url"], dest,
                             should_cancel=should_cancel, on_progress=on_progress,
                             on_retry=on_retry)
    return {
        "path": dest,
        "filename": filename,
        "version_number": target["version_number"],
        "size": written,
        "dir": directory,
    }
