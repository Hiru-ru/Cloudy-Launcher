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

"""小云 AI（Xiaoyun AI）独立 APP 常量。

小云 AI 是独立于云朵启动器运行的本地汉化工具：扫描 mod jar 内的英文语言文件
（en_us.json），用本地 DeepSeek 模型批量翻译成简体中文，生成可在游戏内启用的
汉化资源包。版本号独立维护，模型与推理运行时不并入启动器安装包。
"""
import os
import sys

# 独立版本号（与启动器分开维护）。首个正式版采用三段版本号。
# 1.1.0：纯进度窗口（删除配置表单与主题切换，跟随启动器全局主题），大卡片自动
# 收缩为右下角小胶囊，本地 DeepSeek 模型翻译并生成可在游戏内启用的汉化资源包。
AI_VERSION = "1.1.0"
AI_APP_NAME = "Xiaoyun AI"
AI_DISPLAY_NAME = "小云 AI"
AI_VERSION_TAG = "v" + AI_VERSION
AI_STAGE = "正式版"

# 语言文件名（Minecraft 1.11+ 语言文件为 JSON，小写命名）。
LANG_EN = "en_us.json"
LANG_ZH = "zh_cn.json"
# jar 内语言文件路径片段：assets/<namespace>/lang/en_us.json
LANG_DIR_MARK = ("assets", "lang")

# 资源包 pack_format：用于较新版本（1.20.5+ 为 32/34 等）。测试版默认 15，
# 并在 pack.mcmeta 同时写 supported_formats 区间以尽量兼容多版本。
DEFAULT_PACK_FORMAT = 15
PACK_FORMAT_MIN = 15
PACK_FORMAT_MAX = 99

# 译文免责提示：写入资源包说明与界面，明确机器翻译可能有误。
TRANSLATION_DISCLAIMER = "AI 机器翻译，可能存在不准确，仅供参考。"

# 推理默认参数（与已验证的 llama-server 测试一致）。
DEFAULT_CTX = 2048
DEFAULT_THREADS = 6
DEFAULT_TEMP = 0.2
DEFAULT_RETRY_TEMP = 0.1
DEFAULT_N_PREDICT = 120

# 并行翻译：每个 server slot 的上下文大小（短文本 + 输出足够）。
PER_SLOT_CTX = 2048


def worker_lines(total_entries: int) -> int:
    """按待翻译条目总数返回并行翻译线数（真机实测，4 核 CPU 封顶 4 线）。

    实测：4 slot 吞吐最高（约 1.85 条/秒），8 slot 因 CPU 争抢反而倒退，故不采用
    更多线。分档：<200 用 1 线，200-499 用 2 线，>=500 用 4 线。
    """
    total_entries = int(total_entries or 0)
    if total_entries < 200:
        return 1
    if total_entries < 500:
        return 2
    return 4


# few-shot 示例：经实测可显著稳定短专有名词/菜单文本的翻译，并引导术语保留。
FEW_SHOT_EXAMPLES = (
    "EN: Video Settings\nZH: 视频设置\n"
    "EN: Clear Active Toasts\nZH: 清除当前通知\n"
    "EN: Sodium Options\nZH: Sodium 选项\n"
)
# 单条翻译的停止序列：译文通常为单行，遇到换行即停，防止补全模式续写模板。
STOP_SEQUENCES = ["\n", "EN:", "ZH:"]

# ---------------------------------------------------------------------------
# 玻璃主题三档（与启动器一致：磨砂 / 通透 / 普通），可在窗口内切换。
# ---------------------------------------------------------------------------
THEME_FROST = "frost"
THEME_CLEAR = "clear"
THEME_NORMAL = "normal"
THEME_KEYS = (THEME_FROST, THEME_CLEAR, THEME_NORMAL)
THEME_LABELS = {
    THEME_FROST: "磨砂",
    THEME_CLEAR: "通透",
    THEME_NORMAL: "普通",
}
DEFAULT_THEME = THEME_FROST

