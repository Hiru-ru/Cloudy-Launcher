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

"""版本内容扫描：mod / 光影包 / 材质包 / 数据包的真实条目读取与图标提取。

v1.3.12.0 新增。版本设置页「版本详细信息」四个计数与展开列表（见第二张参考图）的数据来源。
纯标准库（``os`` / ``zipfile`` / ``json`` / ``tomllib``），不引入第三方依赖；单个文件损坏
不影响整批扫描，读不到图标的条目 ``icon`` 为 ``None``，由界面显示问号。

扫描口径（版本隔离目录 ``.minecraft/versions/<别名>/`` 下）：

- mod：``mods/*.jar``（含 ``.jar.disabled`` 停用态），尽量读 Fabric ``fabric.mod.json``、
  Forge/NeoForge ``META-INF/mods.toml``、旧版 ``mcmod.info`` 取名称 / 版本 / 图标；
- 光影包：``shaderpacks/*.zip``，无标准图标；
- 材质包：``resourcepacks/*.zip``（也支持文件夹），读根目录 ``pack.png`` 与 ``pack.mcmeta``；
- 数据包：启动器内容目录 ``datapacks/`` 以及各世界 ``saves/<世界>/datapacks/``，读
  ``pack.mcmeta`` 描述。
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 运行环境为 3.13，仅兜底
    tomllib = None

from . import game_dirs

#: 内容分类键。
KIND_MOD = "mod"
KIND_SHADER = "shader"
KIND_RESOURCE = "resourcepack"
KIND_DATAPACK = "datapack"

#: 分类 → 展开列表标题（对齐第二张图左上角“mod版本详细信息”）。
KIND_TITLES = {
    KIND_MOD: "mod版本详细信息",
    KIND_SHADER: "光影包版本详细信息",
    KIND_RESOURCE: "材质包版本详细信息",
    KIND_DATAPACK: "数据包版本详细信息",
}

#: 分类 → 概览计数按钮文案。
KIND_COUNT_LABELS = {
    KIND_MOD: "mod",
    KIND_SHADER: "光影包",
    KIND_RESOURCE: "材质包",
    KIND_DATAPACK: "数据包",
}


# --------------------------------------------------------------------------- #
# 通用辅助
# --------------------------------------------------------------------------- #
def _flatten_chat(value) -> str:
    """把 Minecraft 文本组件（str / dict / list）压成纯文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "".join(_flatten_chat(item) for item in value)
    if isinstance(value, dict):
        text = str(value.get("text") or "")
        extra = value.get("extra")
        if extra:
            text += _flatten_chat(extra)
        return text
    return ""


def _strip_disabled(name: str) -> tuple[str, bool]:
    """去掉 ``.disabled`` 停用后缀，返回 (剩余文件名, 是否停用)。"""
    if name.endswith(".disabled"):
        return name[: -len(".disabled")], True
    return name, False


def _read_zip_text(archive: zipfile.ZipFile, member: str) -> str:
    return archive.read(member).decode("utf-8", errors="replace")


def _read_zip_member_quiet(archive: zipfile.ZipFile, member: str) -> bytes | None:
    """读 zip 内指定成员；成员缺失 / 路径异常返回 None。"""
    try:
        if member in archive.namelist():
            return archive.read(member)
    except (OSError, KeyError):
        return None
    return None


def _resolve_icon_path(archive: zipfile.ZipFile, icon_path: str) -> bytes | None:
    """按 jar 内相对路径定位图标，兼容前导 ``/`` 与 ``assets/`` 前缀差异。"""
    raw = str(icon_path or "").strip().lstrip("/")
    if not raw:
        return None
    candidates = [raw]
    if not raw.startswith("assets/"):
        candidates.append("assets/" + raw)
    for candidate in candidates:
        data = _read_zip_member_quiet(archive, candidate)
        if data:
            return data
    return None


def _entry(name: str, detail: str = "", icon: bytes | None = None,
           disabled: bool = False, path: str = "") -> dict:
    return {
        "name": str(name or ""),
        "detail": str(detail or ""),
        "icon": icon,
        "disabled": bool(disabled),
        "path": str(path or ""),
    }


