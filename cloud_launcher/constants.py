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

"""全局常量：应用名称、版本号、窗口尺寸、默认角色等。

版本号规则：主版本.次版本.功能序号.bug修复号
当前版本：1.3.4.1

v1.3.4.1：下载页顶部间距微调——
- 分类标签行增加顶部留白，六个标签不再紧贴窗口顶；标签与下方内容栈之间增加间距，
  搜索框与原版游戏分组同步下移、不紧贴标签；仅布局间距调整，不改功能与视觉风格。

v1.3.4.0：新增内容搜索与图文展示（只浏览、不下载，内容本体下载后续版本开发）——
- 数据源自 Modrinth 官方 REST（免 API key），覆盖 mod / 整合包 / 光影包 /
  资源包 / 数据包五类 project_type，标题 / 简介 / 作者 / 下载量 / 图标齐全；
- 每个分类视图含搜索框与「搜索」按钮（回车同样触发），结果以两列玻璃卡片
  网格展示，每张卡片必带图片，无图标 / 加载失败用程序化占位图兜底；
- 搜索元数据 JSON 与图标全部落盘到 yd/content_search/ 本地缓存目录，图标复用。

v1.3.3.3：修复 26.x 版本带加载器下载在第 5 步「下载游戏支持库文件」永久卡住
（总进度 99.70%、0 B/s、剩余文件 1、面板一直「进行中…」）——
- 国内镜像源链：新增阿里云 maven 与华为云 maven，库下载候选顺序改为
  阿里云 → BMCL → 华为云 → 官方源，避开官方 libraries.minecraft.net
  「200 后挂住不回数据」的滴灌式限流；
- 分片并发下载：大文件按 Range 分片并发（最多 4 片、全局 2 片并发），单片
  4 次重试与 429 退避，单片长时间无数据即换新连接，8MB 安装器从十几分钟压到十几秒；
- 串行救援：并发池里失败的文件先按指数退避串行重试（最多 3 轮），
  救不回来才中止安装，杜绝「只差最后一个文件」时整批失败；
- 步内进度可信：进度改用 tracker 快照的已完成 / 总数占比（无总数退回字节占比），
  不再出现剩余 1 个文件却停在 99.70% 不动的情况。

v1.3.3.2：修复加载器下载在最后一步「下载游戏支持库文件」约 99.40% 反复失败——
- 库 URL 兼容：无 downloads.artifact.url 时读取库顶层 maven ``url`` 拼接官方地址，
  size/sha1 兼容顶层字段（修复 Fabric 官方 maven 库在 BMCL 404 的问题）；
- 下载整轮重试：download_one 在所有候选源一轮失败后退避重试，配合 .part 断点续传，
  消除官方 piston-data 资源瞬时 404 / 并发抢 BMCL 的误判；
- Forge/NeoForge 版本自动回退：同 MC 前缀从新到旧回退到镜像可用的版本（NeoForge 请求
  21.1.265 自动回退到 21.1.248）；
- Forge 客户端处理器链：新增 forge_install，用本机 Java 运行安装器处理器
  （DOWNLOAD_MOJMAPS / ForgeAutoRenamingTool / binarypatcher），本地生成无发布 URL 的
  ``:client`` 补丁化客户端 Jar 并按 sha1 校验，不再对 404 的 client 工件硬下载。

v1.3.3.1：标题栏去掉品牌 LOGO 与英文全名——
- 自定义标题栏不再显示 LOGO 和 "Cloudy Launcher"，只保留右侧最小化 / 关闭按钮，
  左侧空白区域仍可按住拖动窗口；
- 侧栏品牌区保持 LOGO + "CLY" 不变；关于页 LOGO + 全名 + 版本号不变。

v1.3.3.0：品牌英文改名与关于页重构——
- 全名改为 "Cloudy Launcher"，缩写 / 短名改为 "CLY"（替换原中文「云朵启动器 / 云朵」）；
- 标题栏与窗口标题不再带版本号，统一显示 "Cloudy Launcher"；侧栏品牌区只留 LOGO + "CLY"，
  去掉版本标签；
- 版本号移到关于页：关于页显示 LOGO、全名 "Cloudy Launcher" 与版本号 "Version 1.3.3.0"，
  品牌 / 关于区域全部英文，不写中文；
- 启动页（原个人页）顶部的「个人页」标题删除。

v1.3.2.0：三项真机改造——
- 下载页不再显示「已安装」按钮态：所有版本（含已装）条目按钮恒为「下载」且可点，
  允许对同一版本重复下载；已安装判定保留，用于开始下载时的撞名提示；
- 点「开始下载」时别名对应目录已存在，不再静默自动改名，弹中文提示框
  （「名称已重复，请立刻起名字」）并聚焦别名输入框，用户改成不冲突的新名字后才放行；
- 新增 natives 自动解压（natives_bootstrap）：外部版本 natives 目录为空 / 缺失时，
  从对应的 natives-windows Jar 解压原生库，本地缺失的 Jar 先下载到全局 libraries。

v1.2.12.8：真机反馈下载列表页点分组横条展开仍有「挤压感」——探针实测发现真根因：
build_entries() 对超过 40 条的大分组走分批路径，同步只建第一批 40 条就返回，动画
target_h 只算了 40 条高度；260ms 动画播完后，剩余几百条通过 QTimer 每 0ms 一批冒
出来，每批高度跳一次。改为全部条目同步一次建完（不再分批），动画 target_h 是完整高度；
同时修时序：动画前不再 setMaximumHeight(16M)（那会让父 layout 瞬间撑全高），改为只
放开 minimumHeight，由动画自身从收起态高度平滑长到完整高度。

v1.2.12.7：真机反馈下载列表页点分组横条展开仍有「挤压感，把屏幕挤到那边去了」——
真根因是上几轮动画播错了对象：一直在动画 body.maximumHeight，但 self（整个分组）的
sizeHint() 早已是完整高度，父 layout 在动画开始前就瞬间把分组撑到全高，下面的分组被
猛地推下去（这就是"挤压/挤到那边"），然后 body 才在内部慢慢长出来。改为动画分组自身
self.maximumHeight：收起态锁 _HEADER_HEIGHT，展开时从 _HEADER_HEIGHT 平滑长到
_HEADER_HEIGHT + body 完整高度，父 layout 每一帧按 self.maximumHeight 分配高度，
下面分组平滑下移，不再瞬间挤压。

v1.2.12.6：真机反馈下载列表页点分组横条展开后还是「挤压」感——根因是展开动画播的是空壳
高度：build_entries() 旧版推迟到动画结束后才跑，动画期间 body 里没条目、sizeHint 是 0，
动画一结束条目瞬间全部冒出来。改为动画开始前先 build_entries() 让 sizeHint 是完整高度，
手风琴动画从 0 平滑长到完整高度；动画时长 160→260ms。

v1.2.12.5：详情页加载器横条展开版本列表加 maximumHeight 手风琴动画，消除瞬间顶出感。

v1.2.12.4：真机实拍反馈下载页手风琴分组「收起时横条磨砂 OK，一点开下面整块变成不透明白板」——
展开态 paintEvent 误切了「置顶档」更白的 TOP_GLASS 色（top alpha=186），叠在片内磨砂上接近
不透明，把底下壁纸卡通人物全糊死。展开 / 收起统一改回普通半透磨砂色（150/92/54），整块都能
透出壁纸，不再顶出一块白边。

v1.2.12.3：真机反馈下载页右侧滚动条（"推来推去那个轮"）还是太粗，要求越细越好——
- 全局滚动条厚度由 3px 压到 2px 发丝线，滑块最小长度 28→22；
- 滑块平时白色不透明度 96→55（几乎隐形、不挡壁纸），hover 才提到 110；轨道 / 箭头保持透明。

v1.2.12.2：修复 26.3 详情页在用户自换壁纸之上看不清、下载面板点不开 / 找不到取消、
总进度长时间卡住不动四项真机反馈——
- 详情页每个加载器分组卡片与候选版本行改为片内局部磨砂（毛玻璃）自绘背板，压在高饱和
  壁纸大字与卡通插画之上保证标题 / 版本号可读；版本别名输入框、返回箭头提高白片不透明度；
- 下载面板 5 秒空闲自动收起为右下角小胶囊后，点击小胶囊现在会重新铺开面板（旧版漏接
  收起态点击，用户点小入口无反应、进而找不到取消按钮）；
- 下载步内全局百分比改为按实时已完成文件 / 字节进度回填加权进度，不再等整批下载完成才
  一次性跳到下一档，库 / 资源 / 加载器库下载期间总进度平滑推进；
- 取消下载链路（大叉 → 中断请求 → 半成品清理）保持 v1.2.12.0 既有实现，收起态重新展开
  后即可看到取消入口。

v1.2.12.1：修复 26.3 等新年度版本号在详情页被误判「暂时没有这个版本的加速器」、
卡片置灰点不动的问题——
- Fabric 支持性判定改为「loader 列表非空 + profile/json 真实拉取成功」，不再用
  intermediary.version 严格等值（新体系该字段为 0.0.0 占位，会把真实支持的版本误杀）；
- NeoForge 匹配在旧「前缀 ↔ MC 版本」映射表之外，补充新年度版本号同名直配规则
  （26.3 ↔ NeoForge 26.3.x），快照号不做同名匹配；
- 加载器支持性缓存 schema 升到 2，旧版本落盘的误判缓存自动作废重建；
- 详情页卡片内文字标签鼠标事件穿透到卡片本体，点在版本号 / 状态文字上也能选中；
  可用卡片右侧同时展示具体加载器版本号。

v1.2.12.0：下载链路从「版本 JSON + 客户端 Jar」两步骨架扩展为完整安装编排——
- 版本详情页：点条目先进详情视图（返回箭头 + 版本别名输入框 + Forge / NeoForge / Fabric /
  OptiFine 四张加载器卡片 + 底部开始下载胶囊），自动探测该 MC 版本对四个加载器的支持性，
  不支持 / 查不到对应版本的卡片置灰并显示「暂时没有这个版本的加速器」；探测结果按 MC 版本
  缓存到 ``yd/loader_support_cache.json``，同一版本下次打开直接读缓存、不重新联网，只有清单
  里出现缓存中没有的新版本才重新探测；
- 允许重复下载同一 MC 版本并自定义别名（目录名 ↔ 原生 mc_version ↔ 加载器类型 / 版本分离），
  下载中途可取消并清理半成品；
- 下载面板改为展开时顶部居中铺开、5 秒无操作收回右下角小胶囊；展开态底部居中加大叉取消按钮，
  右上角小 X 仅收起面板；
- 补齐依赖库 / natives / 资源文件真实下载与落盘；Forge / NeoForge / Fabric / OptiFine 四个
  加载器全部走真实下载安装链路；进入详情页自动扫描加载器支持性；
- 去掉分组内第二条滚动条，全页只保留最外侧一条最细滚动条；
- 启动链路探测本机 Java、组装 JVM 参数并尝试真实拉起游戏进程；无 Java 给出引导提示。

v1.2.11.0：新增 exe 同级便携 ``.minecraft`` 目录与版本隔离、本地已安装版本扫描；下载页
每条版本条目接入下载按钮与单例下载状态浮层（铺开 / 5 秒无操作自动收回右下角小入口、
透明毛玻璃、五步分步清单、总进度 / 速度 / 剩余文件数）；分块并发下载默认 20 线程、预估
总内容大于 1GB 自动切 30 线程；个人页游戏版本选择器改为两行可视、滚轮滚动的已安装版本
列表；全局滚动条收窄为极细透明小竖线。本轮下载骨架只打通版本 JSON 与客户端 Jar 两步，
依赖库 / 资源文件 / 真正拉起游戏进程（JVM / 本机 Java）留待后续轮次。

v1.2.10.0：下载页新增四个分组横条分类方块图标与每条版本条目左侧小方块图标；版本清单
分类结果缓存到 ``yd/version_manifest_cache.json``，首次无缓存才联网全量拉取，之后启动直接
读缓存渲染、不重新刷新列表；后台按国内镜像 → 官方顺序轻量比对最新正式 / 预览版号，发现一个
或两个新版本时弹出淡入淡出提示窗；不新增手动刷新按钮，不下载游戏客户端。

v1.2.9.2：修复下载页全量列表真机暴露的退出原生崩溃、组内视口高度收缩、清单瞬时断连
无重试、分批条目坐标塌顶四项问题；全量分类口径与双向显现动画保持 v1.2.9.1 不变。

v1.2.9.1：下载页由「四分组各放一条代表版本」改为全量版本分类列表——正式版 / 预览版 /
远古版 / 愚人节版各自拉取清单内全部版本条目，「最新版本」分组仍只保留最新正式版 + 最新
预览版两条；四个分组点开才在组内独立滚动区构建条目、收起即释放；条目随分组内滚动从左
往右滑入淡入（向下滚）、反向从右往左退回（向上滚），动画时长跟随滚轮快慢；窗口尺寸、
其余界面基线不变。

v1.2.8.1：下载页修复四条收起横条下方被拉伸填满的不透明留白白板（内容容器缺透明
规则导致自动填充默认浅灰）；正式版 / 预览版 / 远古版 / 愚人节版四个分组展开后的单行
条目改为联网拉取代表版本号与发布日期回填，离线 / 失败静默留空；窗口尺寸、其余界面基线
不变。

v1.2.7.1：下载页五张版本卡片改造为可折叠分组（手风琴），标题横条收起时不显图标、
点击平滑展开，最新版本分组默认展开并展示最新正式版 / 预览版号与发布日期；整体再缩小、
列表可滚动。窗口尺寸、文字 / 主色 / 侧栏卡片圆角等既有基线不变。

v1.2.6.1：下载页五张版本卡片整体缩小，新增四张网上现成 3D 方块渲染图资源与
官方版本清单只读拉取端点；窗口尺寸、文字 / 主色 / 侧栏卡片圆角等既有基线不变。
"""