# 卡片三主题配色（RGBA），数值与启动器三档对齐。
CARD_GLASS_TOP = (255, 255, 255, 176)
CARD_GLASS_MID = (255, 255, 255, 102)
CARD_GLASS_BOTTOM = (255, 255, 255, 62)
CARD_GLASS_BORDER = (255, 255, 255, 188)
CARD_CLEAR_TOP = (255, 255, 255, 96)
CARD_CLEAR_MID = (255, 255, 255, 52)
CARD_CLEAR_BOTTOM = (255, 255, 255, 28)
CARD_CLEAR_BORDER = (255, 255, 255, 160)
CARD_NORMAL_PANEL = (255, 255, 255, 255)
CARD_NORMAL_BORDER = (214, 226, 236, 255)
# 磨砂两级缩放的短边像素（越小越糊）。
BLUR_SHORT_SIDE = 100
CARD_RADIUS = 16.0

# 收起态小胶囊尺寸（与启动器下载面板手感一致）。
PILL_WIDTH = 178
PILL_HEIGHT = 44
# 小胶囊相对启动器窗口右下角的留白。
PILL_MARGIN_RIGHT = 18
PILL_MARGIN_BOTTOM = 18
# 大卡片 ↔ 小胶囊几何动画时长（毫秒）。
PANEL_ANIM_MS = 320

# 源码运行（开发调试）时的模型 / 引擎回退候选；正式打包后改用内置的
# _MEIPASS/models/model.gguf 与 _MEIPASS/llama/llama-server.exe（见下方函数）。
# 克隆源码后，把量化模型放到 xiaoyun_ai/bundled/models/model.gguf，
# llama.cpp 运行时（llama-server.exe 及同目录 DLL）放到
# xiaoyun_ai/bundled/llama/。该 bundled/ 目录不入库（见 .gitignore）。
def _dev_bundled_model() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "bundled", "models", "model.gguf")


def _dev_bundled_server() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "bundled", "llama", "llama-server.exe")

# 术语保护：这些专有名词默认不翻译，避免小模型错译（如 Fabric→布料、Sodium→硅）。
# 键为小写英文词，值为应保留的写法。
PROTECTED_TERMS = {
    "sodium": "Sodium",
    "fabric": "Fabric",
    "lithium": "Lithium",
    "phosphor": "Phosphor",
    "iris": "Iris",
    "forge": "Forge",
    "neoforge": "NeoForge",
    "optifine": "OptiFine",
    "minecraft": "Minecraft",
    "java": "Java",
    "api": "API",
    "gui": "GUI",
    "hud": "HUD",
    "fps": "FPS",
    "tps": "TPS",
    "mod": "mod",
    "mods": "mods",
    "tick": "tick",
    "ticks": "ticks",
    "chunk": "chunk",
    "chunks": "chunks",
    "biome": "biome",
    "redstone": "红石",
}

# 版权致谢（公开分发时在「关于」页与 NOTICE 中列出）。
THIRD_PARTY_NOTICES = [
    "DeepSeek-R1-Distill-Qwen-1.5B：DeepSeek（MIT License），"
    "基座 Qwen2.5（Apache License 2.0）。",
    "llama.cpp：llama.cpp 团队（MIT License）。",
    "PySide6 / Qt：The Qt Company（LGPL / 商业授权）。",
]


def resource_path(relative: str) -> str:
    """返回打包内置资源绝对路径；兼容源码运行与 PyInstaller onefile。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "resources", relative)


def first_existing(paths: list[str]) -> str:
    """返回候选列表中第一个真实存在的路径；都不存在时返回空串。"""
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return ""


def bundle_base_dir() -> str:
    """PyInstaller onefile 解压根目录（_MEIPASS）；源码运行时返回本模块目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def bundled_model_path() -> str:
    """内置模型路径：打包后从 _MEIPASS/models 取；源码运行回退到工程内 bundled。"""
    if getattr(sys, "frozen", False):
        path = os.path.join(bundle_base_dir(), "models", "model.gguf")
        return path if os.path.isfile(path) else ""
    return first_existing([_dev_bundled_model()])


def bundled_server_path() -> str:
    """内置推理引擎：打包后从 _MEIPASS/llama 取；源码运行回退到工程内 bundled。"""
    if getattr(sys, "frozen", False):
        path = os.path.join(bundle_base_dir(), "llama", "llama-server.exe")
        return path if os.path.isfile(path) else ""
    return first_existing([_dev_bundled_server()])
