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

"""正版皮肤纹理后台下载线程：在独立线程拉取皮肤 PNG，信号回主线程交给 GL 预览。

纯标准库 urllib 下载字节，QImage 在接收线程（主线程）从字节构建，避免在 GL 线程之外
触碰 OpenGL 纹理对象；下载失败由调用方回退到内置史蒂夫 / 艾利克斯皮肤。
"""
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .. import constants as C


class SkinFetchWorker(QThread):
    """下载单个正版皮肤 PNG，成功回传 QImage 与模型类型，失败回传中文错误。"""

    succeeded = Signal(QImage, bool)
    failed = Signal(str)

    def __init__(self, skin_url: str, slim: bool, parent=None) -> None:
        super().__init__(parent)
        self._url = skin_url
        self._slim = slim

    def run(self) -> None:
        if not self._url:
            self.failed.emit("未提供正版皮肤地址。")
            return
        request = urllib.request.Request(
            self._url,
            headers={"User-Agent": f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=C.SKIN_FETCH_TIMEOUT) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            self.failed.emit(f"皮肤下载失败（HTTP {exc.code}）。")
            return
        except Exception as exc:  # 网络 / 超时 / SSL 统一兜底
            self.failed.emit(f"皮肤下载失败：{exc}")
            return

        image = QImage()
        if not image.loadFromData(data):
            self.failed.emit("皮肤图片解析失败，已回退到内置角色。")
            return
        self.succeeded.emit(image, self._slim)