APP_NAME = "CLY"
APP_FULL_NAME = "Cloudy Launcher"
# HTTP 请求头 User-Agent 必须是纯 ASCII（urllib 按 latin-1 编码请求头，非 ASCII 会直接抛
# UnicodeEncodeError）；对外网络标识与显示名分开，认证 / 下载统一引用本常量。
APP_UA_NAME = "CloudyLauncher"
APP_VERSION = "1.1.0"
APP_VERSION_TAG = f"v{APP_VERSION}"
# 发布阶段：正式版采用三段版本号（主.次.修订）；此前四段号（主.次.功能.修复）为
# 内部测试版。AI 助手保持入口，正式版发布后再持续打磨。
APP_STAGE = "正式版"
# 标题栏 / 窗口标题只显示英文全名，不再拼接版本号；版本号仅在关于页展示。
APP_DISPLAY_NAME = APP_FULL_NAME
# 关于页版本号文案（全英文）。
ABOUT_VERSION_LABEL = f"Version {APP_VERSION}"
# 作者反馈 QQ：关于页「问题反馈」卡展示，遇到问题或 Bug 可加此号联系。
AUTHOR_QQ = "2756141828"
# 关于页「本版本介绍」要点（中文条目，随版本更新同步改写）。
ABOUT_RELEASE_NOTES = [
    '首个正式版：云朵启动器与云朵桌宠统一发布正式版 1.1.0（此前的四段版本号为内部测试版，正式版改用三段版本号）；内置 AI 助手入口保留，将在正式版发布后持续打磨。',
    '游戏下载与启动：支持原版游戏、Mod、整合包、光影包、资源包、数据包分类搜索与下载，正版 / 离线账号、版本隔离、多线程加速下载，自动探测本机 Java 并拉起游戏。',
    '整合包导入导出：支持 CurseForge、MultiMC/Prism、MCBBS 及本地文件导入，并可导出为离线完整包、Modrinth .mrpack、MultiMC/Prism、CurseForge、MCBBS 五种格式。',
    '个性化与皮肤：可自定义 Logo、显示名称、壁纸与毛玻璃主题；皮肤支持正版账号自动使用正版皮肤、离线账号导入本地皮肤，内置史蒂夫 / 艾利克斯。',
    '桌宠陪伴：独立桌宠 APP，3D 角色头部跟随鼠标，空闲随机挥手、拍手、吃东西、跳跃、欢呼、打哈欠、跳舞、摸小狗等动作，带饥饿值、头顶对话气泡与爱心 / 音符 / 问号 / Zzz 情绪粒子，鼠标一动立刻恢复正常。',
    '桌宠小狗：驯服狼会随机进场陪伴，可喂狗、摸狗，具备走路、摇尾、开心、被摸等动画，陪伴一段时间后自动退场。',
    '桌宠困倦睡眠：长时间空闲会先打哈欠、随后趴下入睡并周期冒 Zzz，鼠标一动立刻醒来。',
    '功能开关：「设置 · 桌宠」页可一键全部开启 / 全部关闭，也能单独控制空闲小动作、悬停喂食菜单、饥饿值、小狗陪伴、困倦睡觉五项，默认全部开启；开关只做在启动器里，桌宠本身不放置任何设置入口。',
    '问题反馈：使用中遇到任何问题或 Bug，可在「问题反馈」卡查看作者 QQ 并联系作者。',
]

# 窗口默认尺寸（1.1.1.3 起在 1.1.1.2 基础上整体放大）
WINDOW_WIDTH = 980
WINDOW_HEIGHT = 660
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600

