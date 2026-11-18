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

"""启动时后台静默恢复正版会话：用本地保存的 refresh_token 静默换新整条登录链路。

网络请求放在独立 ``QThread``，不阻塞主界面；成功回传完整玩家档案给主线程切正版态，
失败回传中文原因，由主窗口清除本地账号文件并保持离线。纯标准库认证模块，不引入第三方
HTTP / 认证库。
"""
from PySide6.QtCore import QThread, Signal

from .. import constants as C
from ..microsoft_auth import MicrosoftAuth


class AccountRestoreWorker(QThread):
    """用本地刷新令牌静默恢复正版账号；成功回传档案，失败回传中文错误。"""

    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, refresh_token: str, parent=None) -> None:
        super().__init__(parent)
        self._refresh_token = refresh_token
        # 静默恢复用更短的单跳超时，使关闭窗口时等待线程收尾的时间有确定上界。
        self._auth = MicrosoftAuth(timeout=C.RESTORE_HTTP_TIMEOUT)

    def run(self) -> None:
        if not self._refresh_token:
            self.failed.emit("本地未保存登录令牌。")
            return
        try:
            profile = self._auth.refresh_profile(self._refresh_token)
        except Exception as exc:  # 网络 / 超时 / SSL 等未预期异常统一兜底
            self.failed.emit(f"静默恢复登录失败：{exc}")
            return
        if profile:
            self.succeeded.emit(profile)
        else:
            self.failed.emit("本地登录态已失效，需要重新完成设备码授权。")
