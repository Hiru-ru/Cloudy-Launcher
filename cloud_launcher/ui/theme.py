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

"""全局视觉主题：配色常量集中在 constants.py，本模块提供 QSS 样式表。

v1.2.1.8：根窗口、侧栏、卡片三处容器本地样式表迁入本全局表（objectName 限定选择器），
避免祖先本地表切断 app 全局表中后代控件的属性选择器规则。

v1.2.1.9：开始游戏主按钮保持固定 44px 高、146px 宽、水平策略 Fixed 不拉伸，border-radius
取半高 22px，两端正半圆；加载进度条改用自绘 CapsuleProgressBar（见 capsule_progress_bar.py），
轨道与填充都由 paintEvent 圆角路径绘制，原生 ``QProgressBar::chunk`` 不画填充端头圆角的
问题不再影响主进度条；下方 QProgressBar 规则仅作为未自绘原生实例的兜底外观。

v1.2.1.10：个人页左侧卡片改为上行昵称、下行三格游玩统计（总游戏时长 / 启动次数 /
最近游玩），新增 ``statValue``（大数值）与 ``statLabel``（小标签）两组标签规则；
删除独立的启动器版本号展示卡片，其余控件外观沿用既有达标数值，不回退。

v1.2.1.11：昵称单独成通长窄卡并再缩小；三格统计拆出独立放大卡片，``statValue`` /
``statLabel`` / ``statValueDate`` 字号整体放大；统计卡与预览卡底部各加一条置灰的
``versionPicker`` 版本选择占位下拉，仅占位不展开；其余控件外观沿用既有达标数值。

v1.2.1.12：上段玩家名称窄卡与玩家人物卡横排并排等高；下段通长游玩统计卡内三格纵向
竖列（总游戏时长 / 启动次数 / 最近游玩），``statValue`` / ``statLabel`` / ``statValueDate``
字号沿用既有数值；全页仅统计卡底部保留一条置灰 ``versionPicker`` 游戏版本占位下拉，
人物卡底部不再重复占位行；其余控件外观沿用既有达标数值。

v1.2.1.13：按参考原型重构主体为两列——左列上下叠放玩家名称卡与游玩统计卡（三格纵向
竖列不变），右列玩家人物预览卡整列撑高；``versionPicker`` 游戏版本占位下拉从统计卡内
移出，成为主体下方独立通长一行，全页仍仅此一条；``statValue`` / ``statLabel`` /
``statValueDate`` 字号与其余控件外观沿用既有达标数值，不回退。

v1.2.1.14：左侧导航栏删除「个人页」以外的全部竖排占位图标入口，仅保留品牌区与「个人页」
导航项；随之移除已无实例的 ``QToolButton[navIcon="true"]`` 样式规则，``navItem`` 规则保留。
侧栏宽度、间距与其余控件外观沿用既有达标数值，不回退；后续导航布局由用户逐步口述补充。

v1.2.2.0：为微软正版设备码登录弹窗与正版账号信息补属性选择器规则——``dialogRoot`` 圆角
玻璃面板、``dialogTitle`` / ``dialogHint`` / ``dialogLink`` / ``deviceCode`` /
``dialogStatus``（含 ``statusOk`` / ``statusError`` 两态）/ ``dialogButton``，以及个人页
``uuidLabel`` 小号等宽 UUID 与 ``logoutButton`` 退出登录文字按钮；配色沿用既有通透玻璃数值，
不新增不透明实色块。

v1.2.2.1：修复认证 / 皮肤下载请求头 User-Agent 使用中文应用名导致的 latin-1 编码崩溃，
网络标识改用纯 ASCII 常量；本版本仅修复该运行时错误，界面样式规则无改动。

v1.2.2.2：微软正版登录由 v2 Azure-AD 设备码切换到 v1 Live-Connect 官方启动器设备码，
仅调整认证端点 / 客户端标识 / 令牌前缀，界面控件与 QSS 规则保持不变，无样式改动。

v1.2.3.1：微软正版设备码登录弹窗改为无边框真圆角玻璃面板——窗口根容器透明，内部
``dialogPanel`` 承载三段亮白玻璃渐变、20px 大圆角与同系细亮边；新增自绘标题栏
``dialogTitleBar`` / 标题文字 ``dialogTitleText`` / 关闭按钮 ``dialogClose`` 规则；
``deviceCode`` 码框圆角加大、字距收紧，``dialogButton`` 改为半高圆角轻玻璃胶囊；
配色仍全部复用既有玻璃数值，不新增不透明实色块。

v1.2.4.0：主窗口背景改由最底层 ``BackgroundLayer`` 自绘——外部 ``wallpaper/`` 目录
壁纸 cover 铺满，根容器 QSS 背景置透明；壁纸缺失 / 损坏 / 被删除时静默回退既有蓝白渐变；
不调用系统模糊接口、不挂 QGraphicsBlurEffect、不引入第三方模糊库，跨电脑表现一致。

v1.2.4.1：模糊下沉为卡片 / 侧栏片内局部磨砂。背景层只画清晰壁纸（不再全屏柔化、不叠整窗
磨砂罩）；``QFrame#card`` / ``QFrame#sidebar`` 的背景与边框移交各自 paintEvent 自绘（见
card_widget.py / nav_sidebar.py / frosted_backdrop.py），本全局表中二者置透明背景、无边框，
避免白渐变与自绘磨砂块双重叠加；圆角半径在自绘路径内控制。其余控件 QSS 规则不变。

v1.2.4.2：删除人物预览卡内层 ``QFrame#preview-pane`` 白玻璃小窗规则（半透白 + 白描边 +
14px 圆角）——它与外层卡片磨砂叠成两层玻璃；3D 预览直接放入外层卡片，配套预览玻璃 / 边框
颜色常量已从 constants.py 移除，本全局表不再保留该选择器。其余控件 QSS 规则不变。

v1.2.4.3：3D 预览背景透明由 ``skin_preview.py`` 的 GL alpha 缓冲 + 透明背景属性 +
``WA_AlwaysStackOnTop`` 合成顺序开关 + 透明清屏实现，本全局表不新增 / 改动任何预览控件背景
规则；卡片、侧栏磨砂与其余控件 QSS 规则不变。

v1.2.4.4：仅标题栏最小化 / 关闭两个按钮由 ``TitleCircleButton`` 自绘、收进
``TitleButtonGroup`` 成组浅玻璃框，本全局表新增一条 ``QFrame#titleButtonGroup`` 透明规则；
离线 / 正版分段、开始游戏主按钮、导航项、卡片与侧栏外观全部沿用 v1.2.4.3 旧 QSS 不改动；
六个按钮的橡皮筋拉扯 + 松开弹簧回弹动画由 ``spring_button.py`` 控制器在绘制层驱动，不在
本样式表内改色、改圆角、改几何。

v1.2.4.5：导航 ``navItem``、分段 ``modeButton``、主按钮 ``primaryButton`` 三组规则统一改为
iOS 白色半透明胶囊：默认白玻璃细亮边、深色字，hover 略亮；选中态（``navActive`` /
``modeActive``）只用更亮填充 + 亮描边 + 加粗深色字区分，删除旧蓝色渐变、蓝边与蓝字；主按钮
文字由白色改为深色、填充改白玻璃，固定 44×146 与圆角 22 几何保留。输入框、下拉、进度条、
登录弹窗按钮等规则不在本轮范围，保持既有数值不变。

v1.2.4.6：返工收窄透明范围——只有这六个功能键走下面三组按钮规则的半透明玻璃；背景、卡片、
侧栏、进度条、输入框、下拉、登录弹窗按钮等其余规则全部回退 v1.2.4.5 基线，不做整窗 / 全页面
模糊毛玻璃。六按钮填充透明度按真实窗口像素明度差下调；主按钮 ``primaryButton`` 单独引用
``COLOR_BTN_GLASS_PRIMARY`` 一组更淡的填充与描边（身后是较暗浅蓝壁纸 / 罩层，不与导航、
分段共用一档白），hover / pressed 各有专用档，不再压成不透明白板。

主按钮填充沿用玻璃蓝 + 顶部白光三段通透渐变与同系浅蓝细边，明度差维持可辨但不浮凸的
区间，不退回闷实蓝块。选中态、输入框等其余控件沿用既有达标数值，不回退。

v1.2.5.1：按 PCL 式参考骨架重构五导航，参考图标签 + 卡片布局归属「下载」页。
新增分类标签 ``categoryTab`` / ``categoryActive`` 六标签等宽横排规则；版本卡片
``versionCard`` 容器由 ``VersionCard.paintEvent`` 自绘片内局部磨砂、QSS 只关闭原生
背景边框，文字 ``versionCardText`` / ``versionCardTopText`` 居中加粗；导航项内部改为
图标标签 + 文字标签布局，``navText`` 默认 / ``navActive`` 两态规则，选中态隐藏图标只留
加粗文字；``download-page`` / ``placeholder-page`` 容器透明。配色全部沿用既有浅蓝白
iOS 玻璃体系，不新增不透明实色块；「启动」个人页控件规则原样保留、不删除。

v1.2.7.1：下载页五卡片改为可折叠分组手风琴，旧 ``versionCard`` 系列选择器移除，替换为
``versionSection`` 容器、``sectionHeader`` 标题横条、``sectionTitle`` 分组名、
``sectionArrow`` 折叠箭头、``versionRow`` 条目行、``versionRowIcon / versionRowTitle /
versionRowSubtitle`` 规则；色值复用既有普通档 / 置顶档两组版本分组磨砂，不新增色值。

v1.2.8.1：补 ``#download-container`` 与滚动视口透明规则，修复四条收起横条下方被拉伸
填满的不透明留白白板；四分组条目联网回填代表版本号与日期，选择器 / 色值沿用 v1.2.7.1。

v1.2.10.0：下载页四个全量分组横条最左侧补分类方块图标 ``sectionHeaderIcon``，每条版本条目
左侧补分组小方块 ``versionEntryIcon``（分组内共享同一张缩放贴图）；新增非模态淡入淡出更新
提示窗 ``updateNoticePopup`` 面板 / 标题 / 说明 / 变化行 / 确认按钮规则。清单本地缓存与后台
检查线程逻辑不在样式表内，不新增不透明实色块。

v1.2.11.0：全局所有滚动条（``page-scroll`` / ``section-scroll`` / 个人页版本列表及任意
``QScrollArea``）收窄为极细透明小竖线——轨道透明、无箭头、无粗滑块；下载页每条版本右侧
``versionDownloadBtn`` 下载按钮与「已安装」禁用态；单例下载浮层 ``downloadPanel`` 展开大面板 /
收起小胶囊两套形态、左侧三统计、右侧五步清单（done / running / pending / skipped 四态着色）
与底部细进度条；个人页 ``versionOption`` 两行滚轮已安装版本选项与占位提示。面板片内磨砂由
``download_panel.py`` 的 paintEvent 自绘，QSS 只关闭原生背景边框、控制文字与行内控件外观。

v1.2.9.2：下载页退出崩溃、视口固定高度、清单重试与分批坐标修复未新增 / 改动任何 QSS
选择器与色值，样式规则沿用 v1.2.9.1 基线。

v1.2.9.1：四分组由单条代表版本改为全量分类列表，新增 ``section-scroll`` 组内独立滚动
区透明规则、``versionEntry`` 轻量玻璃条目行、``versionEntryTitle / versionEntryTime``
文字、``sectionCount`` 计数与 ``sectionPlaceholder`` 占位样式；最新两行 ``versionRow``
规则原样保留。
"""
from .. import constants as C