# 离线内置角色池（史蒂夫 / 艾利克斯，离线模式随机生成；正版角色由登录档案皮肤替换）
SKIN_STEVE = "steve"
SKIN_ALEX = "alex"
SKIN_CHOICES = {
    SKIN_STEVE: {"label": "史蒂夫", "file": "steve.png", "slim": False},
    SKIN_ALEX: {"label": "艾利克斯", "file": "alex.png", "slim": True},
}
DEFAULT_SKIN = SKIN_STEVE

# ---------------------------------------------------------------------------
# 微软（正版）账号登录：v1 Live-Connect 设备码（Device Code）OAuth 流程。
# 不要求用户自行在 Azure 注册应用：复用官方 Minecraft Launcher 长期公开使用的旧版
# Live-Connect 公共客户端 ID（public client，无 client_secret，客户端 ID 写在程序里属于
# OAuth 桌面公开客户端允许的做法）。整条链路纯 Python 标准库 urllib 实现，不引入第三方依赖。
# 注意：该公开 ID 属借用他人已审批应用身份，若日后被微软吊销，所有复用方同时失效。
#
# 2026-10-31 根因记录：原 v2 Azure-AD（consumers/oauth2/v2.0，Prism 公开 GUID
# c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb，scope=XboxLive.signin offline_access）设备码在
# 浏览器同意环节被 msproxy 旧同意层判定为「第一方应用 + 第一方资源」，报
# AADSTS65002 / invalid_request（“该应用是第一方应用，用户无需同意，也不得同意第一方应用”）：
# 该 Prism 应用注册只配置了 loopback 授权码回调，未开放设备码用户同意。离线实测 consumers
# 个人账号下其余 v2 公开 ID 同样不可用（edu 仅限组织目录、office365 目录中不存在、
# LiquidLauncher 同为 loopback 应用）。故切换到官方 Launcher v1 Live-Connect 身份，与
# mcapi-auth 默认 login_device_code_v1 一致；依旧是设备码 + 后台轮询，不开本地端口、
# 不做授权码 loopback 回调。
# ---------------------------------------------------------------------------
# 官方 Minecraft Launcher v1 Live-Connect 压缩形式公开客户端 ID（无客户端密钥）
MS_PUBLIC_CLIENT_ID = "00000000402b5328"
# v1 Live-Connect 设备码申请端点 / 令牌端点（旧 login.live.com/oauth20_*.srf 族）
MS_DEVICE_CODE_URL = "https://login.live.com/oauth20_connect.srf"
MS_TOKEN_URL = "https://login.live.com/oauth20_token.srf"
# v1 资源 scope：Xbox Live RPS 票据（MBI_SSL）
MS_OAUTH_SCOPE = "service::user.auth.xboxlive.com::MBI_SSL"
# v1 拿到的是不透明 RPS ticket（EwAIA... 形态），换取 Xbox Live 时 RpsTicket 不得加
# "d=" 前缀（加前缀 XBL 会 401）；只有 v2 Azure-AD 的 JWT 令牌才需要 "d=" 前缀。
MS_XBL_USE_D_PREFIX = False

# 备查（v2 Azure-AD consumers 端点，2026-10-31 真机设备码同意环节报 65002，已弃用）：
#   MS_V2_AAD_BASE = "https://login.microsoftonline.com/consumers/oauth2/v2.0"
#   MS_V2_CLIENT_ID = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"
#   MS_V2_SCOPE = "XboxLive.signin offline_access"

MS_XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
MS_XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MS_MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MS_MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"

# 下载页版本清单：Mojang 官方版本元数据接口（只读拉取版本号文本与发布日期，本轮不下载
# 游戏客户端、不解析版本文件清单、不绑定下载 / 启动动作）。
# 国内镜像 BMCLAPI2 优先、官方 piston-meta 兜底，逐个尝试，任一成功即用；全部失败才静默
# 占位。两个端点返回同一份 version_manifest_v2.json 结构。
MC_VERSION_MANIFEST_URLS = (
    "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json",
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
)
# 兼容旧引用：取第一个镜像作为单一端点默认值。
MC_VERSION_MANIFEST_URL = MC_VERSION_MANIFEST_URLS[0]
# 清单是小 JSON，超时压短：关闭窗口时后台线程不会长时间阻塞在 urlopen 上，保证 wait 能等到收尾。
META_HTTP_TIMEOUT = 6
# 瞬时断连 / 远端无响应时的轻量重试：最多尝试 META_FETCH_RETRIES 次，间隔 META_RETRY_DELAY 秒；
# 全部失败才由界面静默回退占位，不弹窗、不阻塞主线程（重试发生在后台拉取线程内）。
META_FETCH_RETRIES = 1
META_RETRY_DELAY = 0.5

# 版本清单本地缓存：落在 exe 同级 yd/ 目录（与账号文件同目录），只缓存分类后的版本号与
# 日期文本，不缓存任何游戏下载链接。首次无缓存才联网全量拉取；之后启动直接读缓存渲染，
# 不重新刷新列表；后台轻量比对最新版号发现新版本时静默覆盖本缓存，当前界面保持不重建。
META_CACHE_DIRNAME = "yd"
META_CACHE_FILENAME = "version_manifest_cache.json"

# 分组横条分类方块 / 条目左侧小方块尺寸（px）。
SECTION_HEADER_ICON_SIZE = 22
ENTRY_ICON_SIZE = 18
# 新版本提示弹窗：淡入 / 淡出时长（ms），停留后点「知道了」淡出关闭，不打断主窗口操作。
UPDATE_NOTICE_FADE_MS = 220
UPDATE_NOTICE_HOLD_MS = 5200

# v1.2.9.1：四个全量分组的归类口径。
# 正式版 = type release 全集；预览版 = type snapshot 且不在下方愚人节白名单内；
# 远古版 = old_beta + old_alpha 合并后按时间倒序；愚人节版 = 白名单精确 id 命中全集。
# 愚人节特殊版本线上清单里 type 均为 snapshot，必须先从预览版剔除再单独成组。
APRIL_FOOL_IDS = (
    "15w14a",
    "1.RV-Pre1",
    "3D Shareware v1.34",
    "20w14infinite",
    "22w13oneblockatatime",
    "23w13a_or_b",
    "24w14potato",
    "24w14a",
    "25w14craftmine",
)

# 分组内独立滚动区高度上限：748 条预览版不把外层页面撑成超长列表，条目在组内滚动。
SECTION_SCROLL_MAX_HEIGHT = 340
# 条目进场 / 显现动画：位移幅度（px）、基准时长（ms）、时长上下限；滚轮越快动画越短。
ENTRY_SLIDE_DISTANCE = 22
ENTRY_ANIM_BASE_MS = 200
ENTRY_ANIM_MIN_MS = 110
ENTRY_ANIM_MAX_MS = 280
# 首次点开分组时首批可见条目的交错间隔（ms）。
ENTRY_STAGGER_MS = 12
# 视口上下缓冲（px）：条目进入该缓冲带即开始显现，避免贴着视口边缘才动。
ENTRY_VIEWPORT_PADDING = 14
# 超大列表分批构建：不超过阈值的小列表同步一次建完；超过阈值后首批同步建首屏，
# 其余按批次由定时器分批补建，避免数百条控件一次性创建阻塞主线程。
ENTRY_BATCH_THRESHOLD = 40
ENTRY_BATCH_SIZE = 40

# 单次 HTTP 请求超时（秒）；设备码授权总等待超时（秒，10 分钟）
AUTH_HTTP_TIMEOUT = 60
# 启动静默恢复专用的单次 HTTP 超时（秒）：恢复是后台尽力而为，单跳超过该时长即视为失败、
# 保持离线，下次启动再试；同时给关闭窗口时等待线程收尾设定确定上界，避免运行中的 QThread
# 被析构触发 0xC0000409。
RESTORE_HTTP_TIMEOUT = 8
# 正版皮肤 PNG 下载的单次超时（秒）：皮肤是小图，10s 足够；同时给关闭窗口等待皮肤线程
# 收尾设定确定上界。
SKIN_FETCH_TIMEOUT = 10
AUTH_POLL_TIMEOUT = 600
# 轮询初始间隔（秒）；服务端要求 slow_down 时自动拉长
AUTH_POLL_INTERVAL = 2.0
# MC 服务令牌在过期前预留的提前量（秒），避免边界时刻拿到即将过期的令牌
MC_TOKEN_EXPIRE_MARGIN = 120

# 配色：苹果风通透磨砂玻璃（macOS / iOS 面板观感）。
# 窗口根背景保持不透明蓝白渐变；侧栏、卡片、输入框、按钮、进度条统一为半透明
# 白色玻璃叠加 + 细亮白边框。不调用系统模糊接口、不真透视桌面，跨电脑表现一致。
# 背景：浅柔蓝白两段，作为玻璃片下方可透出的层次；未检测到外部壁纸时回退到这套渐变。
COLOR_BG_TOP = "#eaf4fc"
COLOR_BG_BOTTOM = "#bcdcef"