# --------------------------------------------------------------------------- #
# mod 元数据
# --------------------------------------------------------------------------- #
def _mod_from_fabric(archive: zipfile.ZipFile) -> dict | None:
    raw = _read_zip_member_quiet(archive, "fabric.mod.json")
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    # 旧版 fabric.mod.json 可能是模组数组，取第一个。
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return None
    name = _flatten_chat(data.get("name")) or str(data.get("id") or "")
    version = _flatten_chat(data.get("version"))
    icon = None
    icon_field = data.get("icon")
    if isinstance(icon_field, str):
        icon = _resolve_icon_path(archive, icon_field)
    return {"name": name, "detail": version, "icon": icon}


def _mod_from_toml(archive: zipfile.ZipFile, member: str) -> dict | None:
    if tomllib is None:
        return None
    raw = _read_zip_member_quiet(archive, member)
    if raw is None:
        return None
    try:
        parsed = tomllib.loads(raw.decode("utf-8", errors="replace"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    mods = parsed.get("mods")
    if not isinstance(mods, list) or not mods:
        return None
    first = mods[0] if isinstance(mods[0], dict) else {}
    name = str(first.get("displayName") or first.get("modId") or "")
    version = str(first.get("version") or "")
    # ${file.jarVersion} 等占位无展示意义，清掉。
    if version.startswith("${"):
        version = ""
    icon = None
    logo = str(first.get("logoFile") or parsed.get("logoFile") or "")
    if logo:
        icon = _resolve_icon_path(archive, logo)
    return {"name": name, "detail": version, "icon": icon}


def _mod_from_mcmod_info(archive: zipfile.ZipFile) -> dict | None:
    raw = _read_zip_member_quiet(archive, "mcmod.info")
    if raw is None:
        return None
    text = raw.decode("utf-8", errors="replace")
    # 部分旧文件带 // 注释，标准 JSON 无法解析，粗暴去掉整行注释。
    cleaned = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        data = data.get("modList") or data.get("mods") or []
    if not isinstance(data, list) or not data:
        return None
    first = data[0] if isinstance(data[0], dict) else {}
    name = str(first.get("name") or "")
    version = str(first.get("version") or "")
    icon = None
    logo = str(first.get("logoFile") or "")
    if logo:
        icon = _resolve_icon_path(archive, logo)
    return {"name": name, "detail": version, "icon": icon}


def _scan_mod_file(path: str, filename: str, disabled: bool) -> dict:
    base = os.path.basename(path)
    fallback = _entry(base[:-4] if base.lower().endswith(".jar") else base,
                      icon=None, disabled=disabled, path=path)
    try:
        with zipfile.ZipFile(path) as archive:
            info = (
                _mod_from_fabric(archive)
                or _mod_from_toml(archive, "META-INF/mods.toml")
                or _mod_from_toml(archive, "META-INF/neoforge.mods.toml")
                or _mod_from_mcmod_info(archive)
            )
    except (OSError, zipfile.BadZipFile):
        return fallback
    if not info or not info.get("name"):
        return fallback
    return _entry(info["name"], info.get("detail", ""), info.get("icon"),
                  disabled=disabled, path=path)


# --------------------------------------------------------------------------- #
# pack.mcmeta / pack.png（材质包、数据包）
# --------------------------------------------------------------------------- #
def _read_pack_meta_bytes(raw: bytes) -> str:
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ""
    pack = data.get("pack") if isinstance(data, dict) else None
    if not isinstance(pack, dict):
        return ""
    return _flatten_chat(pack.get("description")).strip()


def _scan_pack_zip(path: str, disabled: bool, want_icon: bool) -> dict:
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    description = ""
    icon = None
    try:
        with zipfile.ZipFile(path) as archive:
            meta_raw = _read_zip_member_quiet(archive, "pack.mcmeta")
            if meta_raw:
                description = _read_pack_meta_bytes(meta_raw)
            if want_icon:
                icon = _read_zip_member_quiet(archive, "pack.png")
    except (OSError, zipfile.BadZipFile):
        pass
    return _entry(name, description, icon if want_icon else None,
                  disabled=disabled, path=path)


def _scan_pack_folder(path: str, want_icon: bool) -> dict:
    name = os.path.basename(path)
    description = ""
    icon = None
    meta_path = os.path.join(path, "pack.mcmeta")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "rb") as handle:
                description = _read_pack_meta_bytes(handle.read())
        except OSError:
            pass
    if want_icon:
        icon_path = os.path.join(path, "pack.png")
        if os.path.isfile(icon_path):
            try:
                with open(icon_path, "rb") as handle:
                    icon = handle.read()
            except OSError:
                icon = None
    return _entry(name, description, icon, path=path)


# --------------------------------------------------------------------------- #
# 目录收集
# --------------------------------------------------------------------------- #
def _iter_pack_files(folder: str, extensions: tuple[str, ...]):
    """生成 (绝对路径, 文件名, 是否停用)；目录不存在时为空。"""
    if not os.path.isdir(folder):
        return
    for filename in sorted(os.listdir(folder)):
        full = os.path.join(folder, filename)
        if os.path.isfile(full):
            base, disabled = _strip_disabled(filename)
            if base.lower().endswith(extensions):
                yield full, base, disabled
        elif os.path.isdir(full) and not filename.startswith("."):
            # 文件夹形态的包（材质包/数据包）。
            yield full, filename, False


def _scan_mods(version_dir: str, should_cancel) -> list[dict]:
    entries: list[dict] = []
    folder = os.path.join(version_dir, "mods")
    if os.path.isdir(folder):
        for filename in sorted(os.listdir(folder)):
            if callable(should_cancel) and should_cancel():
                break
            base, disabled = _strip_disabled(filename)
            if not base.lower().endswith(".jar"):
                continue
            entries.append(_scan_mod_file(os.path.join(folder, filename),
                                          base, disabled))
    return entries


def _scan_simple_packs(version_dir: str, subfolder: str,
                       extensions: tuple[str, ...], want_icon: bool,
                       should_cancel) -> list[dict]:
    entries: list[dict] = []
    folder = os.path.join(version_dir, subfolder)
    for full, _name, disabled in _iter_pack_files(folder, extensions):
        if callable(should_cancel) and should_cancel():
            break
        if os.path.isdir(full):
            entries.append(_scan_pack_folder(full, want_icon))
        else:
            entries.append(_scan_pack_zip(full, disabled, want_icon))
    return entries


def _scan_datapacks(version_dir: str, should_cancel) -> list[dict]:
    entries: list[dict] = []
    # 1) 启动器内容下载目录 datapacks/。
    data_folder = os.path.join(version_dir, "datapacks")
    for full, _name, disabled in _iter_pack_files(
            data_folder, (".zip",)):
        if callable(should_cancel) and should_cancel():
            break
        if os.path.isdir(full):
            entries.append(_scan_pack_folder(full, False))
        else:
            entries.append(_scan_pack_zip(full, disabled, False))
    # 2) 各世界 saves/<世界>/datapacks/，详情里标注所属世界。
    saves = os.path.join(version_dir, "saves")
    if os.path.isdir(saves):
        for world in sorted(os.listdir(saves)):
            world_dir = os.path.join(saves, world)
            if not os.path.isdir(world_dir):
                continue
            dp_dir = os.path.join(world_dir, "datapacks")
            for full, _name, disabled in _iter_pack_files(dp_dir, (".zip",)):
                if callable(should_cancel) and should_cancel():
                    break
                if os.path.isdir(full):
                    item = _scan_pack_folder(full, False)
                else:
                    item = _scan_pack_zip(full, disabled, False)
                item["detail"] = "世界：%s" % world
                entries.append(item)
    return entries


# --------------------------------------------------------------------------- #
# 对外接口
# --------------------------------------------------------------------------- #
def count_content(alias: str) -> dict[str, int]:
    """轻量计数（不读 jar 元数据），返回各分类条目数，供概览四个计数按钮。"""
    version_dir = game_dirs.version_dir(alias)
    counts = {
        KIND_MOD: 0,
        KIND_SHADER: 0,
        KIND_RESOURCE: 0,
        KIND_DATAPACK: 0,
    }

    def _count_files(subfolder: str, extensions: tuple[str, ...]) -> int:
        folder = os.path.join(version_dir, subfolder)
        total = 0
        if not os.path.isdir(folder):
            return 0
        for filename in os.listdir(folder):
            base, _disabled = _strip_disabled(filename)
            full = os.path.join(folder, filename)
            if os.path.isfile(full) and base.lower().endswith(extensions):
                total += 1
            elif os.path.isdir(full):
                total += 1
        return total

    counts[KIND_MOD] = _count_files("mods", (".jar",))
    counts[KIND_SHADER] = _count_files("shaderpacks", (".zip",))
    counts[KIND_RESOURCE] = _count_files("resourcepacks", (".zip",))
    counts[KIND_DATAPACK] = _count_files("datapacks", (".zip",))
    # 世界内数据包额外计入。
    saves = os.path.join(version_dir, "saves")
    if os.path.isdir(saves):
        for world in os.listdir(saves):
            world_dir = os.path.join(saves, world)
            if os.path.isdir(world_dir):
                counts[KIND_DATAPACK] += _count_files(
                    os.path.join("saves", world, "datapacks"), (".zip",))
    return counts


def scan_content(alias: str, kind: str, should_cancel=None) -> list[dict]:
    """扫描某分类的全部条目，返回 entry 列表（含图标字节，无图标为 None）。"""
    version_dir = game_dirs.version_dir(alias)
    if kind == KIND_MOD:
        return _scan_mods(version_dir, should_cancel)
    if kind == KIND_SHADER:
        return _scan_simple_packs(version_dir, "shaderpacks",
                                  (".zip",), False, should_cancel)
    if kind == KIND_RESOURCE:
        return _scan_simple_packs(version_dir, "resourcepacks",
                                  (".zip",), True, should_cancel)
    if kind == KIND_DATAPACK:
        return _scan_datapacks(version_dir, should_cancel)
    raise ValueError("未知内容分类：%s" % kind)


# --------------------------------------------------------------------------- #
# 启用 / 禁用 / 删除（内容列表弹窗操作）
# --------------------------------------------------------------------------- #
_DISABLED_SUFFIX = ".disabled"


def _inside_versions(path: str) -> bool:
    """校验路径确实位于 versions 目录内，防止界面传入越界路径。"""
    root = os.path.normpath(game_dirs.versions_dir())
    norm = os.path.normpath(path)
    return norm == root or norm.startswith(root + os.sep)


def toggle_content(path: str, enable: bool) -> tuple[bool, str]:
    """启用/禁用一个内容条目（文件或文件夹加/去 ``.disabled`` 后缀）。

    返回 ``(是否成功, 中文原因)``；目标名已存在时不覆盖。
    """
    path = os.path.normpath(str(path or ""))
    if not path or not os.path.exists(path):
        return False, "内容不存在或已被移除"
    if not _inside_versions(path):
        return False, "路径不在版本目录内，已阻止"
    if enable:
        if not path.endswith(_DISABLED_SUFFIX):
            return True, ""
        target = path[: -len(_DISABLED_SUFFIX)]
    else:
        if path.endswith(_DISABLED_SUFFIX):
            return True, ""
        target = path + _DISABLED_SUFFIX
    if os.path.exists(target):
        return False, "目标名称已存在，无法切换"
    try:
        os.rename(path, target)
    except OSError as exc:
        return False, "切换失败：%s" % exc
    return True, ""


def delete_content(path: str) -> tuple[bool, str]:
    """删除一个内容条目（文件删除、文件夹整目录删除），返回 ``(是否成功, 中文原因)``。"""
    path = os.path.normpath(str(path or ""))
    if not path or not os.path.exists(path):
        return False, "内容不存在或已被移除"
    if not _inside_versions(path):
        return False, "路径不在版本目录内，已阻止"
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except OSError as exc:
        return False, "删除失败：%s" % exc
    return True, ""
