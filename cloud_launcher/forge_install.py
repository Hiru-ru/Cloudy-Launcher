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

"""Forge 无头客户端安装：用本机 Java 运行安装器处理器（processors），本地生成补丁化客户端 Jar。

背景：现代 Forge（1.20.2 起，securemodules / 模块化）的版本 JSON 里，
``net.minecraftforge:forge:<mc>-<ver>:client`` 这个库的 ``downloads.artifact.url`` 为空，
官方与 BMCL maven 对该 ``-client.jar`` 都返回 404。它不是一个发布工件，而是 Forge 安装器
在安装时由处理器链本地生成的产物：

1. ``DOWNLOAD_MOJMAPS``（installertools）：下载 Mojang 官方映射并转成 TSRG；
2. ``ForgeAutoRenamingTool``：用 TSRG 映射把混淆的官方 client.jar 重命名为官方名（MC_OFF）；
3. ``binarypatcher``：用 ``data/client.lzma`` 二进制补丁对 MC_OFF 打补丁，产出最终 client Jar。

本模块纯 Python 编排，只负责：下载 installer 与处理器 maven 库、解析 install_profile、
解压补丁数据、替换处理器参数里的占位变量，然后用本机 ``java`` 执行各处理器主类（主类名从
处理器 Jar 的 manifest 读取），并按处理器 ``outputs`` 声明的 sha1 校验产物。字节码重命名 /
二进制补丁全部由 Forge 官方工具完成，本模块不重实现这些算法。

只运行适用于 client 侧的处理器（``sides`` 含 ``client`` 或未声明 sides），server 专属处理器
跳过。所有下载走 BMCL maven 主源、官方 maven 兜底，复用 :mod:`download_engine` 的断点续传 /
重试 / sha1 校验。
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import time
import urllib.error
import zipfile

from . import constants as C
from . import download_engine as engine
from . import game_dirs
from .download_engine import DownloadTask, ProgressTracker, download_one


def installer_local_path(alias: str, mc: str, forge_version: str) -> str:
    """Forge installer 在本版本 ``forge_work`` 内的固定落盘路径。

    :func:`loaders.build_forge_profile` 在第 1 步构建 profile 时已把同一个 installer
    下载到该路径；第 5 步据此直接复用，不再重复下载数 MB 的安装包。
    两处命名必须保持一致（``forge-{mc}-{ver}-installer.jar``）。
    """
    return os.path.join(
        game_dirs.version_dir(alias), "forge_work",
        f"forge-{mc}-{forge_version}-installer.jar",
    )


def count_client_processors(alias: str, mc: str, forge_version: str) -> int | None:
    """读已落盘 installer 的 install_profile，返回 client 侧处理器数量；不可用返回 None。"""
    path = installer_local_path(alias, mc, forge_version)
    if not (os.path.isfile(path) and os.path.getsize(path) > 0):
        return None
    try:
        with zipfile.ZipFile(path) as zf:
            profile = json.loads(zf.read("install_profile.json").decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return None
    return sum(1 for p in profile.get("processors") or []
               if _processor_applies_to_client(p))


# --------------------------------------------------------------------------- #
# Maven 坐标（处理器数据里的 [group:artifact:version[:classifier][@ext]] 形式）
# --------------------------------------------------------------------------- #
def _parse_bracket_coord(token: str) -> tuple[str, str, str, str, str]:
    """解析 ``net.minecraft:client:1.21.1:mappings@tsrg`` 为各段；扩展名默认 ``jar``。"""
    extension = "jar"
    body = token
    if "@" in body:
        body, extension = body.split("@", 1)
    parts = body.split(":")
    group = parts[0] if len(parts) >= 1 else ""
    artifact = parts[1] if len(parts) >= 2 else ""
    version = parts[2] if len(parts) >= 3 else ""
    classifier = parts[3] if len(parts) >= 4 else ""
    return group, artifact, version, classifier, extension


def _coord_rel_path(group: str, artifact: str, version: str,
                    classifier: str, extension: str) -> str:
    """坐标 → 仓库相对路径 ``group/path/artifact-version[-classifier].ext``。"""
    group_path = group.replace(".", "/")
    suffix = f"-{classifier}" if classifier else ""
    filename = f"{artifact}-{version}{suffix}.{extension}"
    if version:
        return f"{group_path}/{artifact}/{version}/{filename}"
    return f"{group_path}/{artifact}/{filename}"


def _official_maven_url(rel_path: str, group: str) -> str:
    """按 group 选官方 maven 兜底地址；BMCL 主源失败时使用。"""
    if group == "net.minecraft":
        return "https://libraries.minecraft.net/" + rel_path
    if group == "net.minecraftforge":
        return "https://maven.minecraftforge.net/" + rel_path
    return "https://repo1.maven.org/maven2/" + rel_path


_BRACKET_PATTERN = re.compile(r"\[([^\[\]]+)\]")


def _add_external_coord(coord: str, needed: set) -> None:
    """把 data/args 里的一个括号 maven 坐标按规则加入外部下载集合。

    带 classifier 的坐标是处理器链中间/输出产物（mcp_config 内 mappings、client 的
    slim/extra/srg、Forge :client 等，maven 仓库不存在），由对应处理器生成；vanilla
    client 由原版步骤提供在版本目录。两者都不下载，其余无 classifier 坐标（如
    mcp_config zip）才加入。
    """
    coord = str(coord or "").strip()
    if not coord:
        return
    group, artifact, _v, classifier, _e = _parse_bracket_coord(coord)
    if classifier:
        return
    if group == "net.minecraft" and artifact == "client":
        return
    needed.add(coord)


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def is_processor_generated(lib: dict) -> bool:
    """判定某库是否为处理器本地生成、无下载 URL（如 Forge 的 ``:client`` 工件）。

    有顶层 maven ``url``、artifact ``url`` 或 ``_local_jar``（OptiFine 已落盘标记）都不算；
    剩下有坐标但无任何可下载地址的，即为处理器生成，需走处理器链而非普通下载。
    """
    if lib.get("_local_jar"):
        return False
    if str(lib.get("url") or "").strip():
        return False
    artifact = (lib.get("downloads") or {}).get("artifact") or {}
    if str(artifact.get("url") or "").strip():
        return False
    return bool(str(lib.get("name") or "").strip())


def run_forge_install(mc: str, forge_version: str, alias: str, java_path: str,
                      should_cancel=None, tracker: ProgressTracker | None = None,
                      log=print) -> str:
    """执行 Forge 客户端处理器链，返回生成的 client Jar 本地绝对路径。

    任一处理器非零退出、输出 sha1 不匹配或被取消都抛异常；成功返回 PATCHED client Jar 路径。
    """
    mc = str(mc or "").strip()
    forge_version = str(forge_version or "").strip()
    libraries_root = game_dirs.libraries_dir(alias)
    work_dir = os.path.join(game_dirs.version_dir(alias), "forge_work")
    os.makedirs(work_dir, exist_ok=True)
    if tracker is None:
        tracker = ProgressTracker()

    # ---- 1. 下载 installer 并落盘（处理器 {INSTALLER} 引用此文件）----
    installer_path = installer_local_path(alias, mc, forge_version)
    installer_name = os.path.basename(installer_path)
    primary = C.FORGE_INSTALLER_URL.format(mc=mc, ver=forge_version)
    mirror = (
        "https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/"
        f"{mc}-{forge_version}/{installer_name}"
    )
    if not _installer_usable(installer_path):
        log(f"[forge] 下载 installer {forge_version}")
        task = DownloadTask(
            url=primary,
            local_path=installer_path,
            mirror_url=mirror,
            label=installer_name,
        )
        ok, reason = download_one(task, tracker, should_cancel)
        if not ok:
            raise RuntimeError(f"Forge 安装包下载失败 {installer_name}: {reason}")
        # download_one 成功时已调用 tracker.record_file_done()，此处不再重复记账。
    else:
        log(f"[forge] 复用已下载的 installer {installer_name}")
        tracker.record_file_done()
    with zipfile.ZipFile(installer_path) as installer_zip:
        install_profile = json.loads(
            installer_zip.read("install_profile.json").decode("utf-8")
        )
        installer_entries = set(installer_zip.namelist())

    # ---- 2. 解析 client 侧要跑的处理器，并收集所需 maven 坐标 ----
    processors = [
        p for p in install_profile.get("processors") or []
        if _processor_applies_to_client(p)
    ]
    needed_coords: set[str] = set()
    for proc in processors:
        needed_coords.add(str(proc.get("jar") or ""))
        for cp in proc.get("classpath") or []:
            needed_coords.add(str(cp))
        # 处理器 args 里的括号坐标是真实输入工件（如 MCP_DATA --input 的 mcp_config
        # zip），不在 jar/classpath/data 中；不收集下载就会报 Input does not exist。
        for arg in proc.get("args") or []:
            for match in _BRACKET_PATTERN.finditer(str(arg)):
                _add_external_coord(match.group(1), needed_coords)
    # data 段以括号 maven 坐标引用的工件同样按规则收集（带 classifier 的产物跳过）。
    for data_entry in (install_profile.get("data") or {}).values():
        raw = str((data_entry or {}).get("client") or "").strip()
        for match in _BRACKET_PATTERN.finditer(raw):
            _add_external_coord(match.group(1), needed_coords)
    needed_coords.discard("")
    log(f"[forge] client 处理器 {len(processors)} 个，依赖库 {len(needed_coords)} 个")
    if not processors:
        # 1.12.2 等老版本 Forge 没有处理器链：安装器只负责把 universal 等库放进
        # libraries（已在前面的普通库步骤完成），不生成补丁 client，直接沿用原版 client.jar。
        log("[forge] 老版本无处理器，复用原版 client.jar")
        return _vanilla_client_jar(alias)
    # 校正总槽位（只增不减）：实际处理器数可能与调用方预估不同，避免比例被 clamp 后停在 99.99%。
    tracker.set_total(max(tracker.total_files, 1 + len(processors)), tracker.total_bytes)

    # ---- 3. 下载处理器 maven 库到版本 libraries 目录 ----
    coord_to_local: dict[str, str] = {}
    for coord in sorted(needed_coords):
        if should_cancel and should_cancel():
            raise InterruptedError("Forge 安装已被取消")
        group, artifact, version, classifier, extension = _parse_bracket_coord(coord)
        rel = _coord_rel_path(group, artifact, version, classifier, extension)
        local = os.path.join(libraries_root, rel.replace("/", os.sep))
        bmcl = C.BMCL_MAVEN_URL.format(path=rel)
        official = _official_maven_url(rel, group)
        task = DownloadTask(
            url=bmcl,
            local_path=local,
            mirror_url=None,
            extra_urls=[official],
            label=coord,
        )
        ok, reason = download_one(task, tracker, should_cancel)
        if not ok:
            raise RuntimeError(f"处理器库下载失败 {coord}: {reason}")
        coord_to_local[coord] = local

    # ---- 4. 解析 data 变量（client 侧）----
    data_values = install_profile.get("data") or {}
    resolved_vars = _build_variables(
        data_values, installer_zip_path=installer_path,
        installer_entries=installer_entries, work_dir=work_dir,
        libraries_root=libraries_root, mc_jar_path=_vanilla_client_jar(alias),
        version_dir=game_dirs.version_dir(alias),
    )

    # ---- 5. 逐个运行处理器 ----
    for index, proc in enumerate(processors, start=1):
        jar_coord = str(proc.get("jar") or "")
        jar_local = coord_to_local[jar_coord]
        classpath = [jar_local]
        for cp in proc.get("classpath") or []:
            cp_local = coord_to_local.get(str(cp))
            if cp_local:
                classpath.append(cp_local)
        main_class = _read_main_class(jar_local)
        resolved_args = [_substitute_arg(str(arg), resolved_vars, coord_to_local)
                         for arg in proc.get("args") or []]
        log(f"[forge] 处理器 {index}/{len(processors)} {main_class}")
        _run_java(java_path, classpath, main_class, resolved_args,
                  should_cancel=should_cancel)
        # 按 outputs 校验产物 sha1
        _verify_outputs(proc.get("outputs") or {}, resolved_vars, log)
        tracker.record_file_done()

    # ---- 6. 确认最终 client Jar 已生成并返回 ----
    patched_token = str(data_values.get("PATCHED", {}).get("client", ""))
    client_jar_path = _substitute_arg("{PATCHED}", resolved_vars)
    if not (os.path.isfile(client_jar_path) and os.path.getsize(client_jar_path) > 0):
        raise RuntimeError("Forge client Jar 未生成")
    log(f"[forge] client Jar 生成完成：{client_jar_path}")
    return client_jar_path


def cleanup_work_dir(alias: str) -> None:
    """处理器链成功后清理 forge_work 临时目录（installer 与解压数据），不删 libraries 产物。"""
    import shutil

    work_dir = os.path.join(game_dirs.version_dir(alias), "forge_work")
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 内部辅助
# --------------------------------------------------------------------------- #
def _installer_usable(path: str) -> bool:
    """installer 文件存在且能作为 Zip 打开（含 ``install_profile.json``）才算可复用。

    下载中断残留的半截 Jar 必须重下，否则后续 ``zipfile`` 解析会抛 BadZipFile，
    让整步直接失败——用户现场「第二个加载器直接失败」就可能是这类残留。
    """
    if not (os.path.isfile(path) and os.path.getsize(path) > 0):
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            zf.getinfo("install_profile.json")
        return True
    except (OSError, KeyError, zipfile.BadZipFile):
        try:
            os.remove(path)
        except OSError:
            pass
        return False


def _processor_applies_to_client(processor: dict) -> bool:
    """无 sides 视为 client+server 都跑；显式 sides 只有含 client 才跑。"""
    sides = processor.get("sides")
    if not sides:
        return True
    return "client" in sides


def _vanilla_client_jar(alias: str) -> str:
    client = game_dirs.find_client_jar(alias)
    if not client:
        raise RuntimeError("原版 client.jar 尚未下载，无法运行 Forge 处理器")
    return client


def _build_variables(data_values: dict, installer_zip_path: str,
                     installer_entries: set, work_dir: str,
                     libraries_root: str, mc_jar_path: str,
                     version_dir: str) -> dict:
    """构造处理器参数占位变量表：内置变量 + data 里 client 侧解析后的路径 / 字面量。"""
    variables: dict[str, str] = {
        "ROOT": version_dir,
        "SIDE": "client",
        "MINECRAFT_JAR": mc_jar_path,
        "INSTALLER": installer_zip_path,
    }
    for key, value in data_values.items():
        raw_value = str((value or {}).get("client") or "").strip()
        variables[key] = _resolve_data_value(
            raw_value, installer_zip_path=installer_zip_path,
            installer_entries=installer_entries, work_dir=work_dir,
            libraries_root=libraries_root,
        )
    return variables


def _resolve_data_value(raw_value: str, installer_zip_path: str,
                        installer_entries: set, work_dir: str,
                        libraries_root: str) -> str:
    """解析单个 data 值：括号坐标 → 本地路径；引号 → 字面量；斜杠 → 从 installer 解压。"""
    if raw_value.startswith("[") and raw_value.endswith("]"):
        group, artifact, version, classifier, extension = _parse_bracket_coord(
            raw_value[1:-1]
        )
        rel = _coord_rel_path(group, artifact, version, classifier, extension)
        return os.path.join(libraries_root, rel.replace("/", os.sep))
    if raw_value.startswith("'") and raw_value.endswith("'"):
        return raw_value[1:-1]
    if raw_value.startswith("/"):
        return _extract_installer_file(
            raw_value.lstrip("/"), installer_zip_path,
            installer_entries, work_dir,
        )
    return raw_value


def _extract_installer_file(entry_name: str, installer_zip_path: str,
                            installer_entries: set, work_dir: str) -> str:
    """把 installer 内某个文件解压到 work_dir（保持相对路径），返回本地绝对路径。"""
    if entry_name not in installer_entries:
        raise RuntimeError(f"installer 内缺少数据文件：{entry_name}")
    target = os.path.join(work_dir, entry_name.replace("/", os.sep))
    if os.path.isfile(target) and os.path.getsize(target) > 0:
        return target
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with zipfile.ZipFile(installer_zip_path) as zf:
        with zf.open(entry_name) as src, open(target, "wb") as out:
            out.write(src.read())
    return target


_VAR_PATTERN = re.compile(r"\{([A-Z0-9_]+)\}")


def _substitute_arg(arg: str, variables: dict, coord_paths: dict | None = None) -> str:
    """替换处理器参数里的 ``{VAR}`` 占位（可与路径片段组合，如 ``{ROOT}/README.txt``）。

    传入 ``coord_paths`` 时，还会把 ``[maven 坐标]`` 替换为该工件已下载的本地路径
    （Forge 官方安装器在运行处理器前会把 args 里的括号坐标解析成本地文件）。
    """
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, match.group(0)))
    text = _VAR_PATTERN.sub(_replace, arg)
    if coord_paths:
        def _replace_bracket(match: re.Match) -> str:
            coord = match.group(1).strip()
            local = coord_paths.get(coord)
            return local if local else match.group(0)
        text = _BRACKET_PATTERN.sub(_replace_bracket, text)
    return text


def _read_main_class(jar_path: str) -> str:
    """从处理器 Jar 的 manifest 读取 ``Main-Class``；缺失则抛错。"""
    with zipfile.ZipFile(jar_path) as zf:
        manifest = zf.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace")
    for line in manifest.splitlines():
        if line.lower().startswith("main-class:"):
            main_class = line.split(":", 1)[1].strip()
            if main_class:
                return main_class
    raise RuntimeError(f"处理器 Jar 缺少 Main-Class：{jar_path}")


def _run_java(java_path: str, classpath: list[str], main_class: str,
              resolved_args: list[str], should_cancel=None,
              timeout: float | None = None) -> None:
    """执行 ``java -cp <classpath> <mainClass> <args>``；轮询取消，非零退出即抛错。

    除用户取消外还有总时长上限（默认 :data:`C.FORGE_PROCESSOR_TIMEOUT`）：处理器真的
    挂住时抛错中止，让面板显示失败原因，而不是无限期停在「进行中」。
    """
    limit = float(timeout if timeout is not None else C.FORGE_PROCESSOR_TIMEOUT)
    command = [
        java_path,
        "-cp", os.pathsep.join(classpath),
        main_class,
        *resolved_args,
    ]
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    started = time.monotonic()
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=1)
            break
        except subprocess.TimeoutExpired:
            if should_cancel and should_cancel():
                proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise InterruptedError("Forge 处理器已被取消")
            if time.monotonic() - started > limit:
                proc.kill()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                raise RuntimeError(
                    f"处理器 {main_class} 超过 {int(limit)} 秒未结束，已中止"
                )
    if proc.returncode != 0:
        detail = (stderr or b"").decode("utf-8", errors="replace")
        detail += (stdout or b"").decode("utf-8", errors="replace")
        raise RuntimeError(
            f"处理器 {main_class} 退出码 {proc.returncode}：{detail.strip()[:2000]}"
        )


def _verify_outputs(outputs: dict, variables: dict, log) -> None:
    """按处理器 outputs 的 ``{输出}: {SHA}`` 声明，校验产出文件 sha1。"""
    import hashlib

    for output_token, sha_token in outputs.items():
        output_path = _substitute_arg(str(output_token), variables)
        expected_sha = _substitute_arg(str(sha_token), variables).lower()
        if not os.path.isfile(output_path):
            raise RuntimeError(f"处理器产物缺失：{output_path}")
        digest = hashlib.sha1()
        with open(output_path, "rb") as f:
            while True:
                block = f.read(C.DOWNLOAD_CHUNK_SIZE)
                if not block:
                    break
                digest.update(block)
        actual_sha = digest.hexdigest().lower()
        if expected_sha and actual_sha != expected_sha:
            raise RuntimeError(
                f"处理器产物 sha1 不匹配 {output_path}：期望 {expected_sha}，实际 {actual_sha}"
            )
        log(f"[forge] 产物校验通过 {os.path.basename(output_path)} {actual_sha[:12]}")
