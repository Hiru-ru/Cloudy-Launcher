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

"""
Cloudy Launcher (CLY) v1.3.9.2
A Minecraft launcher built with Python + PySide6.
Offline profile page + Microsoft device-code login: GPU 3D skin preview,
persistent refresh tokens and silent session restore; content search with
real downloads into installed version directories, pagination and
per-card supported-version labels with incompatibility warnings.
Settings personalization: glass style modes with style previews and
hover tooltips, seven-color tints (whole-window tint in normal mode),
blank-default wallpaper selection (up to three custom wallpapers),
logo/name rewriting with independent switches, a master Apple-animation
toggle, and looping background music.

Run: python main.py
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from cloud_launcher import constants
from cloud_launcher.config_store import ConfigStore
from cloud_launcher.resources import resource_path
from cloud_launcher.ui.main_window import MainWindow
from cloud_launcher.ui.theme import global_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(constants.APP_FULL_NAME)
    app.setApplicationDisplayName(constants.APP_DISPLAY_NAME)
    app.setOrganizationName("CloudLauncher")

    icon = QIcon(resource_path("app_icon.ico"))
    app.setWindowIcon(icon)

    app.setStyleSheet(global_stylesheet())

    config = ConfigStore()
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
