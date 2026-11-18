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

"""便携 ``.minecraft`` 目录管理、版本隔离与本地已安装版本扫描。

v1.2.11.0 新增。目录口径沿用本工程既有便携规则：与 ``config.json`` 同目录
（打包后为 exe 同级，源码运行时为工程根），程序拷到哪里数据就在哪里，**不使用**
``%APPDATA%\\.minecraft``。v1.3.10.0 曾随数据目录改造把 ``.minecraft`` 移入 CLY，
v1.3.10.1 按用户要求改回 exe 同级——其余运行期数据仍在 CLY，唯独 ``.minecraft`` 留在外面。

v1.2.12.0：目录名与版本号 / 加载器解耦——目录名是用户自定义**别名**（可重复下载同一 MC
版本、不同加载器并存），原生 ``mc_version``、加载器类型与版本记录在隔离目录内的
``install_meta.json``。隔离目录内新增 ``libraries/``（依赖库 jar）与 ``natives/``（解压后的
原生库）子目录；全局资源统一落到 ``.minecraft/assets``。

目录结构::

    <exe 同级>/.minecraft/
        assets/
            objects/<hash[:2]>/<hash>          # 现代版本资源对象
            virtual/legacy/<name>               # 1.12 及更早版本 legacy 资源
        versions/
            <别名>/
                <别名>.json                     # 最终生效版本元数据（合并后落盘）
                install_meta.json              # 别名 ↔ mc_version ↔ 加载器类型 / 版本
                client.jar                     # 客户端 Jar
                libraries/                     # 依赖库 jar
                natives/                       # 解压后的原生库
                saves/                         # 本版本独立存档目录（版本隔离）
                config/                        # 本版本独立配置目录（版本隔离）

- 目录缺失时由 :func:`ensure_base_dirs` 自动创建；已存在则直接扫描，不重复创建、不覆盖。
- 任何磁盘 / 权限异常统一静默回退（返回空目录列表或 ``False``），不弹窗、不抛到主线程。
"""
import json
import os
import re

from . import constants as C
from .resources import app_base_dir

# 目录名安全字符：保留 Unicode 字母/数字（含中文）与点/横线/下划线，仅把路径分隔符、
# Windows 非法文件名字符与控制字符替换为下划线，既防止目录逃逸，又不静默吞掉用户起的中文名。
_UNSAFE_DIR_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def sanitize_version_id(version_id: str) -> str:
    """把版本号 / 别名清洗为合法目录段；空值回退 ``version``。"""
    safe = _UNSAFE_DIR_CHARS.sub("_", str(version_id or "").strip())
    safe = safe.strip("._-")
    return safe or "version"


def minecraft_root() -> str:
    """``.minecraft`` 便携根目录绝对路径（v1.3.10.1 起回到 exe 同级，不进 CLY，不保证已创建）。"""
    return os.path.join(app_base_dir(), C.MINECRAFT_DIR_NAME)


def versions_dir() -> str:
    """``.minecraft/versions`` 绝对路径（不保证已创建）。"""
    return os.path.join(minecraft_root(), C.VERSIONS_DIR_NAME)


def assets_root() -> str:
    """全局资源根目录 ``.minecraft/assets``（不保证已创建）。"""
    return os.path.join(minecraft_root(), "assets")


def assets_objects_dir() -> str:
    """现代版本资源对象目录 ``.minecraft/assets/objects``。"""
    return os.path.join(assets_root(), "objects")


def assets_virtual_legacy_dir() -> str:
    """1.12 及更早版本 legacy 资源目录 ``.minecraft/assets/virtual/legacy``。"""
    return os.path.join(assets_root(), "virtual", "legacy")


def assets_index_path(index_id: str) -> str:
    """资源索引 JSON 落盘路径 ``.minecraft/assets/indexes/<id>.json``。"""
    return os.path.join(assets_root(), "indexes", f"{index_id}.json")