def global_stylesheet() -> str:
    """应用到 QApplication 的全局样式表。"""
    return f"""
    QWidget {{
        color: {C.COLOR_TEXT};
        font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
        font-size: 14px;
        /* v1.3.9.2：全局清除焦点虚线框（点状描边方块）。 */
        outline: none;
    }}

    /* 个人页滚动容器与内容容器：透明底、无边框；样式统一走全局表，
       避免在容器本地 setStyleSheet 切断后代按钮的属性选择器规则。 */
    QScrollArea#page-scroll {{
        background: transparent;
        border: none;
    }}
    QWidget#page-container {{
        background: transparent;
    }}
    QWidget#title-bar {{
        background: transparent;
    }}

    /* 根窗口背景不再由 QSS 绘制不透明渐变：v1.2.4.0 起整窗背景（默认渐变回退 /
       外部清晰壁纸 cover 铺满）由最底层 BackgroundLayer 自绘；v1.2.4.1 起卡片 / 侧栏
       局部磨砂由各自 paintEvent 自绘，根容器保持透明。 */
    QWidget#root {{
        background: transparent;
        border-radius: 18px;
    }}

    /* 左侧导航栏与通用卡片：v1.2.4.1 起背景、圆角、描边全部由各自 paintEvent 自绘片内
       局部磨砂（见 card_widget.py / nav_sidebar.py / frosted_backdrop.py），这里只关闭
       QSS 原生背景与边框，避免再叠一层白渐变把磨砂块压成白板。圆角半径在自绘路径内控制。 */
    QFrame#sidebar {{
        background: transparent;
        border: none;
    }}

    QFrame#card {{
        background: transparent;
        border: none;
    }}

    /* 标题栏：最小化 / 关闭两个 iOS 白色圆形凸起按钮由 TitleCircleButton 自绘（白底圆 +
       浅描边 + 底部柔和投影 + 符号），成组浅玻璃圆角框由 TitleButtonGroup 自绘；这里只
       保证容器与按钮背景透明、不留 QSS 直角方块，外形不在 QSS 内绘制。 */
    QFrame#titleButtonGroup {{
        background: transparent;
        border: none;
    }}

    /* 侧边导航项：v1.2.5.1 起按钮内部为「图标标签 + 文字标签」水平布局，左右内边距由
       内部 QHBoxLayout 控制，这里 QSS padding 置 0，避免双重挤压；选中态隐藏图标、
       只保留加粗文字（图标显隐由 NavItem.set_active 切换）。 */
    QPushButton[navItem="true"] {{
        text-align: left;
        padding: 0px;
        border: 1px solid {C.COLOR_BTN_BORDER};
        border-radius: {C.NAV_ITEM_RADIUS}px;
        background: {C.COLOR_BTN_GLASS};
        font-size: 15px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[navItem="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_HOVER};
    }}
    QPushButton[navItem="true"][navActive="true"] {{
        background: {C.COLOR_BTN_GLASS_ACTIVE};
        border: 1px solid {C.COLOR_BTN_BORDER_ACTIVE};
        color: {C.COLOR_TEXT};
        font-weight: 600;
    }}
    /* 导航项内部文字标签：默认浅色深字，选中加粗；图标在选中态由代码隐藏。 */
    QLabel[navText="true"] {{
        font-size: 15px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[navText="true"][navActive="true"] {{
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}

    /* 输入框：通透磨砂玻璃 */
    QLineEdit {{
        background: {C.COLOR_FIELD_GLASS};
        border: 1px solid {C.COLOR_FIELD_BORDER};
        border-radius: 10px;
        padding: 7px 11px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QLineEdit:hover {{
        background: {C.COLOR_FIELD_GLASS_HOVER};
    }}
    QLineEdit:focus {{
        border: 1px solid {C.COLOR_PRIMARY};
        background: rgba(255,255,255,150);
    }}

    /* 账号模式分段按钮：离线 / 正版（1.2.2.0 起正版可点击进入设备码登录）。
       v1.2.4.6 与导航 / 主按钮同属六个半透明玻璃功能键；选中态只靠更亮填充 + 亮边 +
       加粗深色字区分，不再用蓝色渐变与蓝字；拉扯回弹动画由 SpringPushButton 控制器驱动。 */
    QPushButton[modeButton="true"] {{
        background: {C.COLOR_BTN_GLASS};
        border: 1px solid {C.COLOR_BTN_BORDER};
        border-radius: 12px;
        padding: 8px 14px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[modeButton="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_HOVER};
    }}
    QPushButton[modeButton="true"][modeActive="true"] {{
        background: {C.COLOR_BTN_GLASS_ACTIVE};
        border: 1px solid {C.COLOR_BTN_BORDER_ACTIVE};
        color: {C.COLOR_TEXT};
        font-weight: 600;
    }}
    QPushButton[modeButton="true"]:disabled {{
        background: rgba(255,255,255,66);
        color: rgba(109,138,156,140);
        border: 1px dashed rgba(255,255,255,88);
    }}

    /* 概览四个内容计数 chip：非白板玻璃片，填充更透，靠细边与 hover 保持可点感。 */
    QPushButton[countButton="true"] {{
        background: {C.COLOR_COUNT_CHIP_GLASS};
        border: 1px solid {C.COLOR_COUNT_CHIP_BORDER};
        border-radius: 12px;
        padding: 8px 14px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[countButton="true"]:hover {{
        background: {C.COLOR_COUNT_CHIP_HOVER};
        border: 1px solid {C.COLOR_COUNT_CHIP_BORDER_HOVER};
    }}
    QPushButton[countButton="true"]:pressed {{
        background: {C.COLOR_COUNT_CHIP_PRESSED};
    }}

    /* 开始游戏主按钮：固定 44px 高、146px 宽、不参与水平拉伸，两端正半圆胶囊；
       v1.2.4.6 为六个半透明玻璃功能键之一，单独引用更淡的 PRIMARY 专用色，深色加粗字，
       细亮边勾轮廓；radius 严格等于固定高度一半（44 / 2 = 22），各状态保持同一数值。
       拉扯回弹动画由 SpringPushButton 控制器驱动。 */
    QPushButton[primaryButton="true"] {{
        background: {C.COLOR_BTN_GLASS_PRIMARY};
        color: {C.COLOR_TEXT};
        border: 1px solid {C.COLOR_BTN_BORDER_PRIMARY};
        border-radius: 22px;
        padding: 0px 18px;
        font-size: 15px;
        font-weight: 600;
    }}
    QPushButton[primaryButton="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_PRIMARY_HOVER};
        border: 1px solid {C.COLOR_BTN_BORDER_PRIMARY_HOVER};
    }}
    QPushButton[primaryButton="true"]:pressed {{
        background: {C.COLOR_BTN_GLASS_PRIMARY_PRESSED};
        border: 1px solid {C.COLOR_BTN_BORDER_PRIMARY};
    }}
    QPushButton[primaryButton="true"]:disabled {{
        background: rgba(255,255,255,96);
        color: rgba(109,138,156,150);
        border: 1px solid rgba(255,255,255,120);
        border-radius: 22px;
    }}

    /* 弹窗主按钮（确定 / 知道了）：与弹窗取消按钮同高（36）、同圆角（12），仅靠略亮填充 +
       深色加粗字区分主操作。不套用主窗口 44 高 / 圆角 22 的胶囊规则——Qt 在 border-radius
       超过控件半高时会丢弃圆角（36 高半高为 18，配 22 会被渲染成方形），故弹窗单独定义。 */
    QPushButton[dialogPrimary="true"] {{
        background: {C.COLOR_BTN_GLASS_PRIMARY};
        color: {C.COLOR_TEXT};
        border: 1px solid {C.COLOR_BTN_BORDER_PRIMARY};
        border-radius: 12px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton[dialogPrimary="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_PRIMARY_HOVER};
        border: 1px solid {C.COLOR_BTN_BORDER_PRIMARY_HOVER};
    }}
    QPushButton[dialogPrimary="true"]:pressed {{
        background: {C.COLOR_BTN_GLASS_PRIMARY_PRESSED};
    }}
    QPushButton[dialogPrimary="true"]:disabled {{
        background: rgba(255,255,255,96);
        color: rgba(109,138,156,150);
        border: 1px solid rgba(255,255,255,120);
        border-radius: 12px;
    }}

    /* 进度条（原生实例兜底；主进度条为自绘 CapsuleProgressBar，不走本块 chunk 绘制）：
       通透凹槽玻璃轨道 + 低不透明玻璃蓝填充；满格也不压成实色贴图。 */
    QProgressBar {{
        background: {C.COLOR_BAR_TRACK};
        border: 1px solid {C.COLOR_BAR_BORDER};
        border-radius: 9px;
        height: 18px;
        text-align: center;
        color: {C.COLOR_TEXT};
        font-size: 12px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {C.COLOR_CHUNK_LEFT},
                                    stop:1 {C.COLOR_CHUNK_RIGHT});
        border-radius: 9px;
        margin: 1px;
    }}

    QLabel[cardTitle="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QLabel[cardValue="true"] {{
        font-size: 18px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    /* 个人页游玩统计（左列统计卡内纵向竖列）：每行左侧小标签、右侧大数值，自上而下
       依次为总游戏时长 / 启动次数 / 最近游玩，沿用通透玻璃配色，不凸出 */
    QLabel[statValue="true"] {{
        font-size: 22px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QLabel[statLabel="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QLabel[statValueDate="true"] {{
        font-size: 15px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}

    /* 游戏版本占位下拉：全页仅主体下方独立通长一行一条，置灰不可点，通透玻璃观感与
       输入框一致；本轮仅占位，真实版本列表后续接入。 */
    QComboBox[versionPicker="true"] {{
        background: {C.COLOR_FIELD_GLASS};
        border: 1px dashed {C.COLOR_FIELD_BORDER};
        border-radius: 10px;
        padding: 6px 11px;
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QComboBox[versionPicker="true"]:disabled {{
        background: rgba(255, 255, 255, 66);
        color: rgba(109, 138, 156, 140);
        border: 1px dashed rgba(127, 196, 232, 88);
    }}
    QComboBox[versionPicker="true"]::drop-down {{
        border: none;
        width: 22px;
    }}
    /* v1.3.20.3 自定义磨砂下拉面板内的透明列表：背景由 Card 磨砂承载，只画 item */
    QListView[comboView="true"] {{
        background: transparent;
        border: none;
        outline: none;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QListView[comboView="true"]::item {{
        background: transparent;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 20px;
    }}
    QListView[comboView="true"]::item:hover {{
        background: rgba(255, 255, 255, 130);
    }}
    QListView[comboView="true"]::item:selected {{
        background: {C.COLOR_PRIMARY_GLASS_TOP};
        color: {C.COLOR_TEXT};
    }}
    QLabel[hintLabel="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        line-height: 150%;
    }}
    QLabel[pageTitle="true"] {{
        font-size: 19px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
    }}

    /* 微软正版登录弹窗：无边框悬浮玻璃面板，与主窗口苹果风通透质感统一。
       窗口根容器透明（圆角外不填系统灰底），内部 dialogPanel 画三段亮白玻璃 +
       20px 大圆角 + 同系细亮边；浮层面板比卡片更不透明一点，叠在任意背景上都干净不发灰。 */
    QDialog[dialogRoot="true"] {{
        background: transparent;
        border: none;
    }}
    QFrame#dialogPanel {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 rgba(255, 255, 255, 250),
                                    stop:0.45 rgba(255, 255, 255, 244),
                                    stop:1 rgba(255, 255, 255, 238));
        border: 1px solid {C.COLOR_CARD_BORDER};
        border-radius: 20px;
    }}
    QWidget[dialogTitleBar="true"] {{
        background: transparent;
    }}
    QLabel[dialogTitleText="true"] {{
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[dialogClose="true"] {{
        background: transparent;
        border: none;
        border-radius: 10px;
        color: {C.COLOR_TEXT_LIGHT};
        font-size: 14px;
    }}
    QPushButton[dialogClose="true"]:hover {{
        background: rgba(255,255,255,110);
        color: {C.COLOR_TEXT};
    }}
    QPushButton[dialogClose="true"]:pressed {{
        background: rgba(255,255,255,70);
    }}
    QLabel[dialogTitle="true"] {{
        font-size: 18px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
    }}
    QLabel[dialogHint="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        line-height: 150%;
    }}
    QLabel[dialogLink="true"] {{
        font-size: 13px;
        padding: 2px 0;
    }}
    QLabel[dialogLink="true"] a {{
        color: {C.COLOR_PRIMARY};
    }}
    QLabel[dialogLink="true"] a:hover {{
        color: {C.COLOR_PRIMARY_DARK};
    }}
    QLabel[deviceCode="true"] {{
        font-family: Consolas, "Courier New", monospace;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: 4px;
        color: {C.COLOR_TEXT};
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 rgba(255,255,255,150),
                                    stop:1 rgba(255,255,255,88));
        border: 1px solid {C.COLOR_FIELD_BORDER};
        border-radius: 16px;
        padding: 18px 14px;
        margin: 4px 0;
    }}
    QLabel[dialogStatus="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        min-height: 22px;
    }}
    QLabel[dialogStatus="true"][statusOk="true"] {{
        color: #2E9E63;
        font-weight: 600;
    }}
    QLabel[dialogStatus="true"][statusError="true"] {{
        color: #D2564B;
    }}
    QPushButton[dialogButton="true"] {{
        background: {C.COLOR_FIELD_GLASS};
        border: 1px solid {C.COLOR_FIELD_BORDER};
        border-radius: 18px;
        height: 36px;
        padding: 0px 24px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[dialogButton="true"]:hover {{
        background: {C.COLOR_FIELD_GLASS_HOVER};
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
    }}
    QPushButton[dialogButton="true"]:pressed {{
        background: rgba(255,255,255,70);
    }}

    /* 个人页正版账号信息：UUID 小字与退出登录文字按钮 */
    QLabel[uuidLabel="true"] {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        font-family: Consolas, "Courier New", monospace;
    }}
    QPushButton[logoutButton="true"] {{
        background: transparent;
        border: none;
        color: #D2564B;
        font-size: 12px;
        padding: 2px 4px;
    }}
    QPushButton[logoutButton="true"]:hover {{
        text-decoration: underline;
    }}

    /* ---- v1.2.7.1 PCL 式下载页骨架：分类标签 + 可折叠版本分组 + 通用占位页 ---- */
    QWidget#download-page, QWidget#placeholder-page {{
        background: transparent;
    }}

    /* v1.2.8.1 白板修复：下载页内容容器与滚动视口显式透明。旧版 #download-container
       没有对应 QSS 规则，保留 Qt 默认自动填充的不透明浅灰，被 widgetResizable 拉伸到
       整个视口高度后在四条收起横条下方压出一大块不透明白板；与个人页 #page-container
       对齐，这里同样关闭原生背景填充，留白处透出底层背景层。 */
    QWidget#download-container {{
        background: transparent;
    }}
    QScrollArea#page-scroll > QWidget {{
        background: transparent;
        border: none;
    }}

    /* 顶部分类标签（原版游戏 / mod / 整合包 / 光影包 / 资源包 / 数据包）：六标签等宽横排，
       默认通透白玻璃细边浅色字，hover 略亮，选中态更亮填充 + 亮边 + 加粗深色字；本轮
       点击只切换视觉选中态，不接真实分类拉取。 */
    QPushButton[categoryTab="true"] {{
        background: {C.COLOR_TAB_GLASS};
        border: 1px solid {C.COLOR_TAB_BORDER};
        border-radius: {C.SETTINGS_TAB_RADIUS}px;
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        padding: 0px {C.SETTINGS_TAB_PADDING_X}px;
    }}
    QPushButton[categoryTab="true"]:hover {{
        background: {C.COLOR_TAB_GLASS_HOVER};
    }}
    QPushButton[categoryTab="true"][categoryActive="true"] {{
        background: {C.COLOR_TAB_GLASS_ACTIVE};
        border: 1px solid {C.COLOR_TAB_BORDER_ACTIVE};
        color: {C.COLOR_TEXT};
        font-weight: 600;
    }}

    /* v1.2.10.0 分组横条最左侧分类方块图标；横条 / 面板 / 最新两行条目背景由自绘接管，
       QSS 只关闭原生背景与边框。 */
    QFrame#versionSection, QFrame#sectionHeader, QFrame#versionRow {{
        background: transparent;
        border: none;
    }}
    QLabel[sectionHeaderIcon="true"], QLabel[versionEntryIcon="true"] {{
        background: transparent;
        border: none;
    }}
    QLabel[sectionTitle="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QFrame#versionSection[sectionOpen="true"] QLabel[sectionTitle="true"] {{
        font-weight: 600;
    }}
    QLabel[sectionArrow="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        min-width: 16px;
    }}
    QLabel[versionRowIcon="true"] {{
        background: transparent;
        border: none;
    }}
    QLabel[versionRowTitle="true"] {{
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[versionRowSubtitle="true"] {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.2.12.0 全量分组：轻量玻璃条目行（组内第二条滚动条已移除，仅外层一条细滚动条） ---- */
    QWidget#section-list-container {{
        background: transparent;
    }}
    QLabel[sectionCount="true"] {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        min-width: 48px;
    }}
    QLabel[sectionPlaceholder="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        padding: 14px 0px;
    }}
    QFrame#versionEntry {{
        background: rgba(255, 255, 255, 84);
        border: 1px solid rgba(255, 255, 255, 110);
        border-radius: 10px;
    }}
    QLabel[versionEntryTitle="true"] {{
        font-size: 12px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[versionEntryTime="true"] {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.2.10.0 新版本提示小弹窗：面板由 paintEvent 自绘圆角玻璃，QSS 只关原生背景 ---- */
    QFrame#updateNoticePopup, QFrame#updateNoticeRow, QLabel[updateNoticeRowIcon="true"] {{
        background: transparent;
        border: none;
    }}
    QLabel[updateNoticeTitle="true"] {{
        font-size: 16px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[updateNoticeHint="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        line-height: 150%;
    }}
    QLabel[updateNoticeRowLabel="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[updateNoticeRowVersion="true"] {{
        font-size: 13px;
        font-weight: 600;
        color: {C.COLOR_PRIMARY};
        background: transparent;
        border: none;
    }}
    QPushButton#updateNoticeOk {{
        font-size: 13px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: rgba(255, 255, 255, 150);
        border: 1px solid rgba(190, 222, 238, 150);
        border-radius: 17px;
        padding: 0px 22px;
    }}
    QPushButton#updateNoticeOk:hover {{
        background: rgba(255, 255, 255, 190);
    }}
    QPushButton#updateNoticeOk:pressed {{
        background: rgba(222, 238, 248, 190);
    }}

    /* ---- v1.2.12.9 滚动条完全透明：占位置但看不见，避免 AlwaysOn 后白色边边 ----
       v1.3.9.2：设置页滚动条已 ScrollBarAlwaysOff 彻底隐藏；水平规则见下方删除说明。 */
    QScrollBar:vertical {{
        background: transparent;
        width: {C.SCROLLBAR_THICKNESS}px;
        margin: 0px;
        border: none;
    }}
    QScrollBar:vertical::handle {{
        background: transparent;
        border: none;
        min-height: {C.SCROLLBAR_MIN_LENGTH}px;
    }}
    QScrollBar:vertical::handle:hover {{
        background: transparent;
    }}
    QScrollBar:vertical::add-line, QScrollBar:vertical::sub-line {{
        height: 0px;
        background: none;
        border: none;
    }}
    QScrollBar:vertical::add-page, QScrollBar:vertical::sub-page {{
        background: transparent;
    }}
    /* v1.3.9.2：通用水平滚动条规则全部删除——Qt 样式表解析器在同时存在水平
       ::handle 规则时会让垂直滚动条的 width 规则失效（退回原生 22px 宽滑块）；
       工程内所有 QScrollArea 水平策略均为 ScrollBarAlwaysOff，水平规则无实例。 */

    /* ---- v1.2.11.0 下载页每条版本右侧下载按钮；已安装置灰禁用显示「已安装」 ---- */
    QPushButton#versionDownloadBtn {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(190, 222, 238, 128);
        border-radius: 12px;
        font-size: 12px;
        color: {C.COLOR_TEXT};
        padding: 0px 10px;
    }}
    QPushButton#versionDownloadBtn:hover {{
        background: rgba(255, 255, 255, 134);
        border: 1px solid rgba(190, 222, 238, 170);
    }}
    QPushButton#versionDownloadBtn:disabled {{
        background: rgba(255, 255, 255, 46);
        border: 1px dashed rgba(127, 196, 232, 84);
        color: rgba(109, 138, 156, 132);
    }}

    /* ---- v1.2.11.0 单例下载状态浮层：面板片内磨砂由 paintEvent 自绘，QSS 只关原生背景 ---- */
    QFrame#downloadPanel, QFrame#downloadPanelExpanded, QFrame#downloadPanelCollapsed {{
        background: transparent;
        border: none;
    }}
    QLabel#downloadPanelTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QPushButton#downloadPanelCollapseBtn {{
        background: rgba(255, 255, 255, 70);
        border: none;
        border-radius: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        font-size: 15px;
    }}
    QPushButton#downloadPanelCollapseBtn:hover {{
        background: rgba(255, 255, 255, 120);
        color: {C.COLOR_TEXT};
    }}
    /* v1.2.12.0 展开态底部居中大叉：取消当前下载任务（区别于右上小 X 仅收起面板）。 */
    QPushButton#downloadPanelCancelBtn {{
        background: rgba(232, 96, 86, 34);
        border: 1px solid rgba(232, 96, 86, 96);
        border-radius: 20px;
        color: #D2564B;
        font-size: 18px;
        font-weight: 700;
    }}
    QPushButton#downloadPanelCancelBtn:hover {{
        background: rgba(232, 96, 86, 58);
        border: 1px solid rgba(232, 96, 86, 140);
    }}
    QPushButton#downloadPanelCancelBtn:pressed {{
        background: rgba(232, 96, 86, 78);
    }}
    QLabel#downloadPanelStatCaption {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel#downloadPanelPercent {{
        font-size: 22px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel#downloadPanelSpeed, QLabel#downloadPanelRemain {{
        font-size: 15px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QFrame#downloadStepRow {{
        background: transparent;
        border: none;
    }}
    QLabel#downloadStepIcon {{
        background: transparent;
        border: none;
        font-size: 13px;
    }}
    QLabel#downloadStepText {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel#downloadStepIcon[stepState="done"], QLabel#downloadStepText[stepState="done"] {{
        color: #2E9E63;
    }}
    QLabel#downloadStepText[stepState="done"] {{
        color: {C.COLOR_TEXT};
    }}
    QLabel#downloadStepIcon[stepState="running"], QLabel#downloadStepText[stepState="running"] {{
        color: {C.COLOR_PRIMARY};
        font-weight: 600;
    }}
    QLabel#downloadStepIcon[stepState="pending"], QLabel#downloadStepText[stepState="pending"] {{
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QLabel#downloadStepIcon[stepState="skipped"], QLabel#downloadStepText[stepState="skipped"] {{
        color: rgba(109, 138, 156, 110);
    }}
    QProgressBar#downloadPanelBar {{
        background: rgba(255, 255, 255, 44);
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar#downloadPanelBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {C.COLOR_CHUNK_LEFT},
                                    stop:1 {C.COLOR_CHUNK_RIGHT});
        border-radius: 3px;
        margin: 0px;
    }}
    QLabel#downloadCollapsedIcon {{
        font-size: 13px;
        color: {C.COLOR_PRIMARY};
        background: transparent;
        border: none;
    }}
    QLabel#downloadCollapsedName {{
        font-size: 12px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel#downloadCollapsedPercent {{
        font-size: 12px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.2.12.21 个人页版本选择手风琴横条 ---- */
    QPushButton[versionAccordionHeader="true"] {{
        background: transparent;
        border: none;
        text-align: left;
    }}
    QPushButton[versionAccordionHeader="true"]:hover {{
        background: rgba(255, 255, 255, 30);
    }}
    QLabel[versionCurrentLabel="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[versionArrow="true"] {{
        font-size: 16px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.2.11.0 个人页两行滚轮已安装版本列表 ---- */
    QScrollArea#version-list-scroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#version-list-scroll > QWidget {{
        background: transparent;
        border: none;
    }}
    QWidget#version-list-container {{
        background: transparent;
    }}
    /* 版本选择列表单独的可见滑块：覆盖全局透明滚动条，苹果风半透明圆角、不抢视线 */
    QScrollArea#version-list-scroll QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px 1px;
        border: none;
    }}
    QScrollArea#version-list-scroll QScrollBar:vertical::handle {{
        background: rgba(120, 150, 170, 120);
        border-radius: 3px;
        min-height: 26px;
    }}
    QScrollArea#version-list-scroll QScrollBar:vertical::handle:hover {{
        background: rgba(100, 130, 150, 175);
    }}
    QScrollArea#version-list-scroll QScrollBar:vertical::add-line,
    QScrollArea#version-list-scroll QScrollBar:vertical::sub-line {{
        height: 0px;
        background: none;
        border: none;
    }}
    QScrollArea#version-list-scroll QScrollBar:vertical::add-page,
    QScrollArea#version-list-scroll QScrollBar:vertical::sub-page {{
        background: transparent;
    }}
    QPushButton[versionOption="true"] {{
        background: rgba(255, 255, 255, 84);
        border: 1px solid rgba(255, 255, 255, 104);
        border-radius: 10px;
        text-align: left;
        padding: 0px 12px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[versionOption="true"]:hover {{
        background: rgba(255, 255, 255, 112);
    }}
    QPushButton[versionOption="true"]:checked {{
        background: {C.COLOR_PRIMARY_GLASS_TOP};
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}

    /* v1.3.17.0 账号管理：多账号条目行 / 类型标签 / 当前标记 */
    QPushButton[accountRow="true"] {{
        background: rgba(255, 255, 255, 84);
        border: 1px solid rgba(255, 255, 255, 104);
        border-radius: 10px;
        text-align: left;
        padding: 0px 10px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[accountRow="true"]:hover {{
        background: rgba(255, 255, 255, 112);
    }}
    QPushButton[accountRow="true"]:checked {{
        background: {C.COLOR_PRIMARY_GLASS_TOP};
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
    }}
    QLabel[accountName="true"] {{
        font-size: 13px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QLabel[accountTag="true"] {{
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 8px;
        background: rgba(162, 207, 233, 46);
        border: 1px solid rgba(118, 178, 212, 40);
        color: {C.COLOR_PRIMARY_DARK};
    }}
    QLabel[accountActiveTag="true"] {{
        font-size: 11px;
        font-weight: 600;
        color: {C.COLOR_PRIMARY};
    }}
    /* v1.3.19.0 账号三点菜单：菜单项 / 分隔线 */
    QPushButton[menuItem="true"] {{
        background: transparent;
        border: none;
        border-radius: 8px;
        text-align: left;
        padding: 7px 12px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[menuItem="true"]:hover {{
        background: rgba(255, 255, 255, 130);
    }}
    QPushButton[menuItem="true"][danger="true"] {{
        color: #e86056;
    }}
    QPushButton[menuItem="true"][danger="true"]:hover {{
        background: rgba(232, 96, 86, 46);
    }}
    QFrame[menuSeparator="true"] {{
        background: rgba(255, 255, 255, 140);
        border: none;
        margin: 4px 8px;
    }}
    QLabel[versionListPlaceholder="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        padding: 10px 0px;
    }}

    /* ---- v1.2.12.0 版本详情页：返回箭头 + 别名输入 + 四加载器卡片 + 底部开始下载胶囊 ---- */
    QWidget#versionDetailView {{
        background: transparent;
    }}
    QPushButton#detailBackBtn {{
        background: rgba(255, 255, 255, 150);
        border: 1px solid rgba(255, 255, 255, 178);
        border-radius: 18px;
        padding: 0px 16px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton#detailBackBtn:hover {{
        background: rgba(255, 255, 255, 186);
    }}
    QLineEdit#detailAliasInput {{
        background: rgba(255, 255, 255, 150);
        border: 1px solid rgba(255, 255, 255, 178);
        border-radius: 12px;
        padding: 0px 14px;
        font-size: 14px;
        color: {C.COLOR_TEXT};
        selection-background-color: {C.COLOR_PRIMARY_GLASS_BORDER};
    }}
    QLineEdit#detailAliasInput:focus {{
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        background: rgba(255, 255, 255, 176);
    }}
    QScrollArea#detail-scroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#detail-scroll > QWidget {{
        background: transparent;
        border: none;
    }}
    QWidget#detailCardHost {{
        background: transparent;
    }}
    QFrame#loaderSection {{
        background: transparent;
        border: none;
    }}
    QFrame#loaderSectionHeader {{
        background: transparent;
        border: none;
        border-radius: 14px;
    }}
    QFrame#loaderSectionHeader[selected="true"] {{
        background: transparent;
        border: none;
    }}
    QFrame#loaderSectionHeader[selected="true"] QLabel#loaderCardTitle {{
        font-weight: 600;
        color: {C.COLOR_PRIMARY};
    }}
    QFrame#loaderSection:disabled QFrame#loaderSectionHeader {{
        background: transparent;
        border: none;
    }}
    QLabel#loaderCardTitle {{
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QFrame#loaderSection:disabled QLabel#loaderCardTitle {{
        color: rgba(109, 138, 156, 128);
    }}
    QLabel#loaderCardStatus {{
        font-size: 12px;
        color: {C.COLOR_PRIMARY};
        background: transparent;
        border: none;
    }}
    QLabel#loaderCardStatus[unavailable="true"] {{
        color: rgba(109, 138, 156, 140);
    }}
    QLabel#loaderCardArrow {{
        font-size: 16px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        min-width: 16px;
    }}
    QFrame#loaderSection:disabled QLabel#loaderCardArrow {{
        color: rgba(109, 138, 156, 90);
    }}
    QWidget#loaderSectionBody {{
        background: transparent;
        border: none;
    }}
    QLabel#loaderVersionCount {{
        font-size: 12px;
        font-weight: 600;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        padding: 4px 6px 0px 6px;
    }}
    QFrame#loaderVersionRow {{
        background: rgba(255, 255, 255, 84);
        border: 1px solid rgba(255, 255, 255, 110);
        border-radius: 10px;
    }}
    QFrame#loaderVersionRow:hover {{
        background: rgba(255, 255, 255, 128);
    }}
    QFrame#loaderVersionRow[selected="true"] {{
        background: rgba(79, 159, 208, 60);
        border: 1px solid {C.COLOR_PRIMARY};
    }}
    QLabel#loaderVersionRowTitle {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QFrame#loaderVersionRow[selected="true"] QLabel#loaderVersionRowTitle {{
        font-weight: 600;
        color: {C.COLOR_PRIMARY};
    }}
    QLabel#loaderVersionRowTime {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QPushButton#detailStartDownloadBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {C.COLOR_CHUNK_LEFT},
                                    stop:1 {C.COLOR_CHUNK_RIGHT});
        border: none;
        border-radius: 22px;
        color: #FFFFFF;
        font-size: 15px;
        font-weight: 700;
        padding: 0px 30px;
    }}
    QPushButton#detailStartDownloadBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {C.COLOR_CHUNK_LEFT},
                                    stop:1 {C.COLOR_CHUNK_RIGHT});
    }}
    QPushButton#detailStartDownloadBtn:pressed {{
        background: rgba(0, 0, 0, 24);
    }}

    /* ---- v1.3.4.0 内容搜索视图：搜索按钮 + 玻璃结果卡片 + 状态提示 ---- */
    QPushButton[contentSearchBtn="true"] {{
        background: {C.COLOR_BTN_GLASS};
        border: 1px solid {C.COLOR_BTN_BORDER};
        border-radius: 12px;
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[contentSearchBtn="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_HOVER};
    }}
    QPushButton[contentSearchBtn="true"]:pressed {{
        background: {C.COLOR_BTN_GLASS_ACTIVE};
    }}
    QPushButton[contentSearchBtn="true"]:disabled {{
        background: rgba(255, 255, 255, 60);
        color: {C.COLOR_TEXT_LIGHT};
        border: 1px solid rgba(255, 255, 255, 90);
    }}

    QScrollArea#content-scroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#content-scroll > QWidget, QWidget#content-container {{
        background: transparent;
    }}

    /* v1.3.8.2：内容卡片背景改由 ContentCard.paintEvent 片内磨砂自绘
       （圆角矩形内只模糊正后方壁纸 + 三段白玻璃高光 + 细亮边），QSS 只留透明与无边框，
       否则会盖一层平涂半透明白、把磨砂糊成纯白片。 */
    QFrame#contentCard {{
        background: transparent;
        border: none;
    }}
    QLabel#contentCardTitle {{
        background: transparent;
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QLabel#contentCardDesc {{
        background: transparent;
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QLabel#contentCardMeta {{
        background: transparent;
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QLabel#contentStatus {{
        background: transparent;
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
    }}

    /* ---- v1.3.5.0 个人页版本横条三点入口 + 版本设置页骨架 ---- */
    /* 三点按钮整体由 paintEvent 自绘（浅玻璃圆 + 三圆点），这里只关掉原生背景与描边。 */
    QPushButton#versionMoreBtn {{
        background: transparent;
        border: none;
        padding: 0px;
    }}

    QWidget#versionSettingsPage, QWidget#vsSectionPage, QWidget#vsStack {{
        background: transparent;
    }}
    QScrollArea#vs-scroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#vs-scroll > QWidget {{
        background: transparent;
        border: none;
    }}

    QPushButton#vsBackBtn {{
        background: rgba(255, 255, 255, 150);
        border: 1px solid rgba(255, 255, 255, 178);
        border-radius: 18px;
        font-size: 15px;
        color: {C.COLOR_TEXT};
        padding: 0px;
    }}
    QPushButton#vsBackBtn:hover {{
        background: rgba(255, 255, 255, 186);
    }}
    QPushButton#vsBackBtn:pressed {{
        background: rgba(255, 255, 255, 128);
    }}

    QLabel[vsTitle="true"] {{
        font-size: 17px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[vsVersionTitle="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel[vsSkeletonChip="true"] {{
        background: rgba(255, 255, 255, 78);
        border: 1px solid rgba(255, 255, 255, 112);
        border-radius: 10px;
        padding: 3px 10px;
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
    }}

    QPushButton[vsNavItem="true"] {{
        background: {C.COLOR_BTN_GLASS};
        border: 1px solid {C.COLOR_BTN_BORDER};
        border-radius: 12px;
        padding: 0px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton[vsNavItem="true"]:hover {{
        background: {C.COLOR_BTN_GLASS_HOVER};
    }}
    QPushButton[vsNavItem="true"]:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {C.COLOR_PRIMARY_GLASS_TOP},
                                    stop:1 {C.COLOR_PRIMARY_GLASS_BOTTOM});
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        font-weight: 700;
        color: {C.COLOR_PRIMARY_DARK};
    }}

    QLabel[vsInfoTitle="true"] {{
        font-size: 16px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel[vsInfoSub="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    QLabel[vsFieldCaption="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    /* 占位下拉：保留玻璃框形态，文字压淡表示不可交互。 */
    QFrame[vsStubField="true"] {{
        background: rgba(255, 255, 255, 118);
        border: 1px solid rgba(255, 255, 255, 150);
        border-radius: 10px;
    }}
    QLabel[vsStubFieldText="true"] {{
        font-size: 13px;
        color: rgba(43, 71, 89, 165);
        background: transparent;
        border: none;
    }}
    QLabel[vsStubFieldChevron="true"] {{
        font-size: 14px;
        color: rgba(109, 138, 156, 170);
        background: transparent;
        border: none;
    }}

    /* 占位按钮：玻璃底 + 淡描边，置灰文字标明本轮不可用。 */
    QPushButton[vsStubButton="true"] {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(255, 255, 255, 132);
        border-radius: 10px;
        padding: 0px 14px;
        font-size: 13px;
        color: rgba(43, 71, 89, 150);
    }}
    QPushButton[vsStubButton="true"]:disabled {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(255, 255, 255, 132);
        color: rgba(43, 71, 89, 150);
    }}

    QLabel[vsHint="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.3.6.0 内容卡片下载入口 + 目标版本选择浮层 ---- */
    QFrame#contentVersionPicker {{
        background: transparent;
        border: none;
        border-radius: 18px;
    }}
    QPushButton#contentCardDownloadBtn {{
        background: rgba(255, 255, 255, 112);
        border: 1px solid rgba(190, 222, 238, 150);
        border-radius: 13px;
        padding: 0px;
        font-size: 12px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QPushButton#contentCardDownloadBtn:hover {{
        background: rgba(255, 255, 255, 168);
    }}
    QPushButton#contentCardDownloadBtn:pressed {{
        background: rgba(255, 255, 255, 96);
    }}
    QPushButton#contentCardDownloadBtn:disabled {{
        background: rgba(255, 255, 255, 70);
        border: 1px solid rgba(255, 255, 255, 110);
        color: rgba(43, 71, 89, 140);
    }}

    QLabel#contentPickerTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel#contentPickerSubtitle {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel#contentPickerFooter {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QScrollArea#contentPickerScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#contentPickerScroll > QWidget, QWidget#contentPickerList {{
        background: transparent;
    }}
    QPushButton#contentPickerClose {{
        background: transparent;
        border: none;
        padding: 0px;
        font-size: 15px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QPushButton#contentPickerClose:hover {{
        color: {C.COLOR_TEXT};
    }}
    QPushButton#contentPickerCancel {{
        background: rgba(255, 255, 255, 120);
        border: 1px solid rgba(255, 255, 255, 160);
        border-radius: 14px;
        padding: 0px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QPushButton#contentPickerCancel:hover {{
        background: rgba(255, 255, 255, 178);
    }}
    QPushButton#contentPickerOk {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {C.COLOR_PRIMARY_GLASS_TOP},
                                    stop:1 {C.COLOR_PRIMARY_GLASS_BOTTOM});
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        border-radius: 14px;
        padding: 0px;
        font-size: 13px;
        font-weight: 700;
        color: {C.COLOR_PRIMARY_DARK};
    }}
    QPushButton#contentPickerOk:hover {{
        background: {C.COLOR_PRIMARY_GLASS_TOP};
    }}

    /* ---- v1.3.7.0 卡片支持版本标签 + 分页栏 ---- */
    QLabel#contentCardVersions {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QFrame#contentPagination {{
        background: transparent;
        border: none;
    }}
    QPushButton#pageNavBtn {{
        background: rgba(255, 255, 255, 120);
        border: 1px solid rgba(255, 255, 255, 160);
        border-radius: 15px;
        padding: 0px 14px;
        font-size: 12px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QPushButton#pageNavBtn:hover {{
        background: rgba(255, 255, 255, 178);
    }}
    QPushButton#pageNavBtn:disabled {{
        background: rgba(255, 255, 255, 70);
        border: 1px solid rgba(255, 255, 255, 110);
        color: rgba(43, 71, 89, 140);
    }}
    QPushButton#pageNumberBtn {{
        background: rgba(255, 255, 255, 112);
        border: 1px solid rgba(190, 222, 238, 150);
        border-radius: 15px;
        padding: 0px;
        font-size: 12px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
    }}
    QPushButton#pageNumberBtn:hover {{
        background: rgba(255, 255, 255, 168);
    }}
    QPushButton#pageNumberBtn:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {C.COLOR_PRIMARY_GLASS_TOP},
                                    stop:1 {C.COLOR_PRIMARY_GLASS_BOTTOM});
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        font-weight: 700;
        color: {C.COLOR_PRIMARY_DARK};
    }}
    QLabel#pageInfo {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel#pageDots {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.3.8.0 卡片加载器标签 ---- */
    QLabel#contentCardLoaders {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}

    /* ---- v1.3.9.0 设置页个性化 ---- */
    QWidget#settings-page, QWidget#personalization-page {{
        background: transparent;
    }}
    QScrollArea#settingsScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#settingsScroll > QWidget, QWidget#settingsList {{
        background: transparent;
    }}
    QLabel[sectionHint="true"] {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
    }}
    QLabel[switchLabel="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
    }}
    /* v1.3.16.0 启动设置页：字段标签 / 多行参数框 / 勾选 / 单选 / 内存条 */
    QLabel[fieldLabel="true"] {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
    }}
    QTextEdit {{
        background: {C.COLOR_FIELD_GLASS};
        border: 1px solid {C.COLOR_FIELD_BORDER};
        border-radius: 10px;
        padding: 7px 11px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QTextEdit:focus {{
        border: 1px solid {C.COLOR_PRIMARY};
        background: rgba(255,255,255,150);
    }}
    QCheckBox, QRadioButton {{
        font-size: 13px;
        color: {C.COLOR_TEXT};
        background: transparent;
        spacing: 8px;
    }}
    QProgressBar#memBar {{
        background: rgba(255, 255, 255, 70);
        border: none;
        border-radius: 6px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar#memBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {C.COLOR_PRIMARY_GLASS_TOP},
                                    stop:1 {C.COLOR_PRIMARY_GLASS_BOTTOM});
        border-radius: 6px;
    }}
    /* 分段单选按钮（玻璃风格 / 品牌四档 / 开关行小按钮共用） */
    QPushButton[segOption="true"] {{
        background: rgba(255, 255, 255, 74);
        border: 1px solid rgba(255, 255, 255, 110);
        border-radius: 10px;
        font-size: 13px;
        color: {C.COLOR_TEXT_LIGHT};
        padding: 6px 10px;
    }}
    QPushButton[segOption="true"]:hover {{
        background: rgba(255, 255, 255, 104);
        color: {C.COLOR_TEXT};
    }}
    QPushButton[segOption="true"]:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {C.COLOR_PRIMARY_GLASS_TOP},
                                    stop:1 {C.COLOR_PRIMARY_GLASS_BOTTOM});
        border: 1px solid {C.COLOR_PRIMARY_GLASS_BORDER};
        color: {C.COLOR_PRIMARY_DARK};
        font-weight: 700;
    }}
    /* 悬停浮现的轻量操作按钮（删除 / 重新添加 / 导入等） */
    QPushButton[ghostAction="true"] {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(255, 255, 255, 140);
        border-radius: 9px;
        font-size: 12px;
        color: {C.COLOR_TEXT};
        padding: 4px 10px;
    }}
    QPushButton[ghostAction="true"]:hover {{
        background: rgba(255, 255, 255, 150);
    }}
    QPushButton[ghostAction="true"][danger="true"]:hover {{
        background: rgba(232, 96, 86, 120);
    }}
    QPushButton[ghostAction="true"]:disabled {{
        background: rgba(255, 255, 255, 46);
        border: 1px solid rgba(255, 255, 255, 70);
        color: rgba(109, 138, 156, 150);
    }}
    /* 壁纸缩略图按钮 */
    QPushButton#wallpaperThumb {{
        background: rgba(255, 255, 255, 74);
        border: 2px solid rgba(255, 255, 255, 120);
        border-radius: 10px;
        padding: 2px;
    }}
    QPushButton#wallpaperThumb:checked {{
        border: 2px solid {C.COLOR_PRIMARY_DARK};
    }}
    QLineEdit#customNameField {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(255, 255, 255, 140);
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 13px;
        color: {C.COLOR_TEXT};
    }}
    QLabel#modpackError {{
        font-size: 11px;
        color: #d9534f;
        background: transparent;
        border: none;
    }}

    /* ---- v1.3.12.0 版本设置：头像选择 / 加载器行 / 展开列表行 / 版本选项 ---- */
    QPushButton#avatarOption {{
        background: rgba(255, 255, 255, 80);
        border: 1px solid rgba(255, 255, 255, 120);
        border-radius: 10px;
        padding: 0px;
    }}
    QPushButton#avatarOption:hover {{
        background: rgba(255, 255, 255, 128);
    }}
    QPushButton#avatarOption:checked {{
        border: 2px solid {C.COLOR_PRIMARY};
        background: rgba(255, 255, 255, 150);
    }}

    QFrame#loaderRow {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(255, 255, 255, 128);
        border-radius: 12px;
    }}
    QFrame#loaderRow[selectable="true"]:hover {{
        background: rgba(255, 255, 255, 132);
    }}
    QFrame#loaderRow[disabledRow="true"] {{
        background: rgba(255, 255, 255, 56);
        border: 1px solid rgba(255, 255, 255, 80);
    }}
    QLabel#loaderRowName {{
        font-size: 14px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel#loaderRowStatus {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QWidget#loaderRowStatusCol {{
        background: transparent;
        border: none;
    }}
    QLabel#loaderRowSub {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QFrame#loaderRow[disabledRow="true"] QLabel#loaderRowName {{
        color: rgba(109, 138, 156, 150);
    }}
    QPushButton#loaderRowRemove {{
        background: transparent;
        border: none;
        font-size: 15px;
        color: {C.COLOR_TEXT_LIGHT};
    }}
    QPushButton#loaderRowRemove:hover {{
        color: #D2564B;
    }}
    QLabel#loaderRowChevron {{
        font-size: 16px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
        min-width: 14px;
    }}

    /* 内容列表弹窗滚动区：透明底+视口透明，避免视口默认不透明背景盖住卡片自绘磨砂。 */
    QScrollArea#contentListScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#contentListScroll > QWidget {{
        background: transparent;
    }}

    /* 进度弹窗阶段列表 / 加载器版本列表：同样让滚动区与视口透明，磨砂才透得出来。 */
    QScrollArea#taskPhaseScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#taskPhaseScroll > QWidget {{
        background: transparent;
    }}
    QScrollArea#mcVersionScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#mcVersionScroll > QWidget {{
        background: transparent;
    }}
    QWidget#loaderRowBody {{
        background: transparent;
        border: none;
    }}
    QFrame#contentRow {{
        background: rgba(255, 255, 255, 84);
        border: 1px solid rgba(255, 255, 255, 110);
        border-radius: 10px;
    }}
    QLabel#contentRowName {{
        font-size: 13px;
        font-weight: 600;
        color: {C.COLOR_TEXT};
        background: transparent;
        border: none;
    }}
    QLabel#contentRowDetail {{
        font-size: 11px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    QLabel#contentRowIcon {{
        background: transparent;
        border: none;
    }}
    QFrame#contentMasterRow {{
        background: rgba(255, 255, 255, 64);
        border: 1px solid rgba(255, 255, 255, 100);
        border-radius: 10px;
    }}
    QPushButton#contentRowDelete {{
        background: rgba(255, 255, 255, 96);
        border: 1px solid rgba(210, 86, 75, 120);
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        color: #D2564B;
    }}
    QPushButton#contentRowDelete:hover {{
        background: rgba(210, 86, 75, 40);
        color: #B8463C;
    }}

    QLabel#vsBusy {{
        font-size: 12px;
        color: {C.COLOR_TEXT_LIGHT};
        background: transparent;
        border: none;
    }}
    """