# ---------------------------------------------------------------------------
# v1.2.4.0 外部自定义壁纸与毛玻璃背景层
#
# 壁纸不打进 exe、也不进入源码 zip：启动时在 exe 同级外部目录 ``wallpaper/`` 按固定
# 优先级读取；目录缺失、文件损坏或被用户删除时，静默回退到上面的蓝白渐变默认背景，
# 不弹窗、不崩溃。以后接入任意自定义壁纸时沿用同一目录与回退口径。
# ---------------------------------------------------------------------------
WALLPAPER_DIR_NAME = "wallpaper"
# 固定优先级文件名；目录里存在任一受支持图片即作为壁纸（同名覆盖即可换图）。
WALLPAPER_CANDIDATES = (
    "wallpaper.png",
    "wallpaper.jpg",
    "wallpaper.jpeg",
    "wallpaper.webp",
    "wallpaper.bmp",
)
WALLPAPER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# 背景层毛玻璃：先把壁纸降采样到短边该尺寸，再平滑放大回窗口尺寸，得到等效大半径
# 柔化（不引入第三方模糊库、不挂 QGraphicsBlurEffect，避免连带模糊上层控件）。
WALLPAPER_BLUR_SHORT_SIDE = 96
# 壁纸之上、卡片之下的中性磨砂罩：上缘更亮、底部略透，统一基调并保证文字对比度；
# 亮壁纸沿用这套偏白罩。暗壁纸分支色值预留，后续自定义深色壁纸时按平均亮度切换。
# 元组顺序为 (R, G, B, A)，供背景层 paintEvent 直接构造 QColor；A 取值 0-255。
# 罩层不压满：保留足够不透明度压住局部高对比色块、保证深墨蓝文字可读，同时让模糊后的
# 壁纸暖色与角色色块从罩层下隐约透出，形成 iOS 式水印毛玻璃层次。
COLOR_WALLCOVER_TOP_RGBA = (234, 244, 252, 150)
COLOR_WALLCOVER_BOTTOM_RGBA = (188, 220, 239, 118)
# 平均亮度高于该阈值视为亮壁纸（沿用深色文字 + 白玻璃）；低于阈值视为暗壁纸。
WALLPAPER_LIGHT_THRESHOLD = 0.52

# 玻璃面板三段渐变：上缘白色反光高光 -> 中部半透 -> 底部更透（整体通透，非实白）。
# v1.2.4.0 接入外部壁纸后，顶部高光略提亮模拟玻璃片上缘反光，中部 / 底部进一步降不透明度，
# 让模糊壁纸色从卡片玻璃后透出；文字仍为深墨蓝，对比度由罩层与顶部高光共同保证。
COLOR_GLASS_TOP = "rgba(255, 255, 255, 176)"
COLOR_GLASS_MID = "rgba(255, 255, 255, 102)"
COLOR_GLASS_BOTTOM = "rgba(255, 255, 255, 62)"
COLOR_CARD = "rgba(255, 255, 255, 118)"
COLOR_CARD_BORDER = "rgba(255, 255, 255, 188)"

# v1.2.4.1：模糊只下沉到每张卡片 / 侧栏玻璃片内部（片内局部磨砂），背景壁纸保持清晰。
# 下面一组 (R, G, B, A) 元组供卡片 / 侧栏 paintEvent 自绘三段白玻璃高光与描边使用，
# 与上面 QSS rgba 字符串一一对应；小控件（输入框 / 按钮 / 进度条等）仍走 QSS 字符串。
COLOR_GLASS_TOP_RGBA = (255, 255, 255, 176)
COLOR_GLASS_MID_RGBA = (255, 255, 255, 102)
COLOR_GLASS_BOTTOM_RGBA = (255, 255, 255, 62)
COLOR_CARD_BORDER_RGBA = (255, 255, 255, 188)
# 卡片后方壁纸小块先降采样到短边该尺寸、再平滑放大回卡片尺寸，得到片内大半径柔化；
# 仅作用于圆角面板内部，卡片外壁纸保持清晰，不挂 QGraphicsBlurEffect、不引第三方模糊库。
PANEL_BLUR_SHORT_SIDE = 100

# 侧栏玻璃三段，比卡片略透
COLOR_SIDEBAR_TOP = "rgba(255, 255, 255, 158)"
COLOR_SIDEBAR_MID = "rgba(255, 255, 255, 90)"
COLOR_SIDEBAR_BOTTOM = "rgba(255, 255, 255, 56)"
COLOR_SIDEBAR = "rgba(255, 255, 255, 104)"
COLOR_SIDEBAR_BORDER = "rgba(255, 255, 255, 168)"
COLOR_SIDEBAR_TOP_RGBA = (255, 255, 255, 158)
COLOR_SIDEBAR_MID_RGBA = (255, 255, 255, 90)
COLOR_SIDEBAR_BOTTOM_RGBA = (255, 255, 255, 56)
COLOR_SIDEBAR_BORDER_RGBA = (255, 255, 255, 168)

# 玻璃输入框：通透白玻璃，描边压到弱光，不再勾出高亮矩形轮廓
COLOR_FIELD_GLASS = "rgba(255, 255, 255, 84)"
COLOR_FIELD_GLASS_HOVER = "rgba(255, 255, 255, 112)"
COLOR_FIELD_BORDER = "rgba(255, 255, 255, 88)"

# v1.2.4.6：六个可拉扯按钮（导航 / 离线 / 正版 / 开始游戏 / 标题栏最小化 / 关闭）只做这一层
# 「iOS 浅色半透明玻璃胶囊」——半透明白叠加在卡片 / 侧栏磨砂与背景之上，下层颜色能从按钮
# 玻璃后透出，不再是不透明白板；选中态 / 主操作档只比默认略亮一档用于辨识，依旧保持透明。
# 色值只作用于这六个按钮，输入框 / 弹窗按钮 / 卡片 / 侧栏 / 背景全部沿用上面既有数值，不在
# 本轮范围内。
COLOR_BTN_GLASS = "rgba(255, 255, 255, 88)"
COLOR_BTN_GLASS_HOVER = "rgba(255, 255, 255, 100)"
COLOR_BTN_GLASS_ACTIVE = "rgba(255, 255, 255, 104)"
COLOR_BTN_BORDER = "rgba(255, 255, 255, 110)"
COLOR_BTN_BORDER_ACTIVE = "rgba(255, 255, 255, 175)"

# 版本设置页概览四个内容计数按钮（mod/光影包/材质包/数据包）：用户明确不要白板，
# 故比普通 modeButton 进一步收掉白填充，做成更通透的玻璃 chip，只靠细边 + hover 维持
# 可点感，深色文字仍清晰；不做不透明实块。
COLOR_COUNT_CHIP_GLASS = "rgba(255, 255, 255, 42)"
COLOR_COUNT_CHIP_HOVER = "rgba(255, 255, 255, 68)"
COLOR_COUNT_CHIP_PRESSED = "rgba(255, 255, 255, 32)"
COLOR_COUNT_CHIP_BORDER = "rgba(255, 255, 255, 96)"
COLOR_COUNT_CHIP_BORDER_HOVER = "rgba(255, 255, 255, 130)"

# 开始游戏主按钮单独一组：它位于底部启动行、身后是较暗的浅蓝壁纸 / 罩层（不像分段 /
# 导航那样叠在白卡片上），若沿用上面偏白的一档会在暗背景上压成一块亮白板。探针实测
# 边缘空白区明度差需要收到 5 以内，故主按钮填充更淡、描边更弱；hover 略亮一档、pressed
# 再收一档，只靠位置 + 深色加粗字维持主操作层级，不再凸出成白色实块。
COLOR_BTN_GLASS_PRIMARY = "rgba(255, 255, 255, 34)"
COLOR_BTN_GLASS_PRIMARY_HOVER = "rgba(255, 255, 255, 46)"
COLOR_BTN_GLASS_PRIMARY_PRESSED = "rgba(255, 255, 255, 28)"
COLOR_BTN_BORDER_PRIMARY = "rgba(255, 255, 255, 120)"
COLOR_BTN_BORDER_PRIMARY_HOVER = "rgba(255, 255, 255, 140)"

# 选中态（导航 / 模式共用）：填充再贴近面板，边框几乎透明，选中辨识只靠中蓝加粗文字，
# 不再用一圈有色硬边勾出浮起矩形。
COLOR_PRIMARY_GLASS_TOP = "rgba(162, 207, 233, 52)"
COLOR_PRIMARY_GLASS_BOTTOM = "rgba(146, 197, 226, 42)"
COLOR_PRIMARY_GLASS_BORDER = "rgba(190, 222, 238, 22)"