def version_dir(alias: str) -> str:
    """某版本隔离目录 ``.minecraft/versions/<别名>`` 绝对路径（不保证已创建）。"""
    return os.path.join(versions_dir(), sanitize_version_id(alias))


def version_json_path(alias: str) -> str:
    """版本元数据 JSON 在隔离目录内的绝对路径。"""
    safe = sanitize_version_id(alias)
    return os.path.join(version_dir(alias), C.VERSION_JSON_FILENAME.format(id=safe))


def install_meta_path(alias: str) -> str:
    """安装元数据 ``install_meta.json`` 在隔离目录内的绝对路径。"""
    return os.path.join(version_dir(alias), C.VERSION_META_FILENAME)


def client_jar_path(alias: str) -> str:
    """云朵下载写入的客户端 Jar（固定 ``client.jar``）在隔离目录内的绝对路径。"""
    return os.path.join(version_dir(alias), C.VERSION_CLIENT_JAR_FILENAME)


def find_client_jar(alias: str) -> str | None:
    """返回版本目录内实际存在且非空的客户端 Jar 路径，两种命名都识别。

    - 云朵下载的版本固定为 ``client.jar``；
    - 标准 MC / 其他启动器（PCL2、官方启动器等）放入的版本为与目录同名的
      ``<id>.jar``。

    两者都不存在时返回 ``None``，调用方据此判定该版本未真正安装。
    """
    safe = sanitize_version_id(alias)
    cloud_jar = os.path.join(version_dir(alias), C.VERSION_CLIENT_JAR_FILENAME)
    if os.path.isfile(cloud_jar) and os.path.getsize(cloud_jar) > 0:
        return cloud_jar
    standard_jar = os.path.join(
        version_dir(alias), C.VERSION_STANDARD_JAR_FILENAME.format(id=safe)
    )
    if os.path.isfile(standard_jar) and os.path.getsize(standard_jar) > 0:
        return standard_jar
    return None


def libraries_dir(alias: str) -> str:
    """版本隔离目录内依赖库目录 ``libraries/``。"""
    return os.path.join(version_dir(alias), C.VERSION_LIBRARIES_DIR_NAME)


def global_libraries_dir() -> str:
    """全局依赖库目录 ``.minecraft/libraries``。

    标准 MC / PCL2 / 官方启动器等外部启动器把依赖库集中放在这里（与版本目录平级），
    而云朵下载的版本放在各自的 ``versions/<别名>/libraries``。启动外部版本时必须
    两处都查，否则 classpath 里一个库都拿不到。
    """
    return os.path.join(minecraft_root(), C.VERSION_LIBRARIES_DIR_NAME)


def find_library(alias: str, relative_path: str) -> str | None:
    """解析某个依赖库 jar 的真实路径：版本隔离目录优先，其次全局 ``libraries``。

    ``relative_path`` 是 Maven 相对路径（形如 ``org/lwjgl/lwjgl/3.4.3/lwjgl-3.4.3.jar``）。
    两处都不存在（或为空文件）返回 ``None``，调用方按缺失处理、不把空路径塞进 classpath。
    """
    rel = str(relative_path or "").strip().replace("/", os.sep).replace("\\", os.sep)
    if not rel:
        return None
    for root in (libraries_dir(alias), global_libraries_dir()):
        candidate = os.path.join(root, rel)
        try:
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
                return candidate
        except OSError:
            continue
    return None


def _dir_has_content(path: str) -> bool:
    """目录存在且至少有一个条目（空目录视同没有）。"""
    try:
        return os.path.isdir(path) and bool(os.listdir(path))
    except OSError:
        return False


