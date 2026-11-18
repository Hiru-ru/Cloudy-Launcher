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

"""桌宠后端：独立 APP 程序导入、皮肤路径解析与桌宠进程启停（不含界面控件）。

口径（v1.4.1.0）：

- 桌宠是独立 APP，启动器不内置；用户在「设置 · 桌宠」页通过文件选择导入桌宠
  可执行文件（.exe）或其发布压缩包（.zip），导入后复制到 ``CLY/pet`` 并记录路径；
- 皮肤：正版账号使用正版皮肤（界面先下载落盘），禁止导入皮肤；离线账号优先用
  导入的自定义皮肤，否则用内置史蒂夫 / 艾利克斯；
- 启动器以子进程方式拉起桌宠 exe，通过命令行参数传入皮肤路径、模型类型与窗口位置；
  关闭时只终止本次启动的桌宠进程，不影响其他程序。
"""
import ctypes
import os
import shutil
import subprocess
import sys
import zipfile
from ctypes import wintypes

from .resources import data_dir, resource_path

PET_DIR_NAME = "pet"
PET_EXE_NAME = "云朵桌宠.exe"
OFFICIAL_CACHE_NAME = "official_skin.png"
# 导入桌宠程序时允许的来源文件类型。
APP_EXTS = (".exe", ".zip")
SKIN_EXTS = (".png", ".jpg", ".jpeg")

# ---------------------------------------------------------------------------
# Windows 进程枚举（仅标准库 ctypes）：用于按 exe 路径定位孤儿桌宠并整树终止。
# ---------------------------------------------------------------------------
_TH32CS_SNAPPROCESS = 0x00000002
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class _PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _taskkill_path() -> str:
    return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                        "System32", "taskkill.exe")


def _process_image_path(pid: int) -> str | None:
    """读取某进程的可执行文件完整路径；无权限 / 已退出时返回 None。"""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        kernel32.CloseHandle(handle)


def running_pet_pids(app_path: str) -> list[int]:
    """枚举可执行路径等于 ``app_path`` 的全部桌宠进程（含历史孤儿）。"""
    if sys.platform != "win32" or not app_path:
        return []
    target = os.path.normcase(os.path.abspath(app_path))
    kernel32 = ctypes.windll.kernel32
    snap = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    entry = _PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
    pids = []
    try:
        if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                pid = entry.th32ProcessID
                image = _process_image_path(pid)
                if image and os.path.normcase(os.path.abspath(image)) == target:
                    pids.append(pid)
                if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return pids