# 开始游戏主按钮：玻璃蓝 + 顶部白光高光的通透三段渐变，保留主操作层级但不做闷实蓝块；
# 顶部一道白色反光模拟苹果玻璃片质感，中部玻璃蓝、底部略深。固定高度 44px、固定宽度
# 146px、不参与水平拉伸，圆角取半高 22px 形成两端正半圆的饱满椭圆胶囊；描边改用与
# 填充同色系、略深一档的浅蓝细边勾勒轮廓，不再用亮白高光边（那是旧版浮起感的来源）
# ——只画形状、不打浮起高光。
COLOR_PRIMARY_BTN_TOP = "rgba(255, 255, 255, 104)"
COLOR_PRIMARY_BTN_MID = "rgba(151, 205, 233, 124)"
COLOR_PRIMARY_BTN_BOTTOM = "rgba(124, 189, 221, 116)"
COLOR_PRIMARY_BTN_BORDER = "rgba(118, 178, 212, 78)"
COLOR_PRIMARY_BTN_BORDER_HOVER = "rgba(132, 188, 220, 96)"
COLOR_PRIMARY_BTN_BORDER_PRESSED = "rgba(104, 168, 204, 70)"

# 进度条：轨道更通透，边框由高亮白改为同系浅蓝弱边，消除长条上下勾边；填充保持低不透明玻璃蓝
COLOR_BAR_TRACK = "rgba(255, 255, 255, 44)"
COLOR_BAR_BORDER = "rgba(190, 222, 238, 34)"
COLOR_CHUNK_LEFT = "rgba(170, 216, 238, 110)"
COLOR_CHUNK_RIGHT = "rgba(130, 192, 224, 96)"

COLOR_PRIMARY = "#4f9fd0"
COLOR_PRIMARY_DARK = "#3d87b6"
COLOR_TEXT = "#2b4759"
COLOR_TEXT_LIGHT = "#6d8a9c"
COLOR_ACCENT = "#7fc4e8"

# ---------------------------------------------------------------------------
# v1.2.5.1：PCL 式下载页骨架——顶部分类标签（原版游戏 / mod / 整合包 / 光影包 /
# 资源包 / 数据包）与五张版本卡片（最新版本 / 正式版 / 预览版 / 远古版 / 愚人节版）。
# 本轮只搭排版骨架、不接真实版本拉取 / 下载 / 设置 / 打包 / 关于功能；配色沿用既有
# 浅蓝白 iOS 玻璃体系，不引入不透明实色块。
# ---------------------------------------------------------------------------
# 分类标签：默认通透白玻璃细边、浅色字；选中态更亮填充 + 亮边 + 加粗深色字。
COLOR_TAB_GLASS = "rgba(255, 255, 255, 74)"
COLOR_TAB_GLASS_HOVER = "rgba(255, 255, 255, 96)"
COLOR_TAB_GLASS_ACTIVE = "rgba(255, 255, 255, 128)"
COLOR_TAB_BORDER = "rgba(255, 255, 255, 96)"
COLOR_TAB_BORDER_ACTIVE = "rgba(255, 255, 255, 180)"

# 版本卡片片内局部磨砂三段白玻璃（普通档，与通用卡片同一通透语言）。
COLOR_VERSION_GLASS_TOP_RGBA = (255, 255, 255, 140)
COLOR_VERSION_GLASS_MID_RGBA = (255, 255, 255, 80)
COLOR_VERSION_GLASS_BOTTOM_RGBA = (255, 255, 255, 45)
COLOR_VERSION_BORDER_RGBA = (255, 255, 255, 176)
# 第一张「最新版本」：填充略深一档以突出置顶推荐，仍保持透明 + 片内磨砂。
COLOR_VERSION_TOP_GLASS_TOP_RGBA = (255, 255, 255, 186)
COLOR_VERSION_TOP_GLASS_MID_RGBA = (255, 255, 255, 128)
COLOR_VERSION_TOP_GLASS_BOTTOM_RGBA = (255, 255, 255, 84)
COLOR_VERSION_TOP_BORDER_RGBA = (255, 255, 255, 200)

# v1.2.12.2：版本详情页分组卡片片内局部磨砂三段白玻璃。详情页身后是用户自换的高饱和
# 大字 / 卡通壁纸，旧版只盖一层 alpha 76 的极淡 QSS 白底、没有片内磨砂，壁纸大字直接压在
# 分组标题与版本号上无法辨认；本组不透明度高于下载页版本卡片，先把壁纸压暗压柔，再叠
# 三段白玻璃高光，文字对比度由罩层保证；仍保持通透、不挂 QGraphicsBlurEffect。
COLOR_DETAIL_GLASS_TOP_RGBA = (255, 255, 255, 140)
COLOR_DETAIL_GLASS_MID_RGBA = (255, 255, 255, 80)
COLOR_DETAIL_GLASS_BOTTOM_RGBA = (255, 255, 255, 45)
COLOR_DETAIL_BORDER_RGBA = (255, 255, 255, 198)
# 展开区内单条候选版本行：比分组卡片弱一档的磨砂白玻璃。
COLOR_DETAIL_ROW_TOP_RGBA = (255, 255, 255, 190)
COLOR_DETAIL_ROW_MID_RGBA = (255, 255, 255, 156)
COLOR_DETAIL_ROW_BOTTOM_RGBA = (255, 255, 255, 120)
COLOR_DETAIL_ROW_BORDER_RGBA = (255, 255, 255, 152)
# 详情页分组卡片 / 版本行圆角半径。
COLOR_DETAIL_SECTION_RADIUS = 14.0
COLOR_DETAIL_ROW_RADIUS = 10.0
# 当前选中分组：比默认白玻璃偏浅蓝一档，描边略亮，只靠填充与弱蓝边辨识选中，不勾硬浮起轮廓。
COLOR_DETAIL_ACTIVE_TOP_RGBA = (199, 226, 241, 224)
COLOR_DETAIL_ACTIVE_MID_RGBA = (182, 217, 239, 196)
COLOR_DETAIL_ACTIVE_BOTTOM_RGBA = (170, 211, 235, 156)
COLOR_DETAIL_ACTIVE_BORDER_RGBA = (201, 229, 243, 202)

# ---------------------------------------------------------------------------
# v1.2.11.0：便携 .minecraft 目录、版本隔离、并发下载引擎与单例下载面板。
#
# 目录口径沿用本工程既有便携规则：与 config.json、yd/ 缓存同目录（exe 同级，源码运行时
# 工程根），程序拷到哪里数据就在哪里，不使用 %APPDATA%\.minecraft。每个版本独立隔离到
# ``versions/<版本号>/`` 下，自带 saves / config 子目录，互不污染。
# ---------------------------------------------------------------------------
MINECRAFT_DIR_NAME = ".minecraft"
VERSIONS_DIR_NAME = "versions"
# 版本隔离子目录：存档与配置按版本独立存放。
VERSION_SAVES_DIR_NAME = "saves"
VERSION_CONFIG_DIR_NAME = "config"
# 版本目录内固定文件名：版本元数据 JSON 与客户端 Jar。
VERSION_JSON_FILENAME = "{id}.json"
# 云朵下载的版本统一把客户端 jar 命名为 client.jar。
VERSION_CLIENT_JAR_FILENAME = "client.jar"
# 标准 MC / 其他启动器（PCL2、官方启动器等）的客户端 jar 与版本目录同名：<id>.jar。
# 扫描版本时两种命名都要识别，外部放入的标准版本才能被云朵发现。
VERSION_STANDARD_JAR_FILENAME = "{id}.jar"