def find_natives_dir(alias: str) -> str:
    """返回该版本启动时应使用的 natives 目录。

    顺序：云朵口径 ``<版本目录>/natives``（有内容才用）→ 外部启动器口径
    ``<版本目录>/<别名>-natives``（PCL2 等解压位置）→ 回落到 ``natives/``
    默认路径（目录可空，现代版本由 LWJGL 自行解压到 ``natives/lwjgl`` 等子目录）。
    """
    safe = sanitize_version_id(alias)
    cloud_natives = os.path.join(version_dir(alias), C.VERSION_NATIVES_DIR_NAME)
    if _dir_has_content(cloud_natives):
        return cloud_natives
    external_natives = os.path.join(
        version_dir(alias), f"{safe}{C.VERSION_EXTERNAL_NATIVES_SUFFIX}"
    )
    if _dir_has_content(external_natives):
        return external_natives
    return cloud_natives


def natives_dir(alias: str) -> str:
    """版本隔离目录内原生库目录 ``natives/``。"""
    return os.path.join(version_dir(alias), C.VERSION_NATIVES_DIR_NAME)


def launch_log_path(alias: str) -> str:
    """游戏进程 stdout/stderr 重定向日志，用于排查启动后立即退出等问题。"""
    return os.path.join(version_dir(alias), "launcher_launch.log")


def _saves_dir(alias: str) -> str:
    return os.path.join(version_dir(alias), C.VERSION_SAVES_DIR_NAME)


def _config_dir(alias: str) -> str:
    return os.path.join(version_dir(alias), C.VERSION_CONFIG_DIR_NAME)


def ensure_base_dirs() -> bool:
    """确保 ``.minecraft/versions`` 与全局资源目录存在；成功返回 ``True``，异常静默返回 ``False``。"""
    try:
        os.makedirs(versions_dir(), exist_ok=True)
        os.makedirs(assets_objects_dir(), exist_ok=True)
        return True
    except OSError:
        return False


def ensure_version_dirs(alias: str) -> bool:
    """确保某版本隔离目录及其 ``libraries/``、``natives/``、``saves/``、``config/`` 子目录存在；
    异常静默返回 ``False``。"""
    try:
        target = version_dir(alias)
        os.makedirs(libraries_dir(alias), exist_ok=True)
        os.makedirs(natives_dir(alias), exist_ok=True)
        os.makedirs(_saves_dir(alias), exist_ok=True)
        os.makedirs(_config_dir(alias), exist_ok=True)
        os.makedirs(target, exist_ok=True)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# 安装元数据读写（别名 ↔ 原生 mc_version ↔ 加载器类型 / 版本）
# --------------------------------------------------------------------------- #
def write_install_meta(alias: str, mc_version: str, loader: str,
                       loader_version: str = "", extra: dict | None = None) -> bool:
    """把安装元数据原子写入隔离目录；成功返回 ``True``，异常静默返回 ``False``。"""
    # 先并入 extra（保留 avatar / modpack_* 等附加字段），再用显式核心字段覆盖，
    # 避免 extra 里的旧 loader / mc_version 把本次新值冲掉。
    meta: dict = {}
    if isinstance(extra, dict):
        meta.update(extra)
    meta.update({
        "schema": 1,
        "alias": sanitize_version_id(alias),
        "mc_version": str(mc_version or ""),
        "loader": str(loader or C.LOADER_VANILLA),
        "loader_version": str(loader_version or ""),
    })
    path = install_meta_path(alias)
    tmp_path = path + ".tmp"
    try:
        ensure_version_dirs(alias)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError:
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def read_install_meta(alias: str) -> dict:
    """读取隔离目录安装元数据；缺失 / 损坏返回空字典，不抛错。"""
    path = install_meta_path(alias)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def unique_alias(base_alias: str) -> str:
    """生成不与现有隔离目录冲突的别名：基础名已占用时依次追加 ``-2``、``-3``…。

    v1.3.2.0 起下载页不再调用本函数静默改名（用户明确否决，改为弹框要求自己命名）；
    保留函数供历史测试与其他只读场景使用。
    """
    base = sanitize_version_id(base_alias) or "version"
    candidate = base
    index = 2
    while os.path.isdir(version_dir(candidate)):
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def alias_exists(alias: str) -> bool:
    """v1.3.2.0：判定某别名对应的版本隔离目录是否已存在（用于「开始下载」撞名提示）。"""
    safe = str(alias or "").strip()
    if not safe:
        return False
    return os.path.isdir(version_dir(safe))


