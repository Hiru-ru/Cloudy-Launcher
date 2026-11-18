# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Cloudy Pet / 云朵桌宠
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

"""云朵桌宠（Cloudy Pet）独立 APP 常量。

桌宠是独立于云朵启动器运行的小程序，版本号独立计；启动器通过「设置 · 桌宠」页
导入本程序后，再以命令行参数把皮肤路径与模型类型传入并启动。
"""
import os
import sys

# 桌宠独立版本号（与启动器版本号分开维护）。正式版采用三段版本号（主.次.修订）；
# 此前四段号（主.次.功能.修复）为内部测试版。
PET_VERSION = "1.1.0"
PET_APP_NAME = "Cloudy Pet"
PET_VERSION_TAG = "v" + PET_VERSION
# 发布阶段：与启动器统一发布正式版 1.1.0。
PET_STAGE = "正式版"

# 桌宠窗口尺寸（透明、无边框、置顶）；竖向构图，角色高 32 单位、宽约 16 单位。
PET_WINDOW_WIDTH = 128
PET_WINDOW_HEIGHT = 168

# 皮肤纹理标准尺寸（64×64 原版布局；旧 64×32 由渲染组件补齐）。
TEX_W = 64
TEX_H = 64

# 相机：沿用启动器角色预览的透视参数，角色在画面中的占比由 FOV/DIST 决定，
# 与窗口像素无关，窗口宽高比取竖向以贴合人物。
CAM_FOV = 38.0
CAM_DIST = 88.0
MODEL_CY = 16.0

# 仅头部跟随鼠标的量程（弧度）：绕颈枢轴左右转头 + 抬头/低头。
# 身体（躯干/双臂/双腿）不随鼠标转动，也不做待机摆臂。
HEAD_YAW_RAD = 0.55
HEAD_PITCH_RAD = 0.35

# 头部角度指数平滑系数（越大越跟手，越小越柔和），与鼠标轮询间隔。
SMOOTH_FACTOR = 0.20
POLL_INTERVAL_MS = 16

# 归一化偏移达到满量程所用的像素半径（以窗口中心为基准）。
POINTER_RADIUS = 120.0

# 空闲检测：鼠标（输入）静止达到该秒数后进入空闲，随机播放动作；先设 3 秒，
# 单独抽成常量便于以后调整（用户口径：先 3 秒，之后慢慢往上调）。
IDLE_THRESHOLD_SEC = 3.0
# 空闲时两个随机动作之间的额外间隔区间（秒，在动作时长之外再随机等待）。
IDLE_GAP_MIN = 0.8
IDLE_GAP_MAX = 2.5

# 饥饿值：0~HUNGER_MAX，随时间下降；降到 HUNGER_LOW 时冒泡「我饿了」并自动吃东西，
# 吃完回满。速率抽成常量，方便以后调整节奏。
HUNGER_MAX = 100.0
HUNGER_LOW = 30.0
HUNGER_DRAIN_PER_SEC = 100.0 / 90.0   # 从满到空约 90 秒，约 63 秒时开始喊饿
HUNGER_RESTORE = 100.0

# 鼠标在窗口内静止（悬停）达到该随机秒数后弹出喂食菜单；鼠标移动或离开立即关闭。
# 用户口径：悬浮 1~3 秒；每次进入悬停在区间内随机取一个触发时长。
HOVER_MENU_MIN_SEC = 1.0
HOVER_MENU_MAX_SEC = 3.0
# 静止判定的抖动容差（像素）：该半径内的硬件抖动不重置计时。
HOVER_JITTER_PX = 4.0

# 小狗（驯服狼）随机进场/退场：进入空闲后在区间内随机等待再进场；陪伴一段随机
# 时间后自动退场。均抽成常量，方便以后调整节奏。
WOLF_ENTER_DELAY_MIN = 1.5
WOLF_ENTER_DELAY_MAX = 4.0
WOLF_STAY_MIN = 12.0
WOLF_STAY_MAX = 22.0

# 困倦 / 睡眠行为链：鼠标持续静止（空闲）达到该秒数后先打哈欠、冒泡「好困啊」，
# 继续静止到入睡秒数后蜷缩睡觉（闭眼、Zzz）；鼠标一动立即醒来。
SLEEP_DROWSY_SEC = 10.0
SLEEP_FALL_SEC = 16.0
# 入睡 / 醒来姿态过渡的指数平滑系数（越大切换越快）。
SLEEP_BLEND_FACTOR = 0.12


def resource_path(relative: str) -> str:
    """返回打包内置资源绝对路径；兼容源码运行与 PyInstaller onefile。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "resources", relative)


def default_skin_path() -> str:
    """内置兜底皮肤（未从命令行取得有效皮肤时使用）。"""
    return resource_path("steve.png")