# ---- 下载并发与分块 ----
# 默认并发线程数；预估总内容大于 1GB 时自动切到大文件档线程数。
DOWNLOAD_THREADS_DEFAULT = 20
DOWNLOAD_THREADS_LARGE = 30
DOWNLOAD_LARGE_BYTES = 1024 * 1024 * 1024  # 1 GiB
# 单次读取 / 分块缓冲大小（字节）；大文件按块流式写入，不整文件堆进内存。
DOWNLOAD_CHUNK_SIZE = 256 * 1024
# 单文件 HTTP 超时（秒）；比清单拉取长，客户端 Jar 体积大。
DOWNLOAD_HTTP_TIMEOUT = 30
# 读取停滞超时（秒）：连接建立后连续这么久一个字节都没收到，主动断开切换下一个源。
# 解决「连接挂死、速度长期 0 B/s」——socket timeout 只在单次 recv 生效，慢源零星发数据
# 不会触发，故用独立 watchdog 强制掐断。
DOWNLOAD_STALL_TIMEOUT = 12
# 下载失败重试次数（仅对网络瞬时错误，离线不可达不反复重试拖垮关闭流程）。
# 全部候选源一轮都失败后，按此次数再整轮重试，配合 .part 断点续传，代价很低；
# 解决高并发下 BMCL 瞬时抖动、而官方源对该对象 404 时的误判失败。
DOWNLOAD_RETRIES = 2
# 重试轮次之间的基础退避（秒），按轮次递增，避免瞬间重新打爆镜像。
DOWNLOAD_RETRY_BACKOFF = 0.6
# 速度统计滑动窗口（秒）：用最近窗口内累计字节差估算实时下载速度。
DOWNLOAD_SPEED_WINDOW_SEC = 2.0
# 单个 Forge / NeoForge 安装器处理器的总时长上限（秒）。
# 26.3 的 binarypatcher 要生成 82 MB 的补丁化 client Jar，实测约 40 秒；正常情况远低于此上限。
# 超限即中止并报错，避免处理器真挂住时面板无限期停在「进行中」。
FORGE_PROCESSOR_TIMEOUT = 900
# 单文件 Range 分片并发下载：体积 ≥ 该阈值且大小已知时启用（2026-11-07 实测
# maven.minecraftforge.net 单连接只有 8~35 KB/s，8 MB 要 5~15 分钟；8 路 Range 并发
# 可到 340~510 KB/s，23 秒下完），服务器不支持 206 时自动回落单连接。
DOWNLOAD_SPLIT_MIN_BYTES = 4 * 1024 * 1024
# 每个分片的目标大小：按此把文件切成若干片，片数受下面上限约束。
DOWNLOAD_SPLIT_PART_BYTES = 1024 * 1024
# 单片最多切几片，避免与批量并发叠加时连接数失控（实测 8 片会触发源站 429 限流）。
DOWNLOAD_SPLIT_MAX_PARTS = 4

# ---- 下载镜像规则（探针实测，2026-11-02）----
# 客户端 Jar：BMCLAPI2 /version/<id>/client.jar 200；官方 piston-data objects/<sha1>/client.jar。
BMCL_CLIENT_JAR_URL = "https://bmclapi2.bangbang93.com/version/{version}/client.jar"
# 依赖库 Maven：BMCLAPI2 /maven/<artifact.path>；官方 libraries.minecraft.net。
BMCL_MAVEN_URL = "https://bmclapi2.bangbang93.com/maven/{path}"
# 国内公共 Maven 镜像（收录 Maven Central 上的原版库：lwjgl / asm / joml / gson 等）。
# 2026-11-07 实测：官方 libraries.minecraft.net 对本机常「200 后挂住不回数据」，同一批工件
# 走阿里云 / 华为云秒级完成；Forge 专属工件（net.minecraftforge:*）两个镜像均 404，只留官方源。
ALIYUN_MAVEN_URL = "https://maven.aliyun.com/repository/public/{path}"
HUAWEI_MAVEN_URL = "https://repo.huaweicloud.com/repository/maven/{path}"
# 资源文件：BMCLAPI2 /assets/<hash[:2]>/<hash>；官方 piston-data objects/<hash>/<name>。
BMCL_ASSET_URL = "https://bmclapi2.bangbang93.com/assets/{prefix}/{hash}"
OFFICIAL_OBJECT_URL = "https://piston-data.mojang.com/v1/objects/{hash}/{name}"

# ---- 下载五步状态机（信息形态对齐「任务管理」安装面板参考图）----
# 顺序固定：原版 json -> 原版支持库 -> 原版资源 -> 安装游戏 -> 游戏支持库。
DOWNLOAD_STEP_JSON = 0
DOWNLOAD_STEP_LIBRARIES = 1
DOWNLOAD_STEP_ASSETS = 2
DOWNLOAD_STEP_INSTALL = 3
DOWNLOAD_STEP_GAME_LIBS = 4
DOWNLOAD_STEP_TITLES = (
    "下载原版 json 文件",
    "下载原版支持库文件",
    "下载原版资源文件",
    "安装游戏",
    "下载游戏支持库文件",
)
# 步骤状态：待办 / 进行中 / 已完成 / 本轮骨架跳过（后续轮次补齐）。
STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_DONE = "done"
STEP_SKIPPED = "skipped"

# ---- 单例下载状态浮层面板 ----
# 铺开后面板宽 / 高（px）；收起态为贴右下角的小胶囊入口。
# v1.2.12.0：展开态从页面顶部居中铺开（对齐 iOS 顶部通知横幅参考图），收起态贴右下角。
DOWNLOAD_PANEL_EXPANDED_WIDTH = 430
DOWNLOAD_PANEL_EXPANDED_HEIGHT = 260
DOWNLOAD_PANEL_COLLAPSED_WIDTH = 150
DOWNLOAD_PANEL_COLLAPSED_HEIGHT = 44
# 收起态距页面右边 / 下边的内边距（px）；展开态距页面顶部 / 左右居中内边距（px）。
DOWNLOAD_PANEL_MARGIN_RIGHT = 18
DOWNLOAD_PANEL_MARGIN_BOTTOM = 18
DOWNLOAD_PANEL_MARGIN_TOP = 18
# 铺开 / 收回动画时长（ms），OutCubic 丝滑曲线。
DOWNLOAD_PANEL_ANIM_MS = 320
# 任务结束（成功 / 失败 / 取消）后，面板无操作自动整体隐藏的倒计时（ms）。
# 下载进行中不自动隐藏；鼠标进入面板暂停倒计时，离开重新计时。
DOWNLOAD_PANEL_AUTOHIDE_MS = 10_000
# 面板圆角半径。
DOWNLOAD_PANEL_RADIUS = 18.0

# ---- 全局极细滚动条 ----
# 竖条 / 横条宽度（px）：v1.2.12.3 按真机反馈再压细——2px 发丝线，轨道透明、无箭头、
# 平时几乎隐形，hover 才略亮；滑块最小长度同步缩短，避免在列表里显得是个"大轮"。
SCROLLBAR_THICKNESS = 2
SCROLLBAR_MIN_LENGTH = 22

# ---------------------------------------------------------------------------
# v1.2.12.0：版本详情页、四加载器支持性探测与真实安装链路、Java 探测与游戏拉起。
# ---------------------------------------------------------------------------
# ---- 版本隔离目录扩展子目录 ----
# 依赖库 jar 统一落到版本隔离目录下的 libraries/；natives 解压到 natives/；
# 全局资源仍在 .minecraft/assets，旧版本 virtual / legacy 目录由编排层处理。
VERSION_LIBRARIES_DIR_NAME = "libraries"
VERSION_NATIVES_DIR_NAME = "natives"
# v1.3.1.8：外部启动器（PCL2 / 官方启动器等）把 natives 解压到 ``<版本目录>/<别名>-natives``，
# 与云朵的 ``natives/`` 不同名；启动时两处都要认，否则原生库目录传错会导致游戏起不来。
VERSION_EXTERNAL_NATIVES_SUFFIX = "-natives"
# 版本安装元数据（别名 ↔ 原生 mc_version ↔ 加载器类型 / 版本），与版本 JSON 同目录。
VERSION_META_FILENAME = "install_meta.json"

# ---- 加载器标识 ----
LOADER_VANILLA = "vanilla"
LOADER_FORGE = "forge"
LOADER_NEOFORGE = "neoforge"
LOADER_FABRIC = "fabric"
LOADER_OPTIFINE = "optifine"
LOADER_KEYS = (LOADER_VANILLA, LOADER_FORGE, LOADER_NEOFORGE, LOADER_FABRIC, LOADER_OPTIFINE)
LOADER_LABELS = {
    LOADER_VANILLA: "原版游戏",
    LOADER_FORGE: "Forge",
    LOADER_NEOFORGE: "NeoForge",
    LOADER_FABRIC: "Fabric",
    LOADER_OPTIFINE: "OptiFine",
}
# 详情页四张第三方加载器卡片顺序（原版始终内置、不占卡片）。
LOADER_CARD_ORDER = (LOADER_FORGE, LOADER_NEOFORGE, LOADER_FABRIC, LOADER_OPTIFINE)
# 不支持 / 查不到对应版本时卡片右侧固定文案。
LOADER_UNAVAILABLE_TEXT = "暂时没有这个版本的加速器"
# 镜像只有版本号、没有安装包时（如 NeoForge 26.3.0.x 全量 404）的卡片文案：
# 版本号列表里有它，但安装包拉不下来，直接按「暂缺」提示而不是让下载必然失败。
LOADER_MIRROR_MISSING_TEXT = "镜像暂未提供这个版本的安装包"
LOADER_PROBING_TEXT = "正在探测兼容性…"
LOADER_AVAILABLE_TEXT = "可以添加"

# ---- 加载器支持性探测缓存（yd 目录，按 MC 版本精确键缓存，命中不重新联网）----
LOADER_SUPPORT_CACHE_FILENAME = "loader_support_cache.json"
# 缓存口径版本：v1.3.3.3 起 NeoForge 增加安装包 HEAD 可用性校验，旧结论会
# 把「只有版本号、没有安装包」的版本误报为可用；随后 Fabric 又接入 Legacy Fabric
# 回退源（1.12.2 等老版本标准 Fabric 无支持）。bump 到 4 让旧缓存整体作废重建。
LOADER_CACHE_SCHEMA = 4