def kill_process_tree(pid: int) -> bool:
    """用 taskkill /T /F 终止指定进程及其整棵子进程树（含 onefile 子进程）。"""
    try:
        cp = subprocess.run(
            [_taskkill_path(), "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return cp.returncode == 0
    except OSError:
        return False


def stop_all_pet_processes(app_path: str) -> list[int]:
    """按路径清理全部桌宠进程（含孤儿），返回实际终止的 PID 列表。"""
    pids = running_pet_pids(app_path)
    killed = []
    for pid in pids:
        if kill_process_tree(pid):
            killed.append(pid)
    return killed


def pet_dir() -> str:
    """桌宠程序与正版皮肤缓存目录（``CLY/pet``）。"""
    path = os.path.join(data_dir(), PET_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def imported_pet_path() -> str:
    """导入后桌宠 exe 的固定落盘路径。"""
    return os.path.join(pet_dir(), PET_EXE_NAME)


def official_cache_path() -> str:
    """正版皮肤本地缓存路径（界面下载后落盘）。"""
    return os.path.join(pet_dir(), OFFICIAL_CACHE_NAME)


# ---------------------------------------------------------------------------
# 桌宠程序导入
# ---------------------------------------------------------------------------
def _import_from_exe(src: str) -> str:
    dst = imported_pet_path()
    shutil.copyfile(src, dst)
    return dst


def _import_from_zip(src: str) -> str:
    """从发布压缩包中找到唯一 exe 解压到固定路径；做 zip-slip 防护。"""
    target_dir = pet_dir()
    exe_member = None
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/"):
                continue
            base = os.path.basename(name)
            if not base.lower().endswith(".exe"):
                continue
            # 只接受平铺或带目录的安全条目，拒绝绝对路径与父目录跳转。
            if os.path.isabs(name) or ".." in name.split("/"):
                continue
            exe_member = info
            break
        if exe_member is None:
            raise ValueError("压缩包内未找到桌宠可执行文件（.exe）。")
        dst = imported_pet_path()
        with zf.open(exe_member) as src_f, open(dst, "wb") as out_f:
            shutil.copyfileobj(src_f, out_f)
    return dst


def import_pet_app(src: str) -> str:
    """把用户选择的桌宠程序（exe/zip）导入到固定路径，返回该路径。"""
    ext = os.path.splitext(src)[1].lower()
    if ext == ".exe":
        return _import_from_exe(src)
    if ext == ".zip":
        return _import_from_zip(src)
    raise ValueError("仅支持导入桌宠 .exe 程序或其 .zip 压缩包。")


def remove_pet_app() -> None:
    """移除已导入的桌宠程序（不删正版皮肤缓存）。

    先终止仍占用该 exe 的全部桌宠进程，再删除文件；文件仍被占用时抛出 OSError
    由界面捕获提示。
    """
    path = imported_pet_path()
    if not os.path.isfile(path):
        return
    stop_all_pet_processes(path)
    os.remove(path)


# ---------------------------------------------------------------------------
# 皮肤路径解析
# ---------------------------------------------------------------------------
def offline_skin_path(config) -> tuple[str, bool]:
    """离线皮肤：优先自定义皮肤，否则按 config.skin 取内置史蒂夫/艾利克斯。"""
    custom = config.custom_skin
    if custom and os.path.isfile(custom):
        # 自定义皮肤的模型类型沿用当前内置角色选择（Alex=细臂）。
        return custom, _builtin_slim(config)
    return _builtin_skin(config)


def _builtin_slim(config) -> bool:
    choice = config.get("skin")
    info = C_SKIN_INFO(choice)
    return bool(info["slim"])


def _builtin_skin(config) -> tuple[str, bool]:
    choice = config.get("skin")
    info = C_SKIN_INFO(choice)
    return resource_path(os.path.join("skins", info["file"])), bool(info["slim"])


def C_SKIN_INFO(skin_id: str) -> dict:
    """延迟引用常量中的内置皮肤定义，缺失时回退史蒂夫。"""
    from . import constants as C
    return C.SKIN_CHOICES.get(skin_id, C.SKIN_CHOICES[C.DEFAULT_SKIN])


def save_official_skin(image) -> str:
    """把正版皮肤 QImage 落盘为本地缓存，返回路径。"""
    path = official_cache_path()
    if not image.save(path, "PNG"):
        raise OSError("正版皮肤缓存写入失败。")
    return path


# ---------------------------------------------------------------------------
# 桌宠进程启停
# ---------------------------------------------------------------------------
def build_argv(app_path: str, skin_path: str, slim: bool,
               x: int | None, y: int | None,
               features: dict | None = None) -> list[str]:
    from . import pet_features as PF
    argv = [
        app_path,
        "--skin", skin_path,
        "--slim", "1" if slim else "0",
        # 启动器握手标志：桌宠据此确认由启动器拉起，直接双击不会带此标志。
        "--from-launcher",
    ]
    if x is not None and y is not None:
        argv.extend(["--x", str(int(x)), "--y", str(int(y))])
    # 功能开关：编码为 key=1,key=0；缺省（None）编码为全开，桌宠据此应用。
    argv.extend(["--features", PF.encode_features(PF.normalize(features))])
    return argv


def launch_pet(app_path: str, skin_path: str, slim: bool,
               x: int | None, y: int | None,
               features: dict | None = None) -> subprocess.Popen:
    """启动桌宠子进程；不显示控制台，独立于启动器事件循环运行。"""
    argv = build_argv(app_path, skin_path, slim, x, y, features)
    return subprocess.Popen(  # noqa: S603 (参数为列表，无 shell 注入)
        argv,
        executable=argv[0],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def stop_pet(process: subprocess.Popen) -> None:
    """终止本次启动的桌宠进程（整棵进程树）；已退出则不处理。

    PyInstaller 单文件 exe 存在 bootloader 父进程 + 实际渲染子进程，单纯 terminate
    Popen 记录的父进程会留下子进程孤儿，故优先 taskkill /T 整树终止，再以
    terminate/kill 兜底。
    """
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        pid = getattr(process, "pid", None)
        if pid is not None:
            kill_process_tree(pid)
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
