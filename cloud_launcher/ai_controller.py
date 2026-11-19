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

"""小云 AI 后端：独立程序导入、落盘与进程启停（不含界面控件）。

小云 AI 是独立打包的程序，启动器不内置：用户在「设置 · AI」页导入其可执行文件
（.exe）或发布压缩包（.zip），复制到 ``CLY/ai`` 并记录；版本设置页的「AI 翻译」
据此拉起独立程序，通过命令行传入该版本目录、资源包输出目录与当前主题。进程枚举与
整树终止复用 :mod:`pet_controller` 的通用工具，不重复实现。
"""
import os
import shutil
import subprocess
import sys
import zipfile

from .resources import data_dir
from .pet_controller import kill_process_tree, running_pet_pids

AI_DIR_NAME = "ai"
AI_EXE_NAME = "小云AI.exe"
APP_EXTS = (".exe", ".zip")


def ai_dir() -> str:
    """小云 AI 程序目录（``CLY/ai``）。"""
    path = os.path.join(data_dir(), AI_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def imported_ai_path() -> str:
    """导入后小云 AI exe 的固定落盘路径。"""
    return os.path.join(ai_dir(), AI_EXE_NAME)


def is_ai_imported() -> bool:
    """是否已导入小云 AI 程序。"""
    return os.path.isfile(imported_ai_path())


# ---------------------------------------------------------------------------
# 程序导入
# ---------------------------------------------------------------------------
def _import_from_exe(src: str) -> str:
    dst = imported_ai_path()
    shutil.copyfile(src, dst)
    return dst


def _import_from_zip(src: str) -> str:
    """从发布压缩包中找到唯一 exe 解压到固定路径；做 zip-slip 防护。"""
    exe_member = None
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/") or not os.path.basename(name).lower().endswith(".exe"):
                continue
            if os.path.isabs(name) or ".." in name.split("/"):
                continue
            exe_member = info
            break
        if exe_member is None:
            raise ValueError("压缩包内未找到小云 AI 可执行文件（.exe）。")
        dst = imported_ai_path()
        with zf.open(exe_member) as src_f, open(dst, "wb") as out_f:
            shutil.copyfileobj(src_f, out_f)
    return dst


def import_ai_app(src: str) -> str:
    """把用户选择的小云 AI 程序（exe/zip）导入固定路径，返回该路径。"""
    ext = os.path.splitext(src)[1].lower()
    if ext == ".exe":
        return _import_from_exe(src)
    if ext == ".zip":
        return _import_from_zip(src)
    raise ValueError("仅支持导入小云 AI .exe 程序或其 .zip 压缩包。")


def remove_ai_app() -> None:
    """移除已导入的小云 AI 程序；先终止仍占用该 exe 的进程，再删除文件。"""
    path = imported_ai_path()
    if not os.path.isfile(path):
        return
    for pid in running_pet_pids(path):
        kill_process_tree(pid)
    if os.path.isfile(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# 进程启停
# ---------------------------------------------------------------------------
def build_ai_argv(app_path: str, game_dir: str, output_dir: str,
                  theme: str, anchor: tuple | None = None) -> list[str]:
    """构造拉起小云 AI 的命令行；握手标志确保双击无法单跑。

    ``anchor`` 为启动器主窗口的全局几何 ``(x, y, w, h)``，传入后小云 AI 据此把
    卡片居中到启动器正中央。
    """
    argv = [app_path, "--from-launcher"]
    if game_dir:
        argv.extend(["--game-dir", game_dir])
    if output_dir:
        argv.extend(["--output-dir", output_dir])
    if theme:
        argv.extend(["--theme", theme])
    if anchor and len(anchor) == 4:
        argv.extend(["--anchor", "%d,%d,%d,%d" % tuple(int(v) for v in anchor)])
    return argv


def launch_ai(app_path: str, game_dir: str, output_dir: str,
              theme: str, anchor: tuple | None = None) -> subprocess.Popen:
    """启动小云 AI 子进程；不显示控制台，独立于启动器事件循环运行。"""
    argv = build_ai_argv(app_path, game_dir, output_dir, theme, anchor)
    return subprocess.Popen(  # noqa: S603（列表参数，无 shell 注入）
        argv,
        executable=argv[0],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def stop_ai(process: subprocess.Popen) -> None:
    """整树终止本次启动的小云 AI 进程（含 onefile 子进程）；已退出则不处理。"""
    if process is None or process.poll() is not None:
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