# ---- Fabric 元数据端点（双端点：官方优先，BMCLAPI 镜像兜底；探针实测 2026-11-02）----
FABRIC_LIST_OFFICIAL = "https://meta.fabricmc.net/v2/versions/loader/{mc}"
FABRIC_LIST_MIRROR = "https://bmclapi2.bangbang93.com/fabric-meta/v2/versions/loader/{mc}"
FABRIC_PROFILE_OFFICIAL = (
    "https://meta.fabricmc.net/v2/versions/loader/{mc}/{loader}/profile/json"
)
FABRIC_PROFILE_MIRROR = (
    "https://bmclapi2.bangbang93.com/fabric-meta/v2/versions/loader/{mc}/{loader}/profile/json"
)
# Legacy Fabric：1.13.2 及更早版本（如 1.12.2）标准 Fabric meta 返回空，由 Legacy Fabric
# 延续支持，同一套 loader、独立 meta；作为列表/profile 的最后回退源（探针实测 2026-11-07）。
LEGACYFABRIC_LIST_URL = (
    "https://meta.legacyfabric.net/v2/versions/loader/{mc}"
)
LEGACYFABRIC_PROFILE_URL = (
    "https://meta.legacyfabric.net/v2/versions/loader/{mc}/{loader}/profile/json"
)

# ---- Forge 元数据 / 安装器端点（BMCLAPI 列表；安装器走官方 maven，BMCL maven 库兜底）----
FORGE_LIST_URL = "https://bmclapi2.bangbang93.com/forge/minecraft/{mc}"
FORGE_INSTALLER_URL = (
    "https://maven.minecraftforge.net/net/minecraftforge/forge/{mc}-{ver}/"
    "forge-{mc}-{ver}-installer.jar"
)

# ---- NeoForge 元数据 / 安装器端点（官方 maven 本机不可达，走 BMCLAPI maven 镜像）----
NEOFORGE_MAVEN_META_URL = (
    "https://bmclapi2.bangbang93.com/maven/net/neoforged/neoforge/maven-metadata.xml"
)
NEOFORGE_INSTALLER_URL = (
    "https://bmclapi2.bangbang93.com/maven/net/neoforged/neoforge/{ver}/"
    "neoforge-{ver}-installer.jar"
)
# 官方 maven 兜底：BMCL 镜像只同步了部分版本（26.3.0.x 全量 404），镜像缺失时再试官方。
NEOFORGE_INSTALLER_OFFICIAL_URL = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/"
    "neoforge-{ver}-installer.jar"
)
# NeoForge 版本主版本号前缀 ↔ 对应 MC 版本（公开已知映射；探测时按前缀匹配，不逐个下载
# 安装器探测）。key 为 NeoForge 版本第一段（如 21.1.x → 1.21.1）。
NEOFORGE_MC_PREFIX_MAP: dict[str, str] = {
    "20.1": "1.20.1",
    "20.2": "1.20.2",
    "20.3": "1.20.3",
    "20.4": "1.20.4",
    "20.5": "1.20.5",
    "20.6": "1.20.6",
    "21.0": "1.21",
    "21.1": "1.21.1",
    "22.0": "1.21.2",
    "22.1": "1.21.3",
    "22.2": "1.21.4",
    "23.0": "1.21.5",
    "23.1": "1.21.6",
    "24.0": "1.21.7",
    "24.1": "1.21.8",
    "25.0": "1.21.9",
    "26.0": "1.21.10",
}

# ---- OptiFine 元数据端点（BMCLAPI 只给列表，不托管 jar；官方站广告中转页取真实下载地址）----
OPTIFINE_LIST_URL = "https://bmclapi2.bangbang93.com/optifine/{mc}"
OPTIFINE_ADLOAD_URL = "https://optifine.net/adloadx?f={filename}"

# ---- 探测 / 元数据 HTTP 超时（秒）----
META_PROBE_TIMEOUT = 12
META_PROBE_RETRIES = 1

# ---- 版本详情页几何与文案 ----
DETAIL_BACK_TEXT = "← 返回"
DETAIL_START_DOWNLOAD_TEXT = "⬇ 开始下载"
DETAIL_ALIAS_DEFAULT_SUFFIX = ""

# v1.3.2.0：开始下载时的别名校验。别名目录已存在时禁止静默改名，弹框要求用户立刻重新命名。
ALIAS_EMPTY_TITLE = "名称不能为空"
ALIAS_EMPTY_MESSAGE = "请先给这个版本起一个名字，再开始下载。"
ALIAS_DUPLICATE_TITLE = "名称已重复"
ALIAS_DUPLICATE_MESSAGE = (
    "这个版本已经有了，名称「{alias}」已被占用。\n"
    "请立刻在上方输入框重新起一个名字，再开始下载。"
)

# ---- Java 探测 ----
# PATH 探测命令；注册表候选根；常见本机安装目录通配前缀。
JAVA_EXECUTABLE_NAME = "java"
JAVA_REGISTRY_ROOTS = (
    r"HKLM\SOFTWARE\JavaSoft\JDK",
    r"HKLM\SOFTWARE\JavaSoft\Java Development Kit",
    r"HKLM\SOFTWARE\WOW6432Node\JavaSoft\JDK",
    r"HKLM\SOFTWARE\WOW6432Node\Java Development Kit",
)
JAVA_SEARCH_DIRS = (
    r"C:\Program Files\Java",
    r"C:\Program Files (x86)\Java",
    r"C:\Program Files\Eclipse Adoptium",
    r"C:\Program Files\Microsoft\jdk",
    r"C:\Program Files\Amazon Corretto",
    r"C:\Program Files\Zulu",
    r"C:\Program Files\BellSoft",
)
# 启动失败 / 缺失 Java 时的引导提示文案。
JAVA_MISSING_TITLE = "未检测到 Java 运行环境"
JAVA_MISSING_MESSAGE = (
    "本机未找到可用的 Java，无法启动游戏。\n"
    "请先安装与该 MC 版本匹配的 Java 运行环境（现代版本建议 Java 17+，\n"
    "1.16 及更早版本建议 Java 8），安装完成后再回到启动页开始游戏。"
)
# v1.3.1.8：版本 profile 声明了 javaVersion.majorVersion 时先校验本机 Java 主版本，
# 版本过低直接给出明确提示，而不是让 JVM 抛出一行看不懂的类版本错误。
JAVA_VERSION_LOW_TITLE = "Java 版本过低"
JAVA_VERSION_LOW_MESSAGE = (
    "这个游戏版本需要 Java {required}，当前检测到的 Java 是 {current}。\n"
    "当前 Java 路径：{path}\n"
    "请安装 Java {required} 或更高版本后重新启动游戏。"
)
# JVM 内存默认值（MB）；由启动命令组装层使用。
DEFAULT_JVM_XMX_MB = 2048
DEFAULT_JVM_XMS_MB = 512

# ---------------------------------------------------------------------------
# v1.3.9.0：设置页「个性化」——玻璃风格三档、七色染色、壁纸选择、品牌改写、背景音乐。
# 全部设置持久化到 config.json；外部导入的素材落在 app 同级外部目录，不打进 exe / 源码包。
# ---------------------------------------------------------------------------

# ---- 玻璃风格三档 ----
# frost：现状片内磨砂（默认）；clear：不糊化，卡片下方壁纸/文字清晰可辨（通透）；
# normal：不透明白片，壁纸文字完全被挡住（普通）。
GLASS_MODE_FROST = "frost"
GLASS_MODE_CLEAR = "clear"
GLASS_MODE_NORMAL = "normal"
GLASS_MODE_KEYS = (GLASS_MODE_FROST, GLASS_MODE_CLEAR, GLASS_MODE_NORMAL)
GLASS_MODE_LABELS = {
    GLASS_MODE_FROST: "磨砂玻璃",
    GLASS_MODE_CLEAR: "通透",
    GLASS_MODE_NORMAL: "普通",
}
# 通透档：不画模糊块，只叠很淡的白玻璃保证文字可读（颜色仍为白色三段、低 alpha）。
COLOR_CLEAR_TOP_RGBA = (255, 255, 255, 96)
COLOR_CLEAR_MID_RGBA = (255, 255, 255, 52)
COLOR_CLEAR_BOTTOM_RGBA = (255, 255, 255, 28)
COLOR_CLEAR_BORDER_RGBA = (255, 255, 255, 160)
# 普通档：不透明白片 + 浅灰描边。
COLOR_NORMAL_PANEL_RGBA = (255, 255, 255, 255)
COLOR_NORMAL_BORDER_RGBA = (214, 226, 236, 255)

