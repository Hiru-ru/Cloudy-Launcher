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

"""v1.3.9.0 背景音乐：只允许一首歌、无限循环。

- 文件管理：导入的歌曲统一存到 app 同级 ``music/bgm.<ext>``，目录里永远只有一首歌；
  重新导入会先删掉旧歌，删除即清空目录。
- 播放：PySide6 自带 QtMultimedia（QMediaPlayer + QAudioOutput），不引入第三方依赖；
  循环次数设为 Infinite，单曲无限循环。
- v1.3.9.2：设置页删除音乐总开关 / 自动播放两个开关——有歌曲即加载并播放，
  无歌曲即静默；config 中旧字段保留但不再使用。
"""
from __future__ import annotations

import os
import shutil

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from . import constants as C
from .resources import data_dir


# ---------------------------------------------------------------------------
# 文件管理
# ---------------------------------------------------------------------------
def music_dir() -> str:
    return os.path.join(data_dir(), C.MUSIC_DIR_NAME)


def current_music_path() -> str:
    """返回当前歌曲的绝对路径；不存在时返回空串。"""
    directory = music_dir()
    if not os.path.isdir(directory):
        return ""
    for name in os.listdir(directory):
        if os.path.splitext(name)[1].lower() in C.MUSIC_EXTS:
            full = os.path.join(directory, name)
            if os.path.isfile(full):
                return full
    return ""


def import_music(src_path: str) -> str:
    """导入一首歌并替换旧歌，返回新文件的绝对路径。

    Raises:
        ValueError: 源文件不存在 / 格式不支持。
    """
    if not os.path.isfile(src_path):
        raise ValueError("源文件不存在")
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in C.MUSIC_EXTS:
        raise ValueError("不支持的音频格式")

    directory = music_dir()
    os.makedirs(directory, exist_ok=True)
    # 目录里只留一首歌：先清掉旧的 bgm.*。
    for name in os.listdir(directory):
        if os.path.splitext(name)[1].lower() in C.MUSIC_EXTS:
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                pass
    target = os.path.join(directory, f"{C.MUSIC_BASENAME}{ext}")
    shutil.copy2(src_path, target)
    return target


def delete_music() -> None:
    """删除当前歌曲。"""
    path = current_music_path()
    if path:
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 播放封装
# ---------------------------------------------------------------------------
class MusicPlayer:
    """QMediaPlayer 的薄封装：单曲无限循环。

    v1.3.9.2 起不再有总开关语义：有歌曲即视为启用并播放。
    """

    def __init__(self) -> None:
        self._audio = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio)
        # 单曲无限循环。
        self._player.setLoops(QMediaPlayer.Loops.Infinite)
        self._enabled: bool = False
        self._loaded_path: str = ""

    def load_from_config(self, config) -> None:
        """启动时扫描歌曲；有文件即加载并播放（旧开关字段不再使用）。"""
        path = current_music_path()
        self._enabled = bool(path)
        if path:
            self._set_source(path)
            self.play()

    def _set_source(self, path: str) -> None:
        if path != self._loaded_path:
            self._player.setSource(QUrl.fromLocalFile(path))
            self._loaded_path = path

    def refresh_source(self) -> None:
        """文件被删除 / 重新导入后，重新扫描并同步播放器状态。"""
        path = current_music_path()
        self._enabled = bool(path)
        if path:
            self._set_source(path)
            self.play()
        else:
            self.stop()
            self._player.setSource(QUrl())
            self._loaded_path = ""

    def release_source(self) -> None:
        """停止播放并清空 source，释放对当前音频文件的占用（Windows 下删文件前必须调用）。"""
        self.stop()
        self._player.setSource(QUrl())
        self._loaded_path = ""

    def set_enabled(self, enabled: bool) -> None:
        """兼容保留：外部旧调用；实际启用态跟随歌曲是否存在。"""
        self._enabled = bool(enabled)
        if not enabled:
            self.stop()
        elif self._loaded_path:
            self.play()

    def play(self) -> None:
        if self._enabled and self._loaded_path:
            self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def shutdown(self) -> None:
        """窗口关闭时停止播放，释放底层音频资源。"""
        self.stop()
        self._player.setSource(QUrl())
        self._audio.deleteLater()
        self._player.deleteLater()
