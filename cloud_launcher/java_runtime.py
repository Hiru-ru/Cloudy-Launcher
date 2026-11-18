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

"""本机 Java 探测、JVM 启动命令组装与游戏进程拉起。

v1.2.12.0 新增。纯 Python 标准库 ``subprocess`` + ``os`` + ``winreg``（仅 Windows 注册表
只读探测），不引入第三方启动器库。

边界如实说明：

- 探测顺序：PATH 上的 ``java`` → 注册表 JDK 安装记录 → 常见安装目录通配扫描；任一命中即返回。
- 命令组装按合并后版本 profile 的 ``arguments.jvm`` / ``arguments.game``（现代版本）或
  ``minecraftArguments``（老版本）模板替换官方占位变量，拼接 ``-cp`` classpath 与 mainClass。
- 本机未安装 Java 时不伪造启动：返回明确错误码与缺失引导提示，由个人页弹窗告知用户安装。
- Forge / NeoForge 安装器内置的二进制补丁合并（installer processors）需要 Java 执行；本模块
  只负责拉起已下载到位的版本 profile，不代执行安装器处理器。
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import uuid
import winreg

from . import constants as C
from . import game_dirs
from . import version_profile


# --------------------------------------------------------------------------- #
# Java 探测
# --------------------------------------------------------------------------- #
_JAVA_VERSION_PATTERN = re.compile(r'version\s+"?([0-9][0-9A-Za-z._+-]*)"?')


def _parse_java_version(text: str) -> str:
    """从 ``java -version`` 输出中提取版本号；解析失败返回空串。

    v1.3.1.8：旧实现只认以 ``version`` 开头的行，OpenJDK / Adoptium 实际首行是
    ``openjdk version "25.0.4" ...``，永远匹配不到，导致版本号恒为空、Java 主版本
    校验形同虚设。改为在整段输出里找 ``version "x.y.z"`` 片段，兼容 ``java version``、
    ``openjdk version`` 与不带引号的写法。
    """
    match = _JAVA_VERSION_PATTERN.search(text)
    return match.group(1) if match else ""


def _probe_java_executable(executable: str) -> dict | None:
    """用给定可执行路径跑 ``-version``，成功返回 ``{path, version, source}``，失败 ``None``。"""
    try:
        proc = subprocess.run(
            [executable, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = proc.stdout.decode("utf-8", errors="replace")
        if proc.returncode == 0 or "version" in output.lower():
            return {"path": executable, "version": _parse_java_version(output), "source": "probe"}
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return None
    return None


_HIVE_ALIASES = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
}


def _registry_java_paths() -> list[str]:
    """只读扫描注册表 JDK 安装记录，返回全部 ``java.exe`` 路径；无权限 / 缺失返回空表。"""
    found: list[str] = []
    for root in C.JAVA_REGISTRY_ROOTS:
        try:
            hive_key, sub = root.split("\\", 1)
            hive = _HIVE_ALIASES.get(hive_key)
            if hive is None:
                continue
            with winreg.OpenKey(hive, sub) as version_key:
                index = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(version_key, index)
                    except OSError:
                        break
                    index += 1
                    with winreg.OpenKey(version_key, sub_name) as detail:
                        try:
                            install_dir, _ = winreg.QueryValueEx(detail, "JavaHome")
                        except OSError:
                            continue
                        candidate = os.path.join(str(install_dir), "bin", "java.exe")
                        if os.path.isfile(candidate) and candidate not in found:
                            found.append(candidate)
        except (OSError, AttributeError, ValueError, PermissionError):
            continue
    return found


def _common_dir_java_paths() -> list[str]:
    """扫描常见 JDK 安装目录，返回全部可用 ``java.exe`` 路径；未找到返回空表。"""
    found: list[str] = []
    for base in C.JAVA_SEARCH_DIRS:
        if not os.path.isdir(base):
            continue
        try:
            for entry in sorted(os.listdir(base)):
                candidate = os.path.join(base, entry, "bin", "java.exe")
                if os.path.isfile(candidate) and candidate not in found:
                    found.append(candidate)
        except OSError:
            continue
    return found


def list_java() -> list[dict]:
    """列出本机全部可用 Java（PATH → 注册表 → 常见目录），按路径去重。

    每项 ``{"path", "version", "source"}``；无可用 Java 时返回空表。供设置页
    「Java 列表」下拉展示与手动选择，未探测到的异常静默兜底为空表。
    """
    candidates: list[dict] = []

    path_probe = _probe_java_executable(C.JAVA_EXECUTABLE_NAME)
    if path_probe:
        path_probe["source"] = "PATH"
        candidates.append(path_probe)

    for candidate in _registry_java_paths():
        probe = _probe_java_executable(candidate)
        if probe:
            probe["source"] = "registry"
            candidates.append(probe)

    for candidate in _common_dir_java_paths():
        probe = _probe_java_executable(candidate)
        if probe:
            probe["source"] = "directory"
            candidates.append(probe)

    seen: set[str] = set()
    result: list[dict] = []
    for item in candidates:
        key = str(item.get("path", "")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def detect_java() -> dict:
    """探测本机可用 Java；返回 ``{"ok", "path", "version", "source"}``，未安装时 ``ok=False``。

    任何探测异常都静默兜底为未安装，不弹窗、不抛到界面线程。
    """
    detected = list_java()
    if detected:
        first = detected[0]
        return {"ok": True, "path": first["path"], "version": first["version"], "source": first["source"]}
    return {"ok": False, "path": "", "version": "", "source": "none"}


# --------------------------------------------------------------------------- #
# 离线 UUID（与 Minecraft 离线账号 UUID 口径一致：MD5("OfflinePlayer:" + 昵称)）
# --------------------------------------------------------------------------- #
def offline_uuid(name: str) -> str:
    """离线（盗版）账号 UUID，等价于 Java ``UUID.nameUUIDFromBytes`` 对
    ``"OfflinePlayer:" + 昵称`` 的 MD5 结果：直接在 16 字节摘要上置 version 3 与 IETF variant。"""
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(digest)))


# --------------------------------------------------------------------------- #
# 占位变量替换与命令组装
# --------------------------------------------------------------------------- #
# 正常启动时所有可选 feature 均关闭：不启用 demo、不自定义分辨率、不使用 quick play。
_ENABLED_FEATURES = {
    "is_demo_user": False,
    "has_custom_resolution": False,
    "has_quick_plays_support": False,
    "is_quick_play_singleplayer": False,
    "is_quick_play_multiplayer": False,
    "is_quick_play_realms": False,
}

# v1.3.16.0：GC 策略 → JVM 参数；``default`` 不追加任何 GC 旗标，跟随 Java 默认。
_GC_FLAGS = {
    C.GC_G1: ["-XX:+UseG1GC"],
    C.GC_SERIAL: ["-XX:+UseSerialGC"],
    C.GC_CMS: ["-XX:+UseConcMarkSweepGC"],
    C.GC_DEFAULT: [],
}


def _split_args(text: str) -> list[str]:
    """把用户手写的参数字符串按空白拆成参数表；空串返回空表。

    口径：本轮按空白分词，参数值内若带空格需用引号包裹；含引号的进阶解析留待后续版本。
    """
    return [token for token in str(text or "").split() if token]


def _memory_args(config) -> list[str]:
    """按内存模式生成 ``-Xmx`` / ``-Xms``：自动用默认值，自定义用配置上限（初始化为一半）。"""
    if getattr(config, "memory_mode", "auto") == "custom":
        mx = getattr(config, "custom_memory_mb", C.DEFAULT_JVM_XMX_MB)
        try:
            mx = max(512, int(mx))
        except (TypeError, ValueError):
            mx = C.DEFAULT_JVM_XMX_MB
        ms = max(256, mx // 2)
        return [f"-Xmx{mx}M", f"-Xms{ms}M"]
    return [f"-Xmx{C.DEFAULT_JVM_XMX_MB}M", f"-Xms{C.DEFAULT_JVM_XMS_MB}M"]


def resolve_game_dir(alias: str, config) -> str:
    """按版本隔离策略解析游戏工作目录。

    本轮仅落地「关闭隔离 → 全局共享 ``.minecraft``」与其余策略「按版本独立目录」；
    按版本类型（可装 Mod / 非正式版）细分隔离目录的规则在后续版本接入。
    """
    if getattr(config, "isolation_mode", C.ISOLATION_ALL) == C.ISOLATION_OFF:
        return game_dirs.minecraft_root()
    return game_dirs.version_dir(alias)


def resolve_java(manual_path: str = "") -> dict:
    """优先使用设置页手动指定的 Java 路径；路径无效或为空时回退自动探测。"""
    manual = str(manual_path or "").strip()
    if manual and os.path.isfile(manual):
        probe = _probe_java_executable(manual)
        if probe:
            probe["source"] = "manual"
            probe["ok"] = True
            return probe
    return detect_java()


def _os_matches(os_block: dict) -> bool:
    """判断规则的 os 条件是否命中当前 Windows 64 位系统。"""
    name = os_block.get("name")
    if name and name != "windows":
        return False
    arch = str(os_block.get("arch") or "").lower()
    if arch:
        # 规则里 x86 表示 32 位；当前为 64 位，x86-only 规则不命中。
        if arch == "x86":
            return False
        if arch not in ("x86_64", "amd64", "x64"):
            return False
    return True


def _features_matches(rule: dict) -> bool:
    """判断规则的 features 条件是否满足；正常启动这些 feature 全部为关闭。"""
    features = rule.get("features")
    if not features:
        return True
    return all(
        bool(_ENABLED_FEATURES.get(key, False)) == bool(required)
        for key, required in features.items()
    )


def _rule_allows(block: dict) -> bool:
    """按官方启动器语义评估参数块规则：顺序处理 allow/disallow，同时校验 os 与 features。

    每条规则先判断是否适用于当前系统（os 命中、features 满足），适用时 allow 置 True、
    disallow 置 False，不适用则不改变结论。
    """
    rules = block.get("rules")
    if not rules:
        return True
    allowed = False
    for rule in rules:
        if not _os_matches(rule.get("os") or {}):
            continue
        if not _features_matches(rule):
            continue
        if str(rule.get("action") or "allow") == "disallow":
            allowed = False
        else:
            allowed = True
    return allowed


def _build_variables(profile: dict, alias: str, session, config) -> dict:
    """构造启动占位变量表；离线 / 正版字段分别取会话与配置。"""
    mc_version = str(profile.get("id") or alias)
    is_ms = bool(getattr(session, "is_microsoft", False))
    player_name = getattr(session, "name", "") if is_ms else config.player_name
    player_name = player_name or config.player_name
    player_uuid = getattr(session, "uuid", "") if is_ms else offline_uuid(player_name)
    access_token = getattr(session, "mc_access_token", "") if is_ms else "0"
    assets_root = game_dirs.assets_root()
    asset_index = profile.get("assetIndex") or {}
    assets_index_name = str(asset_index.get("id") or profile.get("assets") or "legacy")
    return {
        "auth_player_name": player_name,
        "version_name": alias,
        "game_directory": resolve_game_dir(alias, config),
        "assets_root": assets_root,
        "assets_index_name": assets_index_name,
        "auth_uuid": player_uuid,
        "auth_access_token": access_token,
        "clientid": "",
        "auth_xuid": "",
        "version_type": str(profile.get("type") or "release"),
        "user_type": "msa" if is_ms else "legacy",
        "resolution_width": "854",
        "resolution_height": "480",
        "natives_directory": game_dirs.find_natives_dir(alias),
        "launcher_name": C.APP_UA_NAME,
        "launcher_version": C.APP_VERSION,
        "classpath_separator": os.pathsep,
        "library_directory": game_dirs.libraries_dir(alias),
        "user_properties": "{}",
        "quickPlayPath": "",
        "quickPlaySingleplayer": "",
        "quickPlayMultiplayer": "",
        "quickPlayRealms": "",
    }


def _substitute(token: str, variables: dict) -> str:
    """替换 ``${variable}`` 占位；未识别变量保留原样，避免误删官方后续新增参数。"""
    for key, value in variables.items():
        token = token.replace(f"${{{key}}}", str(value))
    return token


def _collect_classpath(profile: dict, alias: str) -> list[str]:
    """收集 classpath：profile libraries 本地存在的 jar + 客户端 Jar + 显式本地 loader Jar。

    v1.3.1.8：两个真机致命坑都按外部启动器口径补齐——
    - 依赖库既可能在版本隔离目录 ``versions/<别名>/libraries``（云朵下载），也可能在
      全局 ``.minecraft/libraries``（PCL2 / 官方启动器放入的标准版本），两处都要查；
    - 客户端 Jar 兼容云朵的 ``client.jar`` 与标准 MC 的 ``<别名>.jar`` 两种命名。
    旧实现只认版本目录内 ``client.jar`` 且只查版本内 libraries，外部版本 classpath
    里既没有主 jar 也没有库，JVM 直接报 ClassNotFoundException: net.minecraft.client.main.Main。
    """
    entries: list[str] = []
    for lib in profile.get("libraries") or []:
        if not _rule_allows(lib):
            continue
        explicit = lib.get("_local_jar")
        if explicit and os.path.isfile(str(explicit)):
            entries.append(str(explicit))
            continue
        found = game_dirs.find_library(alias, version_profile.library_relative_path(lib))
        if found:
            entries.append(found)
    client = game_dirs.find_client_jar(alias)
    if client:
        entries.append(client)
    return entries


def build_launch_command(profile: dict, alias: str, session, config,
                         java_path: str) -> list[str]:
    """按合并后 profile 组装完整 JVM + 游戏参数命令行（不含工作目录）。"""
    variables = _build_variables(profile, alias, session, config)
    jvm_args: list[str] = []
    game_args: list[str] = []

    # ---- 现代版本 arguments 分段 ----
    arguments = profile.get("arguments") or {}
    for item in arguments.get("jvm") or []:
        if isinstance(item, dict):
            if not _rule_allows(item):
                continue
            value = item.get("value")
            pieces = [value] if isinstance(value, str) else list(value or [])
        else:
            pieces = [item]
        for piece in pieces:
            jvm_args.append(_substitute(str(piece), variables))

    for item in arguments.get("game") or []:
        if isinstance(item, dict):
            if not _rule_allows(item):
                continue
            value = item.get("value")
            pieces = [value] if isinstance(value, str) else list(value or [])
        else:
            pieces = [item]
        for piece in pieces:
            game_args.append(_substitute(str(piece), variables))

    # ---- 老版本 minecraftArguments 模板字符串 ----
    legacy_template = str(profile.get("minecraftArguments") or "").strip()
    if legacy_template and not game_args:
        for token in legacy_template.split():
            game_args.append(_substitute(token, variables))

    classpath = _collect_classpath(profile, alias)
    # classpath 占位（部分 loader profile 的 jvm 参数里写了 ${classpath}）。
    classpath_value = os.pathsep.join(classpath)
    variables["classpath"] = classpath_value
    jvm_args = [_substitute(arg, variables) for arg in jvm_args]

    main_class = str(profile.get("mainClass") or "net.minecraft.client.main.Main")

    # ---- v1.3.16.0：内存 / GC / 用户自定义参数 ----
    # 先剔除 profile 自带的 -Xmx/-Xms，再按配置注入内存，避免重复开关。
    jvm_args = [arg for arg in jvm_args if not arg.startswith("-Xmx") and not arg.startswith("-Xms")]
    jvm_args = _memory_args(config) + jvm_args
    jvm_args.extend(_GC_FLAGS.get(getattr(config, "gc_mode", C.GC_DEFAULT_KEY), []))
    jvm_args.extend(_split_args(getattr(config, "jvm_args", "")))
    game_args.extend(_split_args(getattr(config, "game_args", "")))

    command: list[str] = [java_path]
    command.extend(jvm_args)
    # 现代官方版本 JSON 的 jvm 参数里已经自带 `-cp ${classpath}`，此处只补主类；
    # 只有 profile 没自带 -cp 时才补完整 `-cp <classpath> <主类>`，避免命令行出现两段 -cp。
    has_classpath_option = any(
        arg == "-cp" or arg == "-classpath" or arg.startswith("-cp")
        for arg in jvm_args
    )
    if has_classpath_option:
        command.append(main_class)
    else:
        command.extend(["-cp", classpath_value, main_class])
    command.extend(game_args)
    return command


def required_java_major(profile: dict) -> int:
    """版本 profile 声明的 Java 主版本要求（``javaVersion.majorVersion``）；未声明返回 0。"""
    block = profile.get("javaVersion") or {}
    try:
        return int(block.get("majorVersion") or 0)
    except (TypeError, ValueError):
        return 0


def java_major_version(version_text: str) -> int:
    """把 ``java -version`` 的版本串换算成主版本号。

    兼容两种写法：``1.8.0_202`` → 8，``25.0.4`` / ``21`` → 对应数字；无法识别返回 0。
    """
    text = str(version_text or "").strip().strip('"').strip()
    if not text:
        return 0
    parts = text.replace("_", ".").replace("-", ".").split(".")
    try:
        first = int(parts[0])
    except (TypeError, ValueError):
        return 0
    if first == 1 and len(parts) > 1:
        try:
            return int(parts[1])
        except (TypeError, ValueError):
            return 0
    return first