# ---- 七色染色盘（红橙黄绿青蓝紫）；空串表示不染色 ----
TINT_NONE = ""
TINT_COLORS = {
    "red": (238, 84, 84),
    "orange": (240, 150, 60),
    "yellow": (238, 206, 78),
    "green": (96, 190, 110),
    "cyan": (84, 196, 200),
    "blue": (92, 146, 232),
    "purple": (164, 116, 224),
}
TINT_KEYS = ("red", "orange", "yellow", "green", "cyan", "blue", "purple")
TINT_LABELS = {
    "red": "红",
    "orange": "橙",
    "yellow": "黄",
    "green": "绿",
    "cyan": "青",
    "blue": "蓝",
    "purple": "紫",
}
TINT_BG_ALPHA = 92   # 背景整窗染色 alpha
TINT_NAV_ALPHA = 80  # 导航栏染色 alpha

# ---- 壁纸选择 ----
# config 里 wallpaper_file 取该值时走 wallpaper.py 固定优先级/默认壁纸；
# 否则取 wallpaper/ 目录下同名文件。
WALLPAPER_DEFAULT_KEY = "default"

# ---- 品牌（logo / 名字）改写四档 ----
BRAND_MODE_DEFAULT = "default"
BRAND_MODE_LOGO = "logo"
BRAND_MODE_NAME = "name"
BRAND_MODE_BOTH = "both"
BRAND_MODE_KEYS = (BRAND_MODE_DEFAULT, BRAND_MODE_LOGO, BRAND_MODE_NAME, BRAND_MODE_BOTH)
BRAND_MODE_LABELS = {
    BRAND_MODE_DEFAULT: "默认",
    BRAND_MODE_LOGO: "logo改写",
    BRAND_MODE_NAME: "名字改写",
    BRAND_MODE_BOTH: "名字和logo改写",
}
# 导入的自定义 logo 固定存到 yd/ 目录（保留原扩展名）。
CUSTOM_LOGO_DIR = "yd"
CUSTOM_LOGO_BASENAME = "custom_logo"

# ---- 背景音乐：只允许一首歌、无限循环 ----
MUSIC_DIR_NAME = "music"
MUSIC_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac")
MUSIC_BASENAME = "bgm"  # 导入后统一存为 music/bgm.<ext>，保证目录里永远只有一首歌

# ---------------------------------------------------------------------------
# v1.3.9.1：设置页样式修复——iOS 开关配色、普通档整窗染色、玻璃三档样式预览图。
# ---------------------------------------------------------------------------

# ---- 仿 iOS 开关：缩小、椭圆胶囊；开=iOS 绿，关=iOS 浅灰，白钮带细阴影 ----
SWITCH_W = 42
SWITCH_H = 25
SWITCH_KNOB_MARGIN = 2
SWITCH_ON_RGB = (52, 199, 89)      # iOS systemGreen #34c759
SWITCH_OFF_RGB = (233, 233, 235)   # iOS switch off #e9e9eb
SWITCH_KNOB_SHADOW_RGBA = (60, 80, 100, 42)

# ---- 普通档下背景染色同时覆盖面板：白片上叠染色层的 alpha ----
TINT_NORMAL_PANEL_ALPHA = 118

# ---- 玻璃三档样式预览图（摆样子，可点选）----
GLASS_PREVIEW_W = 118
GLASS_PREVIEW_H = 88
GLASS_PREVIEW_RADIUS = 12
GLASS_PREVIEW_PANEL_MARGIN = 10
GLASS_PREVIEW_RING_RGBA = (77, 137, 196, 255)

# ---------------------------------------------------------------------------
# v1.3.9.2：设置页十项修复——标签缩小胶囊化、预览悬停说明、品牌条件显示、
# 音乐删开关、壁纸空白默认限三个、开关苹果动画与动画总开关、虚线全清。
# ---------------------------------------------------------------------------

# ---- 顶部四标签：按比例缩小、不铺满、椭圆胶囊 ----
SETTINGS_TAB_H = 30
SETTINGS_TAB_RADIUS = 15
SETTINGS_TAB_PADDING_X = 22

# ---- 侧栏导航按钮：椭圆胶囊（NavItem 高 46，半径取半值）----
NAV_ITEM_RADIUS = 23

# ---- 玻璃预览悬停 3 秒出说明 tooltip ----
GLASS_PREVIEW_TOOLTIP_DELAY_MS = 3000
GLASS_PREVIEW_TOOLTIPS = {
    "frost": "磨砂玻璃：背景模糊，半透明白色毛玻璃面板，iOS 风格",
    "clear": "通透：不模糊，很淡的半透明玻璃面板",
    "normal": "普通：不透明白色面板，染色时整窗跟随变色",
}

# ---- 壁纸：默认空白项，自定义壁纸最多导入三个 ----
WALLPAPER_MAX_COUNT = 3

# ---- 开关苹果式动画（旋钮位移动画时长）----
SWITCH_ANIM_DURATION_MS = 200
# iOS 流体形变：旋钮滑动途中横向最多拉长的比例（sin(pi*p) 峰值，两端归零）。
SWITCH_KNOB_STRETCH_MAX = 0.22

# ---- 动画总开关默认值（关闭后所有 Q 弹/苹果动画瞬时完成）----
ANIMATIONS_ENABLED_DEFAULT = True

# ---------------------------------------------------------------------------
# v1.3.9.3：品牌开关改显隐语义、旋钮可靠回位、染色圆角裁剪、弹簧全量门控。
# ---------------------------------------------------------------------------

# 品牌区 Logo / 名字显隐默认值（开关关闭=隐藏对应元素，与改写无关）。
LOGO_VISIBLE_DEFAULT = True
NAME_VISIBLE_DEFAULT = True

# ---------------------------------------------------------------------------
# v1.3.10.0：数据目录统一收敛到 exe 旁的 CLY 文件夹（全部平铺）。
# config.json、.minecraft、music、wallpaper、账号、版本/加载器缓存、搜索缓存、
# 自定义 logo 全部直接读写到 CLY 下，不再散落在 exe 同级，也不再使用 yd 子目录。
# ---------------------------------------------------------------------------
DATA_DIR_NAME = "CLY"

# ---------------------------------------------------------------------------
# v1.3.16.0：设置页「启动」标签——账号管理、版本隔离、高级功能（Java/参数/内存/开关）。
# 这些设置先落盘到 config.json；其中自定义 JVM/游戏参数、选定 Java、GC 已接入启动命令
# 组装，隔离策略目录解析与本机语义有限的高级开关按后续版本链路逐步接入。
# ---------------------------------------------------------------------------

# ---- 版本隔离策略 ----
# off：关闭隔离，所有版本共享全局 .minecraft 目录；
# modded：只隔离可安装 Mod 的版本（Forge/NeoForge/Fabric/OptiFine）；
# snapshot：只隔离非正式版（快照 / 远古版）；
# modded_snapshot：同时隔离可装 Mod 的版本与非正式版；
# all：隔离所有版本（现状默认，每个版本独立 versions/<别名> 目录）。
ISOLATION_OFF = "off"
ISOLATION_MODDED = "modded"
ISOLATION_SNAPSHOT = "snapshot"
ISOLATION_MODDED_SNAPSHOT = "modded_snapshot"
ISOLATION_ALL = "all"
ISOLATION_KEYS = (
    ISOLATION_OFF,
    ISOLATION_MODDED,
    ISOLATION_SNAPSHOT,
    ISOLATION_MODDED_SNAPSHOT,
    ISOLATION_ALL,
)
ISOLATION_LABELS = {
    ISOLATION_OFF: "关闭",
    ISOLATION_MODDED: "隔离可安装 Mod 的版本",
    ISOLATION_SNAPSHOT: "隔离非正式版",
    ISOLATION_MODDED_SNAPSHOT: "隔离可安装 Mod 的版本与非正式版",
    ISOLATION_ALL: "隔离所有版本",
}
ISOLATION_DEFAULT = ISOLATION_ALL

# ---- 内存 / GC 策略 ----
GC_DEFAULT = "default"
GC_G1 = "g1"
GC_SERIAL = "serial"
GC_CMS = "cms"
GC_KEYS = (GC_DEFAULT, GC_G1, GC_SERIAL, GC_CMS)
GC_LABELS = {
    GC_DEFAULT: "不指定 GC（跟随 Java 默认）",
    GC_G1: "调优 G1GC",
    GC_SERIAL: "Serial 单线程回收",
    GC_CMS: "CMS 并发回收（老版本）",
}
GC_DEFAULT_KEY = GC_G1

# ---- 高级开关默认值 ----
DISABLE_LAUNCH_WRAPPER_DEFAULT = False
DISABLE_LWJGL_UNSAFE_DEFAULT = False
PREFER_DISCRETE_GPU_DEFAULT = False
VERIFY_SSL_DEFAULT = True