def is_version_installed(alias: str) -> bool:
    """判定版本是否已完整安装：隔离目录内版本 JSON 与客户端 Jar 均存在且非空。

    客户端 Jar 兼容云朵的 ``client.jar`` 与标准 MC 的 ``<id>.jar`` 两种命名，外部
    放入的标准版本也能识别。只下载到一半（缺任一文件）视为未安装，下载页仍显示
    下载按钮；读盘异常返回 ``False``。
    """
    if not alias:
        return False
    json_path = version_json_path(alias)
    try:
        if not (os.path.isfile(json_path) and os.path.getsize(json_path) > 0):
            return False
        return find_client_jar(alias) is not None
    except OSError:
        return False


def _read_version_json_id(json_path: str) -> str:
    """从版本 JSON 读取真实 ``id`` 字段（标准 MC 版本的真实版本号）；异常返回空串。"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return str(data.get("id") or "")
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    return ""


def local_version_base(alias: str) -> str:
    """从本地版本 JSON 解析真实 MC 底座版本号，读不到返回空串。

    规则：加载器 profile（Fabric/Forge 等）带 ``inheritsFrom``，其值即真实 MC 版本；
    普通版本无该字段，直接取 ``id``。供缺 install_meta / 未完整安装（无 client.jar）的
    外部版本在详情页推导 mc_version，避免把用户自定义别名当成真实版本号去远程清单
    定位而抛 KeyError。标准命名 JSON 缺失时，回退到目录内第一个 .json。
    """
    directory = version_dir(alias)
    safe = sanitize_version_id(alias)
    json_path = os.path.join(directory, C.VERSION_JSON_FILENAME.format(id=safe))
    if not os.path.isfile(json_path):
        try:
            candidates = [os.path.join(directory, n)
                          for n in os.listdir(directory) if n.endswith(".json")]
        except OSError:
            return ""
        if not candidates:
            return ""
        json_path = candidates[0]
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    inherits = str(data.get("inheritsFrom") or "").strip()
    if inherits:
        return inherits
    return str(data.get("id") or "").strip()


def scan_installed_entries() -> list[dict]:
    """扫描 ``versions/`` 下已完整安装的版本，返回条目字典列表（按别名升序）。

    每条：``{"alias": 目录别名, "mc_version": 原生版本号, "loader": 加载器键,
    "loader_version": 加载器版本}``。客户端 Jar 兼容云朵 ``client.jar`` 与标准
    ``<id>.jar`` 两种命名，外部启动器 / 手动放入的标准版本也能识别；云朵安装元数据
    缺失时，从版本 JSON 读取真实 id 作为 mc_version、加载器按原版处理。目录缺失、
    权限不足、JSON 损坏都静默跳过，不抛错。
    """
    result: list[dict] = []
    base = versions_dir()
    if not os.path.isdir(base):
        return result
    try:
        entries = os.listdir(base)
    except OSError:
        return result

    for name in entries:
        directory = os.path.join(base, name)
        if not os.path.isdir(directory):
            continue
        json_path = os.path.join(directory, f"{name}.json")
        if not (os.path.isfile(json_path) and os.path.getsize(json_path) > 0):
            continue
        # 两种 jar 命名都识别：外部标准版本（<id>.jar）不再因找不到 client.jar 被漏判。
        if find_client_jar(name) is None:
            continue
        meta = read_install_meta(name)
        json_id = _read_version_json_id(json_path)
        # 无 meta 时优先按本地 JSON 解析底座（加载器 profile 取 inheritsFrom、普通版取
        # id），避免把 fabric-loader-... 这类 loader id 误当成真实 MC 版本；再退回原始
        # JSON id / 目录名兜底。
        mc_version = str(
            meta.get("mc_version")
            or local_version_base(name)
            or json_id
            or name)
        loader = str(meta.get("loader") or C.LOADER_VANILLA)
        loader_version = str(meta.get("loader_version") or "")
        result.append({
            "alias": name,
            "mc_version": mc_version,
            "loader": loader,
            "loader_version": loader_version,
        })

    result.sort(key=lambda item: item["alias"])
    return result


def scan_installed_versions() -> list[str]:
    """扫描已安装版本别名列表（保持 v1.2.11.0 旧接口：返回别名字符串列表，升序）。"""
    return [entry["alias"] for entry in scan_installed_entries()]


def cleanup_partial(alias: str) -> None:
    """取消下载后清理隔离目录内全部 ``.part`` 半成品分片；目录本体保留（存档 / 配置不删）。

    任何删除异常静默忽略，不阻塞取消流程。
    """
    target = version_dir(alias)
    if not os.path.isdir(target):
        return
    try:
        for root, _dirs, files in os.walk(target):
            for filename in files:
                if filename.endswith(".part"):
                    try:
                        os.remove(os.path.join(root, filename))
                    except OSError:
                        continue
    except OSError:
        return


def remove_version_dir(alias: str) -> None:
    """整目录移除（仅用于取消后半成品版本；存档 / 配置随目录一并删除，调用方需确认语义）。"""
    import shutil

    target = version_dir(alias)
    if not os.path.isdir(target):
        return
    try:
        shutil.rmtree(target, ignore_errors=True)
    except OSError:
        return


# --------------------------------------------------------------------------- #
# 版本改名 / 元数据字段更新 / 自定义头像
# --------------------------------------------------------------------------- #
def update_install_meta(target_alias: str, **fields) -> bool:
    """把字段合并写入已有的安装元数据（保留其余字段），成功返回 True。

    第一参数命名为 ``target_alias`` 而非 ``alias``，以便调用方通过 ``alias=...`` 关键字
    安全更新元数据内部的 alias 字段（两者同名会触发参数冲突 TypeError）。
    """
    if not fields:
        return True
    meta = read_install_meta(target_alias)
    if not meta:
        return False
    meta.update(fields)
    path = install_meta_path(target_alias)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError:
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def custom_avatar_path(alias: str) -> str:
    """自定义头像在隔离目录内的固定路径。"""
    return os.path.join(version_dir(alias), "custom_avatar.png")


def rename_version(old_alias: str, new_alias: str) -> tuple[bool, str]:
    """把版本目录整体改名（含版本 JSON 文件名），并同步安装元数据 alias 字段。

    成功返回 ``(True, "")``；目标撞名 / 名字非法返回 ``(False, 中文原因)``，绝不静默改名、
    绝不覆盖已有目录。存档、配置等目录内文件随目录一起移动。
    """
    old = str(old_alias or "").strip()
    new_raw = str(new_alias or "").strip()
    if not old:
        return False, "原版本不存在"
    if not new_raw:
        return False, "版本名不能为空"
    new = sanitize_version_id(new_raw)
    if not new:
        return False, "版本名不合法"
    if new == old:
        return True, ""
    old_dir = version_dir(old)
    if not os.path.isdir(old_dir):
        return False, "原版本目录不存在"
    new_dir = version_dir(new)
    if os.path.exists(new_dir):
        # 撞名必须用户自己改名，不追加 -2 也不覆盖。
        return False, "名字「%s」已经被占用，请换一个" % new
    try:
        os.rename(old_dir, new_dir)
    except OSError as exc:
        return False, "改名失败：%s" % exc
    # 版本 JSON 文件名跟随新别名。
    old_json = os.path.join(new_dir, C.VERSION_JSON_FILENAME.format(id=sanitize_version_id(old)))
    new_json = os.path.join(new_dir, C.VERSION_JSON_FILENAME.format(id=new))
    if os.path.isfile(old_json) and not os.path.exists(new_json):
        try:
            os.rename(old_json, new_json)
        except OSError:
            pass
    # 同步 install_meta 的 alias（该文件内部仍记录新名字）。
    update_install_meta(new, alias=new)
    return True, ""
