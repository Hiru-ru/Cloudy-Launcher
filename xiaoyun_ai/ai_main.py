# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Xiaoyun AI / 小云 AI
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

"""小云 AI（Xiaoyun AI）独立 APP 入口。

小云 AI 不能单独运行：只有云朵启动器在「设置 · AI」页导入并启动时才会带
``--from-launcher`` 握手标志；直接双击不带该标志，提示后退出。启动后显示翻译
主界面，扫描 mod jar 英文语言文件并生成汉化资源包。
"""
import argparse
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

import ai_constants as C
from ai_window import AiWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Xiaoyun AI local translator")
    # 启动器握手：只有云朵启动器拉起时传入，直接双击不带。
    parser.add_argument("--from-launcher", action="store_true",
                        help="internal handshake: launched by Cloudy Launcher")
    # 可选：启动器把默认游戏目录/输出目录传入，作为界面初始值。
    parser.add_argument("--game-dir", default="",
                        help="default .minecraft directory (optional)")
    parser.add_argument("--output-dir", default="",
                        help="default resource pack output directory (optional)")
    parser.add_argument("--theme", default=C.DEFAULT_THEME,
                        choices=C.THEME_KEYS,
                        help="glass theme: frost/clear/normal (optional)")
    parser.add_argument("--anchor", default="",
                        help="launcher global geometry x,y,w,h for centering")
    return parser.parse_args(argv)


def parse_anchor(text: str) -> tuple | None:
    """解析 ``x,y,w,h`` 形式的启动器几何；非法返回 None。"""
    try:
        parts = [int(v.strip()) for v in str(text or "").split(",")]
    except (ValueError, AttributeError):
        return None
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        return None
    return tuple(parts)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication(sys.argv)
    app.setApplicationName(C.AI_APP_NAME)
    # 显式设置窗口图标：PyInstaller 的 icon 只影响 exe 文件本身，运行时标题栏与
    # 任务栏（多窗口并存时用于区分）仍需在此设置，否则显示默认无 logo 图标。
    app.setWindowIcon(QIcon(C.resource_path("app_icon.ico")))

    if not args.from_launcher:
        # 非启动器拉起（如直接双击）：不显示翻译界面，提示后退出。
        QMessageBox.information(
            None,
            C.AI_DISPLAY_NAME,
            f"{C.AI_DISPLAY_NAME}无法单独运行。请打开云朵启动器，在「设置 · AI」页"
            "导入并启动小云 AI。",
        )
        return 0

    anchor = parse_anchor(args.anchor)
    window = AiWindow(game_dir=args.game_dir, output_dir=args.output_dir,
                      theme=args.theme, anchor=anchor)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
