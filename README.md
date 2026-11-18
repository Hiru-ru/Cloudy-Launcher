# Cloudy Launcher（CLY）

- **应用全名**：Cloudy Launcher
- **缩写 / 短名**：CLY
- **当前版本**：`1.1.0`（正式版；启动器与桌宠统一版本号）
- **发布阶段**：正式版（此前的四段版本号均为内部测试版）
- **技术栈**：Python 3.13 + PySide6 6.12（QOpenGLWidget 真 GPU 三维渲染、QtMultimedia 背景音乐）
- **工程性质**：本工程为全新重写版本，不复用旧版任何源码。

## 版本号规则

软件分两个阶段，版本号位数不同：

- **测试阶段（内部测试版，四段号）**：格式 `主版本.次版本.功能序号.bug修复号`（例如 `1.4.4.0`）。新增功能第三位 +1、修复 Bug 第四位 +1，底层语言更换、整体界面形象更换等重大升级才动前两位。测试期启动器最终到 `1.4.4.0`、桌宠最终到 `1.1.2.0`。
- **正式发布（正式版，三段号）**：格式 `主版本.次版本.修订号`（例如 `1.1.0`）。首个正式版启动器与桌宠统一为 `1.1.0`，此后正式版按三段号演进。

## 开源协议与第三方署名

本项目全部源代码以 **GNU GPL v3（GNU 通用公共许可证第 3 版）** 发布，完整许可证见根目录 `LICENSE`；运行时依赖（Python、PySide6/Qt）、构建工具（PyInstaller、Pillow）以及随程序分发的 Minecraft 相关素材（blockrender.dev 渲染图、Mojang 原版 Steve/Alex 皮肤）的许可证与版权方，统一在根目录 `NOTICE.md` 中逐项写明。Minecraft 名称与游戏内纹理为 Mojang Synergies AB / Microsoft 的商标与版权资产，本项目为独立第三方爱好者作品，与 Mojang、Microsoft 无隶属关系。

每个源文件（`cloud_launcher/`、`desktop_pet/` 及入口 `main.py`）顶部均带统一的 SPDX 版权与许可声明：`SPDX-License-Identifier: GPL-3.0-or-later`，版权署名 `Copyright (C) 2026 小鱼`，即按 GPL v3 或其后续版本授权。版权人信息与第三方署名详见 `NOTICE.md`。

## 当前版本范围（正式版 1.1.0）

v1.1.0 是云朵启动器与云朵桌宠的**首个正式版**：启动器与桌宠统一发布、版本号统一为三段号 `1.1.0`。此前的所有版本（启动器四段号演进至 `1.4.4.0`、桌宠四段号演进至 `1.1.2.0`）均为内部测试版，正式版在其全部功能基础上发布。内置 AI 助手保留入口，正式版发布后再持续打磨。

正式版 1.1.0 完整能力：

1. **游戏下载与启动**：原版游戏 / Mod / 整合包 / 光影包 / 资源包 / 数据包六分类搜索与下载，正版 / 离线账号、版本隔离、多线程加速、自动探测 Java 并拉起游戏。
2. **整合包导入导出**：支持 CurseForge、MultiMC/Prism、MCBBS、本地导入，可导出离线完整包、Modrinth .mrpack、MultiMC/Prism、CurseForge、MCBBS 五种格式。
3. **个性化与皮肤**：自定义 Logo、显示名称、壁纸与毛玻璃主题；正版账号自动用正版皮肤、离线账号可导入本地皮肤，内置史蒂夫 / 艾利克斯。
4. **桌宠空闲互动**：3D 角色头部跟随鼠标，空闲随机挥手、拍手、吃东西、跳跃、欢呼、打哈欠、跳舞、摸小狗共 8 个动作，带饥饿值、头顶对话气泡、爱心 / 音符 / 问号 / Zzz 情绪粒子，鼠标一动立刻恢复正常。
5. **驯服狼陪伴**：驯服狼随机进场，可喂狗、摸狗，具备走路 / 摇尾 / 开心 / 被摸动画，停留后自动退场。
6. **困倦睡眠**：长时间空闲先打哈欠、再趴下入睡并周期冒 Zzz，鼠标一动立刻醒来。
7. **功能开关**：「设置 · 桌宠」页可一键全开 / 全关或单独控制空闲小动作、悬停喂食菜单、饥饿值、小狗陪伴、困倦睡觉五项，默认全开；开关只在启动器内，桌宠本身无设置入口。
8. **验证**：两个工程 `compileall` 通过，离屏回归 293/293 全绿，真实窗口渲染确认。

## 历史版本范围（测试版 1.4.4.0 / 桌宠 1.1.2.0）

测试版 v1.4.4.0 是测试期最后一次**功能新增（功能序号 +1）**：围绕桌宠「空闲互动系统」做一批扩展——新增动作、摸狗、困倦/睡眠、情绪粒子，以及只做在启动器里的功能开关。桌宠独立版本同步由 `1.1.1.1` 升至 `1.1.2.0`。

1. **新动作（#505）**：`pet_actions.py` 新增 JUMP / CHEER / YAWN / DANCE，并加 `root_at` 整体位移机制（跳跃腾空、跳舞与欢呼按节拍轻跳）；连同原有 WAVE / CLAP / EAT 与新增 PET 共 8 个动作，空闲时随机触发。
2. **摸狗（#506）**：玩家新增 PET 动作，几何反算让手尖精确落在狗头顶；狼新增 petted 柔和反应（慢摇尾、头向玩家轻蹭、身体微前倾），与喂狗的剧烈开心明确区分；由悬停菜单「摸小狗」条目触发。
3. **困倦 / 睡眠（#507）**：新建 `SleepController`，长时间空闲先打哈欠（气泡「好困啊…」+ YAWN），随后趴下入睡（整体下沉、脚不穿地）并周期冒 Zzz，鼠标一动立刻醒来；基于长时间空闲独立工作，不与饥饿自动进食打架。
4. **情绪粒子（#508）**：新建 `ParticleLayer` 透明覆盖层，自绘爱心 / 音符 / 问号 / Zzz 四种粒子，配合吃东西、喂狗、摸狗、睡眠等场景出现。
5. **功能开关（#509–#511）**：桌宠与启动器各建一份 `pet_features.py` 同口径（idle / hover / hunger / wolf / sleep 五项，默认全开）；config 持久化、`build_argv` 加 `--features` 透传；设置页新增「功能开关」卡片，支持一键全开 / 全关与 5 个独立 iOS 滑块（新建 `ToggleSwitch`）。**开关只做在启动器「设置 · 桌宠」页，桌宠本身不放置任何设置入口。**
6. **验证**：`compileall` 通过；真实窗口渲染确认开关卡片全开 / 全关、摸狗、睡眠、粒子等；离屏回归 291/291 全绿（补功能开关断言、fake 夹具补 pet_features 字段）。

测试版 v1.4.4.0 改动文件：

- 桌宠：新增 `pet_sleep.py`、`pet_particles.py`、`pet_features.py`；修改 `pet_actions.py`、`pet_preview.py`、`pet_wolf.py`、`pet_main.py`、`pet_needs.py`、`pet_feed_menu.py`、`pet_constants.py`（`PET_VERSION` 改为 `1.1.2.0`）。
- 启动器：新增 `pet_features.py`、`ui/toggle_switch.py`；修改 `config_store.py`、`pet_controller.py`、`ui/pet_settings_page.py`、`constants.py`（`APP_VERSION` 改为 `1.4.4.0`、`ABOUT_RELEASE_NOTES` 加条目）。
- 测试 / 文档：`tools/test_v1313_offscreen.py`、新增调试脚本、`README.md`、`说明文档.md`。

## 历史版本范围（1.4.3.0）

v1.4.3.0 是一次**功能新增（功能序号 +1）**：关于页新增「问题反馈」卡，写明作者反馈 QQ，用户使用中遇到任何问题或 Bug 都可以加 QQ 联系作者。

1. **需求**：用户要求把反馈 QQ 加到关于页，作为问题与 Bug 的联系渠道。
2. **常量**：`constants.py` 新增 `AUTHOR_QQ = "2756141828"`，关于页与版本介绍统一引用、便于维护；`APP_VERSION` 升至 `1.4.3.0`，`ABOUT_RELEASE_NOTES` 顶部加本版条目。
3. **关于页结构**：`about_page.py` 由两块改为三块——品牌横条卡（Logo / 名称 / 版本）之后新增「问题反馈」卡（说明文案 + 作者 QQ，号码加粗、支持鼠标选中复制），再下方是「本版本介绍」卡。
4. **验证**：`compileall` 通过；源码真机与打包后 exe 真机（PrintWindow）截图均确认问题反馈卡与 QQ 号显示正常；离屏回归 283/283 全绿（新增反馈 QQ 展示与可复制断言 2 条）。

本轮（v1.4.3.0）改动文件：

- 修改 `cloud_launcher/constants.py`（新增 `AUTHOR_QQ`、`APP_VERSION` 改为 `1.4.3.0`、`ABOUT_RELEASE_NOTES` 加条目）、`cloud_launcher/ui/about_page.py`（新增 `_build_feedback_card`、挂载并更新 docstring）；更新 `tools/test_v1313_offscreen.py` 断言；`README.md`、`说明文档.md`。桌宠代码未改动，仍为 `1.1.0.2`。

## 历史版本范围（1.4.2.0）

v1.4.2.0 是一次**功能新增（功能序号 +1）**：设置页「启动」标签恢复版本隔离与高级功能的全局设置入口，落实用户「复制而非剪切」的口径——这些设置在「启动」标签与版本设置页两处都有，并按「全局默认 + 版本覆盖」协同。

1. **背景**：v1.3.21.0 重构时把版本隔离与高级功能从「启动」标签移到了版本设置页，「启动」标签一度只剩账号管理；用户的本意是把这些设置「复制」到版本设置页，「启动」标签里也应保留。
2. **全局设置面板 `GlobalLaunchConfigPanel`**：在「启动」标签账号管理下方新增「版本隔离」卡（隔离策略）与「高级功能」卡（JVM 参数、游戏参数、启动前命令、Java 列表、GC、内存分配自动/自定义 + 滑条 + 内存优化 + 内存占用只读条、四个高级开关），绑定全局 `ConfigStore`，交互即写全局并落盘。
3. **数据层回退**：`VersionLaunchConfig._read` 改为——某版本有 per-version 覆盖用覆盖；否则回退到全局 `ConfigStore` 同名字段（即跟随「启动」标签），全局也没有才兜底内置默认。
4. **优先级**：per-version 覆盖 > 全局默认 > 内置默认。「启动」标签改的是对所有版本生效的默认值；版本设置页只在想让某版本特殊时单独覆盖，未单独改的版本自动跟随全局。账号身份仍为全局，不进版本设置。
5. **验证**：`compileall` 通过；真机截图确认「启动」标签同时显示账号管理、版本隔离、高级功能且回填正确；离屏回归 281/281 全绿（旧"已移除"断言改"已恢复"，新增全局回退测试 7 项）。

本轮（v1.4.2.0）改动文件：

- 修改 `cloud_launcher/version_launch_config.py`（`_read` 回退源改为全局 store、更新 docstring）、`cloud_launcher/ui/launch_settings_page.py`（新增 `GlobalLaunchConfigPanel`、补控件导入、挂载并刷新、更新 docstring）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.4.2.0`、更新 `ABOUT_RELEASE_NOTES`）；更新 `tools/test_v1313_offscreen.py` 断言；`README.md`、`说明文档.md`。桌宠代码未改动，仍为 `1.1.0.2`。

## 历史版本范围（1.4.1.3）

v1.4.1.3 是一次**缺陷修复（bug 修复号 +1）**，按用户口径明确「桌宠只能由云朵启动器打开，不通过启动器打不开」，修复桌宠可被直接双击独立运行的问题。桌宠独立版本同步由 1.1.0.1 升至 1.1.0.2。

1. **根因**：桌宠入口的命令行参数都有默认值，直接双击 exe（不带任何参数）也能回退内置皮肤正常显示，导致它脱离启动器被单独打开，违背「必须经启动器导入并启动」的设计。
2. **启动器握手**：启动器 `build_argv` 拉起桌宠时新增内部握手标志 `--from-launcher`；桌宠 `pet_main` 启动时校验该标志，只有带握手（由启动器拉起）才显示桌宠窗。
3. **直接双击拦截**：无握手标志时不显示桌宠，弹出提示「云朵桌宠无法单独运行，请在云朵启动器「设置 · 桌宠」页导入并启动」，点确定后退出。
4. **验证**：`compileall` 通过；真机分别验证直接运行（弹提示、无桌宠窗）与带握手运行（桌宠正常显示）两条路径；离屏回归 274/274 全绿（新增握手参数断言）。

本轮（v1.4.1.3）改动文件：

- 修改 `cloud_launcher/pet_controller.py`（`build_argv` 加 `--from-launcher`）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.4.1.3`、更新 `ABOUT_RELEASE_NOTES`）、`desktop_pet/pet_main.py`（加握手参数与校验、无握手弹提示退出）、`desktop_pet/pet_constants.py`（`PET_VERSION` 改为 `1.1.0.2`）；更新 `tools/test_v1313_offscreen.py` 版本断言并补握手断言；`README.md`、`说明文档.md`。

### v1.4.1.2 缺陷修复（黑色小窗）

v1.4.1.2 是一次**缺陷修复（bug 修复号 +1）**，修复真机反馈的「关闭桌宠时会闪现一个黑色小窗」的问题。

1. **根因**：启动器结束桌宠进程时调用系统 `taskkill`，该调用未加静默标志，GUI 程序拉起控制台程序时系统会为其短暂创建一个控制台窗口，即用户看到的黑色小窗。
2. **修复**：`kill_process_tree` 调用 taskkill 时加 `CREATE_NO_WINDOW` 标志并丢弃输出，整树结束进程全程静默，不再弹出任何黑色窗口；同时去掉文本解码，避免中文系统输出编码异常。
3. **验证**：`compileall` 通过；真机脚本在关闭期间高速枚举全部顶层窗口，控制台窗口命中数为 0、进程无残留（BLACKWINDOW_OK）；离屏回归 273/273 全绿。

本轮（v1.4.1.2）改动文件：

- 修改 `cloud_launcher/pet_controller.py`（`kill_process_tree` 加 `CREATE_NO_WINDOW`、静默输出）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.4.1.2`、更新 `ABOUT_RELEASE_NOTES`）；更新 `tools/test_v1313_offscreen.py` 版本断言；新增 `tools/verify_black_window.py`；`README.md`、`说明文档.md`。桌宠本身代码未变，仍为 `1.1.0.1`。

### v1.4.1.1 缺陷修复（关闭/移除）

v1.4.1.1 是一次**缺陷修复（bug 修复号 +1）**，在 v1.4.1.0 新增「桌宠」功能的基础上，修复真机反馈的「关闭桌宠」关不掉、「移除」移除不了的问题。

1. **根因**：桌宠单文件 exe 运行时为 bootloader 父进程 + 渲染子进程两层，旧关闭逻辑只结束父进程，渲染子进程成为孤儿继续显示；且无单实例保护，反复启停累积进程；移除时 exe 被占用导致删除失败。
2. **整树关闭 + 按路径清理**：`pet_controller.py` 新增 ctypes 进程枚举，按 exe 路径匹配全部桌宠进程（含孤儿），以 `taskkill /T /F` 整树结束；`stop_pet` 先取 pid 整树终止，再以 terminate/kill 兜底。
3. **单实例保护**：启动前先清理本次进程与同路径残留，重复点启动不再堆叠多个桌宠。
4. **移除先关后删**：`remove_pet_app` 先强制结束全部相关进程再删除文件，`OSError` 有明确提示，不再静默失败。
5. **桌宠右键退出**：桌宠窗口右键菜单含「退出桌宠」，点击后 `close()` 并显式 `QApplication.quit()`（Tool 窗口 close 不触发应用退出），进程彻底退出、无残留。
6. **验证**：`compileall` 通过；离屏回归 273/273 全绿；真机实测整树关闭、单实例、移除流程、右键退出均无进程残留；启动器冒烟通过。

本轮（v1.4.1.1）改动文件：

- 修改 `cloud_launcher/pet_controller.py`（新增 ctypes 进程枚举、进程树终止、按路径清理，改 `stop_pet / remove_pet_app`）、`cloud_launcher/ui/pet_settings_page.py`（启动单实例、停止/移除/关闭整树加兜底）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.4.1.1`、更新 `ABOUT_RELEASE_NOTES`）、`desktop_pet/pet_main.py`（右键「退出桌宠」并显式退出应用）、`desktop_pet/pet_constants.py`（`PET_VERSION` 改为 `1.1.0.1`）；更新 `tools/test_v1313_offscreen.py` 版本断言；`README.md`、`说明文档.md`。

### v1.4.1.0 功能基线（修复对象）

v1.4.1.0 是一次**功能新增（功能序号 +1）**：新增「桌宠」功能。桌宠是一个**独立做出来的 APP**（当版独立版本号 `1.1.0.0`、本修复版对应 `1.1.0.1`、单独打成一个压缩包），启动器本身不内置，必须在「设置 · 桌宠」页通过**选择文件导入**该 APP 后才能使用。

1. **独立桌宠子工程 `desktop_pet/`**：`pet_preview.py` 复用启动器 `SkinPreview` 的原版三维渲染管线（几何 / UV / 着色器 / 透明合成都在文件内），但去掉了全身刚体转动与待机摆臂，**只保留头部绕颈部枢轴跟随鼠标转动，躯干、双臂、双腿始终静止**；`pet_main.py` 为独立入口，`argparse` 接收 `--skin / --slim / --x / --y`，透明、置顶、无边框窗，`QTimer` 轮询 `QCursor` 驱动头部。
2. **文件选择导入**：`cloud_launcher/pet_controller.py` 支持选择桌宠 `.exe`（直接复制）或其发布 `.zip`（解压取内部 exe，含 zip-slip 防护），统一落盘到 `CLY/pet/云朵桌宠.exe` 并写入 `config.pet_app_path`；未导入时启动按钮禁用，可重新导入或移除。
3. **皮肤口径**：正版账号（`AccountSession.is_microsoft`）桌宠显示正版皮肤，先由 `SkinFetchWorker` 异步下载落盘到 `CLY/pet/official_skin.png` 再启动，**皮肤导入按钮禁用**；离线账号可导入本地皮肤图片（png/jpg/jpeg，复用 `custom_skin` 机制），未导入时用内置史蒂夫 / 艾利克斯。
4. **进程接线**：启动器以 `subprocess.Popen` 子进程拉起桌宠 exe，经命令行参数传入皮肤路径、模型类型与窗口位置；`QTimer` 轮询进程存活，启动器 `shutdown / closeEvent` 经 `pet_page.shutdown()` 只终止本次启动的桌宠进程树，不影响其他程序。
5. **验证**：`compileall` 通过；真机截图离线 / 正版两种口径，确认正版皮肤按钮明显灰化禁用、启动按钮为玻璃胶囊；离屏回归 273 项全绿（新增桌宠程序导入、zip 解析、命令行参数组装、皮肤口径、启停 mock 共 25 条断言）。桌宠独立 exe 真机冒烟通过，`云朵桌宠-v1.1.0.0.zip` 内部为单条目 exe。

本轮改动文件：

- 新增 `desktop_pet/`（独立桌宠子工程）、`cloud_launcher/pet_controller.py`、`cloud_launcher/ui/pet_settings_page.py`；修改 `cloud_launcher/config_store.py`（加 `pet_app_path / pet_window_x / pet_window_y`）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.4.1.0`、更新 `ABOUT_RELEASE_NOTES`）、`cloud_launcher/ui/settings_page.py`（挂载真实桌宠页）、`cloud_launcher/ui/main_window.py`（shutdown 接桌宠收尾）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.23.0）

v1.3.23.0 是一次**界面功能新增（功能序号 +1）**：按手绘线框重构侧栏「关于」页，由原来的居中窄卡片改为上下两块——顶部品牌横条卡（Logo + 名称 + 版本号），下方「本版本介绍」卡逐条列出当前版本要点。

1. **品牌横条卡**：左侧 64×64 Logo，右侧竖排名称（20px 粗体）与版本号（浅色）；Logo / 名称显隐仍跟随设置页个性化开关，版本号始终展示；自定义 Logo / 名称替换口径不变。
2. **本版本介绍卡**：标题「本版本介绍」，正文逐条取 `constants.ABOUT_RELEASE_NOTES`，bullet 前缀、自动换行；要点随版本更新同步改写。
3. **滚动范式对齐打包页**：关于页外层套 `QScrollArea`（`settingsScroll` / `settingsList`），两张磨砂卡片纵向排列，条目增多时可滚动；复用既有 `Card` 局部磨砂与全局样式属性。
4. **验证**：`compileall` 通过；真机截图关于页目检品牌横条与介绍两块布局正常、圆角干净；离屏回归 248 项全绿（新增关于页挂载、版本标签、名称回填、介绍条目齐全、品牌显隐开关口径共 7 条断言）。

本轮改动文件：

- 修改 `cloud_launcher/ui/about_page.py`（重构为品牌横条 + 介绍两块）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.23.0`，新增 `ABOUT_RELEASE_NOTES`）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.22.0）

v1.3.22.0 是一次**功能新增（功能序号 +1）**：在侧栏「打包」页实现整合包导出（打包），把一个已安装实例按规范格式打成压缩包；页面三段式自上而下：选择版本 → 选择打包格式 → 开始打包。

1. **导出后端 `cloud_launcher/modpack_export.py`**：复用导入侧格式键与清单常量；实例文件按黑名单排除底座库、原生库、存档、截图、日志、缓存、核心 jar、版本 profile 与启动器元数据；纯标准库、请求头 UA 纯 ASCII、只读源实例不改写。
2. **四种本地格式**：离线完整包 `.zip`（根目录即游戏内容，无清单）；MultiMC / Prism `.zip`（`mmc-pack.json` + `instance.cfg` + `minecraft/`）；CurseForge `.zip`（`manifest.json` + `overrides/`）；MCBBS `.zip`（`mcbbs.packmeta` + `overrides/`）。
3. **Modrinth `.mrpack`**：mod jar 按文件 sha1 在线反查 Modrinth 版本，命中的进 `index.files`（路径 / 哈希 / 直链 / 大小 / 客户端环境），未收录的兜底进 `client-overrides/`；非 mod 文件随 `client-overrides` 带出；依赖写 `minecraft` 与 `fabric-loader` / `forge` / `neoforge`。
4. **平台 ID 退化壳**：本地元数据只记录 MC 版本与加载器 / 加载器版本，不保存每个 mod 的平台 `projectID` / `fileID` 或哈希映射，因此 CurseForge / MCBBS 无法回溯规范平台 ID，对应清单 `files` 留空、mod 随 `overrides/` 带出，结果提示里如实标注；Modrinth 反查不到的模组同样随覆盖文件带出。
5. **后台线程与打包页**：`cloud_launcher/ui/export_worker.py` 的 `ExportPackWorker(QThread)` 转发阶段、进度、成功、失败信号；`cloud_launcher/ui/package_page.py` 打包页三张卡——版本下拉复用实例扫描结果、格式下拉五项并随格式切换说明、开始打包主按钮；保存对话框默认桌面、按别名补扩展名；主窗口切到打包页时重扫版本列表。
6. **验证**：`compileall` 通过；真机 ImageGrab 打包页两段目检三段布局与格式说明联动正常；离屏回归 241 项全绿（新增四格式结构、MMC 组件、CF/MCBBS 退化壳、MR 全映射 / 全兜底分流、打包页挂载断言）；真实 XPlus 实例离线打包 421 个文件、Worker 跨线程信号回传正常；Modrinth 全量反查实测 80 个映射、7 个兜底。

本轮改动文件：

- 新增 `cloud_launcher/modpack_export.py`、`cloud_launcher/ui/export_worker.py`、`cloud_launcher/ui/package_page.py`；修改 `cloud_launcher/ui/main_window.py`（挂载真实打包页、切到打包页重扫版本）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.22.0`）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.21.0）

v1.3.21.0 是一次**功能新增（功能序号 +1）**：把启动设置页里除「账号管理」外的全部启动相关设置（版本隔离 + 高级功能）搬进版本设置页的「设置」标签，让每个版本独立设计、独立保存；启动设置页最终只保留账号管理。

1. **按版本独立的配置视图**：新增 `cloud_launcher/version_launch_config.py` 的 `VersionLaunchConfig` 视图类。覆盖层保存在 `ConfigStore` 的 `version_settings` 字段（dict，key=版本别名），某字段未覆盖时回落到 `DEFAULT_CONFIG` 内置默认；对外属性接口与 `ConfigStore` 对齐（隔离策略、GC、内存模式/上限、JVM/游戏参数、启动前命令、Java 路径、五个 bool 开关），`java_runtime` 用 getattr 读 config 时零改动复用。
2. **启动设置页瘦身**：移除「版本隔离」与「高级功能」两张卡，只留「账号管理」；`_physical_memory_mb`、`_ComboPopup`、`_GlassComboBox`、`_NoWheelSlider` 等共享控件保留，供版本设置页单向导入。
3. **版本设置页做实**：「设置」标签从骨架提示改为两张卡——版本隔离（隔离策略 + 提示）与高级功能（JVM 多行、游戏参数、启动前命令、Java 列表 + 刷新、GC、内存分配自动/自定义 + 滑条 + 内存优化 + 真实内存占用只读条、四个开关），进入版本时回填该版本独立配置。
4. **回填不落盘**：回填期间对全部控件统一 blockSignals，仅查看版本不会把默认值固化成覆盖，只有用户真正交互才落盘；未自定义的版本始终用内置默认。
5. **启动链路**：`profile_page` 启动某版本时先用 `VersionLaunchConfig(store, alias)` 包裹，再交给 `LaunchWorker`；账号相关（player_name、离线账号、正版会话）仍为全局，不进版本设置。
6. **验证**：`compileall` 通过；真机 ImageGrab 两页目检（启动页只剩账号、版本设置页两卡渲染正常、圆角干净）；离屏回归 205 项全绿（新增 per-version 数据层 / UI / 回填副作用 / 启动链路断言）。

本轮改动文件：

- 新增 `cloud_launcher/version_launch_config.py`；修改 `cloud_launcher/config_store.py`（`DEFAULT_CONFIG` 加 `version_settings`、`load()` 加结构校正）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.21.0`）、`cloud_launcher/ui/launch_settings_page.py`（瘦身只留账号、清理 import、更新 docstring）、`cloud_launcher/ui/version_settings_page.py`（设置标签做实、回填与事件）、`cloud_launcher/ui/profile_page.py`（启动处用版本视图包裹）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.20.4）

v1.3.20.4 是一次**缺陷修复（bug 修复）**：修复设置页下拉弹窗 / 账号悬停菜单在卡片圆角外露出系统直角实线（用户拍屏所见「方形角」）的问题。

1. **根因**：`_ComboPopup` 与 `_AccountMenu` 都是 `Qt.Popup` 顶层窗口，Windows DWM 默认给这类窗口附加系统投影，投影沿窗口的**直角矩形**边缘绘制；即便内部 Card 用圆角 QPainterPath 绘制，圆角外仍沿窗口直角边缘露出约 1px 深色线，形成可见的方形角。
2. **修复**：两处窗口的 `setWindowFlags` 在 `Qt.Popup | Qt.FramelessWindowHint` 基础上追加 `Qt.NoDropShadowWindowHint`，关闭系统 DWM 投影；`WA_TranslucentBackground` 保持开启，圆角外区域维持透明。最小实验对照确认：仅 `Qt.Popup` 时出现直角线，追加该标志后直角线消失、圆角干净。
3. **零业务改动**：弹窗的磨砂 / 通透 / 普通三档材质、数据模型、信号与交互逻辑均不变；`Qt.Dialog` 类型的添加账号窗口本就不带该投影，无需处理。
4. **验证**：`compileall` 通过；真机 ImageGrab 三档下拉与账号菜单目检圆角干净；沙箱回归 184 项全绿（新增 2 条 NoDropShadow 断言）。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.20.4`）、`cloud_launcher/ui/launch_settings_page.py`（`_ComboPopup` 与 `_AccountMenu` 窗口标志追加 `Qt.NoDropShadowWindowHint`、更新 docstring）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.20.3）

v1.3.20.3 是一次**交互打磨（bug 修复）**：解决下拉框 / 内存滑条在鼠标悬停滚动页面时被滚轮误改的问题，并把下拉框原本简陋的系统弹窗替换为跟随全局材质、可在磨砂 / 通透 / 普通间切换的玻璃面板。

1. **禁止滚轮误触**：3 个下拉框（版本隔离、Java、GC 策略）与内存滑条重写 `wheelEvent`，滚轮事件一律 `ignore()`，不再改变选中项 / 数值，事件回传给父级滚动区正常滚动页面；只能点击选择或拖动。
2. **下拉弹窗玻璃化**：新增 `_GlassComboBox` 重写 `showPopup`，弹出自定义 `_ComboPopup`（无边框、透明背景，内含 Card + 透明 QListView 共享 combo 的 model），显示前抓取父窗真实渲染做 live 背景，真正模糊后方内容而非白板。
3. **三档材质切换**：下拉弹窗跟随 `appearance.glass_mode`，在磨砂（frost）/ 通透（clear）/ 普通（normal）间切换，复用个性化页已有的全局切换；数据模型与 `currentIndexChanged` 信号不变，业务逻辑零改动。
4. **验证**：`compileall` 通过；真机 ImageGrab 抓 DWM 真实合成三档目检通过；沙箱回归 182 项全绿（新增滚轮 / 弹窗 11 条断言）。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.20.3`）、`cloud_launcher/ui/launch_settings_page.py`（新增 `_GlassComboBox` / `_ComboPopup` / `_NoWheelSlider`、禁滚轮、自定义磨砂弹窗、更新 docstring）、`cloud_launcher/ui/theme.py`（下拉视图透明 QSS）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.20.2）

v1.3.20.2 是一次**缺陷修复（bug 修复）**：修复从正版切换到离线时正版账号被直接删除（本地登录凭据被清除、需重新登录）的问题。现在「切换账号」与「退出登录」语义分离——切换只改变当前活动身份、保留正版登录凭据，离线态可一键静默续期切回；只有明确点「退出登录」才清除凭据。

1. **切换不再删凭据**：`_switch_to_offline` 只切内存会话（`session.switch_offline`），不再调 `account_store.clear()`，`account.json` 保留。
2. **离线态可切回正版**：新增 `_switch_to_official`，复用 `AccountRestoreWorker` 用本地 refresh_token 静默续期，成功后切回正版并回写轮换令牌；续期失败（令牌失效）才清除并提示重新登录。
3. **弹窗同步**：离线态切换弹窗列出已保存的正版账号（置顶、非当前），点击即切回；当前离线账号标注「（当前）」。
4. **线程收尾**：启动页新增 `shutdown()`，主窗口关闭时等待在途续期线程，避免线程被析构触发原生崩溃。
5. **验证**：`compileall` 通过；沙箱回归 171 项全绿（新增切换保留凭据 / 切回场景 11 条断言）。

历史改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.20.2`）、`cloud_launcher/ui/launch_settings_page.py`（切换保留凭据、新增 `_switch_to_official` / `_saved_official` / `shutdown`、更新 docstring）、`cloud_launcher/ui/main_window.py`（shutdown 收尾启动页线程）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.20.1）

v1.3.20.1 是一次**缺陷修复（bug 修复）**：修复切换账号二级弹窗在正版登录时只列出离线账号、当前正版账号不显示的问题；现在弹窗同时列出当前正版账号与全部离线账号，当前账号（无论正版 / 离线）标注「（当前）」并置顶，点选当前项仅关闭弹窗，点选离线账号即切换。

1. **正版条目补全**：`_build_switch_menu` 先判断当前会话，处于正版（`session.is_microsoft`）时把当前正版账号作为第一项、后缀「（当前）」，点击不切换仅关闭。
2. **离线条目保持**：离线账号照常列出，当前离线昵称标注「（当前）」，其余点击调 `_switch_to_offline` 切换。
3. **底层模型不变**：仍为单份 `AccountSession` / `AccountStore`，多正版账号并存与真实会话切换仍属后续链路。
4. **验证**：`compileall` 通过；沙箱回归 160 项全绿（新增正版会话场景 6 条断言）。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.20.1`）、`cloud_launcher/ui/launch_settings_page.py`（`_build_switch_menu` 补正版当前条目、更新模块 docstring）；更新 `tools/test_v1313_offscreen.py` 回归断言；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.20.0）

v1.3.20.0 是一次**账号切换交互调整（功能调整）**：三点菜单不再把其他账号平铺成多条「切换到 X」，改为统一的「切换账号」入口，点击后弹出二级磨砂弹窗，列出全部已添加账号，当前账号标注「（当前）」，点选任一账号即切换。

1. **统一切换入口**：主菜单（`_AccountMenu`）在「＋ 添加账号」下方仅放一条「切换账号」（仅当存在其他可切换账号时显示），删除原逐条平铺的「切换到 <name>」。
2. **二级选择弹窗**：点击「切换账号」经 `_build_switch_menu` / `_open_switch_menu` 构建标题为「切换账号」的二级 `Qt.Popup`，列出 `config.offline_accounts` 全部账号，当前账号后缀「（当前）」，点击项调 `_switch_to_offline` 切换并关闭弹窗；二级弹窗延迟一事件循环弹出，避免焦点抢占闪烁。
3. **底层模型不变**：`config.offline_accounts`、单份 `AccountSession` / `AccountStore` 及添加 / 重命名 / 移除 / 皮肤导入导出等方法原样保留，仅改切换的界面呈现。
4. **验证**：`compileall` 通过；沙箱回归 154 项全绿；真实窗口截图目检主菜单入口、二级弹窗磨砂与当前标注、点选后账号行正确刷新。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.20.0`）、`cloud_launcher/ui/launch_settings_page.py`（`_AccountMenu` 标题可配置，新增 `_build_switch_menu` / `_open_switch_menu`，`_open_account_menu` 改用统一切换入口，补 QTimer 导入）；更新 `tools/test_v1313_offscreen.py` 回归断言；新增 `tools/shot_switch_menu_13200.py`；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.19.0）

v1.3.19.0 是一次**账号管理界面重构（功能调整）**：设置 → 启动 → 账号管理不再平铺重复显示同一账号，只保留**当前这一个账号行**（离线就只显示离线账号，正版显示正版账号），鼠标悬停账号行时右侧浮现「⋯」三点按钮，点击弹出磨砂菜单，统一承载添加账号、切换账号、重命名、导入/导出皮肤、退出登录/移除账号等操作。

1. **单行展示当前账号**：删除旧的状态行、离线昵称输入框、平铺账号列表三处重复内容，账号卡片只放一个 `_AccountRow`（类型胶囊 + 昵称 + 截断 UUID，整行 tooltip 显示完整 UUID），默认三点按钮隐藏。
2. **悬停三点 + 磨砂菜单**：鼠标进入账号行浮现「⋯」，点击弹出 `Qt.Popup` 磨砂菜单 `_AccountMenu`——「＋ 添加账号」、其他离线账号「切换到 <name>」、离线「重命名账号」、「导入皮肤 / 导出皮肤」，正版 danger「退出登录」、离线 danger「移除账号」；点击菜单外部自动关闭。
3. **底层模型不变**：`config.offline_accounts`、单份 `AccountSession` / `AccountStore` 与增删切换、登录、皮肤导入导出等底层方法原样保留，仅改界面呈现与交互入口；重命名同步替换 `config.player_name` 与离线列表，重名拦截。
4. **验证**：`compileall` 通过；沙箱回归 148 项全绿；真实窗口截图目检默认单行、悬停三点浮现、菜单浅色磨砂、切换后账号行正确刷新。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.19.0`）、`cloud_launcher/ui/launch_settings_page.py`（新增 `_RenameAccountDialog` / `_AccountRow` / `_AccountMenu`，重写账号卡片构建、刷新与菜单/重命名/移除，删除旧平铺列表与孤儿方法，补 QFrame/QCursor 导入）、`cloud_launcher/ui/theme.py`（新增 menuItem / menuSeparator 及 danger 态 QSS）；更新 `tools/test_v1313_offscreen.py` 回归断言；新增 `tools/shot_account_menu_13190.py`；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.18.0）

v1.3.18.0 是一次**界面入口收敛（功能调整）**：删除主页（启动个人页）右上角的「离线 / 正版」分段按钮，账号的添加、类型选择、切换与移除统一到 设置 → 启动 → 账号管理，主页只保留当前账号状态展示。

1. **移除主页模式按钮**：删除个人页顶部并排的「离线 / 正版」两个 SpringPushButton 及仅服务于它们的切换方法与按钮选中态刷新逻辑；顶部不再保留空行，名称卡 / 统计卡 / 人物卡布局对齐不变，窗口尺寸仍 980×660。
2. **账号管理统一入口**：账号的添加（加号弹窗选离线 / 正版）、多离线账号切换、正版设备码登录、退出与移除全部在 设置 → 启动 → 账号管理完成；设置页任一账号操作后仍调用 `profile_page.refresh()`，主页按当前会话状态回填昵称、UUID 与角色，显示链路不依赖被删按钮。
3. **保留项**：名称卡内正版信息行的「退出登录」按钮与 `AccountSession` / `AccountStore` 底层会话、持久化模型原样保留，不改动账号与会话模型。
4. **验证**：`compileall` 通过；沙箱回归保持 145/145 全绿；真实窗口 PrintWindow 截图目检主页顶部已无按钮、设置页切换账号后主页昵称与角色正确刷新。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.18.0`）、`cloud_launcher/ui/profile_page.py`（删除顶部模式按钮、按钮选中态刷新与仅服务按钮的切换方法，移除不再使用的 `MsLoginDialog` 导入，更新模块文档）；新增 `tools/shot_home_no_mode_13170.py` 主页目检脚本；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.17.0）

v1.3.17.0 是一次**功能增强**：设置页「启动」标签的账号管理区从单账号直连改造为**多账号列表**，支持同时保存多个离线账号，正版账号入口收进统一的添加弹窗。

1. **加号添加弹窗**：删除账号区直连的「正版登录」按钮，改为「＋ 添加账号」按钮；点击弹出类型选择窗，先选「离线账号（本地昵称，无需联网）」或「正版账号（微软设备码登录）」。离线需填写昵称，昵称框可编辑；选正版时昵称框禁用，走既有微软设备码登录链路。
2. **离线多账号**：离线昵称列表持久化到 `config.offline_accounts`（去空白、去重、保序），旧配置无列表时用当前昵称回填一条；账号条目按类型显示「离线 / 正版」胶囊、昵称、UUID（条目内截断显示前 8 位，完整 UUID 收进悬停提示）与「当前」标记；点条目切换为当前离线身份，点条目右侧「×」移除该账号，移除当前昵称时回退到列表首条或默认 Steve。
3. **正版条目口径**：当前已登录的正版会话在列表中单独显示一条；多正版账号并存、切换真实会话身份与令牌持久化仍沿用既有单份 `AccountSession` / `AccountStore` 模型，属后续链路，本轮不在启动身份链路伪造多正版切换效果。
4. **回归补断言**：离屏回归新增加号入口存在、旧直连按钮已移除、离线账号添加 / 重名不重复 / 移除落盘、条目数与列表一致、弹窗默认离线、切到正版类型、正版类型禁用昵称框等断言，总数升到 145 项；真实窗口 PrintWindow 截图核对列表条目、类型胶囊与弹窗布局。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.17.0`）、`cloud_launcher/config_store.py`（`offline_accounts` 默认值、load 校正与便捷属性）、`cloud_launcher/ui/launch_settings_page.py`（账号区重构为多账号列表、新增 `_AddAccountDialog`、增删切换 / 登录方法）、`cloud_launcher/ui/theme.py`（账号条目行 / 类型胶囊 / 当前标记 / 昵称样式）；更新 `tools/test_v1313_offscreen.py` 回归断言与截图脚本；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.16.0）

v1.3.16.0 是一次**功能增强**：设置页「启动」标签从空骨架做实，按两张手绘草图落地账号管理、版本隔离、高级功能三块（高级功能内含独立的内存分配块）。

1. **账号管理**：离线昵称可编辑并保存；正版登录 / 退出沿用既有微软会话链路；本地皮肤导入 / 导出复制到 CLY 自定义皮肤目录并落配置。
2. **版本隔离**：五档隔离策略（关闭 / 仅可装 Mod / 仅非正式版 / 可装 Mod 与非正式版 / 隔离所有版本），隔离开启后各版本存档、配置与模组互不干扰，关闭则共享全局 `.minecraft` 目录；目录解析由 `resolve_game_dir` 按策略落到全局目录或版本独立目录。
3. **高级功能**：JVM 参数多行框、游戏参数、启动前命令、Java 列表下拉（自动探测 / 手动指定）+ 刷新、GC 调优下拉；内存分配独立块——自动配置 / 自定义单选、内存滑条、启动前内存优化勾选、底部只读内存条（已用 / 总量、游戏分配）；另有禁用 Launch Wrapper、禁用 LWJGL Unsafe Agent、高性能显卡、正版 SSL 验证四个开关。启动命令组装已接入自定义内存、GC 旗标、用户 JVM / 游戏参数。
4. **口径说明（本轮仅落配置、链路后接）**：启动前命令实际执行、四个本机开关的生效手段、本地导入皮肤在角色预览的渲染、按版本类型细分隔离目录规则，本轮先存配置与界面，不在启动链路伪造生效效果。
5. **回归补断言**：离屏回归新增启动页控件齐全、配置回填、交互落盘、隔离目录解析、命令组装含内存 / GC / JVM / 游戏参数等断言，总数升到 134 项；真实窗口 PrintWindow 截图核对三块布局无白板、无溢出。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.16.0`，新增隔离 / GC / 开关默认常量）、`cloud_launcher/config_store.py`（13 个启动设置字段默认值、load 校正与便捷属性）、`cloud_launcher/java_runtime.py`（`list_java` / `resolve_java` / `resolve_game_dir`，GC / 内存 / 自定义参数注入）、`cloud_launcher/ui/launch_worker.py`（Java 解析与工作目录接入新函数）、`cloud_launcher/ui/settings_page.py`（挂载启动页、切标签刷新）、`cloud_launcher/ui/theme.py`（字段标签 / 多行框 / 勾选 / 单选 / 内存条样式）；新增 `cloud_launcher/ui/launch_settings_page.py`；更新 `tools/test_v1313_offscreen.py` 回归断言与截图脚本；`README.md`、`说明文档.md`。

## 历史版本范围（1.3.15.1）

v1.3.15.1 是一次**缺陷修复（bug 修复）**：用户在版本设置页改名后，主页（启动个人页）「游戏版本」横条仍显示旧名字，要重启程序才更新。

1. **根因**：改名链路本身没问题——版本目录、版本 JSON 文件名、install_meta 的 alias 都已跟随新名，且当当前选中版本正是被改名的版本时，`config.selected_version` 也已正确改写并保存。问题出在返回主页的接线：版本设置页的 `closed` 信号原本只切回主页（`_switch_page("launch")`），没有让个人页重新扫描版本，而横条右侧别名与版本选项列表只在 `refresh_version_list()` 里重建，QStackedWidget 切回不会触发该方法，旧文本于是一直残留。
2. **修复**：主窗口新增 `_close_version_settings()`，返回前先调 `profile_page.refresh_version_list()` 重扫已安装版本再切回主页，横条别名与版本选项按钮即时反映新名；同一条返回路径也覆盖删除版本后的列表刷新。
3. **回归补断言**：离屏回归新增「返回前/后横条文本、config 指向、返回后切回个人页、版本选项含新名不含旧名」等 8 项端到端断言，总数升到 106 项。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.15.1`）、`cloud_launcher/ui/main_window.py`（`closed` 改接新增的 `_close_version_settings`，返回前刷新个人页版本列表）、`tools/run_reg_sandbox.py`（沙箱同时重定向 `resources.app_base_dir`，隔离 config 路径）、`tools/test_v1313_offscreen.py`（版本断言更新与新增）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.15.0）

v1.3.15.0 是一次**功能增强**：版本设置页「修改」分区按 HMCL 风格参考图重做，MC 底座版本号和加载器版本号都能点开选择，不再只能沿用安装时探测到的那一个。

1. **MC 底座版本可点选**：点「Minecraft」行，首次后台拉取版本清单（缓存优先），弹出选择窗按正式版 / 预览版 / 远古版分组列出全部底座，每行版本号右侧带发布时间，当前版本高亮；点行即选定。
2. **加载器全部版本内联展开**：选中某个加载器后，卡片内直接展开「全部版本 (N)」列表（不再另弹小窗），每个版本号右侧带发布时间，点行即切换；再次点已选中的行收起 / 展开。当前加载器版本行在版本号下方显示副标题「发布于 yyyy/MM/dd HH:mm」。
3. **mod 较多时锁定**：该版本已装 mod 达到 20 个及以上时，判定为内容较多、切换版本 / 加载器极易不兼容，版本名、MC 行、各加载器行与「开始修改」按钮全部禁用并拦截，提示文案说明阈值；整合包版本仍按原口径整体锁定。
4. **换底座风险提示**：MC 底座与原版本不同时，开始修改确认框追加提示——旧版本专属文件会保留、已装 mod 可能与新版本不兼容；同时装有内容时再补一句更换底座提醒。补齐文件仍沿用原底座，不受新选版本影响。
5. **回归补断言**：离屏回归新增 MC 弹窗分组 / 时间格式化 / 滚动区命名、内联列表展开 / 选项数 / 计数文案 / 点选切换 / 副标题、mod 阈值锁定与拦截等断言，总数升到 98 项。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.15.0`）、`cloud_launcher/ui/version_settings_page.py`（新增 `_McVersionDialog`、可复用 `_VersionRow`、`LoaderRow` 重构为顶部行 + 内联展开体、MC 行点选拉清单弹窗、内联点选切换、mod 阈值锁定、当前版本副标题与时间格式化）、`cloud_launcher/ui/theme.py`（`mcVersionScroll` 透明规则、内联行浅色块 / hover / 选中描边、展开体透明、副标题样式，清理旧弹窗死规则）、`tools/test_v1313_offscreen.py`（回归断言更新与新增）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.7）

v1.3.14.7 是一次**缺陷修复（bug 修复）**，修的都是真机跑出来的三个问题：重命名弹窗的「确定」按钮是方的、和圆角的「取消」格格不入；点重命名直接报「修改失败：KeyError 清单中找不到版本 请问」；发现新版本弹窗说「已加入最新版本」，但版本列表里根本看不到，必须重启一次才出现。

1. **弹窗按钮为什么是方形（Bug1）**：Qt 的 QSS 有条隐性规则——`border-radius` 一旦超过控件高度的一半，Qt 会**直接丢弃整条圆角声明**、渲染成直角。「确定」按钮高 40（半高 20），却套用了主窗口「开始游戏」按钮那套圆角 22 的胶囊规则（22 > 20），圆角被判非法丢弃，于是变方形；「取消」按钮走的是另一套圆角 12 的规则，所以正常。修复：弹窗两个按钮统一固定高 36、最小宽 96，主按钮改用新增的 `dialogPrimary` 属性，`theme.py` 补一整段圆角 12、含 hover / pressed / disabled 四态的 `dialogPrimary` 样式块；取消按钮仍是 `modeButton`。主窗口 44 高、圆角 22 的胶囊规则保持原样，不受影响。
2. **重命名为什么报 KeyError（Bug2）**：两个独立缺陷叠在一起。其一，`update_install_meta` 的第一个参数原本也叫 `alias`，而 `rename_version` 末尾写的是 `update_install_meta(new, alias=new)`——位置参数和关键字参数同名，**必然抛 TypeError**，而且这行在目录与 JSON 已经改名之后才执行，结果 meta 的 alias 没更新、页面也不刷新。首参已改名为 `target_alias`，调用恢复正常。其二，对没有 `client.jar`、没有 `install_meta` 的外部版本（用户实例里的 26.2 就是这类，目录里只有一个 json），`show_version` 旧逻辑 `entry.mc or meta.mc or alias` 最终把**用户起的别名**当成真实 MC 版本号，拿它去远程清单里定位，清单里当然没有这个别名，于是抛「清单中找不到版本 请问」。修复：新增 `game_dirs.local_version_base()`，从本地版本 JSON 的 `inheritsFrom`（加载器 profile 的真实底座）或 `id` 解析真实 MC 版本；`scan_installed_entries` 推导 mc 也改用同一口径；别名只作最后兜底。
3. **发现新版本为什么必须重启（Bug3）**：后台版本检查成功后，`_on_check_succeeded` 旧逻辑只把新清单写进缓存，源码注释还明写着「不调用 `_apply_meta`，下次启动自动使用新清单」——即推迟刷新本来是刻意设计，但弹窗文案却写「已加入最新版本」，两者自相矛盾。修复：检查成功后先 `_apply_meta()` 更新内存清单并重绘四个分组（`set_list_data` 不触碰 `_expanded`，各分组展开态保留），再写缓存，新版本当场出现在列表里。
4. **回归补断言**：离屏回归新增弹窗按钮属性与同高、外部版与无 meta 加载器版本的底座解析、已装条目 mc 不取 loader id 等 11 项断言，总数升到 83 项；后台检查后列表即时刷新另用沙箱脚本验证 5 项断言。
5. **合规收尾（打包阶段发现）**：PySide6 的打包钩子会把 Qt Virtual Keyboard 一并收进 exe，而它在 Qt 6.12 里属 GPLv3-only / 商业授权的附加模块，本项目从未使用。`build.spec` 已在 `EXE` 之前把它及其 `platforminputcontexts` 插件剔除；对成品 exe 的归档检测结果为 0 个 GPL-only 模块，`NOTICE.md` 同步写明这一点。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.7`）、`cloud_launcher/ui/version_settings_page.py`（`_dialog_button` 改 `dialogPrimary` + 统一 h36，`show_version` 的 mc 版本接 `local_version_base`）、`cloud_launcher/game_dirs.py`（`update_install_meta` 首参改 `target_alias`，新增 `local_version_base`，`scan_installed_entries` 的 mc 改用同一口径）、`cloud_launcher/ui/theme.py`（新增 `dialogPrimary` QSS 块）、`cloud_launcher/ui/download_page.py`（`_on_check_succeeded` 改为即时 `_apply_meta` + 存缓存）、`build.spec`（剔除 GPL-only 的 Qt Virtual Keyboard）、`NOTICE.md`、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.6）

v1.3.14.6 是一次**缺陷修复（bug 修复）**：版本设置页「概览」里，「高级设置」原本只是一张写着「高级设置项将在后续版本按需接入」的空卡，而「补齐文件」「删除版本」两个操作按钮却浮在卡片外面、另起一排，归属关系不对。

1. **两个操作按钮收进「高级设置」卡内**：卡片标题下先用一行说明文字讲清两个按钮各自的作用（「补齐文件」修复缺失或损坏的版本文件；「删除版本」一并移除该版本的全部文件），下面并排放「补齐文件」「删除版本」两个按钮，卡外不再有独立的一排按钮。
2. **回归补断言**：新增高级设置卡数量、卡内两个按钮、按钮属性、无标题空卡不再放操作按钮等 4 项断言，总数升到 72 项。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.6`）、`cloud_launcher/ui/version_settings_page.py`（合并 `_build_advanced_card` 与原 `_build_danger_row`，按钮收进卡内）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.5）

v1.3.14.5 是一次**缺陷修复（bug 修复）**：用户实例里同一游戏版本（如 26.3）装了多个版本条目（默认命名、自己改的名、整合包版等），但下载内容时弹出的「下载到哪个版本」浮层只按「原生版本号 · 加载器」做标签，多个同版本同加载器的条目标签完全一样，无法区分要下到哪个实例。

1. **标签改为以版本别名（即启动器里显示的版本名 / 版本目录名）为主**：每个条目先显示自己的别名，再补充原生版本号与加载器（如「26.3 备份 · 26.3 · Fabric」）；别名与原生版本号相同时不重复展示（默认命名的条目仍显示「26.3 · Fabric」）。这样同版本的多个实例标签不再重名，点「下载」前就能看清目标版本与加载器。
2. **长名字截断**：标签超过 30 字时按字数截断并加「…」，完整名称与隔离目录放在 tooltip 里，不会把按钮撑变形。
3. **回归补断言**：新增下载目标浮层条目数、标签不重复、标签以别名开头、标签含加载器、默认选中与选中条目返回等 6 项断言，总数升到 68 项。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.5`）、`cloud_launcher/ui/content_search_view.py`（`ContentVersionPicker._build_list` 标签改为别名优先 + 长名截断 + tooltip 补全）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.4）

v1.3.14.4 是一次**缺陷修复（bug 修复）**：依据用户真机截图，修下载进度弹窗（`TaskProgressDialog`，整合包 / mod / 光影包等下载时弹出的竖向进度卡片）没有磨砂模糊、背后内容原样透上来的问题，并顺带堵上同类的加载器版本选择弹窗。

1. **进度弹窗此前压根没抓真实背景**：`TaskProgressDialog` 只放了 `Card`，既没设 `reference_window`，也没在显示前调 `capture_live_backdrop`，`Card` 只能按弹窗自身窗口当坐标基准、且无壁纸时仅画半透明白渐变，于是背景卡片文字原样透上来、看起来像一层薄白膜而不是磨砂玻璃。现补齐与 `_GlassDialog` 同一套机制：构造时以父窗口为磨砂采样基准，`showEvent` 首次显示前抓父窗口真实渲染（清晰图 + 短边 100 预模糊图）注入 `Card`，并居中夹在父窗口客户区内，避免卡片越出快照范围出现无内容黑边。
2. **进度弹窗阶段列表滚动区不透明**：内部 `QScrollArea` 及其 viewport 没有 objectName、也没有透明 QSS，viewport 按默认 palette 画出不透明白底，盖住卡片中部的磨砂（表现为一块死白方块）。现命名 `taskPhaseScroll`，并在全局样式表补齐自身与直接子 viewport（`> QWidget`）的透明规则。
3. **加载器版本选择弹窗同类问题一并修复**：`_LoaderVersionDialog` 的版本列表滚动区同样未命名、未透明，现命名 `loaderVersionScroll` 并补同类透明规则，版本列表区域不再盖住磨砂。
4. **回归补断言**：离屏回归新增 `taskPhaseScroll` / `loaderVersionScroll` 命名断言、三条滚动区透明 QSS 规则存在性断言，以及加载器版本弹窗磨砂基准断言，总数升到 62 项。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.4`）、`cloud_launcher/ui/task_progress_dialog.py`（滚动区命名 `taskPhaseScroll`、新增 `showEvent` 抓 live 背景 + 客户区居中）、`cloud_launcher/ui/version_settings_page.py`（`_LoaderVersionDialog` 滚动区命名 `loaderVersionScroll`）、`cloud_launcher/ui/theme.py`（新增 `taskPhaseScroll` / `loaderVersionScroll` 及 viewport 透明规则）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.3）

v1.3.14.3 是一次**缺陷修复（bug 修复）**：依据用户真机反馈与截图，修内容列表弹窗（mod/光影包/材质包/数据包四类，即 `_ContentListDialog`）背景呈均匀浅灰、看不到磨砂模糊、透不出光的问题。

1. **修复内容列表弹窗滚动区不透明、盖住磨砂**：弹窗内部的 `QScrollArea` 及其 viewport 此前没有 objectName、也没有任何透明 QSS 规则，viewport 按默认 palette 绘制不透明背景，铺满卡片中部，把 `Card.paintEvent` 自绘的真实背景 live 模糊完全盖住，只剩滚动区上方标题/总开关处能看到玻璃，于是整片看起来是均匀浅灰白板。现给该滚动区命名 `contentListScroll`，并在全局样式表新增 `QScrollArea#contentListScroll` 自身与直接子 viewport（`> QWidget`）的透明规则，与工程内其他命名滚动区（page-scroll、content-scroll、settingsScroll 等）一致，卡片自绘的 live 模糊得以完整透出，玻璃感保留、不退回白板。内部行 chip（contentRow/contentMasterRow）本就是半透明，无需改动。
2. **回归补断言**：离屏回归新增滚动区 objectName 与透明 QSS 规则存在性断言，防止再次回退为不透明视口。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.3`）、`cloud_launcher/ui/version_settings_page.py`（`_ContentListDialog` 的滚动区命名 `contentListScroll`）、`cloud_launcher/ui/theme.py`（新增 `QScrollArea#contentListScroll` 及 viewport 透明规则）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.2）

v1.3.14.2 是一次**缺陷修复（bug 修复）**：依据用户最新两张截图与明确口径「白板给我删掉，我不需要白板，反正只要能看清就行了」，修两个在真实（无壁纸）环境下暴露的界面问题——整合包「选择版本并命名」浮层在密集卡片背景上文字叠字看不清、版本设置页概览四个内容计数按钮（mod/光影包/材质包/数据包）都是白板。

1. **弹窗改为抓取真实背景的磨砂玻璃（不再只模糊壁纸）**：上一版磨砂体系的前提是主窗口注入一张壁纸，用户用默认空白背景时没有壁纸源，`paint_frosted_panel` 只画三段半透明白渐变，父级已渲染的密集卡片文字透过低 alpha 白渐变显示，造成叠字。现新增 `capture_live_backdrop()`，在模态弹窗显示前用 `QWidget.grab()` 抓取父控件整棵已渲染子树（含卡片文字），按短边 100 降采样得到预模糊图作为底板；`paint_frosted_panel` 新增 `live` 参数，以父控件为坐标基准铺这张模糊图，再叠白玻璃渐变，既压得住卡片文字、又保持玻璃观感，不做白板。`ModpackInstallDialog`、`Card`、`_GlassDialog` 均已接入。
2. **修复四个计数按钮白板**：这四个按钮原先用与其他功能键共用的 `modeButton` 样式（白色半透明填充压在浅色卡片上呈白片）。现给它们单独立 `countButton` 玻璃 chip 样式，把白填充进一步收淡（alpha 42）、靠细边与 hover 保持可点感，深色文字仍清晰可辨，不再是白板；不影响其他 `modeButton` 按钮。
3. **修复弹窗越界产生的无内容黑边**：弹窗若被放到主窗口客户区之外，卡片超出快照范围的部分没有源像素，会出现灰黑条。现 `_GlassDialog` 新增客户区居中逻辑，用全局坐标（`mapToGlobal`）相减计算原点并夹在客户区内；同时 `paint_frosted_panel` 改用全局坐标相减替代跨顶层窗口时结果不可靠的 `mapTo`，保证卡片完整铺满、无黑边。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.2`、新增计数 chip 颜色常量）、`cloud_launcher/ui/frosted_backdrop.py`（新增 `capture_live_backdrop`、`paint_frosted_panel` 新增 `live` 参数并改用全局坐标）、`cloud_launcher/ui/modpack_dialog.py`（显示前抓父控件真实背景并透传 live）、`cloud_launcher/ui/card_widget.py`（`Card` 新增 `set_live_backdrop` 并透传）、`cloud_launcher/ui/version_settings_page.py`（`_GlassDialog` 抓父窗口、客户区居中，计数按钮改用 `countButton`）、`cloud_launcher/ui/theme.py`（新增 `countButton` 玻璃 chip 规则）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.1）

v1.3.14.1 是一次**缺陷修复（bug 修复）**：依据用户两张新截图与语音，修两个弹窗的界面问题——整合包「选择版本并命名」浮层透明无底板、内容列表弹窗近全屏后过大且无磨砂。

1. **修复整合包「选择版本并命名」浮层透明无底板**：`ModpackInstallDialog` 与 `ContentVersionPicker` 同用 `contentVersionPicker` 这个 objectName，但 v1.3.14.0 把该 QSS 底板改成透明后，只给 `ContentVersionPicker` 补了自绘磨砂，本浮层没有 `paintEvent`，于是完全没有底板、背景整合包卡片直接透过来、文字叠在一起看不清。现给它补上 `paintEvent` 调 `paint_frosted_panel` 自绘局部磨砂、去掉 `WA_StyledBackground`，与 `ContentVersionPicker` 同款，随「磨砂玻璃 / 通透 / 普通」三档切换并有正确底板。
2. **内容列表弹窗缩小并补磨砂**：`_ContentListDialog` 上一版近全屏（宽 82%、高 86%、真机 960×894）用户嫌太大，现改为按屏幕取宽 62%、高 72%，宽度夹在 460–680、高度夹在 400–560（真机 680×560），一次仍可显示约 7 行。同时它是独立顶层弹窗，内部 `Card` 原先以弹窗自身为坐标基准、采样错位而呈纯白底，现改为以主窗口为基准（`paint_frosted_panel` 新增 `reference_window`、`Card` 新增 `set_reference_window`），正确取到弹窗正后方的壁纸，磨砂 / 通透 / 普通三档均生效。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.1`）、`cloud_launcher/ui/modpack_dialog.py`（自绘磨砂、去掉 `WA_StyledBackground`、新增导入）、`cloud_launcher/ui/version_settings_page.py`（`_ContentListDialog` 缩小尺寸、`_GlassDialog` 给 Card 设主窗口基准）、`cloud_launcher/ui/frosted_backdrop.py`（`paint_frosted_panel` 新增 `reference_window`）、`cloud_launcher/ui/card_widget.py`（`Card` 新增 `set_reference_window`）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.14.0）

v1.3.14.0 是一次**界面体验增强**：依据用户新截图与语音，把内容列表弹窗显著放大、并让下载页的版本选择浮层使用真正的毛玻璃、跟随玻璃设置。

1. **内容列表弹窗近全屏放大**：`_ContentListDialog` 不再写死 460×360，改为按所在屏幕几何取宽 82%、高 86%（宽度封顶 960、下限 460），列表区随固定高弹窗占满剩余空间，47 个 mod 一次可显示约 13 行（原来仅 1 行），滚动条仍彻底隐藏、滚轮照常。名称列宽度随弹窗加宽（弹窗宽 − 固定占位 212），长名继续右侧省略并保留 tooltip。
2. **下载版本选择浮层改为毛玻璃并跟随玻璃设置**：`ContentVersionPicker` 原先靠 QSS 画近不透明白底（`rgba(251,253,255,249)`），不响应玻璃档位。现改为重写 `paintEvent` 调 `paint_frosted_panel` 自绘局部磨砂，去掉 QSS 死白背景；在设置页切换「磨砂玻璃 / 通透 / 普通」三档时即时跟随——磨砂显示壁纸柔化块、通透显示清晰壁纸、普通为不透明白片。下载页其余面板（`DownloadPanel`、`ContentCard`、`PaginationBar`）本就走同一磨砂/透明口径，全页观感统一。

本轮改动文件：

- 修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.14.0`）、`cloud_launcher/ui/version_settings_page.py`（`_ContentListDialog` 近全屏尺寸、新增 `QApplication/QSizePolicy` 导入）、`cloud_launcher/ui/content_search_view.py`（`ContentVersionPicker` 自绘磨砂、去掉 `WA_StyledBackground`）、`cloud_launcher/ui/theme.py`（`#contentVersionPicker` 背景改透明）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.13.0）

v1.3.13.0 是一次**新功能里程碑**：依据用户 4 张新截图与一段语音，落地 10 项改造，统一下载反馈、补齐内容管理、并给整合包加锁。

1. **统一 PCL2 式竖向进度卡片（新增 `cloud_launcher/ui/task_progress_dialog.py`）**：下载 mod / 整合包 / 光影 / 材质 / 数据包时统一弹出**竖向**进度卡片，**废弃横向进度条**。左侧三统计——总进度百分比、下载速度、剩余文件数；右侧分阶段勾选清单（✓ 已完成 / ● 进行中 / ○ 待办，内部滚动区隐藏滚动条、最大高 300）；底部自绘红色圆形「X」取消按钮（点击给 worker 发中断）。内容下载与整合包下载复用同一卡片，整合包展示 8 阶段、普通内容展示 3 阶段。
2. **修复内容列表名称过长 / 弹窗过大**：`_ContentListDialog` 固定宽 460，内部滚动区双向滚动条始终隐藏、最大高 360；名称与详情 Label 固定宽，用 `QFontMetrics.elidedText` 右侧省略号截断，tooltip 保留全名。
3. **内容项一键开关**：每行一个苹果式开关（启用=绿、禁用=灰，调用 `version_content.toggle_content` 加 / 去 `.disabled`），顶部加「全部」总开关，可一键关闭或打开全部；切换失败回滚视觉并报错。
4. **内容列表删除按钮**：每行一个「删」按钮，点击先弹确认框，确认后调 `version_content.delete_content` 移除文件或文件夹，删空显示「暂无内容」并禁用总开关。
5. **下载完成即时加载、免重启**：新增 `contentChanged` / `contentInstalled` 信号链路，下载成功后立即刷新版本列表与当前版本设置页（计数、头像、信息卡），无需重启即可看到新内容。
6. **整合包使用自己的头像**：`modpack_install.py` 安装阶段从压缩包内提取 `pack.png`（读前 8 字节 PNG 签名校验，纯标准库、无 PIL），成功才在 install_meta 写 `avatar="modpack"`，缺失回退默认方块头像。
7. **删除外层滚动条 / 滑块**：版本设置页外层滚动区垂直策略由按需显示改为始终隐藏，滚轮仍可滚动。
8. **加载器多版本切换**：`_LoaderVersionDialog` 列表最大高由 280 增至 420、隐藏滚动条，当前版本高亮，底部加「取消」，可在大量版本之间切换。
9. **整合包锁定与不兼容警告**：扫描到整合包时禁用版本名输入、全部加载器行（显示「已锁定」）与「开始修改」，提示「这是整合包版本，请勿切换版本或加载器」，且不再启动加载器探测；普通版本若已含 mod / 材质 / 光影 / 数据包，切换前确认框警告「切换加载器可能导致内容不兼容」。
10. **开始修改先确认**：点「开始修改」先弹确认框，点「确定」才执行修改、点「取消」则不改动；整合包直接拦截不启动修改线程。

本轮真机窗口目检还发现并修复一个真实 bug：加载器探测回调 `_on_probe_done` 原先无条件刷新加载器行，会把整合包的「已锁定」态覆盖回普通行；已改为整合包直接返回、且 `show_version` 对整合包不再启动探测。

本轮改动文件：

- 新增 `cloud_launcher/ui/task_progress_dialog.py`；修改 `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.13.0`）、`cloud_launcher/modpack_install.py`（进度 5 参、整合包图标提取与 `avatar` 口径）、`cloud_launcher/ui/modpack_install_worker.py`、`cloud_launcher/ui/content_search_view.py`（接竖向卡片、`contentChanged`）、`cloud_launcher/version_content.py`（开关 / 删除数据层）、`cloud_launcher/ui/version_settings_page.py`（内容列表重写、滚动条隐藏、加载器版本弹窗、整合包锁定、确认框）、`cloud_launcher/ui/theme.py`、`cloud_launcher/ui/download_page.py`、`cloud_launcher/ui/main_window.py`（即时刷新）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.12.0）

v1.3.12.0 是一次**新功能里程碑**：把「版本设置」页从骨架**做实**。左侧导航按用户口径改为三个分区——**概览 / 设置 / 修改**（首项文案是「概览」，纠正旧骨架的错别字「概述」），删除原独立的第 4 个「Mod 管理」分区；mod / 光影 / 材质 / 数据包统一从概览的计数按钮展开。其中「设置」分区本轮仍保留骨架，「概览」与「修改」两个分区全部做实。

1. **概览分区做实 `cloud_launcher/ui/version_settings_page.py`（完整重写）**：
   - **信息卡**：展示该版本使用的加载器与头像；整合包版本优先用整合包头像（版本目录 `pack.png`），缺失再回退方块头像。
   - **个性化卡**：头像选择器 `AvatarPicker` 提供 **10 个真实 MC 经典方块头像**（草方块、泥土、石头、圆石、橡木木板、橡木原木、基岩、玻璃、沙子、红砖；素材来自 blockrender.dev 读取游戏自身 JSON 模型渲染的透明 PNG，**非程序自绘**，落盘 `resources/blocks/`），第 11 格「+」支持自定义头像（选图后复制到版本目录），并提供「修改版本名」（撞名 / 空名报错，绝不静默改名）。
   - **版本详细信息卡**：2×2 四个计数按钮显示 mod / 光影包 / 材质包 / 数据包各有几个，点击弹出 `_ContentListDialog` 展开成列表，每项带图标，**无图标就显示问号「?」**，空态显示「暂无内容」。
   - **高级设置卡**：本轮以说明文案占位（后续版本接入）；**危险区卡**提供「补齐文件」（不改加载器、重跑当前加载器安装补全缺失文件）与「删除版本」。
2. **修改分区做实（对齐第三张 PCL2 参考图）**：进入页面后 `LoaderProbeWorker` 后台真实探测四个加载器兼容性；`LoaderRow` 支持加载器增删——选中某加载器后显示具体版本 + 移除「X」+ 展开 chevron（可打开 `_LoaderVersionDialog` 选具体版本），其余加载器显示「与 X 不兼容」并**置灰禁用**；原版态下可用加载器显示最新版本、不可用显示「无」并置灰。点「开始修改」真正重跑 `VersionModifyWorker`（重新合并落盘版本 JSON → 补齐原版库 / 资源 / 客户端 → 加载器库，Forge 走处理器链），幂等跳过已存在文件，完成后更新 install_meta 并刷新版本、回到概览。
3. **弹窗体系（统一无边框磨砂 `_GlassDialog`）**：`_RenameDialog`（改名）、`_ConfirmDialog`（确认）、`_LoaderVersionDialog`（版本选择）、`_ProgressDialog`（阶段 + 进度条 + 百分比 + 可取消）、`_ContentListDialog`（内容列表）；问号样式仅作用于单个 QLabel 自身，不污染祖先控件。
4. **关键 bug 修复：install_meta 合并覆盖**。`game_dirs.write_install_meta` 原逻辑先写显式核心字段、再 `meta.update(extra)`，而修改线程把读到的旧 meta 作为 `extra` 传入，导致旧 `loader / mc_version` 反把本次新值冲掉（界面显示成功但加载器仍是旧值）。已改为**先并入 extra 保留 `avatar / modpack_*` 等附加字段，再用显式核心字段覆盖**，核心字段始终以本次安装为准。
5. **接线与样式**：`main_window.py` 构造页面时传入 `config`，并在 `shutdown()` 调页面 `shutdown()`（对内容 / 探测 / 修改三个在跑 QThread 中断 + 等待，避免析构崩溃）；`theme.py` 新增 `avatarOption / loaderRow / contentRow / loaderVersionOption / vsBusy` 等 QSS 规则。
6. **验证**：全量 `compileall` 通过；离屏构建冒烟（三分区、首项「概览」、无 mod 键、弹窗可实例化）、加载器行逻辑（原版可用 / 无、选中后互斥置灰、移除回原版、chevron / X 可见态）全绿；真实 `probe_all('1.20.1')` 联网返回 Forge 47.4.29（138 版）、NeoForge 不可用、Fabric 0.20.1、OptiFine 14 版；确定性集成验证 worker 进度到 100%、成功 payload 与 install_meta 加载器更新且保留头像；真实窗口用 PrintWindow 抓分层窗核对概览与修改各状态。

本轮改动文件：

- 重写 `cloud_launcher/ui/version_settings_page.py`；修改 `cloud_launcher/ui/theme.py`（新增 v1.3.12.0 QSS 段）、`cloud_launcher/ui/main_window.py`（传 config、shutdown 接线）、`cloud_launcher/game_dirs.py`（修复 `write_install_meta` 合并顺序）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.12.0`）、新增 `cloud_launcher/resources/blocks/` 10 个真实方块 PNG、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.11.0）

v1.3.11.0 是一次**新功能里程碑**：下载页「整合包」分类从「待支持」改为**真实可下载安装**，打通 Modrinth `.mrpack` 整合包的完整端到端链路。点整合包卡片「下载」后，先让用户**选版本**（整合包自身版本 / 对应 MC 版本），再**可自定义命名**；留空则用整合包自己的名字；**重名或含非法字符则该名字不可用**，确认按钮禁用并给出原因，绝不静默自动改名。产物是一个全新、可启动的版本隔离实例。

1. **核心安装模块 `cloud_launcher/modpack_install.py`（纯标准库）**：8 个阶段（①下载 .mrpack ②解析 index/依赖、构建合并 profile 并落版本 JSON ③原版支持库+老版本 natives ④assets ⑤client.jar ⑥加载器库（Forge 走处理器链）⑦整合包客户端文件 ⑧overrides+install_meta），权重合计 1.0，内部 daemon 采样线程按 ProgressTracker 实时回调全局百分比。关键函数 `fetch_modpack_versions(project_id)`（拉取并标准化含 .mrpack 的版本条目，primary 优先）、`install_modpack(chosen, alias, should_cancel, on_phase, on_progress)`，异常统一类 `ModpackError`。
2. **后台线程 `cloud_launcher/ui/modpack_install_worker.py`（PySide6 QThread）**：`ModpackVersionListWorker`（拉版本列表）与 `ModpackInstallWorker`（跑安装，phase/progress/成功/失败信号），跨线程信号走队列连接。
3. **玻璃浮层 `cloud_launcher/ui/modpack_dialog.py`**：版本单选按钮显示「版本号 · MC 版本 · 加载器 · 大小」；命名输入复用 `customNameField`；`_effective_name()`=输入文本或默认项目标题；实时校验 Windows 非法字符 `\ / : * ? " < > |` 与 `game_dirs.alias_exists` 撞名，确认按钮实时禁用并在 `modpackError` 标签给原因；信号 cancelled/confirmed。
4. **关键 bug 修复：中文名不再被静默吞掉**。`game_dirs.sanitize_version_id` 原用 ASCII 白名单正则把每个非 ASCII 字符替换成 `_` 再剥掉，导致中文整段消失（等同静默改名，用户已否决）。已改为危险字符**黑名单** `[\\/:*?"<>|\x00-\x1f\x7f]`（路径分隔符 + Windows 非法文件名字符 + 控制字符替换为下划线），**保留 Unicode 字母/数字（含中文）与空格**，空值回退 `version`；该函数全工程 8 处引用，目录名、JSON 名、扫描口径全部对齐。
5. **路径安全与失败清理**：`_safe_inside` 在 strip 前显式拒绝以 `/` 开头、第二字符为 `:`（Windows 盘符）或 `..` 逃逸的路径；整合包实例是开始前确认不存在、本次新建的，失败/取消一律 `remove_version_dir` 整目录移除（含工作目录），成功路径才仅删工作目录，避免残留坏实例被扫描到。
6. **加载器口径**：forge/neoforge/fabric-loader 映射到对应加载器（Forge 复用处理器链），无加载器回退 vanilla；`quilt-loader` 无现成 profile 端点，明确中文报错拦截，不半支持。
7. **验证**：离屏弹窗（默认命名/撞名/非法字符/确认回传）与逻辑（路径安全/加载器解析/quilt 拦截/mrpack 选择）断言全绿；真实窗口 GUI 目检确认版本单选、命名、撞名/非法字符拦截交互；并完成 GUI 触发的真实端到端安装（中文名完整保留、结构核验全绿、`scan_installed_entries` 正确识别）。

本轮改动文件：

- 新增 `cloud_launcher/modpack_install.py`、`cloud_launcher/ui/modpack_install_worker.py`、`cloud_launcher/ui/modpack_dialog.py`；修改 `cloud_launcher/ui/content_search_view.py`（启用整合包下载、接线、弹窗、线程回收）、`cloud_launcher/ui/theme.py`（新增 `QLabel#modpackError` 警告红样式）、`cloud_launcher/game_dirs.py`（`sanitize_version_id` 改黑名单、保留中文）、`cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.11.0`）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.10.1）

v1.3.10.1 是对 v1.3.10.0 的**路径修正版**（按用户明确要求「.minecraft 不要迁移」）：游戏目录 `.minecraft` 不再放进 CLY，而是**保留在 exe 同级**（`<exe 目录>/.minecraft`）；其余运行期数据仍按 v1.3.10.0 的口径平铺在 CLY。本版只改游戏目录的存储位置，配置 schema（21 键）、界面与全部交互逻辑保持不变。

1. **游戏目录回到 exe 同级**：`game_dirs.minecraft_root()` 由 `data_dir()/.minecraft`（即 `CLY/.minecraft`）改回 `app_base_dir()/.minecraft`。`minecraft_root()` 是全工程唯一定义 `.minecraft` 路径的位置，`versions / assets / libraries / natives` 等子目录全部经它派生，一处修改即全链路生效。
2. **其余数据保持在 CLY 平铺**：`config.json`、`account.json`、`music/`、`wallpaper/`、`version_manifest_cache.json`、`loader_support_cache.json`、`content_search/` 仍走 `resources.data_dir()`（= `<exe 目录>/CLY`），共 7 项平铺，不做改动。
3. **在线目录实际移回**：`D:\云朵启动器\exe\CLY\.minecraft` 已同卷原子移回 `D:\云朵启动器\exe\.minecraft`（目标位置原先不存在、无覆盖），移回后 exe 侧 `.minecraft` 存在、CLY 内已无该目录；CLY 现剩 7 项平铺。
4. **验证**：路径断言 17 项全 PASS（版本号、`data_dir=CLY`、`minecraft_root` 在 exe 侧且不在 CLY 内、其余数据均在 CLY、在线目录真实结构）；真实窗口目检关于页显示「Version 1.3.10.1」、界面与既有设计一致；打包 exe 在临时目录做带 / 不带账号两例冒烟，窗口出现、等待复现析构竞态后 WM_CLOSE，退出码均为 0，并断言 exe 侧 `.minecraft` 已创建、CLY 内无 `.minecraft`。

本轮改动文件：

- `cloud_launcher/constants.py`（`APP_VERSION` 改为 `1.3.10.1`）、`cloud_launcher/game_dirs.py`（导入改为 `app_base_dir`、`minecraft_root()` 改回 exe 同级、docstring 同步）、`cloud_launcher/resources.py`（`data_dir()` docstring 注明唯独游戏目录保留在 `<app 目录>/.minecraft`）、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.10.0）

v1.3.10.0 是一次**数据目录结构改造**（非 bug 修复）：把原本散落在 exe 同级的运行期数据统一收敛到 exe 旁一个名为 **CLY** 的文件夹，**全部平铺**，不再使用 `yd` 子目录。

1. **统一数据根目录**：新增 `DATA_DIR_NAME = "CLY"` 与 `resources.data_dir()`（= `<exe 目录>/CLY`）。所有运行期数据改为在该目录下平铺读写：
   - `config.json`（配置）
   - `.minecraft/`（游戏本体、版本、资源、存档）
   - `music/`（背景音乐）
   - `wallpaper/`（壁纸）
   - `account.json`（正版账号，原 `yd/account.json`）
   - `version_manifest_cache.json`、`loader_support_cache.json`（原 `yd/` 下两个缓存）
   - `content_search/`（搜索缓存，原 `yd/content_search`）
   - `custom_logo.<ext>`（自定义 logo，原 `yd/` 下）
2. **9 个模块路径重定向**：`config_store`、`game_dirs`、`wallpaper`、`music_player`、`brand`、`account_store`、`loaders`、`version_meta`、`content_search` 全部由 `app_base_dir()` 改走 `data_dir()`，并去掉 `yd` 层级；目录缺失时自动创建 CLY，不读取旧散数据。
3. **迁移范围（按用户确认）**：
   - `D:\云朵启动器\exe`：现有数据**全部迁移**进 CLY（`yd` 改名 CLY 后内容平铺，再把 `.minecraft`、`music`、`wallpaper`、`config.json` 移入）；
   - `D:\我的世界`：**不迁移**，新程序在该处新建空 CLY，旧数据保留不动；同目录其他启动器（HMCL / PCL / LauncherX 等）数据严禁触碰。
4. 配置 schema（21 键）与全部界面功能、交互逻辑保持不变，本版只改变数据的存储位置。
5. **关闭流程加固（修复带账号关闭时的 0xC0000409 崩溃）**：真机冒烟发现 CLY 内存在 `account.json` 时，关闭窗口进程恒以 `0xC0000409` 退出（Qt 原文「QThread: Destroyed while thread is still running」）。根因是静默恢复成功后 `ProfilePage` 启动的 `SkinFetchWorker` 皮肤下载线程——`ProfilePage` 是嵌入主窗口的子控件，其 `closeEvent` 不会被触发，该线程在父控件析构时仍在运行。修复：
   - 新增 `ProfilePage.shutdown()`（由 `MainWindow.shutdown` 显式调用），置位关闭标志并等待在途皮肤线程收尾；`_fetch_official_skin` 在关闭阶段直接返回，不再启动新线程；
   - 新增 `SKIN_FETCH_TIMEOUT = 10`（皮肤小图下载超时）与 `RESTORE_HTTP_TIMEOUT = 8`（静默恢复单跳超时），`MicrosoftAuth` 的 HTTP 超时改为可按调用场景区分，给关闭等待设定确定上界；
   - 移除 `ProfilePage` 上不会被触发的 `closeEvent`，改为确定性的 `shutdown()`。

本轮改动文件：

- `cloud_launcher/constants.py`（版本 bump、新增 `DATA_DIR_NAME`、`RESTORE_HTTP_TIMEOUT`、`SKIN_FETCH_TIMEOUT`）、`cloud_launcher/resources.py`（新增 `data_dir()`）、`cloud_launcher/microsoft_auth.py`（HTTP 超时可配置）、`cloud_launcher/ui/account_restore_worker.py`（恢复用短超时）、`cloud_launcher/ui/skin_fetch_worker.py`（超时常量）、`cloud_launcher/ui/profile_page.py`（新增 `shutdown`、关闭标志、移除失效 closeEvent）、`cloud_launcher/ui/main_window.py`（关闭流程接线）、`cloud_launcher/config_store.py`、`cloud_launcher/game_dirs.py`、`cloud_launcher/wallpaper.py`、`cloud_launcher/music_player.py`、`cloud_launcher/brand.py`、`cloud_launcher/account_store.py`、`cloud_launcher/loaders.py`、`cloud_launcher/version_meta.py`、`cloud_launcher/content_search.py`、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.9.3）

v1.3.9.3 是 v1.3.9.2 的修复版，按用户真机验收反馈修复四项问题，不新增功能。

1. **品牌开关改为显隐语义**：两个开关不再是「改写」——Logo 开关关闭 = 整个隐藏 Logo（侧栏与关于页的 Logo 直接消失），名字开关关闭 = 隐藏名字（不是改名字）；卡片标题改为「Logo 和名字」，删除四档分段控件，「导入 Logo」按钮与名字输入框改为常驻显示（替换内容与显隐相互独立）。config 以 `logo_visible` / `name_visible` 两个布尔承载，旧 `brand_mode` 字段在加载时自动丢弃。
2. **旋钮关闭后精确回到左端点**：真机鼠标点击走 C++ 事件路径，重写的 `checkStateSet` 在该路径下不会被分发（QTest 实证），导致开关虽关闭、旋钮却停在右侧；现改为由可靠的 `toggled` 信号（点击 / `click()` / `setChecked` 三条路径都发射）统一驱动一个进度值 `p`（0=关、1=开），关闭即精确落到 `p=0` 左端点，并在首次显示时瞬时校准，杜绝动画堆积。
3. **选色后侧栏保持椭圆圆角**：侧栏染色此前用 `fillRect` 画整块矩形、方角盖住了圆角；现改为构建 `QPainterPath`（`addRoundedRect`，半径 22px）再 `fillPath`，染色被裁剪进与磨砂面板一致的 22px 圆角，选染色后导航区依旧是椭圆圆角、不再出现 90° 尖角。
4. **自研苹果式流体动画 + 弹簧全量门控**：参考三张 iOS 开关图自研——旋钮中心在两端间线性插值，途中按 `SWITCH_KNOB_STRETCH_MAX*sin(pi*p)` 横向拉长（两端归零）、轨道颜色在关态灰与开态绿之间逐通道渐变，缓动改为 InOutCubic；「苹果动画（Q弹效果）」总开关现在真正彻底：关闭后早期弹簧按钮的光标拉扯（`pull()`）、按压收缩、果冻形变、OutBack 回弹，以及下载面板 / 版本手风琴 / 详情加载器 / 下载页条目揭示与提示弹窗等全部属性动画，一律瞬时到位、按钮完全静止（功能性定时器保留）。

本轮改动文件：

- `cloud_launcher/constants.py`（版本 + 1393 常量块、`SWITCH_KNOB_STRETCH_MAX`、`LOGO_VISIBLE_DEFAULT`/`NAME_VISIBLE_DEFAULT`）、`cloud_launcher/config_store.py`（删 `brand_mode`、加 `logo_visible`/`name_visible` 与布尔校正、迁移丢弃旧字段）、`cloud_launcher/brand.py`（整文件重写：`logo_visible`/`name_visible`、显隐与替换内容解耦）、`cloud_launcher/ui/settings_page.py`（SwitchButton 进度驱动重写、品牌卡显隐重构、`math` 流体形变）、`cloud_launcher/ui/main_window.py`（`set_logo_visible`/`set_name_visible`）、`cloud_launcher/ui/nav_sidebar.py`（染色圆角裁剪、品牌显隐）、`cloud_launcher/ui/about_page.py`（品牌显隐）、`cloud_launcher/ui/spring_button.py`（`pull()` 门控、注释更新）、`cloud_launcher/ui/download_panel.py`、`cloud_launcher/ui/profile_page.py`、`cloud_launcher/ui/version_detail_view.py`、`cloud_launcher/ui/download_page.py`（属性动画门控）、`main.py`、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.9.2）

v1.3.9.2 是 v1.3.9.1 的修复版，按用户真机验收反馈修复设置页「个性化」的十项问题，不新增功能。

1. **顶部标签缩小、椭圆胶囊化**：设置页顶部「个性化 / 启动 / 桌宠 / AI」四个标签不再横向铺满，改为固定高 30px 的椭圆胶囊（圆角 15px），宽度按文字内容走，末尾加弹簧留白。
2. **玻璃预览悬停 3 秒出说明 tooltip**：鼠标停在玻璃三档预览图上 3 秒后弹出说明（`GLASS_PREVIEW_TOOLTIP_DELAY_MS=3000`），解释该档是什么样式、是否 iOS 风格——磨砂档明确标注「iOS 风格」，通透档与普通档说明各自面板特性；移开鼠标 tooltip 立即消失。
3. **侧栏导航恢复椭圆胶囊**：侧栏导航按钮此前被拉成正方形，`navItem` 圆角由 12px 改为 23px（按钮高 46 的半值），恢复完整椭圆胶囊形态。
4. **删除右侧过宽原生大滑块**：设置页滚动区垂直策略改为 `ScrollBarAlwaysOff`，原生宽滚动条不再出现，鼠标滚轮仍可滚动；同时删除样式表中全部通用水平滚动条规则——经 8 个诊断脚本独立进程验证，Qt 样式表解析器在存在水平 `::handle` 规则时会令垂直滚动条的 `width` 规则失效、退回原生 22px 宽滑块，工程内所有滚动区水平策略均为 AlwaysOff，水平规则本就无实例。
5. **品牌区删虚线、按模式条件显示**：去掉默认按钮的虚线焦点框（全局 QSS 加 `outline: none`）；品牌区按模式条件显示——默认什么都不出现，Logo 改写只显示「导入logo」按钮，名字改写只显示名字输入框（占位「输入新的名字」），两者都选则两行都显示。
6. **音乐区删两个开关**：删除「背景音乐总开关」「启动时自动播放」两个开关，只留添加 / 删除按钮；有歌曲时行内显示「♪ 原始文件名」（导入时记录原始文件名，磁盘上仍统一存 `bgm.<ext>`），有歌即自动播放、无歌静默。
7. **新增 Logo / 名字两个独立开关**：品牌区新增「Logo 改写」「名字改写」两个独立开关，与四档分段双向同步（开关组合反推模式：两开=both、只开 Logo=logo、只开名字=name、两关=default）。
8. **壁纸默认空白、最多三个、修复重复**：默认壁纸项改为空白缩略图（不再渲染真实壁纸，默认档加载返回 `(None, 0.0)` 回退内置渐变）；自定义壁纸最多导入三个，达上限不再弹导入框、底层 `import_wallpaper` 也会拒绝；重名导入自动加序号，不再出现两个相同壁纸。
9. **开关苹果式动画 + 动画总开关**：开关旋钮改用 `QVariantAnimation`（200ms、OutQuad 缓动）做苹果式滑动；新增「苹果动画（Q弹效果）」总开关（config 字段 `animations_enabled`，默认开），关闭后开关跳位、按钮按压收缩、果冻形变与 OutBack 回弹全部瞬时完成，拉扯的光标直接跟随保留。
10. **删除全部虚线 / 描边方块**：全局清除焦点虚线框，移除所有点状描边与虚线组成的方块。

本轮改动文件：

- `cloud_launcher/constants.py`（版本 + 新常量块）、`cloud_launcher/config_store.py`（animations_enabled 字段 + 布尔校正）、`cloud_launcher/ui/appearance.py`（动画总开关状态）、`cloud_launcher/ui/spring_button.py`（动画门控）、`cloud_launcher/ui/settings_page.py`（开关动画、tooltip、品牌条件显示与双开关、音乐行、顶部胶囊标签）、`cloud_launcher/ui/theme.py`（outline:none、圆角、删水平滚动条规则）、`cloud_launcher/wallpaper.py`（空白默认、三上限）、`cloud_launcher/music_player.py`（有歌即播）、`cloud_launcher/ui/main_window.py`（host 方法）、`main.py`、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.9.1）

v1.3.9.1 是 v1.3.9.0 的修复版，按用户验收反馈修复设置页「个性化」的五个问题，不新增功能。

1. **玻璃三档加样式预览图**：玻璃风格不再只有文字分段按钮，改为三个可点选的小窗预览（`GlassPreviewButton` / `GlassPreviewGroup`）——每个预览用当前真实壁纸（无壁纸时默认渐变加图形）做底，按对应模式渲染面板效果：磨砂档片内缩放模糊再叠白玻璃、通透档保持清晰只叠低 alpha 白玻璃、普通档不透明白片，面板内画小方块加横线模拟内容，下方保留档位文字标签；选中态加蓝色描边环。
2. **删除全部提示文字**：移除玻璃卡下方长句提示、染色卡的「背景颜色 / 导航栏颜色」标签、品牌卡的 logo 状态文案与「自定义名字」标签、音乐行无歌曲时的提示文案；无歌曲时音乐行留空，有歌曲时仍显示 ♪ 歌名。
3. **普通模式整窗染色**：此前普通档不透明白片把背景染色盖住，只有面板缝隙能看到颜色；`paint_frosted_panel` 的普通档分支在白片填充后，若选中了背景染色，在面板路径内再叠一层染色（新常量 `TINT_NORMAL_PANEL_ALPHA=118`），所有面板（含侧栏白片）跟随变色，配合背景层整窗染色达成「整个窗口切换颜色」。
4. **开关改小、仿 iOS 椭圆样式**：`SwitchButton` 由 46×26 缩到 42×25，椭圆胶囊形；开态用 iOS 绿（52,199,89）、关态用 iOS 浅灰（233,233,235），白色圆钮留 2px 边距并手动画细阴影，不再用蓝色粗条滑块。
5. **版本号升 1.3.9.1**：按修 bug 口径第四位递增，关于页显示 `Version 1.3.9.1`。

本轮改动文件：

- `cloud_launcher/ui/settings_page.py`（重写开关、新增预览控件、删除提示）、`cloud_launcher/ui/frosted_backdrop.py`（普通档面板染色）、`cloud_launcher/ui/main_window.py`（染色刷新面板与预览）、`cloud_launcher/constants.py`（版本 + 新常量块）、`main.py`、`README.md`、`说明文档.md`。

## 历史版本范围（1.3.9.0）

v1.3.9.0 按用户手绘原型，把设置页「**个性化**」页标注的五块功能全部实现，并把设置页重构为顶部四个子标签「**个性化 / 启动 / 桌宠 / AI**」——个性化页为全功能，其余三个标签先挂占位骨架（`PlaceholderPage`），后续版本再填。

1. **玻璃风格三档单选**：分段控件在「磨砂玻璃（仿 iOS 风格）/ 通透（可以看清下面的图片和文字）/ 普通（文字和图片被挡住）」三档间互斥切换，`paint_frosted_panel` 按 `appearance.glass_mode` 三分支绘制——
   - **磨砂玻璃（frost，默认）**：沿用原片内预模糊，面板圆角内只柔化正后方壁纸再叠各面板色板；
   - **通透（clear）**：面板正后方壁纸块**不糊化、保持清晰**映射进圆角路径，再叠统一低 alpha 白玻璃（顶 96 / 中 52 / 底 28），下面的图片文字可看清；
   - **普通（normal）**：填不透明白片（255,255,255,255）+ 浅灰边（214,226,236），壁纸被完全挡住。
   所有经 `paint_frosted_panel` 的面板（Card、ContentCard、NavSidebar、下载页分组条、下载面板、版本详情等）自动跟随。
2. **背景与导航栏调色盘**：用户锁定「红橙黄绿青蓝紫」七色任选，另加一个「无染色」空态；背景整窗染色 alpha 92、导航栏 alpha 80，两排圆形色块互斥单选，无染色时不画色层。
3. **壁纸导入和选择**：`wallpaper.py` 新增 `list_wallpapers`（按修改时间倒序）、`import_wallpaper`（QPixmap 探针校验后 `shutil.copy2`，重名自动加序号）、`load_named_wallpaper`（拒绝目录穿越、只接受纯文件名）、`load_selected_wallpaper`（default / 缺失回退固定优先级）；壁纸缩略图单选，导入后即时切换。
4. **logo 和名字改写**：分段控件四档「默认 / logo 改写 / 名字改写 / 名字和 logo 改写」；新建 `brand.py` 统一解析——自定义 logo 导入到 `yd/custom_logo.<ext>`（先清旧文件、QPixmap 校验），侧栏与关于页 logo、侧栏短名、关于页全名、窗口标题按档位跟随；网络 UA 仍用纯 ASCII 的 `APP_UA_NAME`，不随显示名改。
5. **背景音乐**：用户锁定「只能导一首歌、无限循环、光标停留可删除或重新添加」——
   - 新建 `music_player.py`：导入的歌曲统一存 `music/bgm.<ext>`，导入前清旧文件，**目录里永远只有一首歌**；播放用 `QMediaPlayer + QAudioOutput`，`setLoops(Infinite)` 单曲无限循环；
   - 两个开关语义：开关 1 = 背景音乐总开关 `music_enabled`（关闭即停且不响应播放），开关 2 = 启动时自动播放 `music_autoplay`（关闭则只加载不播放、手动点播放）；循环固定 Infinite，不做开关；
   - 音乐行固定 40px 高，光标停留才浮现「播放 / 重新添加 / 删除」三个幽灵按钮，无歌曲时播放按钮禁用；
   - **Windows 文件句柄坑修复**：QtMultimedia（ffmpeg 后端）播放时持有音频文件句柄，且句柄释放是异步的，立刻 `os.remove` 会静默失败；`MusicPlayer` 新增 `release_source()`（stop + 清空 source），主窗口新增 `_pump_events` 驱动事件循环，删除时在 2 秒上限内轮询 `processEvents` + 删文件直到文件真正消失。

本轮新增 / 改动文件：

- 新增 `cloud_launcher/ui/appearance.py`（外观状态单例）、`cloud_launcher/brand.py`（品牌解析与 logo 导入）、`cloud_launcher/music_player.py`（音乐文件管理 + 播放封装 + release_source）、`cloud_launcher/ui/settings_page.py`（四子标签 + 个性化五块 + 开关/分段/色块/悬停行等控件）；
- 改动 `cloud_launcher/constants.py`（版本升 1.3.9.0 + 新常量块）、`config_store.py`（10 个新字段 + 合法性校正）、`ui/frosted_backdrop.py`（三档分支）、`ui/background_layer.py`（背景染色）、`ui/nav_sidebar.py`（导航染色 + refresh_brand）、`ui/about_page.py`（config 入参 + refresh_brand）、`wallpaper.py`（导入 / 选择 / 列表）、`ui/main_window.py`（host 方法块 + release/pump/轮询删除）、`ui/theme.py`（v1.3.9.0 QSS）、`main.py`、`build.spec`（版本头 + QtMultimedia hiddenimports）。

## 历史版本范围（1.3.8.2）

v1.3.8.2 修复用户反馈的「**磨砂背板被吞了**」：下载页 mod（模组）/ 整合包 / 光影包 / 资源包 / 数据包 五类内容搜索结果卡片没有片内磨砂——卡片背景只是一层 QSS 平涂的半透明白，卡片内壁纸保持清晰锐利，和启动页卡片、原版游戏分组条的磨砂观感完全不一致。

1. **卡片改为自绘片内磨砂**：`ContentCard` 新增 `paintEvent`，与启动页 `Card` 走同一套 `paint_frosted_panel`：在卡片圆角矩形内只截取本卡片正后方的那一小块壁纸做局部柔化，再叠三段白玻璃高光与 1px 细亮边；卡片之外的壁纸仍然清晰，不会整窗糊化。
2. **QSS 不再盖白片**：`theme.py` 的 `QFrame#contentCard` 由 `background: COLOR_CARD` + 实描边改为 `background: transparent; border: none`，避免平涂白层压在自绘磨砂上把磨砂糊成纯白片；`contentCard` 的 objectName 保留，标题 / 简介 / 元信息 / 加载器 / 版本 / 下载按钮等子控件样式选择器不受影响。
3. **色板取主卡片档**：采用 `COLOR_GLASS_TOP/MID/BOTTOM_RGBA`（176/102/62）+ `COLOR_CARD_BORDER_RGBA` 细描边，与启动页卡片一致；不使用更白的 `TOP_GLASS`（alpha 186）档——历史实测该档叠磨砂后会糊成不透明白板、壁纸透不出来。
4. **不改动其他逻辑**：分页、仅第一页写缓存、真实下载、加载器标注、tooltip 多行等既有行为全部保留；卡片圆角沿用 14px，网格两列布局与尺寸不变。

本轮改动文件：

- `cloud_launcher/ui/content_search_view.py`：`ContentCard` 新增 `paintEvent`（片内磨砂自绘），导入 `paint_frosted_panel`；
- `cloud_launcher/ui/theme.py`：`QFrame#contentCard` 改为透明无边框，背景交给自绘；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.8.2` 与文档同步。

## 历史版本范围（1.3.8.1）

v1.3.8.1 修复 v1.3.8.0 上发现的**工具提示（tooltip）横向溢出 bug**：mod 卡片版本标签的 tooltip 把该模组支持的全部正式版版本号用「、」拼成一整条纯文本，像 Fabric API 有 48 个正式版，Qt 在 Windows 上对这段纯文本并未稳定自动换行，tooltip 单行横向撑满、溢出整个屏幕并覆盖到其他窗口之上。

1. **新增纯文本多行工具函数**：`content_search_view.py` 新增 `_wrap_list_tooltip(prefix, values, per_line=6)`，把长列表按每行固定 6 条拆成多行，第一行带说明前缀，行与行之间插入换行符 `\n`；纯文本不引入 HTML / 富文本，宽度确定可控，不再依赖各平台 QToolTip 不一致的自动换行；短列表不超过每行条数时仍只占一行，行为不变。
2. **版本标签 tooltip 接入**：`ContentCard` 里版本 tooltip 先按 `version_key` 倒序排好，再交由 `_wrap_list_tooltip` 生成多行文本，48 个版本号 → 8 行、宽度约 280px，完整收在屏幕内；靠近屏幕右缘时 tooltip 自动向左定位，也不溢出。
3. **加载器标签 tooltip 一并防护**：加载器 tooltip 同样走 `_wrap_list_tooltip`；加载器最多 5 个、不超过每行 6 条，仍单行显示，现状不变，且对未来更长的列表有防护。
4. **不改动其他逻辑**：卡片加载器标注、分页、仅第一页写缓存、真实下载链路等 v1.3.8.0 的行为全部保留。

本轮改动文件：

- `cloud_launcher/ui/content_search_view.py`：新增 `_wrap_list_tooltip`，版本与加载器 tooltip 改为多行；
- `constants.py`、`main.py`、`README.md`、`说明文档.md`：版本升 `1.3.8.1` 与文档同步。

## 历史版本范围（1.3.8.0）

v1.3.8.0 按用户口述「模组那里加入一个，这是什么加载器，也要加入进去」，在下载页 **mod（模组）分类的卡片上标注该模组支持哪些加载器**（Fabric / Quilt / NeoForge / Forge 等）。探针确认 Modrinth search hit 的 `categories` 字段里**加载器 slug 与内容分类 slug 混排**（例如 Sodium 是 `['fabric','neoforge','optimization','quilt']`，其中 `optimization` 是内容分类、不是加载器），需要把加载器单独挑出来。

1. **数据层提取加载器**：`content_search.py` 新增加载器 slug→显示名映射 `LOADER_DISPLAY`（fabric→Fabric、quilt→Quilt、neoforge→NeoForge、forge→Forge，另预留 optifine/modloader/liteloader/rift/babric）与固定展示顺序 `_LOADER_ORDER`（主流加载器在前）；新增纯函数 `mod_loaders(categories)`，只从 categories 里挑出属于加载器的 slug、按固定顺序去重返回显示名，内容分类（library/optimization/utility/decoration 等）一律忽略。`_normalize_hit` 新增 `loaders` 字段，由 `mod_loaders(hit.get("categories"))` 生成。
2. **视图卡片加载器行**：`ContentCard` 在作者/下载量行下方新增「加载器：Fabric、Quilt、…」标签（`QLabel#contentCardLoaders`），**仅 `kind == "mod"` 且加载器列表非空时创建**，tooltip 列出全部加载器；标签开启 `wordWrap` 自动换行——加载器较多（如 Entity Culling 有 5 个）时完整显示不被窄列裁切，同一网格行卡片高度自动对齐。光影包 / 资源包 / 数据包等资源类不适用 mod 加载器概念，这些分类不创建该行。
3. **主题样式**：`theme.py` 文件末尾追加 v1.3.8.0 段，`QLabel#contentCardLoaders` 复用版本标签的 12px 字号与浅色文字，透明背景无边框，与卡片既有视觉统一。
4. **不影响既有下载链路**：本次只做卡片信息标注，真实下载时 `content_install` 按 loader 匹配文件的逻辑不变；v1.3.7.0 的分页、仅第一页写缓存、不兼容提醒等行为全部保留。

本轮改动文件：

- `cloud_launcher/content_search.py`：`LOADER_DISPLAY`、`_LOADER_ORDER`、`mod_loaders`、`_normalize_hit` 新增 `loaders` 字段；
- `cloud_launcher/ui/content_search_view.py`：导入 `mod_loaders`、`ContentCard` 新增加载器行（仅 mod、可换行）；
- `cloud_launcher/ui/theme.py`：文件末尾追加 v1.3.8.0 加载器标签样式段；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.8.0` 与文档同步。

## 历史版本范围（1.3.7.0）

v1.3.7.0 围绕五类内容页（mod / 整合包 / 光影包 / 数据包 / 资源包）补齐三件事：① 每张卡片明确标注「支持哪个版本」，目标版本不兼容时直接提醒无法下载；② 真分页（1、2、3…… 页，offset 递增、每页内容不重复，不是假分页）；③ 缓存口径收紧——只有第一页写 yd 缓存（last.json + 图标落盘），翻到第二页及以后不产生任何缓存文件，图标只在内存持有；但所有页的卡片都能真实下载到版本文件夹。

1. **卡片标注支持版本**：`content_search.py` 新增 `_RELEASE_RE` 与 `release_versions / version_key / latest_releases` 三个版本工具，只挑正式版（过滤快照 / pre / rc / 远古版）；`version_key` 把版本号转 int 元组，修掉字符串比较里 `1.21.10 < 1.21.9` 的错误。卡片新增「支持：26.3、26.2、26.1.2 等 N 个正式版」一行（`QLabel#contentCardVersions`），tooltip 列出全部正式版（按版本号倒序）。
2. **不兼容即提醒无法下载**：版本选择浮层里对不兼容的已安装版本置灰、文字加「（不支持）」、光标改箭头并给出说明，默认选中第一个兼容项；当所有已安装版本都不兼容时，点下载直接弹 `QMessageBox.warning`（带项目名、分类中文名、它支持的最新 5 个正式版），不打开浮层；`content_install.py` 两处 NoCompatibleFile 兜底文案统一加「，无法下载」。
3. **真分页（offset 递增）**：视图新增 `PaginationBar(QFrame)`——上一页 / 页码按钮 / 下一页 / 「第 X/Y 页」，信号 `pageChanged`；总页数 > 7 时只显示首尾 + 当前页前后各 1 + 省略号，页码按钮 30×30、当前页高亮。`ContentSearchView` 新增 `_page/_total_pages/_query` 状态与 `_goto_page`，统一 `_run_search` 按 `offset=(page-1)*DEFAULT_LIMIT` 翻页，每页内容不重复；翻页后滚动回顶，状态文案区分「已保存到本地文件夹」与「本页不写缓存，可直接下载」。
4. **仅第一页写缓存**：`search_content` 内 `persist = (offset == 0)`，只有 persist 时才 `_save_result` 写 last.json、图标落盘并返回 saved_to；非 persist 路径 saved_to 为空、不写任何文件。图标加载 `_fill_icons` 按 persist 分流：persist 走 `("path", 落盘路径)`，否则 `_fetch_icon_bytes` 读 bytes 走 `("bytes", 内存字节)`，图标只在内存持有、不落盘；仍 8 线程并发、单条失败不阻断。
5. **所有页都能真实下载**：缓存限制只针对 yd 缓存，不限制下载行为——任意页卡片点下载，文件都真实落到 `versions/<别名>/` 对应目录（mod→mods、shader→shaderpacks、resourcepack→resourcepacks、datapack→datapacks）。
6. **分页栏重建 bug 修复**：真机首次翻页时分页栏只剩末页按钮、info 停在第 1 页，根因是 `_rebuild` 清空旧控件时对省略号 QLabel 调了 `QButtonGroup.removeButton`（QLabel 从未入组）抛 TypeError，导致清空阶段中断、新按钮未建。修复：导入 `QAbstractButton`，清空时仅对真正的按钮执行 removeButton。

本轮改动文件：

- `cloud_launcher/content_search.py`：版本工具、`supported_versions/icon_bytes` 字段、`_fetch_icon_bytes`、`_fill_icons` persist 分流、`search_content` 仅第一页写缓存；
- `cloud_launcher/ui/content_search_view.py`：图标函数重构（内存 bytes 加载）、`PaginationBar`、卡片版本行、分页状态与翻页、浮层不兼容置灰、全不兼容弹窗、`QAbstractButton` 修复；
- `cloud_launcher/content_install.py`：两处 NoCompatibleFile 文案加「，无法下载」；
- `cloud_launcher/ui/theme.py`：文件末尾追加 v1.3.7.0 分页与版本标签样式段；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.7.0` 与文档同步。

## 历史版本范围（1.3.6.0）

v1.3.6.0 依据用户反馈做两件事：① mod / 光影包 / 数据包 / 资源包 结果页那条又粗又明显的竖向滑块「不要看到它」——彻底隐藏滚动条，滚轮滚动照常；② 这些内容页从「只能看」变为「能真的下进已安装版本里」——卡片新增下载入口，选目标版本后由后台线程把文件落到该版本的隔离目录。

1. **彻底不显示滑块**：`ui/content_search_view.py` 的结果滚动区、版本选择浮层的列表滚动区都设 `VerticalScrollBarPolicy = Qt.ScrollBarAlwaysOff`。Windows 上 QSS 宽度与 `setFixedWidth` 都压不住原生 ~17px 轨道（工程早前已验证），因此按既定口径直接隐藏，滚轮滚动、内容滚动能力完全保留。
2. **真实下载链路**：新增 `content_install.py`（版本解析 + 兼容筛选 + 流式下载 + 原子落盘）与 `ui/content_install_worker.py`（后台线程，信号回主线程）。落点严格按版本隔离：
   - mod → `versions/<别名>/mods/`（`.jar`）
   - 光影包 → `versions/<别名>/shaderpacks/`（`.zip`）
   - 资源包 → `versions/<别名>/resourcepacks/`（`.zip`）
   - 数据包 → `versions/<别名>/datapacks/`（`.zip`）
3. **兼容筛选**：mod 必须与目标版本的加载器匹配（原版 / OptiFine 直说「不能装 mod，请选 Fabric / Forge / NeoForge 版本」）；光影 / 资源包 / 数据包只按目标版本的 MC 号匹配；文件扩展名与分类不符的版本直接跳过（例如数据包项目只提供 `.jar` 时视为不可用）。
4. **下载入口与选择浮层**：卡片右下角「下载」按钮 → 视图内浅白玻璃浮层（圆角 + 细亮边，覆盖在结果网格之上）列出已安装版本（`MC 号 · 加载器`，悬停提示隔离目录），可选中后下载；没有已安装版本时给出「先去原版游戏分类装一个版本」的引导。
5. **进度与结果反馈**：状态行实时显示「正在下载 文件名 → 版本（N%）」；成功后弹框给出文件名与完整落盘路径，可直接核对。
6. **撞名不静默改名**：目标目录已有同名文件时抛出并弹浮层征询「是否覆盖」，用户确认才重下；不静默改名（沿用历史否决项）。
7. **网络稳健性**：Modrinth CDN 走 Cloudflare，国内线路偶发长时间不吐字节，读超时放宽到 60s 并支持最多 3 次重试，失败清理 `.part` 残片后原子落盘。
8. **整合包明确不支持**：`.mrpack` 需解包 + 安装依赖，按钮显示「待支持」并置灰，点击给中文说明。
9. **卡片排版随长标题变化**：卡片标题 / 简介按列宽单行省略（不再把某一列撑宽、把「下载」按钮顶出可视区），两列始终等宽。
10. **首次进分类不再干等**：图标从串行改为 8 线程并发下载（仍只用标准库），首次无缓存进入某分类从原来一分钟量级降到 10 秒内出卡片。
11. **下载完整性对账**：落盘前按 Content-Length 核对实收字节，线路中途断流（少收）不再被当成成功——半截 jar 绝不会进 mods 目录；断流走自动重试，界面显示「线路不稳，正在第 N/3 次重试」。

本轮改动文件：

- 新增 `cloud_launcher/content_install.py`、`cloud_launcher/ui/content_install_worker.py`；
- `cloud_launcher/ui/content_search_view.py`：滚动条 AlwaysOff、卡片下载按钮、版本选择浮层、进度与结果反馈、撞名征询、卡片等宽与标题省略；
- `cloud_launcher/ui/theme.py`：追加 v1.3.6.0 样式段（选择浮层底板与标题 / 副标题 / 列表 / 取消 / 确认 / 关闭、卡片下载按钮四态）；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.6.0` 与文档同步。

## 历史版本范围（1.3.5.1）

v1.3.5.1 按用户真机实拍反馈修正版本设置页的窗口形态：此前打开版本设置页时左侧 CLY 主侧栏（启动/下载/设置/打包/关于）仍占着位置，设置页只占右侧一半、内容被窗口边缘截断。本轮不新增功能，只做布局修正——打开版本设置页时隐藏主侧栏，让设置页铺满整个窗口客户区；返回普通页面时恢复侧栏。

1. **进入即铺满**：`main_window.py` 的 `_open_version_settings` 在切到版本设置页后调用 `self.sidebar.hide()`，QHBoxLayout 自动让出空间，页面栈占满整个 body 宽度；版本设置页自带的「概览 / 设置 / 修改 / Mod 管理」分区导航从窗口左内边距开始，右侧内容完整显示、不再被截断。
2. **返回即恢复**：`_switch_page` 在切回五个普通导航页面前先 `self.sidebar.show()`，从版本设置页返回或任何入口切到普通页面时主侧栏都会恢复，选中态同步正常。
3. **仅布局修正**：版本设置页自身的卡片、占位控件与磨砂玻璃样式一律不动，无新增色系、无新运行时依赖，技术红线不变；按修 bug 口径第四位递增。

本轮改动文件：

- `ui/main_window.py`：`_open_version_settings` 隐藏主侧栏、`_switch_page` 恢复主侧栏，docstring 同步；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.5.1` 与文档同步。

## 历史版本范围（1.3.5.0）

v1.3.5.0 给「游戏版本」行加悬停三点入口并新建版本设置页骨架（对照 PCL2「版本设置」窗形态，明确不要「导出」）。

1. `profile_page.py` 新增 `_VersionMoreButton`（26px 浅玻璃圆 + 横向三圆点自绘）与 `_VersionHeader`，指针移入版本横条才显现三点、移出收起，文字标签对鼠标透明；
2. 新增 `ui/version_settings_page.py`：概览 / 设置 / 修改 / Mod 管理四分区导航（不含导出），概览铺版本信息 / 个性化 / 快捷方式 / 高级管理四卡，所有下拉与按钮置灰占位；
3. `main_window.py` 把版本设置页接入页面栈（不进侧栏五项），`theme.py` 补 v1.3.5.0 样式段（选中态淡蓝玻璃 + 主蓝加粗）。

## 历史版本范围（1.3.4.1）

v1.3.4.1 按真机实拍反馈做顶部间距微调：分类标签与搜索框此前贴得太近、贴着窗口顶，需要整体往下移一点。

1. **标签行顶部留白**：`download_page.py` 新增 `_TAB_TOP_MARGIN=12`，分类标签行整体下移，六个标签不再紧贴窗口顶部。
2. **标签与内容拉开间距**：新增 `_TAB_BOTTOM_MARGIN=10`，标签行与下方内容栈之间产生间距；原版游戏的四个分组、其余五类的搜索框与搜索按钮同步下移，不再紧贴标签。
3. **仅间距微调**：保留左右边距现状，不改标签尺寸、颜色、磨砂玻璃风格与任何功能；按修 bug 口径第四位递增。

本轮改动文件：

- `ui/download_page.py`：标签行上下间距常量与 contentsMargins；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.4.1` 与文档同步。

## 历史版本范围（1.3.4.0）

v1.3.4.0 按用户口述，为下载页顶部除「原版游戏」外的 5 个分类（mod / 整合包 / 光影包 / 资源包 / 数据包）补齐「搜索 + 图文展示」能力。本版本只做搜索浏览，不做内容本体下载（真实下载后续版本开发）。

1. **数据源 Modrinth 官方 REST（免 API key）**：新增 `content_search.py`，调用 `/v2/search` 并以 facets 按 project_type 过滤，五类映射 mod→`mod`、整合包→`modpack`、光影包→`shader`、资源包→`resourcepack`、数据包→`datapack`；解析标题、简介、作者、下载量与图标 URL。实测本机（长沙）接口 200、响应 0.7~2.5s，图标 CDN 可正常下载。
2. **搜索框 + 搜索按钮（用户硬性要求）**：新增 `ui/content_search_view.py`，每个分类视图顶部为搜索输入框与「搜索」按钮，回车同样触发；搜索中按钮置灰显示「搜索中…」，可中断旧任务再发起新搜索。
3. **每条结果必带图片**：结果以两列玻璃卡片网格展示，图标从 CDN 下载并圆角化；无图标或加载失败时显示程序化绘制的占位图（玻璃底 + 图片符号），保证「每一个东西都有图」。
4. **本地缓存落盘**：搜索元数据 JSON 存 `yd/content_search/<分类>/last.json`，图标存 `yd/content_search/icons/` 并按项目复用，不重复下载；满足「搜索来的东西放文件夹里」。
5. **后台线程**：新增 `ui/content_search_worker.py`（QThread），搜索与下图在子线程完成，信号回主线程刷新，不阻塞 UI；中断可取消。
6. **下载页分类栈重构**：分类标签提升为全局，新增分类 QStackedWidget——原版游戏=现有版本列表/详情栈，其余 5 个 index=对应搜索视图，`_select_tab` 切换分类栈；首次进入分类自动拉一批热门内容。现有版本下载链路保持不破坏。

本轮改动文件：

- `content_search.py`（新增）：Modrinth 搜索、图标下载、本地缓存；
- `ui/content_search_worker.py`（新增）：搜索后台线程；
- `ui/content_search_view.py`（新增）：搜索视图、结果卡片、占位图；
- `ui/download_page.py`：全局 tabs + 分类内容栈、`_select_tab` 改造、shutdown 清理；
- `ui/theme.py`：搜索按钮、结果卡片、状态提示 QSS；
- `constants.py`、`main.py`、`build.spec`、`README.md`、`说明文档.md`：版本升 `1.3.4.0` 与文档同步。

## 历史版本范围（1.3.3.3）

v1.3.3.3 修复真机反馈的「26.3 + Forge 66.1.2 在最后一步下载游戏支持库文件永久卡住（总进度 99.70%、0 B/s、剩余文件 1、面板一直显示进行中）」。根因是库下载走官方源时被「200 后挂住不回数据」的滴灌式限流拖死，加上并发池里最后一个文件失败后整批直接中止。

1. **国内镜像源链（新增两个 maven 镜像）**：`constants.py` 增加 `ALIYUN_MAVEN_URL`（阿里云 public）与 `HUAWEI_MAVEN_URL`（华为云 maven）；`version_profile._library_sources` 把库的候选源固定为 **阿里云 → BMCL → 华为云 → 官方源**，Maven Central 系工件（lwjgl / asm / joml / gson 等原版库）全部走国内镜像，只有 Forge 自有 groupId 的库（三个国内镜像都没有）才落到官方 maven。
2. **大文件分片并发下载**：`download_engine` 新增 `_download_split`：按 `Range` 把大文件切成最多 4 片并发（全局最多 2 片同时跑，避免触发官方源 429），单片 4 次重试、429 指数退避、单片长时间无数据自动换新连接；8MB 的 Forge 安装器从十几分钟压到十几秒。
3. **串行救援（rescue_tasks）**：并发池里失败的文件不再立刻中止安装，先串行按指数退避重试最多 3 轮；`ProgressTracker.record_file_recovered` 把救回来的文件从失败计数里扣掉，救不回来才带着首个失败原因中止。
4. **步内进度改用文件计数**：`_refresh_global_percent` 以 tracker 快照的「已完成 / 总文件数」占比推进（无文件总数才退回字节占比），叠加五步权重，消除「只剩 1 个文件却永远停在 99.70%」的观感。
5. **Forge 安装器与处理器链**：安装器改走同一套分片下载（原先 installer 单连接 urllib 只有 8~35 KB/s）；`FORGE_PROCESSOR_TIMEOUT=900` 给处理器链总时长上限，第 5 步内部按 (0.0,0.90) 下载库 + (0.90,0.10) 跑处理器的分段权重推进。
6. **诊断日志**：设置环境变量 `CLY_DIAG_LOG` 后，worker 逐条落盘 pipeline 起点、每步任务数、每个失败文件与最终失败原因，方便真机取证。
7. **加载器安装包可用性预检（修「第二个加载器直接失败」）**：NeoForge 的 BMCL 镜像只有版本号条目、没有安装包（26.3.0.x 实测全部 404），原来探测只看 metadata 就报「可以添加」，点下载必然 404 失败。现在 `loaders._artifact_available` 在探测阶段对 NeoForge 候选版本逐个 HEAD 校验安装包真实存在，只把验证通过的版本交给界面；全部不可用时卡片显示「镜像暂未提供这个版本的安装包」并灰显，不再让用户下载到失败；下载阶段同时补官方 maven 兜底源。

本轮改动文件：

- `constants.py`：新增 `ALIYUN_MAVEN_URL` / `HUAWEI_MAVEN_URL`、`FORGE_PROCESSOR_TIMEOUT`、`DOWNLOAD_SPLIT_*`，版本升 `1.3.3.3`；
- `version_profile.py`：`_library_urls` 替换为 `_library_sources`（四源候选链），`collect_library_tasks` 对应改造；
- `download_engine.py`：`_download_split` / `_stream_response` / `_fast_timeout` / `_probe_size` / `_finalize_part` / `_cleanup_pieces`、`record_file_recovered`、`rescue_tasks`；
- `forge_install.py`、`loaders.py`：安装器复用缓存、client 侧处理器数量判定、处理器链总时长上限；
- `ui/download_worker.py`：步内分段权重、救援接线、`_DIAG_PATH` 诊断日志。

## 历史版本范围（1.3.3.2）

v1.3.3.2 修复真机反馈的「带加载器下载时，在最后一步下载游戏支持库文件约 99.40% 处反复失败」。四个加载器（Fabric / Forge / NeoForge / OptiFine）均已真机串行下载到成功，不改变苹果磨砂玻璃整体形象。

1. **库 URL 兼容顶层 maven 字段**：现代 Fabric profile 没有 `downloads.artifact.url`，只有顶层 `url`（maven 基址）与顶层 `size/sha1`；`_library_urls` / `collect_library_tasks` 改为无 artifact.url 时读顶层 `url` 拼官方地址、BMCL 作镜像，size/sha1 兼容顶层，修复 Fabric 官方库在 BMCL 404 的问题。
2. **下载整轮重试**：`download_one` 在所有候选源一轮都失败后按退避重试（`DOWNLOAD_RETRIES=2`），配合 `.part` 断点续传，消除官方 piston-data 资源瞬时 404 与并发抢 BMCL 的误判。
3. **Forge / NeoForge 版本自动回退**：同 MC 前缀稳定版从新到旧回退到镜像可用的版本；NeoForge 请求 21.1.265 自动回退到 21.1.248。
4. **Forge 客户端处理器链（新增 `forge_install.py`）**：Forge 的 `net.minecraftforge:forge:<ver>:client` 工件 `downloads.artifact.url` 为空，官方与 BMCL 对该 `-client.jar` 均 404，它是安装器处理器本地生成的产物。新模块用本机 Java 运行 client 侧三个处理器（DOWNLOAD_MOJMAPS、ForgeAutoRenamingTool、binarypatcher），主类从各处理器 Jar manifest 读取，按 `outputs` 声明的 sha1 校验产物，本地生成补丁化 client Jar，不再硬下载 404 工件；处理器阶段显示在约 98% 而非卡在 100%。

本轮改动文件：

- `forge_install.py`（新增）：Forge 无头客户端处理器链编排（`run_forge_install`、`is_processor_generated`、`cleanup_work_dir` 等）；
- `loaders.py`：新增 `_neoforge_all_versions` / `_forge_versions_for`，三个 build 函数改 tuple 返回并带同前缀旧版本回退；
- `version_profile.py`：`_library_urls`、`collect_library_tasks` 兼容顶层 url/size/sha1；
- `download_engine.py`：`download_one` 整轮重试 + 退避；
- `constants.py`：`DOWNLOAD_RETRIES=2`、新增 `DOWNLOAD_RETRY_BACKOFF`，版本升 `1.3.3.2`；
- `ui/download_worker.py`：`_resolved_loader_version` 接线、tuple 回传、实际版本落盘，新增 `_run_forge_loader_step`。

## 历史版本范围（1.3.3.1）

v1.3.3.1 按用户口述，把自定义标题栏上的品牌 LOGO 与英文全名删掉，只保留右侧窗口按钮，不改变苹果磨砂玻璃整体形象。

1. **标题栏去掉 LOGO 与名称**：标题栏不再显示云朵 LOGO 和 "Cloudy Launcher"，只保留右侧最小化 / 关闭两个圆形按钮；左侧空白区域仍可按住拖动窗口。
2. **侧栏与关于页不变**：侧栏品牌区保持 LOGO + "CLY"；关于页仍为 LOGO + 全名 + 版本号 "Version 1.3.3.1"。

本轮改动文件：

- `ui/main_window.py`：`_build_title_bar()` 删除 LOGO 与标题标签，只保留 stretch + 窗口按钮组；清理不再使用的 `QPixmap` / `QLabel` 导入；
- `constants.py`：版本升 `1.3.3.1`（关于页版本号自动更新）；
- `ui/nav_sidebar.py`：品牌区保持 LOGO + "CLY"。

## 历史版本范围（1.3.3.0）

v1.3.3.0 完成品牌英文改名与关于页重构，品牌 / 标题 / 关于区域全部英文，不改变苹果磨砂玻璃整体形象。

1. **全名与缩写**：全名改为 **Cloudy Launcher**，缩写 / 短名改为 **CLY**，替换原中文「云朵启动器 / 云朵」。
2. **标题栏与窗口标题去版本号**：标题栏与窗口标题统一显示 "Cloudy Launcher"，不再拼接版本号；侧栏品牌区只保留 LOGO + "CLY"，去掉原版本标签。
3. **版本号移到关于页**：新增真实关于页 `ui/about_page.py`，居中磨砂卡片内显示 LOGO、全名 "Cloudy Launcher" 与版本号 "Version 1.3.3.0"，品牌 / 关于区域全英文、不写中文；关于页更多内容后续按用户口述补充。
4. **删除「个人页」标题**：启动页（原个人页）顶部的「个人页」标题删除，仅保留右侧离线 / 正版按钮。

本轮改动文件：

- `constants.py`：`APP_NAME="CLY"`、`APP_FULL_NAME="Cloudy Launcher"`、`APP_UA_NAME="CloudyLauncher"`、版本升 `1.3.3.0`；`APP_DISPLAY_NAME` 改为只显示英文全名（不带版本）；新增 `ABOUT_VERSION_LABEL`；
- `ui/nav_sidebar.py`：`_build_brand()` 改为 LOGO + "CLY"，删除版本标签；
- `ui/profile_page.py`：`_build_header()` 删除「个人页」标题，仅保留离线 / 正版按钮；
- `ui/about_page.py`（新增）：`AboutPage`，LOGO + 全名 + 版本号；
- `ui/main_window.py`：关于导航由占位页替换为 `AboutPage`。

## 历史版本范围（1.3.2.0）

v1.3.2.0 按真机实拍与口述，完成下载页三项改造，均为功能新增 / 交互口径调整，不改变苹果磨砂玻璃整体形象。

1. **下载页不再显示「已安装」**：旧逻辑里已安装版本的条目按钮被置灰、文案改成「已安装」点不动。现所有版本（含已装）条目按钮恒为「下载」、始终可点，**允许对同一 MC 版本重复下载**；「是否已安装」的判断仍保留，用于开始下载时的撞名提示。
2. **撞名弹框、禁止静默改名**：旧逻辑点「开始下载」时若别名目录已存在，`unique_alias()` 会偷偷追加 `-2`、`-3` 自动改名。现别名（默认等于版本号）对应隔离目录已存在时，**弹中文提示框**「这个版本已经有了，名称已重复，请立刻在上方输入框重新起一个名字」，并自动聚焦、选中别名输入框，用户改成不冲突的新名字后才放行下载；同一版本可重复下载，但必须以新别名另存一份隔离目录。
3. **natives 自动解压**：新增 `natives_bootstrap.py`，外部版本 natives 目录为空 / 缺失时，从对应的 `natives-windows` Jar 解压原生库。现代版本（1.19+ / 26.3）识别坐标第四段为 `natives-windows` 的独立库条目，老版本识别 `downloads.classifiers['natives-windows']`；本地缺失的 Jar 先按官方源 + BMCL 镜像下载到全局 `libraries`（同时进入 classpath），解压目标与 JVM 的 `natives_directory` 保持一致；已有原生库则跳过，不重复解压。

本轮改动文件：

- `constants.py`：版本号升 `1.3.2.0`；新增别名空 / 撞名提示标题与文案常量；
- `game_dirs.py`：新增 `alias_exists(别名)`；`unique_alias()` 保留但下载页不再调用；
- `ui/download_page.py`：`VersionRow` / `VersionEntry` 的 `set_installed()` 改为只保证按钮为「下载」可点；`_start_download_from_detail()` 重写为别名非空 + 撞名校验后才启动 worker；
- `ui/version_detail_view.py`：新增 `focus_alias_input()`（聚焦并全选别名）；
- `natives_bootstrap.py`（新增）：natives 源收集、缺失 Jar 下载、解压与幂等判定；
- `ui/launch_worker.py`：Java 检测后、组装参数前插入 phase 45「正在准备原生库…」。

## 历史版本范围（1.3.1.8）

v1.3.1.8 修复「**能扫描到外部启动器（PCL2）装的标准版本 26.3，点开始游戏却弹『游戏启动后异常退出（退出码 1）』，日志 `java.lang.ClassNotFoundException: net.minecraft.client.main.Main`**」。仅修启动链路与失败提示，不动任何界面形象、不写外部版本目录（对 PCL2 的 26.3 目录全程只读）。

真机取证的四个根因（全部实测确认）：

1. **classpath 漏掉客户端 Jar（直接原因）**：`_collect_classpath()` 只认云朵自己下载的 `client.jar`，而标准版本的客户端 jar 与目录同名（`26.3.jar`，41 483 720 字节），于是 `-cp` 里只有依赖库、没有主类所在 jar → JVM 必然报找不到主类。v1.3.1.7 新增的 `find_client_jar()` 只用在「扫描是否已安装」，没被启动链路调用，属上一轮漏点。
2. **依赖库只查版本隔离目录**：旧逻辑只在 `versions/<别名>/libraries` 找库（外部版本这里是 0 个），而 PCL2 把 114 个库放在全局 `.minecraft/libraries`（实测 74 个在此，其余 40 个全是 linux/macos 平台 classifier，Windows 不需要）。
3. **natives 目录写死错路径**：旧逻辑固定拼 `versions/<别名>/natives`（外部版本没有此目录），而 26.3 用 per-module 布局，natives 实际解压在 `versions/26.3/26.3-natives/`（jna 2 个 dll、lwjgl 10 个文件含 `3.4.3+4` 子目录）。
4. **命令行出现两段 `-cp`**：现代版本 profile 的 `arguments.jvm` 自带 `-cp` 与 `${classpath}` 两条，旧实现末尾又硬拼一次 `-cp <classpath> <mainClass>`。

本轮改动：

- `game_dirs.py` 新增 `global_libraries_dir()`、`find_library(别名, 相对路径)`（**版本隔离目录优先、全局 libraries 回退、0 字节视为缺失**）、`find_natives_dir(别名)`（`natives/` 有内容才用 → 否则 `<别名>-natives` → 再否则回落 `natives/`）；
- `version_profile.py` 抽出 `library_relative_path()`，统一「`downloads.artifact.path` 优先、否则 maven 相对路径」口径，供本地路径与全局回退共用；
- `java_runtime.py`：`_collect_classpath()` 改为「库规则过滤 + 版本目录优先 + 全局 libraries 回退 + `find_client_jar`」，classpath 内不再出现不存在的路径；`natives_directory` 改用 `find_natives_dir`；`build_launch_command()` 检测 jvm 参数是否已自带 `-cp/-classpath`，自带就只追加主类、否则才补完整 `-cp`；
- `ui/launch_worker.py`：启动前先校验客户端 jar，缺失直接给「找不到客户端 jar」的明确文案；按版本 JSON 的 `javaVersion.majorVersion` 校验 Java 主版本，过低报「Java 版本过低」（含需要的版本、当前版本、Java 路径）；启动日志改为**二进制落盘**并按 UTF-8 → GBK → latin-1 依次解码读取——旧实现按 UTF-8 文本模式写，中文 Windows 上 Java 的 GBK 输出会被写坏，弹窗里显示成一串乱码；
- `java_runtime._parse_java_version()` 修正：旧实现只认以 `version` 开头的行，OpenJDK 首行是 `openjdk version "25.0.4"`，导致版本号恒为空、Java 主版本校验形同虚设；改为正则提取 `version "x.y.z"`；
- `ui/profile_page.py`：失败弹窗标题按「缺 Java / Java 版本过低 / 其他」分别给出，不再靠字符串里有没有「Java」猜。

真机验证结果：

- 组装结果断言 11 项全 PASS：Java 25.0.4 检测到、required=25/current=25、命令行只有一段 `-cp`、客户端 jar 识别为 `26.3.jar`、classpath 含该 jar 与 74 个全局库（共 75 条、missing=0）、`natives_directory` = `D:\我的世界\.minecraft\versions\26.3\26.3-natives`、主类紧跟 `-cp` 值；
- **真实拉起 26.3 成功**：pid 起后 **22.1 秒出现窗口 `Minecraft 26.3`**，日志显示 `LWJGL version 3.4.3+4`、`NVIDIA GeForce MX150 / OpenGL 3.3.0 582.66`、`Created window using SDL video driver: windows`（离线账号下 `Failed to fetch user properties 401` 属正常噪声，不影响启动）；
- 38 个 `.py` 编译通过；离线冒烟回归（含下载页四分组、条目分组建、下载面板倒计时）与外部版本扫描、面板回归脚本全部通过。回归脚本里停留在 v1.2.x 时代的「五分组 / 最新版本两行」断言同步更新为 v1.3.1.7 起的四分组结构。

## 历史版本范围（1.3.1.7）

v1.3.1.7 集中修复真机反馈的 5 个体验问题，均为既有逻辑修正、不改变整体苹果磨砂玻璃形象：

1. **下载面板隐藏时机**：旧版「已取消 / 失败 / 成功」后仍常驻、且 5 秒空闲会自动收起，不符合预期。改为：下载**进行中绝不自动隐藏**（进度一直可见）；任务结束（成功 / 失败 / 取消）后启动 **10 秒倒计时，到点整个面板（含右下角小胶囊）整体消失**；用户点右上角小 ✕，任务结束时**立即消失**、下载中则收起为小胶囊不中断下载。鼠标进入面板暂停倒计时、离开重新计时，读失败原因不会看到一半消失。
2. **扫描全部标准版本（PCL2 式）**：旧扫描只认云朵下载的 `client.jar`，外部启动器 / 官方启动器 / PCL2 放入的版本（jar 与目录同名 `<id>.jar`、无云朵 `install_meta.json`）被判未安装。新增 `find_client_jar()` 同时识别非空 `client.jar` 与 `<id>.jar`，并从版本 JSON 读取真实 `id` 作为版本号、加载器缺省按原版处理；手动放进 `versions` 的标准版本现在也能被扫描、选中和启动。
3. **删除下载页多余的「最新版本」分组**：该分组的「最新正式版 / 最新预览版」与下方正式版、预览版首条完全重复，PCL2 等也无此分组，整体移除，下载页只保留正式版、预览版、远古版、愚人节版四个全量分组。
4. **个人页版本选择下拉限高**：旧版随版本增多会撑高整个界面。改为固定**最多显示 3 行**（高度锁定 110px、不撑高界面），超出部分通过右侧**可见滑块**（6px 半透明圆角、hover 提亮、无箭头）或滚轮滚动查看。
5. **分组展开即时显示**：旧版收起态不预建条目，点展开时同步一次性构建数百条控件，界面「卡一下」才显示全部。改为收起态即通过 `QTimer(0)` 在后台分批预建全部条目，且收起时不再销毁已建条目，点展开时条目已就位、动画即时流畅；预建未完成时才同步补完剩余条目兜底。

## 历史版本范围（1.3.1.6）

v1.3.1.6 修复「点开始游戏后进度条瞬间显示『游戏已启动』，但 Minecraft 窗口迟迟不出现、像没打开」。真机诊断确认游戏本身完全正常（SDL3+OpenGL 建窗、NVIDIA MX150 渲染），但从拉起进程到窗口可见实际需要约 16 秒（Datafixer 优化、资源加载、SDL/GL 初始化）；旧 `launch_game` 只要 `Popen` 不抛异常就立即返回，界面立刻置 100%，用户在窗口真正出现前就以为失败，且旧逻辑把进程输出全部丢弃、不检查后续是否退出，进程崩溃也会静默。本轮改动：①新增后台线程 `ui/launch_worker.py`，通过 `phase` 信号回传真实阶段（准备环境 10%→检测 Java 30%→组装参数 55%→拉起进程 70%→等待窗口 75%→95%），进程输出写入 `launcher_launch.log` 不再丢弃；等待循环每 300ms 同时检测进程退出（失败则读取日志尾部如实上报）与游戏窗口（枚举可见、标题以 Minecraft 开头且排除 RenderPearl 辅助窗口），**窗口真正出现才置 100% 报成功**，40 秒超时但进程仍存活则保守报成功，绝不伪造成功。②修复离线模式 `offline_uuid` 确定性缺陷：旧实现在 `uuid.UUID.fields` 的 8 位字段上套用 12/14 位掩码，离线启动必抛 `ValueError`；改为直接对 16 字节 MD5 摘要做字节操作（version 3 + IETF variant，等价 Java `UUID.nameUUIDFromBytes`）。③修复资源索引不落盘：`collect_asset_tasks` 只在内存使用 asset index、从不保存 `assets/indexes/<id>.json`，导致游戏报 `Can't open resource index`，现索引随下载一并落盘。④`_rule_allows` 重写为官方语义（按序处理 allow/disallow，新增 os 与 features 匹配），正确排除 `--demo`、自定义 `--width/--height`、quickPlay 等 feature-gated 参数。仅启动链路与下载索引逻辑改动，不动界面形象。

v1.3.1.5 修复「个人页已扫描到已安装版本（如 26.3-6、26.3-7），版本行却显示『尚未安装』、点开始游戏弹『请先在下方选择一个已安装的游戏版本』打不开」。根因有三：①`_clear_version_options()` 误把 `_version_entries` 清空，导致 `_find_entry()` 始终在空列表里查找，即使选中也返回 None；②安装完成与首次打开都没有自动选中，`selected_version` 为空即被启动校验拦截；③版本行横条文字初始「尚未安装」后从不更新。修复：`_clear_version_options` 不再清 `_version_entries`；`refresh_version_list` 增加 preferred 参数与兜底——本次安装别名优先、其次已存选中、列表非空时默认选中第一个并持久化；新增 `_sync_current_label()` 同步横条；下载页 `versionInstalled` 信号改为发 alias（隔离目录名，多个同 MC 版本也能唯一定位），主窗口回调据此自动选中。仅个人页选择逻辑与下载页信号改动，不动界面形象与下载引擎。

v1.3.1.4 修复原版（无加载器）安装完成后总进度停在 88.00% 不跳到 100% 的问题。五步权重前四步
合计 88%、第 5 步（加载器支持库）占 12%；原版无加载器时该步走 SKIPPED 分支，旧逻辑只发步骤
跳过信号、未把全局百分比推进到 100%，导致 succeeded 之后 run() finally 里最后一次
`_emit_progress` 仍用停在第 4 步的 88% 覆盖 `mark_success` 已显示的 100%（现象：标题已是
「安装完成」、剩余文件 0、第 5 步显示跳过横线，百分比却卡 88%）。修复：SKIPPED 分支显式把
`_global_percent` 置 100%、复位步骤上下文后再发跳过与进度信号。仅 worker 编排逻辑改动，不动
界面形象与下载引擎。

v1.3.1.3 修复真机下载 26.3 反复卡在「安装游戏 进行中...」（总进度 64%、速度 0 B/s、剩余文件 1）。
根因：连接建立后服务器不发数据时，旧逻辑靠 30 秒 socket 超时，且跨线程 watchdog 调
`response.close()` / `socket.shutdown()` 在 Windows 上无法唤醒另一线程阻塞的 recv（诊断实测
拿到的 socket 已标记 closed，shutdown 静默无效），实际仍等满 30 秒，等同永久卡死。改为放弃
跨线程 watchdog，直接把 socket 超时设为 `DOWNLOAD_STALL_TIMEOUT=12` 秒：数据在流动时每次
recv 都在超时前返回（慢源零星发包不误杀），连续 12 秒完全无数据则 socket 自抛 TimeoutError，
`download_one` 捕获后自动切下一候选源。同时保留断点续传——`_download_from` 检测已有 `.part`
大小并带 `Range` 头，206 追加、200 重下，网络 / 停滞错误保留 `.part`，切换源不重复下载，
最终 SHA1 校验兜底。client.jar 与依赖库恢复官方源优先（实测约 0.37 MB/s 快于 BMCL 约 0.1
MB/s）、BMCL 兜底；资源文件维持 BMCL 主 + 官方 mirror。本地挂死测试 elapsed 从 30.1 秒降到
12.1 秒且成功切换。仅下载引擎 / 镜像逻辑改动，不动界面形象。

v1.3.1.0 / v1.3.1.1 / v1.3.1.2 为下载源与下载引擎相关迭代（BMCL 镜像与官方源双候选、各
文件镜像 URL 规则及多源兜底），具体以对应版本留档 exe 为准。

v1.2.12.16 修复真机反馈：下载列表页点分组横条展开仍有「挤压感」。探针实测发现真根因：
build_entries() 对超过 40 条的大分组走分批路径，同步只建第一批 40 条就返回，动画
target_h 只算了 40 条高度；260ms 动画播完后，剩余几百条通过定时器每 0ms 一批冒出来，
每批高度跳一次。同时 Qt 的 body.sizeHint() 在 addWidget 后缓存不刷新（实测 103 条已建完
仍返回 12px）。改为：① 全部条目同步一次建完，不再分批；② 手动遍历条目累加 sizeHint
算目标高度，不依赖 body.sizeHint()；③ 动画前不再 setMaximumHeight(16M)（那会让父
layout 瞬间撑全高）。探针验证 100ms 时高度已平滑长到 2282px，不再瞬间跳变。

v1.2.12.5 详情页加载器横条展开版本列表加 maximumHeight 手风琴动画，消除瞬间顶出感。

v1.2.12.4 修复真机实拍反馈：下载页手风琴分组「收起时横条磨砂 OK，一点开下面整块变成不透明白板」。
展开态 paintEvent 误切了「置顶档」更白的 TOP_GLASS 色（top alpha=186），叠在片内磨砂上接近不透明，
把底下壁纸卡通人物全糊死；展开 / 收起统一改回普通半透磨砂色（150/92/54），整块都能透出壁纸，
不再顶出一块白边。

v1.2.12.3 按真机反馈把全局滚动条（下载页 / 详情页 / 个人页版本列表右侧那条竖线）再压细：
厚度 3px→2px 发丝线、滑块最小长度 28→22，滑块平时白色不透明度 96→55（几乎隐形、不挡壁纸），
hover 才提到 110，轨道与箭头保持透明——拖动时仍可辨，静止时不再像个"大轮"。

v1.2.12.2 针对真机实拍 26.3 详情页四项问题修复：① 分组卡片与候选版本行在用户自换壁纸之上
看不清——改为片内局部磨砂（毛玻璃）自绘背板，压暗壁纸大字与卡通插画，标题 / 版本号可读，
版本别名输入框与返回箭头提高不透明度；② 下载面板 5 秒空闲收起为右下角小胶囊后点不开——
补上收起态点击重新铺开的交互；③ 找不到取消下载入口——重新展开后即可看到大叉；④ 整批下载
期间总进度长时间卡住不动——步内百分比按实时已完成文件 / 字节进度回填加权进度，平滑推进。

v1.2.12.1 修复 26.3 等新年度版本号在详情页被误判「暂时没有这个版本的加速器」、卡片点不动的问题，
并把可用加载器分组改为 PCL2 式可折叠形态：横条点击展开 / 收起，下方列出「全部版本(N)」竖排候选、
单选具体版本（默认最新稳定版），一个分组展开时其余自动收起；不可用分组置灰、横条不可展开，原版
分组始终可选、不展开。

在 v1.2.11.0 便携隔离目录与单例下载面板基础上，补齐**真实依赖库 / natives / 资源文件下载**、
**本机 Java 探测与游戏进程拉起**，并打通「版本详情页 → 选加载器 → 自定义别名 → 下载安装」闭环：

- **版本详情页**：下载条目先进入详情视图（返回箭头 + 版本名自定义输入框 + 原版 / Forge /
  NeoForge / Fabric / OptiFine 五个加载器分组 + 底部居中「开始下载」胶囊）；进入页面自动后台
  扫描该 MC 版本对四个第三方加载器的支持性，可用分组横条可展开全部候选版本单选，不支持或查不到
  版本的分组置灰并显示「暂时没有这个版本的加速器」、横条不可点；支持性结果缓存到
  `yd/loader_support_cache.json`，同一版本下次打开直接读缓存、不重新联网，仅清单出现缓存中没有的
  新版本才重新探测。
- **重复下载与自定义别名**：已安装版本也可再次进入详情页重复下载；隔离目录名即用户自定义
  别名，原生 MC 版本、加载器类型与加载器版本记录在目录内 `install_meta.json`；下载中途可取消，
  取消即清理 `.part` 半成品并收起面板。
- **五步全真实下载编排**：原版 JSON / 合并 profile → 原版依赖库（含老版本 natives classifier
  下载解压）→ 全局资源对象 → client.jar → 加载器专属库；按继承链合并、库按名去重、规则判定
  （os=windows / features）；Fabric / NeoForge / Forge / OptiFine 四条链路均走真实元数据与
  二进制下载，不做占位。
- **下载面板新形态**：点击下载后面板从**顶部水平居中**铺开，5 秒无操作自动收回右下角小胶囊；
  右上角小 ✕ 仅收起面板，底部居中加大号红色叉形**取消下载**按钮；面板仍展示总进度、速度、
  剩余文件与五步分步清单。
- **滚动条收敛**：去掉分组内第二条滚动条，全页只保留最外侧一条最细透明滚动条，条目元素保持
  现状不变。
- **Java 探测与真实拉起**：按 PATH → 注册表 → 常见安装目录三级探测本机 Java；读取隔离目录落盘
  的合并 profile 组装 JVM 命令（现代 arguments 分段 / 老版本 minecraftArguments 模板占位替换、
  classpath 收集、离线 UUID）；探测不到 Java 时弹中文引导提示，不伪造启动成功。

Forge / NeoForge 安装器的二进制补丁合并环节依赖 Java 执行 installer，本机无 Java 时该环节如实
兜底、不谎称可直接进游戏；离线、超时、解析失败静默回退不弹窗、不崩溃；设置 / 打包 / 关于仍为
通用空白占位骨架页；配色沿用既有浅蓝白 iOS 玻璃体系，不新增不透明实色块。

**v1.2.4.3 让 3D 人物预览背景彻底透明**：右侧「玩家人物」卡片里角色直接浮在磨砂卡片上，
轮廓之外不再保留任何白 / 灰矩形底板，透出卡片局部磨砂与壁纸，也不允许退化成黑底；实现组合为
颜色缓冲请求 8 位 alpha、`WA_TranslucentBackground` + 关闭自动填充、`WA_AlwaysStackOnTop`（官方
说明 QOpenGLWidget 默认先于普通控件绘制、下方透不过来，必须压到合成顺序最上层）、源 alpha 混合
与 `(0,0,0,0)` 透明清屏；本机 Intel UHD 620 / OpenGL 4.6 / Qt 6.12 真实窗口屏幕截图实测透明区与
卡片磨砂逐通道一致。3D 标准几何、相机距离、指针跟随分层、待机摆臂、Steve / Alex 双皮肤、外部正版
皮肤与 CLASSIC / SLIM 模型全部保持不变。
**v1.2.4.2 移除人物预览卡内层白框与双层玻璃**：个人页右侧「玩家人物」卡片原先在内层还套了一层
半透明白玻璃小窗（白描边 + 圆角），与外层卡片磨砂叠成两层玻璃，内部 GL 不透明清屏再压出一块
独立冷白板；本轮删除该内层 `preview-pane` 包装、边框样式与配套颜色常量，3D 预览直接放入外层
磨砂卡片，四周留白由卡片自身边距提供；GL 清屏色改为三通道近乎相等的中性浅灰白，与卡片白玻璃
高光贴近，在暖壁纸与默认蓝白渐变两种背景下都不再凸成一块偏色独立矩形（QOpenGLWidget 在本机
Windows / Qt 下无法透明合成，清屏仍为不透明底色，不做 RGBA 透明期待透出父层）。
**v1.2.4.1 修正毛玻璃作用范围**：最底层背景只把壁纸以**清晰**等比 cover 铺满，卡片之外露出的
壁纸保持清晰；模糊**只发生在每张卡片与左侧导航栏玻璃片自身的圆角矩形内**——面板自绘时截取
正后方那一小块清晰壁纸做两级缩放局部柔化，再叠三段白玻璃高光与细亮边，形成 iOS 式片内局部
磨砂。壁纸**不打进 exe、也不进入源码压缩包**；目录缺失、图片损坏或被用户手动删除时，程序静默
回退既有浅柔蓝白渐变默认背景，不弹窗、不崩溃，主 `config.json` 不新增任何壁纸字段。此前
1.2.3.0 起正版**刷新令牌与公开身份**持久化到 exe 同级 `yd/account.json`，下次启动后台静默
续期、自动恢复正版态（PCL2 式长期在线）；短期访问令牌只存内存、不落盘，退出登录 / 切离线 /
续期失败即删除账号文件。1.2.3.1 设备码登录弹窗为无边框真圆角玻璃面板，自绘标题栏与关闭按钮、
支持拖动，码框 / 按钮 / 间距与主窗口苹果风通透质感统一。1.2.2.2 起认证改用 v1 Live-Connect
官方启动器设备码端点（详见下方更新记录）。启动次数与最近游玩日期仍为真正启动游戏后才记录；
窗口尺寸保持 980×660 不变：

- 无边框可拖动主窗口（整体尺寸放大），标题栏显示 Logo、名称与版本号；
- 左侧导航栏为「启动 / 下载 / 设置 / 打包 / 关于」五项竖排导航，未选中项图标 + 文字，选中项隐藏图标只留加粗文字；默认进入启动页（旧个人页：昵称 / 离线正版 / 3D 预览 / 统计 / 开始游戏），下载页为六分类标签 + 五张版本卡片骨架，设置 / 打包 / 关于为占位页；
- 玩家昵称标签与输入框水平并排，本地 `config.json` 持久化；
- **移除欢迎语**：个人页顶部不再显示“欢迎回来，xxx”一类问候文字；
- 标题行右侧为并排的 **离线 / 正版** 模式按钮：离线为本地昵称 + 史蒂夫 / 艾利克斯随机角色；正版通过设备码弹窗完成微软账号登录，登录成功后锁定正版昵称、显示 UUID 并加载本人皮肤；
- **苹果风局部磨砂玻璃**：有外部壁纸时背景层以清晰 cover 铺满整窗，左侧导航栏与各卡片在自身圆角矩形内截取正后方小块壁纸做局部柔化，再叠三段白色高光、细亮边框与大圆角，模糊壁纸只从玻璃片内部水印式透出；卡片之外的壁纸保持清晰；无壁纸时回退浅柔蓝白渐变；输入框、进度条同步通透质感；不调用系统模糊接口、不挂 `QGraphicsBlurEffect`、不真透视桌面，在他人电脑上表现一致；3D 角色预览直接放在外层磨砂卡片内，不再另套内层白玻璃小窗；
- 角色使用 Mojang 官方原版 64×64 皮肤贴图；模型严格按 Minecraft 原版标准玩家模型
  建模（头 8×8×8、躯干 8×12×4、双臂 / 双腿各 4×12×4）；
- **GPU 真三维管线（1.1.3.0）**：由 `QOpenGLWidget` + 手写 OpenGL 着色器在显卡上实时渲染，
  与 Minecraft 背包预览走同一类三维流程——透视投影（近大远小）、硬件深度缓冲自动前后遮挡、
  整图纹理最近邻（Nearest）采样、标准 UV 面映射、MC 式固定面朝向亮度档（顶面最亮、
  正面接近原色、侧面压暗、背面 / 底面最暗）；背面不再靠 CPU 画家算法排序，由显卡深度缓冲
  正确遮挡，可任意左右转动、俯仰看到头顶与脚底；
- **关节级待机动画（1.1.3.1 精简）**：躯干与双腿保持静止，去掉呼吸上下起伏、身体前倾与腿部摆动；仅双臂绕肩关节做缓慢、小幅的左右张合；先做关节局部旋转、再由渲染层叠加指针跟随；动画与指针转向互不干扰；
- **取景与贴合修正（1.1.3.2）**：相机后退，角色在卡片内四周留出边距、不再顶满画面；双臂、双腿回到 Minecraft 标准 4 宽并沿躯干外侧 / 身体中线贴合，消除手臂内侧嵌入躯干、双腿互相嵌入的穿模观感；标准几何、UV、光照、动画与对外接口保持不变；
- **取景居中与摆臂穿模修正（1.1.3.3）**：相机进一步后退，角色在真实个人页卡片内垂直填充约一半、四周留白充足；左右转动本就绕模型中点 Y 轴，俯仰叠加按俯仰角标定的垂直补偿，使左右 / 俯仰都绕角色自身中心原地转向、画面中心不偏移；摆臂改为只朝离开躯干的方向单向轻张、回到竖直即止，另叠加绕肩前后轻摆，根除手臂内收相位扫入躯干的动态穿模；标准几何、UV、光照、正面默认朝向与对外接口保持不变；
- **俯仰方向修正、取景回调与头部跟随（1.1.3.4）**：修正俯仰跟随反向（鼠标上移抬头、下移低头，与指针方向一致）；相机距离从 102 回调到 88，角色比上一版稍微放大一点、四周仍保留均匀边距；指针跟随改为头部绕颈枢轴独立转向——躯干 / 四肢保持直立正面，头部跟随指针左右转头、抬头 / 低头，斜向指针为两个角度的自然组合；左右 yaw 方向、标准几何、UV、光照、待机摆臂与对外接口保持不变；
- **身体小幅同步跟随（1.1.3.5）**：在头部跟随基础上，整体刚体（躯干 / 双臂 / 双腿）也朝指针方向做小幅同步偏转——鼠标上移身体随头轻仰、下移轻俯，左移朝左转、右移朝右转，左上 / 左下 / 右上 / 右下等斜向为 yaw、pitch 两轴自然叠加；身体量程约为头部的三分之一（左右约 ±10°、俯仰约 ±6°），头部以更大幅度领先跟随，呈现“身体轻转、头先转向”的层次；整体绕模型中点旋转，标准相切部件相对位置不变、不互相穿插；标准几何、UV、光照、相机距离、待机摆臂与对外接口保持不变；
- **全局滚动条再压细为发丝线（1.2.12.3）**：真机实拍反馈下载页右侧那条滚动竖线（拖动翻页的"轮"）还是太粗，要求越细越好。`constants.py` 把 `SCROLLBAR_THICKNESS` 由 3px 压到 2px、`SCROLLBAR_MIN_LENGTH` 由 28 压到 22；`theme.py` 竖 / 横滚动条滑块平时白色不透明度由 96 降到 55（静止时几乎隐形、不挡壁纸），hover 才提到 110；轨道、add-page / sub-page、箭头保持透明无背景，圆角半径随厚度取半。覆盖下载页 `#page-scroll`、详情页 `#detail-scroll`、个人页版本列表 `#version-list-scroll` 及任意 `QScrollArea`，单文件改动、不动布局与交互；
- **详情页壁纸之上磨砂背板、收起态小胶囊可点开、步内进度实时推进（1.2.12.2）**：真机实拍在线 v1.2.12.1 的 26.3 详情页，分组横条 / 版本输入框 / 文字直接压在用户自换壁纸（「我自愿上班」大字、三个卡通人物、时间条插画）上几乎不可辨，下载面板收起后点不开、找不到取消入口，整批下载期间总进度长时间卡住。①**详情页局部磨砂**：`version_detail_view.py` 的 `_LoaderSection` 外层分组与 `_VersionRow` 候选行重写 `paintEvent`，复用 `frosted_backdrop.paint_frosted_panel` 做片内局部磨砂自绘背板——分组整块覆盖横条与展开列表，分默认白玻璃 / 选中浅蓝玻璃 / 不可用压暗三态；版本行弱磨砂背板、选中换浅蓝；`theme.py` 把横条 / 版本行旧 QSS 底色与边框全部置透明交由自绘，避免双重叠加；版本别名输入框、返回箭头白片不透明度由 84 提到 150、边框 104 提到 178，focus 态 176，保证在壁纸大字上可读。②**收起态小胶囊点击展开**：`download_panel.py` 的 `mousePressEvent` 旧版收起态只重启空闲计时、漏调 `expand()`，5 秒自动收起后点右下角小入口无反应；补上 `collapsed` 态点击直接 `expand()`，展开态点击维持重启空闲计时。③**取消链路**：展开态大叉 → `cancelRequested` → `_cancel_current_download` → `requestInterruption()` → worker 清理半成品后 `cancelled` 复位，链路沿用 v1.2.12.0 既有实现未改动；修好收起态展开后即可重新看到取消入口，5 秒自动收起设计保留以避免遮挡详情页。④**步内全局进度实时回填**：`download_worker.py` 旧版 `_global_percent` 只在每步 `_finish_step` 整批完成时一次性跳到下一档，并发下载期间采样线程读到的全局百分比停在上一步完成值，整批库 / 资源下载期间总进度长时间不动；新增 `_current_step` / `_step_before` 与 `_refresh_global_percent()`，采样线程每 0.3 秒先按 tracker 实时快照（优先文件完成率、无文件总数退回字节完成率）算步内比例，叠加该步之前权重基线回填全局百分比，库 / 资源 / 加载器库三步进行中平滑推进；第 0 步联网 JSON 与第 3 步单客户端 Jar 同样登记当前步骤；每步开始 `ProgressTracker.reset_counters()` 清零上一步遗留的已完成 / 失败文件与累计字节，避免跨步计数沿用让本步占比失真顶满。技术红线不变：仅 PySide6 自带模块 + Python 标准库，UA 纯 ASCII，不挂 `QGraphicsBlurEffect`，不引第三方 HTTP / 加密 / PIL / numpy；
- **修复 26.3 新年度版本号加载器误判置灰、详情页改为可折叠版本分组（1.2.12.1）**：真机反馈 26.3 详情页 Forge / NeoForge / Fabric 三张真实可用的加载器卡片全部显示「暂时没有这个版本的加速器」、点不动，OptiFine 真实未出、置灰正确。①**Fabric 判定修正**：新年度版本号（如 26.3）列表里 `intermediary.version` 为 `0.0.0` 占位，旧代码要求 intermediary 与 MC 版本严格等值导致匹配失败；改为 loader 列表非空取最新稳定版后，再拉取该 loader 的 `profile/json`（官方 `meta.fabricmc.net` → BMCLAPI 镜像双端点），返回有效合并层（含 `mainClass` / `inheritsFrom`）才判可用，intermediary 不再做硬门槛。②**NeoForge 年度号直配**：旧 `NEOFORGE_MC_PREFIX_MAP` 只覆盖旧 `1.21.x ↔ 21.1` 体系，新两段纯数字年度号（`26.3`）不在映射表被误杀；未命中映射表时若 MC 为两段纯数字年度号，直接以 MC 作为 NeoForge 版本前缀匹配 metadata 中的稳定候选，快照号（`26.4-snapshot-6`、`25wxxa`）不做同名匹配；稳定过滤保留、按段数值降序取最新。③**缓存 schema 升级**：`LOADER_CACHE_SCHEMA` 由 1 升到 2，`_load_cache()` 校验 schema 不匹配整体作废重建，避免 v1.2.12.0 落盘的 26.3 误判缓存复活。④**标签事件穿透**：分组横条内标题 / 状态 / 箭头三个 `QLabel` 默认不转发鼠标事件给父容器，点在文字上事件被标签吃掉、只有点边距空白才触发横条；三个标签补 `WA_TransparentForMouseEvents`，点在文字上同样触发横条点击。⑤**PCL2 式可折叠版本分组**：`version_detail_view.py` 把原单行单选卡片重构为 `_LoaderSection` 分组——横条（加载器名 + 最新版本状态 + ∧/› 箭头）点击切换展开 / 收起，展开区小标题「全部版本(N)」下竖排候选版本行（Forge 附发布时间，Fabric / NeoForge / OptiFine 端点无时间字段则只显示版本号，不逐个额外请求时间端点、不伪造时间）；单选具体版本、默认选中最新稳定版，一个分组展开时其余自动收起；不可用分组 `setEnabled(False)` 置灰、横条不可展开；原版分组不挂版本列表、点横条选回原版。探测结果模型 `_result` 新增 `versions` 全量候选列表（`[{"version", "time"}]`，新 → 旧），Forge 按 build 降序带 `modified` 时间、Fabric 只列稳定 loader、NeoForge 列全部稳定候选、OptiFine 稳定版在前预览在后；列表随探测结果一并缓存与回传。下载 worker 链路签名不变，`startDownloadRequested` 仍回传 `(mc, alias, loader, loader_version)`，所选具体版本号经 `loader_version` 透传。实测 26.3：Forge 66.1.2（15 条）、NeoForge 26.3.0.101（23 条）、Fabric 0.20.1（稳定 1 条）可用，OptiFine 真实未出置灰；1.21.1 四连可用、1.20.1 旧判定不退化；技术红线不变：仅 PySide6 自带模块 + Python 标准库，UA 纯 ASCII，不挂 `QGraphicsBlurEffect`，不引第三方 HTTP / 加密 / PIL / numpy；
- **版本详情页 + 四加载器真实下载 + 依赖库 / 资源 / Java 拉起 + 顶部居中可取消面板（1.2.12.0）**：在 v1.2.11.0 便携隔离目录、20/30 并发引擎与单例面板基础上，把原先占位的第 2 / 3 / 5 步全部补为真实链路，并按四张参考图重做下载入口、面板形态与滚动条。①**版本详情视图**：新增 `ui/version_detail_view.py`，下载页顶层改为 `QStackedWidget`（index 0 = 原有分组列表，index 1 = 详情视图）；条目下载按钮不再直接开面板，而是 `_open_detail(vid)` 切进详情页——顶部「← 返回」箭头 + 版本名自定义 `QLineEdit`（默认回填 MC 版本号），中部原版卡片 + Forge / NeoForge / Fabric / OptiFine 四张第三方卡片单选，底部居中蓝色「⬇ 开始下载」胶囊；新增 `ui/loader_probe_worker.py` 后台线程，进入页面即调 `loaders.probe_all(mc)` 扫描四个加载器支持性，可用卡片右侧显示「可以添加」并可选中，不支持 / 查不到版本卡片置灰不可选、右侧显示「暂时没有这个版本的加速器」，探测失败回退原版选中态。②**加载器支持性缓存**：`loaders.py` 把按 MC 版本精确键的探测结果（含 schema 版本）永久缓存到 `yd/loader_support_cache.json`（临时文件 + `os.replace` 原子落盘）；同一版本下次打开详情页直接读缓存、不重新联网，仅清单里出现缓存中没有的新版本才重新探测；网络异常按不可用兜底、静默不弹窗。③**真实依赖编排**：新增 `version_profile.py`，沿 `inheritsFrom` 继承链合并原版与加载器 profile，库按 `name` 去重、`arguments.jvm / game` 去重拼接、规则判定（os=windows / features）；收集依赖库任务（Maven 坐标相对路径、规则过滤）、老版本 `natives-*` classifier 下载并解压到隔离目录 `natives/`、`assetIndex` 资源对象任务（legacy 版本落 `assets/virtual/legacy`，现代版本落 `assets/objects`）、`client.jar` 任务；`game_dirs.py` 目录口径改为「别名 = 隔离目录名」，原生 MC 版本 / 加载器类型 / 加载器版本记录在目录内 `install_meta.json`，依赖库落 `libraries/`、natives 落 `natives/`。④**四加载器真实链路**：`loaders.py` 实现 Fabric（官方 meta + BMCLAPI 双端点，校验 intermediary 版本号一致，profile JSON 构建）、Forge（BMCLAPI 版本列表 + 官方 Maven installer，提取 installer 内 `version.json` 并下载其 libraries，BMCL Maven 镜像兜底）、NeoForge（BMCLAPI Maven metadata 匹配 MC 前缀 + installer 提取 `version.json` 与 47 个库）、OptiFine（BMCLAPI 元数据列表 + `adloadx` 广告中转页正则解析真实下载地址）；四条链路均为真实元数据与二进制下载，不做占位；Forge / NeoForge installer 的二进制补丁 `processors` 环节依赖 Java 执行 installer，本机无 Java 时如实兜底、不谎称可直接进游戏。⑤**重写下载 worker**：`ui/download_worker.py` 五步真实编排（JSON / 合并 profile 权重 0.06 → 原版库 0.30 → 资源 0.28 → client.jar 0.24 → 加载器专属库 0.12），新增 `cancelled` 信号；`requestInterruption()` 后中断即清理 `.part` 半成品并回传取消；成功回传 `{alias, mc_version, loader, loader_version}`；构造签名 `VersionDownloadWorker(mc_version, alias, loader=..., loader_version="", parent)`。已安装版本也放行进入详情页重复下载，别名经 `game_dirs.unique_alias` 去重。⑥**下载面板新形态**：`download_panel.py` 展开几何改为顶部水平居中（`x=(面板宽-总宽)//2`、`y=18`），收起态仍贴右下角；新增底部居中 40×40 红色玻璃大叉 `#downloadPanelCancelBtn`（`cancelRequested` 信号，下载中显示、成功 / 失败 / 取消后隐藏），标题右上小 ✕ 仅收起面板；新增 `mark_cancelled()`（标题「已取消」、收起面板、不弹失败提示）；5 秒空闲自动收起口径不变。⑦**滚动条收敛**：删除分组内层 `_InnerScrollArea` 与 `#section-scroll`，分组条目直接交给最外侧 `#page-scroll` 一条极细透明滚动条，条目元素布局保持现状不变。⑧**Java 探测与真实拉起**：新增 `java_runtime.py`，`detect_java()` 按 PATH → 注册表 → 常见目录三级探测；`build_launch_command()` 处理现代 `arguments` 分段与老版本 `minecraftArguments` 模板占位替换、classpath 收集、离线 UUID（MD5 OfflinePlayer 口径）；`launch_game()` 无 Java 返回 `JAVA_MISSING_MESSAGE`、不伪造启动；`profile_page.py` 删除旧模拟随机进度 timer 与占位弹窗，选中缺失版本点开始游戏弹引导提示，选中后读隔离目录落盘合并 profile、探测 Java 并拉起进程，成功才记启动次数与当天日期，失败复位按钮 / 进度条并按是否缺 Java 选标题弹引导；版本列表按钮文案 = 别名、tooltip 标注「MC 版本 · 加载器 版本号」，选中持久化别名。技术红线不变：只用 PySide6 自带模块与 Python 标准库（`winreg` 为标准库，属允许范围），不挂 `QGraphicsBlurEffect`（`QGraphicsOpacityEffect` 按需使用）、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，HTTP UA 纯 ASCII，未引入新运行时依赖；
- **便携目录版本隔离、分块并发下载、单例下载面板与两行滚轮版本列表（1.2.11.0）**：在 v1.2.10.0 全量分类列表基础上打通「下载版本 → 安装 → 个人页选版本」闭环。①**便携 `.minecraft` 目录与版本隔离**：新增 `game_dirs.py`，数据落在 exe 同级（源码运行时工程根）`.minecraft/versions/<版本号>/`，目录缺失自动 `ensure_base_dirs() / ensure_version_dirs()` 生成；判定已安装要求隔离目录内 `<id>.json` 与 `client.jar` 同时存在且非空，`scan_installed_versions()` 按版本号升序扫描；每版本独立 `saves/`、`config/`，不使用 `%APPDATA%\.minecraft`。②**分块并发下载引擎**：新增 `download_engine.py`（纯标准库 `urllib` + `concurrent.futures` + `threading`），`choose_thread_count()` 预估字节大于 1GB 走 30 线程、否则 20 线程；256KB 分块流式写、主 URL 失败切 BMCL 兜底镜像、SHA1 校验、`.part` 原子落盘、幂等跳过已完整文件；`ProgressTracker` 2 秒滑动窗口统计速度与剩余文件；`download_worker.py` 五步状态机后台 `QThread`，第 1 步下载原版 json、第 4 步下载 client.jar 为真实步骤，第 2 / 3 / 5 步本轮占位跳过，离线 / 超时 / 校验失败统一 `failed` 静默回退。③**单例下载状态面板**：新增 `download_panel.py`，`DownloadPanel` 为下载页直接子浮层、不参与父布局，整个页面生命周期只创建复用一次；`start(version_id)` 重置步骤与进度并展开，`update_progress / set_step / mark_success / mark_failed` 接线 worker 信号；`QPropertyAnimation` + `OutCubic` 在右下角锚点铺开 / 收回，展开态为标题 + 左侧总进度 / 速度 / 剩余文件三统计 + 右侧五步清单 + 底部细进度条，收起态为小胶囊（图标 + 版本名 + 百分比）；`QTimer` 5 秒空闲自动收回，`enterEvent / leaveEvent / mousePressEvent` 停表与重启；`paintEvent` 调共享 `paint_frosted_panel` 片内磨砂。④**下载页按钮与已安装标识**：`VersionRow` 与 `VersionEntry` 新增 `downloadRequested` 信号与右侧 `versionDownloadBtn`；`AccordionSection` 注入已安装判定回调并刷新按钮态；`DownloadPage` 单任务单例（已有 worker 在跑忽略后续点击），成功后加入已安装集合、刷新全部分组按钮态并 `emit versionInstalled`；`shutdown()` 纳入下载线程中断等待与面板收尾。⑤**个人页两行滚轮列表**：`profile_page.py` 删除禁用占位 `QComboBox`，替换为固定两行高的 `QScrollArea#version-list-scroll`，条目为 checkable `versionOption` 按钮、选中持久化到 `config.selected_version`；空列表显示占位提示；下载成功由主窗口 `versionInstalled` 信号回调 `refresh_version_list()`。⑥**全局细透明滚动条**：`theme.py` 所有 `QScrollBar` 竖 / 横向收窄到 3px、轨道与页码透明、隐藏箭头、滑块 28px 最小长度半透明白、hover 略亮，覆盖 `page-scroll / section-scroll / version-list-scroll` 及任意 `QScrollArea`；同步补上面板、下载按钮、版本选项与占位全套 QSS。`config_store.py` 新增 `selected_version` 字段与类型校正；本轮仍不解析完整依赖库 / 资源清单、不拉起 JVM 与本机 Java 进程，Forge / NeoForge / Fabric / OptiFine 加载器选择与版本详情页不在本轮范围；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`（`QGraphicsOpacityEffect` 按需使用）、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **分组横条分类图 + 条目小图标、清单本地缓存与后台更新淡入淡出弹窗（1.2.10.0）**：按真机观感反馈补齐下载页分类图与二次启动不刷新行为。①**分组 / 条目方块图标**：此前四张方块图虽已下载、`SECTIONS` 也绑定了 `block_file`，但 `AccordionSection` 标题横条并未创建图标 `QLabel`，四个分组横条光秃秃；本轮横条最左侧补 `sectionHeaderIcon`（仅四个全量分组、最新版本横条不重复挂图，22px），`VersionEntry` 条目左侧补 `versionEntryIcon`（18px，与横条共享同一张分组贴图）；模块级 `_PIXMAP_CACHE` 按 `(block_file, size)` 缓存缩放后 `QPixmap`，748 条预览版不再重复解码 256×256 原图。②**清单本地缓存**：`version_meta.py` 新增 `_cache_path() / _manifest_is_valid() / load_cached_manifest() / save_cached_manifest()`，清单分类结果以 `{"schema":1,"fetched_at":...,"manifest":{...}}` 原子写入 `yd/version_manifest_cache.json`（临时文件 + `os.replace`）；`VersionMetaWorker` 先读缓存，命中直接回传 `source="cache"` 不联网，无缓存 / 损坏才按国内 BMCLAPI2 → 官方 piston-meta 轮询全量拉取，成功后由主线程落盘；二次及以后启动直接读缓存渲染、不重新拉全量、不清空重绘。③**后台静默检查 + 更新提示弹窗**：缓存命中启动后另起 `VersionCheckWorker` 轻量线程，只比对 `latest.release` / `latest.snapshot` 版号，差异时收集「最新正式版 / 最新预览版」新旧版号与时间，静默覆盖缓存但**不调用 `_apply_meta` 重建当前列表**；`UpdateNoticePopup` 为 `DownloadPage` 直接子非模态 `QFrame` 浮层，`QGraphicsOpacityEffect` 驱动 220ms OutCubic 淡入、点「知道了」220ms InCubic 淡出后 `deleteLater()`，一个或两个版本更新分别列出对应变化行（分类小图标 + 分类名 + 新版号）；无变化不弹窗。④**线程关闭加固**：两个 QThread `run()` 开头 / 返回后检查 `isInterruptionRequested()`，`fetch_manifest_groups` / `_fetch_payload` 透传 `should_cancel` 回调，端点轮询与重试间隔分段检查、被取消抛 `InterruptedError`；HTTP 超时压到 6s、重试 1 次，`DownloadPage.shutdown()` 中断后 wait 7000ms 覆盖最坏阻塞窗口，`MainWindow.shutdown()` 对会话恢复线程同样先中断再等待，杜绝退出阶段 QThread 未结束即析构触发 `0xC0000409`。本轮不新增手动刷新按钮，只拉版本号与日期文本、不下载游戏客户端、不解析完整版本文件清单、不绑定下载 / 启动动作；离线 / 断连 / 超时静默回退占位；全量分类口径、双向滑入淡入显现动画、点开构建 / 收起释放懒加载、组内独立滚动与嵌套边界转发保持 v1.2.9.2 设计不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`（`QGraphicsOpacityEffect` 按需使用）、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **下载页全量列表四项真机缺陷修复（1.2.9.2）**：在 v1.2.9.1 全量分类列表基础上修复本轮真机暴露的四处问题。①**退出原生崩溃**：测试脚本 `main()` 直接返回不触发 `closeEvent`，下载页清单后台线程 `_meta_worker` 与主窗口会话恢复线程 `_restore_worker` 仍在运行，进程析构 C++ 控件后线程才 emit 信号、槽函数访问已销毁原生对象，进程以 `0xC0000409` 退出且无 Python traceback；`download_page.py` 新增 `DownloadPage.shutdown()`（中断并等待清单线程、`RuntimeError` 兜底），`main_window.py` 新增 `MainWindow.shutdown()`（等待恢复线程后调用下载页 `shutdown()`），两个 `closeEvent` 先执行 `shutdown()` 再保存配置，回归脚本收尾显式 `window.shutdown(); window.close(); QTest.qWait(60)` 等待线程自然结束。②**组内视口高度**：list 型分组内层 `QScrollArea` 原用 `setMaximumHeight(340)`，`setWidgetResizable(True)` 下视口随内容 `sizeHint` 收缩成一两行高；改为 `setFixedHeight(340)`，展开后视口恒定 340px，条目多时组内独立滚动、条目少时底部透明留白。③**清单瞬时断连重试**：`constants.py` 新增 `META_FETCH_RETRIES = 2` / `META_RETRY_DELAY = 1.5`，`version_meta.py` 的 `fetch_manifest_groups()` 把 HTTP 请求与 JSON 解析包进重试循环，中间失败轻量等待后重试，全部尝试仍失败才上抛由界面静默占位，规避偶发 `Remote end closed connection without response` 导致整组清单空白。④**分批条目坐标塌顶**：超大列表分批构建时，最后一批条目在布局尚未分配垂直几何时就进入可见性判定，映射坐标与本地几何均为 0，被误判进首屏并把 y=0 固化到容器顶部，真机首行叠出列表末条、首条被挤出视口；修复为分批收尾批次无论第几批都按首屏路径 `_finalize_layout(first_pass=True)`，判定前 `activate()` 强制布局完成几何分配、清空上一轮 `_cached_top` 重新映射，坐标取值在映射为 0 而本地几何非 0 时以本地几何为准，`place_directly()` 只校正水平偏移、垂直位置完全交给布局，二次校验定时器回调前同样激活布局并刷新缓存。正式版 103、预览版 748、远古版 61（分批路径）、愚人节版 9（同步路径）真机坐标连续、首末条位置正确。全量分类口径、双向滑入淡入动画、点开构建 / 收起释放懒加载与嵌套边界转发保持 v1.2.9.1 设计不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **下载页全量版本分类列表 + 分组内滚动双向显现动画（1.2.9.1）**：推翻 v1.2.8.1「四分组各只放一条代表版本」的旧边界，`version_meta.py` 重写为解析官方 `versions` 完整数组并归类——`release` 全集进正式版、`snapshot` 且不在 `APRIL_FOOL_IDS` 白名单内进预览版、`old_beta` + `old_alpha` 合并按时间倒序进远古版、白名单精确命中条目进愚人节版；分类抽成纯函数 `classify_versions()` 供离线回归单测，未知 / 未来新增 type 兜底归入预览版不丢失；`latest.release` / `latest.snapshot` 只回填「最新版本」分组固定两行。`download_page.py` 四个分组由单条占位改为懒加载列表：`AccordionSection` list 型 body 内嵌独立 `QScrollArea`（上限 340px），点开分组动画结束才构建 `VersionEntry` 轻量条目（版本号 + 日期两栏玻璃行），收起动画结束销毁全部条目控件释放内存；`set_list_data()` 先暂存全量数据，未展开不预构建。滚动驱动双向显现：内层滚动条 `valueChanged` 计算方向与滚轮位移，视口缓冲带内未显现条目播放滑入 + 淡入并行动画——向下滚从左往右、向上滚从右往左，滚出视口复位隐藏供反向滚回重显；动画时长按滚轮速度在 110–280ms 之间伸缩（滚得快动画短、滚得慢动画缓），首次点开首屏条目交错 12ms 入场，超出首屏条目直接就位；透明度特效按需创建，仅首屏与缓冲带条目挂 `QGraphicsOpacityEffect`，非首屏条目保持默认不透明；超大列表分批构建，首批同步建首屏、其余定时器分批补建，分批中途只刷新几何、全部就位后才做一次可见性判定，避免数百条控件一次性创建阻塞主线程；条目垂直坐标首次映射后缓存复用；收起销毁条目时先停动画、断信号、剥离特效再摘除父对象，杜绝退出清理阶段原生控件析构崩溃；嵌套滚动区滚到上 / 下边界后忽略滚轮事件交回外层页面滚动。横条右侧新增条目计数（`n 条`）；离线 / 超时 / 解析失败条目区保持「版本列表加载中…」占位，分组正常显示不弹窗。`theme.py` 新增 `section-scroll` / `section-list-container` 透明规则、`versionEntry` 玻璃圆角行与 `versionEntryTitle / versionEntryTime / sectionCount / sectionPlaceholder` 选择器，最新两行 `versionRow` 规则原样保留；未新增色值常量，复用既有浅蓝白玻璃体系。本轮**只拉版本号与日期文本，不下载游戏客户端、不绑定下载 / 启动动作**；分类标签点击仍只切单选高亮；启动个人页、3D 预览、离线 / 正版认证链路、账号持久化、壁纸与片内局部磨砂体系全部保持不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **修复下载页底部白板 + 四分组联网回填代表版本号（1.2.8.1）**：真机翻拍反馈下载页四条收起横条下方占据下半屏一大块不透明白色空白板，且正式版 / 预览版 / 远古版 / 愚人节版展开后只有方块占位、不拉版本号。白板根因：下载页内容容器 `#download-container` 缺少 QSS 透明规则，保留 Qt 默认自动填充的不透明浅灰（239,239,239），`setWidgetResizable(True)` 把容器拉伸到整个视口高度，分组末尾弹簧留白区被这块不透明矩形填满；个人页 `#page-container` 因有透明规则而正常。修复：`theme.py` 为 `#download-container` 与 `QScrollArea#page-scroll > QWidget` 补 `background: transparent` 规则，`download_page.py` 显式关闭容器与滚动视口自动填充背景、开启 `WA_StyledBackground`，留白处透出底层背景层，不再压白板。版本回填：`version_meta.py` 由四元组扩展为 `fetch_section_versions()` 一次解析 `release / snapshot / ancient / april` 四组 `(版本号, 北京时间发布日期)`；正式版分组代表 = `latest.release`、预览版分组代表 = `latest.snapshot`（与最新版本两行同源），远古版固定取经典正式版 `1.12.2`、清单缺失回退最早一条 release，愚人节版取 `APRIL_FOOL_IDS` 精确白名单中 `releaseTime` 最新一条；`version_meta_worker.py` 信号由四个标量改为 `succeeded(object)` 回传整组字典；`download_page.py` 新增 `_section_rows / _section_names` 映射，`_apply_meta(sections: dict)` 按本次全集刷新，缺失分类回退初始分组名占位、不覆盖。副标题口径：有日期拼「前缀，发布于 YYYY/MM/DD HH:MM」，无日期仅保留前缀短语；离线、超时、解析失败时对应槽位留空，分组正常显示，不弹窗、不阻塞、不崩溃。本轮**仍不拉旧版本完整列表、不下载游戏客户端、不绑定下载 / 启动动作**；其余启动个人页、3D 预览、认证链路、账号持久化、壁纸与片内局部磨砂体系全部保持不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **下载页改为可折叠分组手风琴 + 发布日期只读展示（1.2.7.1）**：在 v1.2.6.1 五卡片基础上，按参考图把下载页五张横条改造为五个可折叠分组。标题横条再缩小一档（高度 36px、图标仅在展开后出现），左侧分组名、右侧 ∧ / ∨ 折叠箭头，**收起态不显示方块图标**；点击横条以 160ms OutCubic 平滑高度动画展开 / 收起，分组列表放入 `QScrollArea` 可滚轮滑动浏览。「最新版本」分组默认展开，内含两行实时条目：最新正式版（草方块 `grass_block.png`）、最新预览版（钻石块 `diamond_block.png`），每行大版本号 + 「最新正式版 / 最新预览版，发布于 YYYY/MM/DD HH:MM」小字；`version_meta.py` 在 `latest.release` / `latest.snapshot` 之外解析对应 `releaseTime`，按 UTC+8 北京时间格式化，日期解析失败仅留空、不影响版本号。正式版 / 预览版 / 远古版 / 愚人节版四个分组展开后只放各自代表方块占位条目（草方块 / 钻石块 / 命令方块 / 金块），本轮不拉旧版本列表、**不下载游戏客户端、不绑定下载 / 启动动作**；离线、超时或解析失败时版本号与日期槽位留空，分组正常显示，不弹窗、不阻塞、不崩溃。`theme.py` 新增 `sectionHeader / sectionTitle / sectionArrow / versionRow / versionRowTitle / versionRowSubtitle` 选择器并下调横条与条目字号；其余启动个人页、3D 预览、认证链路、账号持久化、壁纸与片内局部磨砂体系全部保持不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **下载页五卡片缩小 + 方块 3D 渲染图 + 官方版本号只读展示（1.2.6.1）**：在 v1.2.5.1 五导航骨架基础上改造「下载」导航五张版本卡片。布局：五张仍竖排均分，仅把卡片高度、方块图标尺寸、字号与卡片间距整体调小；卡片由原单居中文字改为「方块图标 + 左侧名称 + 右侧版本号」三栏横排。素材：四张方块图均取自公开渲染服务的现成 256×256 透明 3D 等距渲染 PNG（`resources/blocks/`），不由程序自绘——正式版草方块、预览版钻石块、远古版命令方块、愚人节版金块；「最新版本」卡片不放方块图标。版本号：新增纯标准库 `cloud_launcher/version_meta.py` 只读请求 Mojang 官方 `version_manifest_v2.json`，后台 `QThread`（`cloud_launcher/ui/version_meta_worker.py`）拉取 `latest.release` 回填「最新版本」卡片、`latest.snapshot` 回填「预览版」卡片；正式版 / 远古版 / 愚人节版不拉版本号。本轮**只拉版本号文本展示**，不下载游戏客户端、不解析完整版本清单、不绑定下载 / 启动动作；离线、超时或解析失败时版本号槽位留空，卡片正常显示，不弹窗、不阻塞、不崩溃。`constants.py` 追加官方清单端点与超时常量；`theme.py` 新增方块图标与版本号标签选择器并下调卡片字号；`tools/fetch_block_icons.py` 为可复用的方块素材拉取脚本（仅构建期运行，不进运行时依赖）。分类标签点击仍只切换单选高亮；设置 / 打包 / 关于保持通用占位骨架页；启动个人页、3D 预览、认证链路、账号持久化、壁纸与片内局部磨砂体系全部保持不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新运行时依赖；
- **PCL 式五导航骨架 + 下载页六标签五版本卡片（1.2.5.1）**：按用户提供的 PCL 式参考截图先搭界面骨架、功能后续逐步接入。左侧导航由原单一「个人页」重构为「启动 / 下载 / 设置 / 打包 / 关于」五项竖排导航，每项为图标 + 文字；点击切换页面时被选中项隐藏图标、只保留加粗文字，未选中项恢复图标 + 文字；五张导航透明 PNG 由 `tools/make_assets.py` 从桌面五张白底 3D 图标 flood-fill 抠除外部纯白背景、按非透明包围盒裁剪后等比贴到 96×96 透明画布居中，输出到 `resources/icons/`。页面归属（用户最终确认方案）：「启动」导航直接挂旧 `ProfilePage` 个人页作为默认可见页——3D 角色预览、昵称、离线 / 正版登录、游玩统计、游戏版本占位行、加载进度条与开始游戏按钮全部原样恢复显示；「下载」导航新增 `cloud_launcher/ui/download_page.py` 骨架页：顶部横排六个等宽分类标签（原版游戏 / mod / 整合包 / 光影包 / 资源包 / 数据包），点击只切换单选高亮、不接真实分类拉取；下方五张通长版本横条卡片（最新版本 / 正式版 / 预览版 / 远古版 / 愚人节版）纵向均分撑满，每张为透明 + 片内局部磨砂圆角横条、文字居中，第一张「最新版本」引用略深一档三段白玻璃与亮边突出置顶推荐；卡片磨砂复用 `frosted_backdrop.paint_frosted_panel`，不挂 `QGraphicsBlurEffect`、不引第三方模糊库。新增 `cloud_launcher/ui/placeholder_page.py` 通用占位页，设置 / 打包 / 关于三个导航各挂一个实例，仅居中标题 + 后续开放提示，本轮不接真实功能。旧个人页（3D 角色预览、离线 / 正版登录、游玩统计、开始游戏进度条、账号持久化与静默恢复）代码完整保留、不删不退化，作为启动导航页面直接可见；全局指针轮询仅在启动个人页可见时才转发给 GL 预览，切到下载骨架或占位页时停止转发。`constants.py` 新增分类标签三态玻璃 / 描边与版本卡片普通档、置顶档两组三段磨砂色值；`theme.py` 新增 `categoryTab / categoryActive`、`versionCard` 容器透明、`versionCardText / versionCardTopText`、`navText` 导航文字规则，导航项内边距移交内部图标 + 文字布局控制。窗口保持 980×660（最小 900×600）；3D 标准几何 / 相机距离 / 分层指针跟随 / 待机摆臂、Steve / Alex 双皮肤、外部正版皮肤与 CLASSIC / SLIM 模型、离线 / 正版分段交互、认证五段链路与账号持久化、外部壁纸与片内局部磨砂体系全部保持不变；技术红线不变：只用 PySide6 自带模块与 Python 标准库，不挂 `QGraphicsBlurEffect`、不引 PIL / numpy / scipy / 第三方 HTTP / 认证 / 加密库，未引入新依赖；
- **仅六功能键半透明玻璃、拖拽彻底去格挡、主按钮独立淡玻璃档（1.2.4.6）**：真机两轮反馈先指出「拖拽按钮仍被挡住」，随后明确透明范围口径——只有导航「个人页」、离线、正版、开始游戏、标题栏最小化、关闭这六个功能键做透明玻璃，背景、卡片、侧栏、进度条、输入框等其余区域不做整窗 / 全页面模糊毛玻璃；且六按钮此前被做成不透明白板，要求改成真正半透明、透出下层。本轮先把上一轮误改的 `background_layer.py`、`frosted_backdrop.py`、`capsule_progress_bar.py`、`main_window.py` 与 `constants.py` 非按钮色值整体回退 v1.2.4.5 基线（清晰壁纸 + 片内局部磨砂），只保留 `spring_button.py` 取消格挡控制器。材质侧：用真实窗口 `grab()` 像素明度探针逐按钮采样边缘空白区（避开中央文字 / 符号笔画），以按钮明度减紧邻背景明度的 ΔL 作为「白板凸出」量化指标；导航 / 离线 / 正版 / 最小化 / 关闭五颗把填充透明度下调到 ΔL ≤ 3.1，开始游戏主按钮因身后是较暗浅蓝壁纸 / 罩层、不与分段导航共用一档白，单独新增 `COLOR_BTN_GLASS_PRIMARY / _HOVER / _PRESSED` 与 `COLOR_BTN_BORDER_PRIMARY / _HOVER` 一组更淡专用色，`theme.py` 的 `primaryButton` 默认 / hover / pressed 三态与三条描边分别引用专用常量，复测 ΔL=4.5 全部融合达标；标题圆主体白圆透明度由 210 下调到 54、描边由 238 下调到 110，外层成组浅玻璃框保持 v1.2.4.5 基线不动。手感侧：`spring_button.py` 取消上一版两道格挡墙——`pull()` 不再把偏移硬 clamp 到 16px，改为阻尼 0.34 乘渐近软饱和 `max_len / (max_len + length)`（日常拖拽几乎线性跟手、极远才缓慢趋近 110px 上限，无硬截断点）；按住拖动时按钮 `move()` 做真实几何整体跟随，`paintEvent` 调 `setClipping(False)` 放开 painter 矩形裁剪，平移后一端不再被切平；松开 300ms OutBack 回弹，动画结束 `setGeometry(_orig_geo)` 复位按压瞬间原始几何；`click()` / `clicked` 信号保留，仅响应左键、悬停不变形。离屏探针断言六项：按住拖出矩形外跟随、继续远拉偏移单调增长无硬墙、松开复位原始几何、clicked 触发一次、标题圆跟随、标题圆复位，全部通过。输入框、版本下拉、进度条、登录弹窗按钮、退出登录文字按钮、卡片 / 侧栏 / 背景全部不在本轮范围，保持 v1.2.4.5 基线。技术红线不变：不挂 `QGraphicsBlurEffect`、不引第三方模糊 / HTTP / 认证 / 加密库，只用 PySide6 自带模块与标准库；窗口 980×660、两列个人页布局、3D 标准几何 / 相机距离 / 分层指针跟随 / 待机摆臂、Steve / Alex 双皮肤、外部正版皮肤、离线 / 正版分段交互、认证五段链路与账号持久化、预览区透明无黑底白板全部保持不变，未引入新依赖；
- **六按钮统一白玻璃胶囊、全局光标拉扯 + 果冻形变（1.2.4.5）**：真机反馈上一轮按钮「拉的时候像有东西挡住、拉不远」，且要求六个按钮全部换成第二张参考图那种 iOS 白色半透明胶囊、统一透明玻璃语言。本轮分两部分修复。手感侧：`spring_button.py` 的 `SpringController` 拉扯向量不再用按钮本地事件坐标（指针拖出按钮矩形后向量不再增长、被边界卡死），`mouseMoveEvent` 改用 `QCursor.pos()` 经 `mapFromGlobal` 映射回本控件坐标，指针在按钮外也持续跟随；限幅由 10px 放宽到 16px、阻尼由 0.22 调到 0.30，标题栏小圆按钮覆盖为 6px / 0.22；新增沿拉扯方向的非均匀果冻形变——`apply_transform` 先平移到拉扯偏移与控件中心，按 `atan2` 得到方向角后 `rotate(angle) → scale(方向拉伸 1+7%×幅度, 垂直压缩 1-4.5%×幅度) → rotate(-angle)`，幅度随偏移归一化大小线性变化，松手随偏移一起回弹归零，文字与形状一起轻微变形；形变只在按钮矩形内部完成，不依赖越界绘制，避免被父片裁剪成「被压住」的观感。材质侧：`theme.py` 的 `navItem`、`modeButton`、`primaryButton` 三组规则统一改为白半透明胶囊——新增 `COLOR_BTN_GLASS / _HOVER / _ACTIVE / _PRIMARY` 与 `COLOR_BTN_BORDER / _BORDER_ACTIVE` 一套白玻璃色值；默认白玻璃细亮边、深色字，hover 略亮，选中态（`navActive` / `modeActive`）只用更亮填充 + 亮描边 + 加粗深色字区分，删除旧浅蓝渐变、蓝边与蓝字；开始游戏主按钮由三段玻璃蓝渐变白字改为白玻璃、深色加粗字，固定 44×146 与圆角 22 几何保留。标题栏 `TitleCircleButton` 材质并入同一套白玻璃语言（白圆 210 透明度 + 238 亮白描边 + 单层淡投影，关闭 hover 浅红反馈保留），不再保留旧独立厚重白圆样式。输入框、版本下拉、进度条、登录弹窗按钮、退出登录文字按钮不在本轮范围，保持既有样式。技术红线不变：不挂 `QGraphicsBlurEffect`、不引第三方模糊 / HTTP / 认证 / 加密库，只用 PySide6 自带模块与标准库；窗口 980×660、两列个人页布局、3D 标准几何 / 相机距离 / 分层指针跟随 / 待机摆臂、Steve / Alex 双皮肤、外部正版皮肤、离线 / 正版分段交互、认证五段链路与账号持久化、预览区透明无黑底白板全部保持不变，未引入新依赖；
- **六个按钮橡皮筋拉扯 + 松开弹簧回弹、标题栏白圆成组（1.2.4.4）**：按用户最终收窄口径，本轮只给六个按钮加手感动画，不改卡片、分段按钮与主按钮材质，整窗其余外观退回 v1.2.4.3 旧样子。新增 `cloud_launcher/ui/spring_button.py`：`SpringController` 维护拉扯偏移与收缩缩放两段动画——左键 `press()` 进入拉扯态、整体由 1.0 轻微收到 0.96（80ms OutQuad）；按住拖动 `pull(position)` 取指针相对按钮中心的向量，按阻尼 0.22 折算偏移并限幅到大按钮 10px（标题栏小圆按钮覆盖为 4px、阻尼 0.16，避免被拽出成组框）；松开 `release()` 后 260ms OutBack（`setOvershoot(1.15)` 把默认 1.7 过冲收到柔和一档）把偏移与缩放从当前状态插值回 (0, 0, 1.0)，曲线中段略大于 1 时偏移反向轻晃、缩放轻微超过 1，形成橡皮筋弹回手感。`SpringPushButton` 继承 `QPushButton`，重写 `mousePressEvent / mouseMoveEvent / mouseReleaseEvent` 驱动控制器（仅响应左键，悬停不变形），`paintEvent` 内围绕中心 `translate(偏移) → scale → translate` 后交 `QStyle.drawControl(CE_PushButton)` 整体渲染 QSS 背景 / 圆角 / 文字；只变换渲染内容、不改动 geometry、不触碰布局与尺寸策略，`click()` 与 `clicked` 信号保持不变。接入的六个按钮为：导航「个人页」、离线、正版、开始游戏，以及标题栏最小化、关闭；退出登录文字按钮与登录弹窗按钮保持普通 `QPushButton`、不接动画。标题栏旧两个独立系统风按钮删除，改为 `TitleCircleButton`（28×28，paintEvent 自绘两层向下偏移柔和投影 + 白色圆 + 浅灰描边 + 符号：最小化画横线、关闭画 ✕，关闭 hover 浅红底红符号）与 `TitleButtonGroup`（固定高 34、圆角 17 浅白玻璃框，内部 margins 6/3/6/3、spacing 6 收进两个圆按钮）。三张卡片外围投影浮层、离线 / 正版分段白色凸起片、开始游戏透明毛玻璃胶囊均属早期被用户否决的整窗改动，本版已全部回退：卡片沿用 v1.2.4.3 片内局部磨砂、分段沿用旧玻璃蓝选中态、主按钮沿用旧三段玻璃蓝渐变白字椭圆胶囊。技术红线不变：不挂 `QGraphicsBlurEffect`、不引第三方模糊 / HTTP / 认证 / 加密库，只用 PySide6 自带模块与标准库。窗口 980×660、两列个人页布局、3D 标准几何 / 相机距离 / 分层指针跟随 / 待机摆臂、Steve / Alex 双皮肤、外部正版皮肤、离线 / 正版分段交互、认证五段链路与账号持久化、预览区透明无黑底白板全部保持不变，未引入新依赖；
- **3D 人物预览背景彻底透明、角色直接浮在磨砂卡片上（1.2.4.3）**：v1.2.4.2 删掉内层白框后，`SkinPreview`(QOpenGLWidget) 自身仍是一块不透明浅灰白清屏矩形，在磨砂卡片上依旧是独立底板；真机反馈要求把这块白底彻底删掉、轮廓外透出卡片磨砂与壁纸，且明确不允许出现黑底。本轮不再保留不透明清屏底色，改为透明合成组合：`QSurfaceFormat` 请求 8 位 alpha 颜色缓冲；控件开启 `WA_TranslucentBackground` 并关闭自动填充背景；开启 `WA_AlwaysStackOnTop`——Qt 官方文档说明 QOpenGLWidget 默认先于所有普通非 GL 控件绘制、下方 widget 透不过来，只开 alpha 缓冲在本机 Windows / DWM 真实屏幕合成下会把 alpha=0 清屏区显示成黑色矩形（离屏 `grab()` 合成正常、屏幕合成发黑，必须以真实窗口屏幕截图复核，不能只看 widget 截图），压到合成顺序最上层后轮廓外 alpha=0 区域才能透出下方卡片；`initializeGL` 打开 `GL_BLEND` 源 alpha 混合、`glClearColor(0,0,0,0)`，角色不透明片 alpha=1、透明区不写任何底色。本机 Intel UHD 620 / OpenGL 4.6 / Qt 6.12 默认渐变与外部壁纸两态真实窗口屏幕截图实测：GL 透明区与卡片磨砂参照同高度逐通道一致，无黑底、无独立白 / 灰矩形。本控件矩形之上没有叠放其他控件（卡片标题在 body 之外），`WA_AlwaysStackOnTop` 打破堆叠顺序的副作用在此场景不成立。3D 标准几何、相机距离（FOV 38 / DIST 88）、身体 0.18 / 0.10 与头部 0.55 / 0.35 分层指针跟随、待机双臂摆臂、Steve / Alex 双皮肤、外部正版皮肤纹理替换与 CLASSIC / SLIM 手臂模型、离线 / 正版分段按钮、认证五段链路与账号持久化全部保持不变，未引入新依赖；
- **移除人物预览卡内层白框与双层玻璃、GL 底色融入卡片（1.2.4.2）**：真机实拍反馈右侧「玩家人物」卡片小人背后还有一块白色底板、且比外层磨砂多叠了一层玻璃。定位为三层叠加：外层 `Card` 局部磨砂大圆角片、内层 `QFrame#preview-pane` 半透白玻璃小窗（白描边 + 14px 圆角）、`SkinPreview`(QOpenGLWidget) 自身不透明清屏铺满；内层白框几乎把外层磨砂全挡住，形成「两层玻璃 + 一块冷白板」观感。本轮删除 `profile_page.py` 中 `preview_box / pane / pane_layout` 全部包装，3D 预览直接加入外层卡片 `body`，四周留白由卡片自身边距提供；删除 `theme.py` 的 `QFrame#preview-pane` 规则与 `constants.py` 配套 `COLOR_PREVIEW_GLASS / COLOR_PREVIEW_BORDER` 常量；GL 清屏色由冷蓝白 `#ECF4FA` 改为三通道近乎相等的中性浅灰白 `(243,244,245)`，与卡片白玻璃高光贴近。受本机 Windows / Qt 下 QOpenGLWidget 的 FBO 无法把透明像素合成透出父控件（真透明会黑底）限制，清屏仍为不透明底色、不做 RGBA 透明；卡片磨砂会随壁纸透出明暗与色偏，GL 固定纯色在卡片下部存在细微色差，属于该限制下的固有差异。左侧昵称卡 / 统计卡 / 侧栏局部磨砂、3D 标准几何 / 相机 / 指针跟随 / 待机摆臂、离线 / 正版分段按钮、认证五段链路与账号持久化全部保持不变，未引入新依赖；
- **模糊下沉为卡片 / 侧栏片内局部磨砂（1.2.4.1）**：v1.2.4.0 把整窗壁纸先降采样柔化铺满、卡片只盖一层半透明白片，整张壁纸都是糊的；按用户反馈「不是全部都模糊，而是每一个卡片下才这样模糊、有玻璃质感」返工为 iOS 式局部毛玻璃。最底层 `BackgroundLayer` 不再做全屏降采样柔化、也不叠整窗中性磨砂罩，只把清晰壁纸等比 cover 铺满，卡片之外露出的壁纸保持清晰；新增 `cloud_launcher/ui/frosted_backdrop.py` 共享服务 `FrostedBackdrop`（模块级单例 `backdrop`），持有清晰原图并按主窗口尺寸构建一张清晰 cover 缓存图，提供 `cover_rect` 等比几何与 `paint_frosted_panel` 自绘工具。`Card` 与 `NavSidebar` 重写 `paintEvent`：用 `mapTo` 取面板相对主窗口的矩形，从共享清晰缓存上 `copy()` 出正后方小块，先快变换压到短边 40px、再平滑放大回面板尺寸得到片内大半径柔化，`QPainterPath` 圆角路径裁剪绘制（模糊绝不溢出面板矩形），其上叠三段白玻璃高光与 1px 细亮边；QSS 中 `QFrame#card` / `QFrame#sidebar` 的背景与边框移交自绘、置透明无边框，避免白渐变双重叠加压成白板。无壁纸时面板只画三段白玻璃渐变与描边，回退观感与旧默认背景一致。技术红线不变：不挂 `QGraphicsBlurEffect`（会连带模糊上层文字）、不引入 PIL / numpy / scipy，柔化仅靠两级缩放；子控件（文字、输入框、按钮、GL 预览）由 Qt 在自绘层之后独立绘制，不被柔化。个人页两列布局、三格纵向统计、独立通长版本占位行、3D 标准几何 / 相机 / 指针跟随 / 待机摆臂、自绘胶囊进度条、开始游戏椭圆胶囊按钮、离线 / 正版分段按钮、认证五段链路与账号持久化全部保持不变，未引入新依赖；
- **外部可替换壁纸与 iOS 式毛玻璃背景（1.2.4.0）**：按用户提供的卡通壁纸与三张 iOS 锁屏 / 桌面深色磨砂参考图，把主窗口背景从写死的蓝白渐变改为**外部可替换壁纸 + 真实柔化毛玻璃**。新增 `cloud_launcher/wallpaper.py` 负责目录发现、安全加载与平均亮度采样，新增 `cloud_launcher/ui/background_layer.py` 独立背景层铺在根窗口最底层（`WA_TransparentForMouseEvents`，不拦截指针跟随事件）。壁纸取自 exe 同级外部目录 `wallpaper/`，固定优先级读取 `wallpaper.png / .jpg / .jpeg / .webp / .bmp`，目录内其余受支持图片按文件名排序兜底；**壁纸不打进 exe、不进入源码压缩包**，用户以后把任意图片同名覆盖到该目录即可换图。模糊不挂 `QGraphicsBlurEffect`（会连带模糊上层卡片与文字）、不引入 PIL / numpy / scipy 等第三方模糊库：先把原图降采样到短边 96px 得到与窗口尺寸无关的柔化小图，绘制时再按 cover 矩形双线性平滑放大到窗口尺寸，两级缩放等效大半径高斯柔化，窗口缩放不重建缓存。壁纸按 cover 等比放大铺满、居中裁切；其上叠一层中性磨砂罩（上缘偏亮、底部略透）统一基调、压住局部高对比色块并保证深墨蓝文字可读；侧栏圆角 22px、卡片圆角 20px，玻璃三段顶部保留白色反光高光、中下部进一步透化，模糊壁纸从玻璃片后水印式透出。**回退口径**：壁纸目录缺失、文件损坏、格式不支持或被用户手动删除时，加载全程 `try/except` 静默返回空图，背景层绘制既有浅柔蓝白渐变默认背景，不弹窗、不抛异常、不崩溃；主 `config.json` schema 不新增任何壁纸字段。本版壁纸为亮调，沿用既有深色文字 + 白玻璃体系；平均亮度阈值与暗壁纸分支色值已在常量中预留，后续接入任意深色自定义壁纸时再切换磨砂与文字配色。登录弹窗维持既有亮白玻璃面板不变，壁纸与毛玻璃只作用于主窗口；个人页两列布局、三格纵向统计、独立通长版本占位行、3D 标准几何 / 相机 / 指针跟随 / 待机摆臂、自绘胶囊进度条、开始游戏椭圆胶囊按钮、离线 / 正版分段按钮与认证五段链路全部保持不变，未引入新依赖；
- **设备码登录弹窗无边框真圆角玻璃化（1.2.3.1）**：真机实拍反馈登录弹窗「角落磨不平、不够好看」。根因是弹窗沿用系统原生标题栏与直角窗口外壳，QSS 的圆角只绘制在客户区背景上，外层系统矩形外壳在四角露出无法磨平的硬直角。本轮把 `MsLoginDialog` 改为与主窗口一致的无边框悬浮面板：`FramelessWindowHint` 去掉系统标题栏与外壳，自绘一条含云朵 Logo、小标题与 ✕ 关闭按钮的标题栏并支持按住拖动；面板改为三段玻璃渐变 + 20px 大圆角 + 同系细亮边；设备码码框圆角加大到 16px、换成更白的两段玻璃、字距由 6px 收到 4px、上下留白更舒展；「取消 / 关闭」按钮改为 36px 高、18px 半高圆角的轻玻璃胶囊，hover / 按下有通透反馈；链接 hover 加深一档，状态行行高与区块间距统一调整。认证五段链路、后台轮询、成功 / 失败状态文案、个人页布局、3D 预览、皮肤下载与其余全部界面规则保持不变，未引入新依赖；
- **正版账号本地持久化与启动静默续期（1.2.3.0）**：此前正版登录的刷新令牌、昵称、UUID、皮肤地址只保存在进程内存，关闭启动器即清空，下次启动默认离线、需要重新走一遍设备码授权。本轮对标 PCL2 等主流桌面启动器的长期在线做法：登录成功后把**刷新令牌**与公开身份（昵称、UUID、皮肤地址、手臂模型类型）写入 exe 同级独立目录 `yd/account.json`（明文 JSON 单文件，与只存离线昵称 / 统计 / 窗口位置的主 `config.json` 分离）；下次启动时后台独立 `QThread` 读取本地存档，用刷新令牌静默换新微软访问令牌并重走 Xbox Live → XSTS → Minecraft → 玩家档案链路，成功后自动切回正版态、回写轮换后的新刷新令牌并刷新个人页；静默续期失败（令牌过期 / 被吊销 / 未购买游戏 / 网络异常）时自动删除本地账号文件、保持离线界面，不弹窗打扰，需要时点「正版」重新设备码授权。短期微软 / Xbox / XSTS / Minecraft 访问令牌与过期时间**不落盘**；点「离线」或「退出登录」立即删除账号文件。主 `config.json` schema 不混入任何账号字段；不做 DPAPI 加密、不引入第三方认证 / 加密库；个人页布局、3D 预览、皮肤下载、自绘胶囊进度条与开始游戏椭圆胶囊按钮等既有外观与对外接口保持不变；
- **正版登录由 v2 Azure-AD 设备码切换到 v1 Live-Connect 官方启动器设备码（1.2.2.2）**：1.2.2.1 真机点「正版」走完设备码申请后，浏览器在 `login.live.com/oauth20_remoteconnect.srf` 同意页报「该应用是第一方应用，用户无需同意，也不得同意第一方应用……invalid_request」（AADSTS65002）。离线诊断定位：原复用的 Prism v2 公开 GUID 只在 Azure 应用注册里配置了本地 loopback 授权码回调，并未开放设备码用户同意；设备码申请端点不做流类型校验所以先返回 200，到浏览器同意环节才被旧同意层判定为「第一方应用 × 第一方资源」而拒绝用户授权；其余 v2 公开 ID 在个人消费者账号下同样不可用（教育版仅限组织目录、Office365 版目录中不存在、LiquidLauncher 同为 loopback 应用）。本轮把认证链路整体切换到官方 Minecraft Launcher 的旧版 Live-Connect（v1）公开身份：客户端 ID `00000000402b5328`、设备码端点 `login.live.com/oauth20_connect.srf`、令牌端点 `login.live.com/oauth20_token.srf`、资源 scope `service::user.auth.xboxlive.com::MBI_SSL`，申请体带 `response_type=device_code`，轮询 `grant_type` 用短名 `device_code`；v1 拿到的是不透明 RPS 票据，换取 Xbox Live 时 `RpsTicket` 不再加 `d=` 前缀（v2 JWT 才需要）。后续 Xbox Live → XSTS → Minecraft 登录 → 档案链路报文保持不变；仍是设备码 + 后台轮询弹窗，不开本地端口、不做授权码 loopback 回调，不引入第三方认证库，令牌依旧只存进程内存、不落盘；个人页布局、3D 预览、皮肤下载与全部界面样式规则无改动；
- **修复正版登录 / 皮肤下载请求头中文编码崩溃（1.2.2.1）**：实机点「正版」申请设备码时弹窗报 `'latin-1' codec can't encode characters in position 0-4: ordinal not in range(256)`——认证链路与皮肤下载线程的 `User-Agent` 原先拼接中文应用名「云朵启动器」，而 HTTP 请求头只能按 latin-1（ASCII）编码，中文序号超出 256 直接抛 `UnicodeEncodeError`，在发出第一个请求前就失败。本轮新增纯 ASCII 网络标识常量 `APP_UA_NAME = "CloudLauncher"`，认证模块与皮肤下载线程的请求头统一改用该英文标识，中文显示名仅保留在窗口标题等界面层；除该运行时崩溃外，登录流程、界面布局、皮肤切换与其余对外接口均无改动；
- **接入微软正版设备码登录与本人皮肤 3D 预览（1.2.2.0）**：标题行「正版」按钮由置灰占位改为可用，点击后弹出设备码登录窗——主线程申请设备码、自动用系统浏览器打开微软消费者授权页、自动把 8 位设备码复制到剪贴板，独立 `QThread` 后台轮询授权；授权完成后纯标准库 `urllib` 依次完成 Xbox Live → XSTS → Minecraft 服务令牌交换并拉取玩家档案（昵称、无横杠 UUID、皮肤地址与 CLASSIC / SLIM 模型类型）。登录成功后昵称框锁定为微软昵称、显示格式化 UUID 与「退出登录」按钮，后台线程下载正版全身皮肤替换现有 GL 预览，SLIM 档案自动切换细臂网格；皮肤下载失败回退内置史蒂夫 / 艾利克斯。微软 / Minecraft 令牌、刷新令牌与档案只保存在进程内存，`config.json` 不写入任何凭据，程序下次启动默认离线。认证复用开源启动器公开的桌面公共客户端 ID（无客户端密钥），不要求用户自行在 Azure 注册应用；Xbox 未开通、未成年 / 成年验证、未购买 Java 版等错误统一翻译为中文提示。未引入任何第三方 HTTP 或认证库，离线随机角色、两列布局、3D 管线、自绘胶囊进度条与开始游戏椭圆胶囊按钮等既有外观与对外接口保持不变；
- **删除侧栏全部占位图标入口、仅保留个人页（1.2.1.14）**：按用户分步设计指令，左侧导航栏移除「个人页」以外的全部 8 个竖排占位小图标（实例列表、版本选择、编辑资料、修改皮肤、游戏目录、账号管理、云朵服务、更多选项）及其「后续版本开放」提示弹窗；侧栏仅保留品牌区（云朵 Logo + 名称 + 版本号）与「个人页」导航项。同步移除已无实例的 `QToolButton[navIcon="true"]` 样式规则、占位信号与未用 `QToolButton` / `QMessageBox` 导入；侧栏宽度、间距与个人页两列布局、3D 预览、胶囊进度条、开始游戏椭圆胶囊按钮、离线 / 正版分段按钮等其余外观与对外接口保持不变，未引入新依赖；后续导航布局由用户逐步口述补充；
- **按参考原型重构两列主体：左列昵称+统计上下叠、右列人物整列撑高、版本行独立通长（1.2.1.13）**：按用户提供的手绘参考原型重构个人页主体——主体改为**一条两列水平行**：**左列**上下叠放玩家名称卡（上）与游玩统计卡（下，三格仍为**纵向竖列**，自上而下 **总游戏时长 → 启动次数 → 最近游玩日期**）；**右列**“玩家人物”3D 预览卡整列撑高，与左列两行总高度顶部、底部对齐（左右拉伸比 6:4）。**游戏版本**置灰下拉占位行从统计卡内部移出，成为主体两列卡片下方一条**独立通长横条**，横跨整个内容区，全页仍**仅此一条**，人物卡与统计卡内部都不再重复版本入口；统计卡不再带“游玩统计”小标题，三行统计直接在卡内竖列铺开。玩家名称输入框字号 10px、高度 24px 维持不变；启动次数与最近游玩日期仍只在点击“开始游戏”、模拟加载到 100% 后才记录，打开启动器不计数、不写日期。开始游戏椭圆胶囊按钮、自绘胶囊加载进度条、3D 模型几何 / 相机距离 / 鼠标跟随 / 待机摆臂、离线 / 正版分段按钮、标题栏 Logo+名称+版本号与左侧导航栏保持不变，未引入新依赖；
- **上段名称 / 人物并排、下段统计竖排、单条游戏版本占位行（1.2.1.12）**：按旧版实拍对照与最新反馈返工个人页主体——**上段一条水平行**：左侧玩家名称窄卡、右侧“玩家人物”3D 预览卡左右并排、顶部与底部对齐（等高）；**下段一张通长“游玩统计”卡**，内部三格改为**纵向竖列**，自上而下依次为 **总游戏时长 → 启动次数 → 最近游玩日期**（不再左右横排）；全页**仅统计卡最底部保留一条**「游戏版本」置灰下拉占位行，玩家人物卡底部不再重复第二条版本入口，避免出现两个版本选择。玩家名称输入框字号由 11px 再缩到 10px、高度由 26px 降到 24px，能看清昵称即可；占位行标签由“版本选择”更名为 **游戏版本**（仍为置灰下拉，显示“未选择版本”，仅作入口占位，真实版本列表后续接入，本轮不做版本拉取）。为让上段两卡与下段统计卡在 980×660 窗口内一屏放下、不再出现纵向滚动条，上排卡片最小高度与统计卡行距同步收紧，3D 预览最小高度随卡片高度下调；启动次数与最近游玩日期仍只在点击“开始游戏”、模拟加载到 100% 后才记录，打开启动器不计数、不写日期。开始游戏椭圆胶囊按钮、自绘胶囊加载进度条、3D 模型几何 / 相机距离 / 鼠标跟随 / 待机摆臂、离线 / 正版分段按钮与对外接口签名保持不变，未引入新依赖；
- **昵称独立窄卡、统计拆出放大、版本选择占位行、记录时机改为启动游戏（1.2.1.11）**：按实机反馈继续调整个人页——玩家名称从统计卡片中拆出，单独成一张顶部通长窄卡片，输入框字号再缩到 11px、高度 26px，能看清昵称即可；三格游玩统计 **总游戏时长 / 启动次数 / 最近游玩日期** 拆出独立做成一张放大的“游玩统计”卡片，数值字号整体放大（数值 22px、日期 15px、标签 13px），与右侧“玩家人物”3D 预览卡片左右并排（拉伸比 3:4，两卡片等高 300px，窗口仍为 980×660）；统计卡片底部、玩家人物卡片底部各加一条 **版本选择** 占位行（标签 + 置灰下拉框，显示“未选择版本”，仅作入口占位，真实版本列表后续接入，本轮不做版本拉取）。记录时机修正：启动次数与最近游玩日期不再在打开启动器、进入个人页 `refresh()` 时累计 / 写入，改为点击“开始游戏”、模拟加载到 100%（本次启动游戏事件）后才启动次数 +1、写入当天 `YYYY-MM-DD` 日期并持久化；游戏总时长同样只在游戏运行会话内累计，打开启动器不计时，真实 Minecraft 进程接入后按会话结算时长。开始游戏椭圆胶囊按钮、自绘胶囊加载进度条、3D 模型几何 / 相机 / 鼠标跟随 / 待机摆臂、离线 / 正版分段按钮与对外接口签名保持不变，未引入新依赖；
- **个人页布局重构：昵称缩小、三格统计与角色预览并排、删除版本号卡片（1.2.1.10）**：按参考卡重构个人页上半区——左侧卡片内上下两行，上行是缩小后的玩家名称（标签固定宽、输入框 12px / 30px 高），下行是三格游玩统计 **总游戏时长 / 启动次数 / 最近游玩日期**，每格为上方大数值、下方小标签；整张左侧卡片再与右侧“玩家人物”3D 预览卡片左右并排（拉伸比 3:4，两卡片等高 300px）。统计区 **不设置游戏版本选择项**；启动次数在每次打开启动器（页面 `refresh()`）时累计 +1，最近游玩记录当天 `YYYY-MM-DD` 日期，均写入本地 `config.json`；原先底部独立通长的“当前版本：云朵启动器 vX”版本号卡片整体删除。开始游戏椭圆胶囊按钮、自绘胶囊加载进度条、3D 模型几何 / 相机 / 鼠标跟随 / 待机摆臂、离线 / 正版分段按钮与对外接口签名保持不变，未引入新依赖；
- **加载进度条改为自绘胶囊、填充端头圆角生效（1.2.1.9）**：实机反馈问题不在开始游戏按钮，而在底部加载进度条——进度进行到一半时填充右端是垂直方头，填满 100% 时整条被矩形填充盖住轨道圆角、两端露直角，观感仍是长条矩形。先用真实窗口 A/B 对照探针验证：Qt 原生 `QProgressBar::chunk` 在样式表下只画矩形填充段，`border-radius` 对填充端头不生效，去掉 `margin`、去掉边框、加大圆角四种写法均为方头，纯 QSS 无法修复。本轮新增自绘 `CapsuleProgressBar`（继承 `QProgressBar`，`setRange / setValue / setFormat / text()` 等对外接口保持不变），在 `paintEvent` 里用 `QPainterPath` 圆角矩形分别绘制轨道与填充，半径严格取内容高度一半，任意进度比例与填满状态下两端都是正半圆胶囊；配色沿用既有通透玻璃数值，不凸出、不改布局、不引入新依赖，四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变；
- **修复主按钮圆角 / 渐变未生效（1.2.1.8）**：1.2.1.6、1.2.1.7 反复调整按钮高度、宽度与 `border-radius`，实机反馈“还是一样的”、两端仍只是小圆角矩形。本轮先排除旧包 / 残留进程误匹配（本地与 D 盘三份 exe 哈希一致），再用真实窗口 A/B 对照探针定位根因：根窗口、左侧导航栏、通用卡片原先在各自本地 `setStyleSheet` 上写样式；Qt 中祖先一旦调用本地样式表，其子树后代解析样式时就被替换为这份本地表，`QApplication` 全局样式表里针对后代控件的属性选择器规则（`QPushButton[primaryButton="true"]` 等）不再参与匹配——所以主按钮的玻璃蓝三段渐变与 22px 半圆圆角根本没作用到按钮上，控件回退成系统默认矩形，只靠默认小圆角，平直长边占据主体。修复方式：把 `#root`、`#sidebar`、`#card` 三处容器样式全部迁入 `global_stylesheet()` 全局表（用 objectName 限定选择器，互不影响），容器本身不再调用本地 `setStyleSheet`，后代按钮 / 输入框 / 进度条的全局属性选择器规则恢复正常匹配；主按钮仍为固定 44px 高、146px 宽、水平 Fixed 不拉伸、`border-radius` 取半高 22px，真实窗口帧复核两端呈正半圆的饱满椭圆胶囊，玻璃蓝通透渐变与同系浅蓝细边保持不变、不退回闷实蓝块；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **主按钮收窄为饱满椭圆胶囊、消除长条矩形观感（1.2.1.7）**：实机再次反馈“两边都换成椭圆形，别换成长方形 / 正方形”。先核对源码与真实窗口几何：1.2.1.6 两端半圆几何其实已生效，但按钮在水平布局里仍带 stretch 拉伸、宽度被拉到约 160px（宽高比 3.8 以上），平直长边占据主体，两端半圆在实拍里不显眼，整体被看成长条矩形。本轮把按钮改为固定 44px 高、146px 宽、水平策略 Fixed 不再参与拉伸，`border-radius` 取半高 22px，宽高比约 3.3，左右两端呈正半圆的饱满椭圆胶囊；填充沿用 1.2.1.5 起已达标的玻璃蓝 + 顶部白光三段通透渐变与同系浅蓝细边，明度差维持“可辨但不浮凸”，不退回闷实中蓝块；选中态、进度条、输入框沿用既有达标数值不回退；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **主按钮恢复胶囊（椭圆）形体、保持不浮凸（1.2.1.6）**：实机特写反馈“怎么变平了呀，不是椭圆形吗”——1.2.1.5 为消除浮凸把填充差与亮白边框一起压得过低，真实窗口帧测量显示按钮只剩 26px 高、12px 小圆角的矩形，两端不成半圆，椭圆/胶囊形体在面板上读不出来。本轮固定按钮高度 42px、`border-radius` 取半高 21px，让左右两端呈正半圆的胶囊形体；填充保留 1.2.1.5 已达标的玻璃蓝 + 顶部白光三段通透渐变，与面板明度差维持在“可辨但不浮凸”的区间，不退回闷实中蓝；边框由亮白弱光换成与填充同色系、略深一档的浅蓝细边，只勾勒胶囊轮廓、不打浮起高光；选中态、进度条、输入框沿用 1.2.1.5 已达标数值不回退；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **主按钮玻璃白光化、描边整体弱化（1.2.1.5）**：实机再次反馈“新版本还是一样的”，本轮不再只调透明度，而是在真实窗口里对每个可见控件做几何定位与横 / 纵像素明度剖面——定位到真正凸出源是右下角开始游戏主按钮（内部比面板背景暗 31 个明度阶，闷实中蓝填充），进度条长条与昵称输入框是靠一圈高亮白边框勾出矩形轮廓，导航 / 离线选中块仍留 1px 有色硬边；据此把主按钮改为玻璃蓝 + 顶部白光高光的三段通透渐变（顶部白色反光、中部玻璃蓝、底部略深，弱白光细边、白字保留），选中态填充再贴近面板、边框近乎透明、只靠中蓝加粗文字区分，进度条边框由高亮白改为同系浅蓝弱边、轨道更通透，输入框描边压成弱光；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **选中态进一步融入面板（1.2.1.4）**：按实机特写反馈，左侧导航“个人页”选中长条与右上角“离线”选中块仍肉眼可见“凸出一点点”、边界没和面板融为一体——真实窗口像素采样定位到选中态与背景明度差仍有 39~43、四周亮白描边勾出浮起轮廓；本轮把导航选中与离线选中进一步降到极低不透明淡蓝玻璃（明度差压到 16~18），亮白描边改为几乎不可见的同系浅蓝弱边，保留中蓝加粗文字维持选中辨识；开始游戏主按钮同步弱化亮白边框与不透明度，仍是全窗唯一较深的主操作层级；进度条 0% / 50% / 100% 三帧复核保持通透；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **蓝色控件通透化（1.2.1.3）**：针对实机上导航选中、离线选中与开始游戏主按钮像实色蓝块“凸”在玻璃面板上的反馈返工——选中态降为低不透明淡蓝玻璃、文字改为深玻璃蓝以保证对比；主按钮单独保留一组略深但仍通透的玻璃蓝，不再是饱和实色块；进度条填充进一步贴近轨道颜色、轨道描边弱化，满格也不形成明显蓝带；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **进度条与人物预览区通透化（1.2.1.2）**：按“全部要通透”的观感返工——进度条初始等待轨道改为更通透的凹槽玻璃，加载中与“准备完成”的填充段降为低不透明玻璃蓝，满格也不再压成实色贴图；人物预览不再是一块比卡片更白的独立白板：GL 控件包进一层半透明玻璃小窗并留出边距，GL 清除色取与小窗同系浅蓝（Windows / Qt 下 QOpenGLWidget 无法真透明合成，开启透明会呈黑底，故以同色融合替代 RGBA 透明）；四张卡片布局、3D 模型几何、相机、跟随、待机摆臂与对外接口保持不变，未引入新依赖；
- **通透玻璃质感细化重做（1.2.1.1）**：按苹果风通透毛玻璃重做全局主题——背景改为更浅柔的蓝白渐变，侧栏、卡片改为三段白色高光玻璃（上缘反光、中部半透、底部更透）；输入框、进度条轨道、未选模式按钮统一为通透白玻璃；开始游戏主按钮、离线选中态、导航选中态改为半透明玻璃蓝渐变 + 亮白描边，进度条填充为半透明玻璃蓝；提高蓝色玻璃在浅背景上的不透明度以保证识别度；卡片布局、3D 预览、随机离线角色、待机摆臂、指针跟随与对外接口保持不变，未引入新依赖；
- **通透磨砂玻璃与离线 / 正版模式按钮（1.2.1.0）**：界面改为苹果风通透磨砂质感，侧栏与卡片为半透明白色高光叠加、细亮边框、大圆角，输入框与进度条同步通透；窗口背景仍是不透明蓝色渐变，不调用系统模糊、不真透视桌面；标题行右侧原“随机生成”标签替换为并排的「离线 / 正版」分段按钮，离线选中可用、正版置灰占位；个人页原有卡片布局、3D 预览、随机离线角色、待机摆臂、指针跟随与对外接口保持不变，未引入新依赖；
- **贴图最近邻采样**：关闭平滑像素插值，皮肤切片放大后保持 MC 方块像素的锐利硬边；
- 默认正面正对镜头，指针跟随与拖拽只在零偏移之上叠加转向；
- 参考 Minecraft 按 E 键背包预览：指针在整个窗口任意位置移动，身体小幅同步偏转、头部领先扭向指针，指针在右朝右、在左朝左、上移抬头、下移低头，斜向指针两个方向同时跟随；指针以 16ms 频率采样、指数平滑收敛，跟随顺滑不卡顿；贴图随头部一起转动，不拉伸变形；
- 部件外形轮廓保持原版标准尺寸与位置，肩、髋分界清晰；仅在被遮挡的接触面内部保留极小的
  防穿透重叠，配合深度缓冲避免转动、俯仰时漏出背景缝隙；
- 游玩统计为左列下方统计卡内三格纵向竖列：总游戏时长按小时计时法显示（“X 小时”）在上、累计启动次数居中、最近游玩日期（`YYYY-MM-DD`，无记录显示“—”）在下；启动次数与最近游玩日期在真正启动游戏后才记录，打开启动器不计数；全页仅主体两列卡片下方保留一条通长游戏版本占位行，统计卡与玩家人物卡内部都不重复设置版本入口；
- 游戏加载进度条 + 开始游戏按钮（本版本为模拟加载动画，游戏启动逻辑后续版本接入）。

> 正版登录的**刷新令牌与公开身份**保存在 exe 同级 `yd/account.json`，下次启动由后台线程
> 静默续期自动恢复正版；短期访问令牌只存进程内存、不落盘；点「离线」或「退出登录」即删除
> 账号文件。主 `config.json` 只保存离线昵称、统计与窗口位置，不混入任何账号字段。三维渲染器
> 只消费一张皮肤图与手臂模型类型，离线内置皮肤与正版皮肤共用同一套纹理、网格与投影逻辑。
> 本版本仅使用 PySide6 自带的 `QtOpenGL / QtOpenGLWidgets` 与 Python 标准库，未引入 Qt3D、
> QtWebEngine、HTTP 或第三方认证 / 加密库。

## 目录结构

```
云朵启动器-v1.3.1.8/
├── main.py                     # 程序入口
├── requirements.txt            # 运行时依赖
├── build.spec                  # PyInstaller 打包配置
├── build.bat                   # 一键打包脚本
├── README.md
├── 说明文档.md
├── tools/
│   ├── make_assets.py           # 由参考图生成 Logo 与应用图标
│   ├── fetch_vanilla_skins.py   # 从官方客户端 jar 提取 Steve / Alex 原版皮肤
│   ├── fetch_block_icons.py      # 下载下载页四张方块 3D 渲染图（仅构建期运行）
│   ├── smoke_test.py            # 离线冒烟测试（昵称、随机角色、加载进度）
│   ├── capture_live.py         # 真实窗口置顶并屏幕截图目检
│   ├── preview_check.py         # 启动主窗口 grab() 截图
│   ├── angle_test.py            # 强制偏转 yaw / pitch 验证三维各面渲染
│   ├── anim_test.py             # 遍历待机相位抓连续帧，核对双臂张合动画
│   └── default_view_test.py     # 默认正面视角与指针偏移叠加取证
└── cloud_launcher/
    ├── __init__.py
    ├── constants.py             # 名称、版本号、尺寸、配色、角色、壁纸与微软认证端点常量
    ├── resources.py             # 源码 / 打包双模式资源路径解析
    ├── wallpaper.py             # 外部壁纸目录发现、安全加载与平均亮度采样（缺失 / 损坏静默回退）
    ├── config_store.py          # 本地离线配置读写（config.json，不混入正版账号字段与壁纸字段）
    ├── account_store.py         # 正版刷新令牌与公开身份持久化（yd/account.json，独立于离线配置）
    ├── microsoft_auth.py        # 微软设备码 → Xbox Live → XSTS → Minecraft 档案认证（纯标准库）
    ├── account_session.py        # 当前账号内存会话（离线 / 正版互斥；短期令牌不落盘）
    ├── version_meta.py           # 官方版本清单只读拉取 / 全量分类 / yd 本地缓存读写（纯标准库）
    ├── game_dirs.py              # 便携 .minecraft 目录、别名隔离、安装元数据与本地已安装条目扫描
    ├── download_engine.py        # 分块并发下载引擎、进度统计、镜像兜底、Maven 路径 / natives 解压辅助（纯标准库）
    ├── version_profile.py        # 原版 / 加载器 profile 继承链合并、库 / natives / 资源 / client.jar 任务收集
    ├── loaders.py                # Forge / NeoForge / Fabric / OptiFine 支持性探测、yd 缓存与安装 profile 构建
    ├── java_runtime.py           # 本机 Java 三级探测、JVM 命令组装与游戏进程拉起（纯标准库 + winreg）
    ├── content_search.py         # Modrinth 内容搜索、图标下载、yd/content_search 本地缓存（纯标准库）
    ├── content_install.py        # 内容真实下载：版本解析 / 加载器与扩展名筛选 / 流式下载 / 原子落盘 / 撞名抛异常
    ├── resources/
    │   ├── cloud_logo.png       # 云朵 Logo
    │   ├── app_icon.ico          # 应用图标
    │   ├── icons/                # 五导航透明 PNG 图标（启动 / 下载 / 设置 / 打包 / 关于）
    │   ├── blocks/              # 下载页四张方块 3D 等距透明渲染图
    │   └── skins/
    │       ├── steve.png        # 史蒂夫官方原版皮肤（64×64）
    │       └── alex.png          # 艾利克斯官方原版皮肤（64×64）
    └── ui/
        ├── theme.py              # 全局 QSS 样式表（含正版登录弹窗与 UUID / 退出按钮规则）
        ├── background_layer.py   # 最底层背景层：默认渐变回退 / 清晰壁纸 cover 铺满（不做全屏模糊）
        ├── frosted_backdrop.py   # 共享清晰壁纸缓存 + 卡片 / 侧栏片内局部磨砂自绘工具
        ├── main_window.py        # 主窗口与标题栏（全局指针轮询跟随、创建会话 / 账号文件、启动静默恢复线程）
        ├── nav_sidebar.py        # 左侧五导航栏（片内局部磨砂自绘，选中项隐藏图标只留文字）
        ├── download_page.py      # 下载页（列表态 ↔ 详情态双层栈、分组条目、已安装标识、面板与 worker 接线）
        ├── version_detail_view.py  # 版本详情页（返回箭头 + 别名输入框 + 五加载器卡片 + 开始下载胶囊）
        ├── loader_probe_worker.py  # 四加载器支持性后台扫描线程（读 yd 缓存，缺键才联网探测）
        ├── download_panel.py     # 单例下载状态浮层（顶部居中展开 / 右下收起、五步清单、底部大叉取消、5 秒自动收起）
        ├── download_worker.py    # 版本下载后台线程（五步全真实编排、进度 / 步骤 / 成功 / 失败 / 取消信号）
        ├── content_search_view.py  # 五类内容搜索视图（搜索行 + 两列带图卡片 + 下载入口 + 版本选择浮层）
        ├── content_search_worker.py  # 内容搜索后台线程（搜索与图标下载，中断可取消）
        ├── content_install_worker.py  # 内容下载后台线程（解析 / 进度 / 成功 / 失败 / 撞名信号）
        ├── version_meta_worker.py  # 清单全量加载线程 + 后台最新版号检查线程（中断可取消、失败静默）
        ├── placeholder_page.py   # 设置 / 打包 / 关于通用空白占位骨架页
        ├── launch_settings_page.py  # 设置页「启动」标签：账号管理 / 版本隔离 / 高级功能（Java、参数、内存、开关）
        ├── profile_page.py       # 启动导航个人页（离线 / 正版切换、昵称锁定、UUID、本人皮肤替换、统计竖列、两行滚轮已安装版本列表、加载条）
        ├── capsule_progress_bar.py  # 自绘胶囊加载进度条（轨道 / 填充圆角路径，原生 chunk 不画端头圆角）
        ├── card_widget.py        # 通用局部磨砂圆角卡片（片内局部模糊 + 三段白玻璃高光自绘）
        ├── spring_button.py      # 橡皮筋拉扯 + 松开弹簧回弹控制器与 SpringPushButton 基类
        ├── ms_login_dialog.py   # 微软正版设备码登录弹窗（后台轮询线程、自动开浏览器 / 复制设备码）
        ├── account_restore_worker.py  # 启动静默恢复线程（本地刷新令牌后台续期，成功回传档案 / 失败回退离线）
        ├── skin_fetch_worker.py  # 正版皮肤纹理后台下载线程
        ├── skin_preview.py       # 角色 GPU 真三维预览组件（QOpenGLWidget + 着色器，支持外部皮肤与细臂模型）
        ├── skin_preview_software_archive.py  # 1.1.2.1 纯软件渲染版回退留档，不被引用、不参与打包
        └── skin_preview_gl_archive.py  # 早期 OpenGL 方案留档，不被引用、不参与打包
```

> 壁纸目录 `CLY/wallpaper/`（v1.3.10.0 起位于数据目录 CLY 内）**不参与 PyInstaller 打包、
> 也不进入源码压缩包**；发布后用户把 `wallpaper.png / .jpg / .jpeg / .webp / .bmp` 放进该目录即可换图，
> 删除或损坏时程序自动回退默认蓝白渐变背景。


## 源码运行

```bat
pip install -r requirements.txt
python main.py
```

## 打包 exe

```bat
build.bat
```

等价命令：

```bat
pyinstaller --noconfirm --clean build.spec
```

产物位于 `dist\云朵启动器.exe`。v1.3.10.1 起数据分两处存放：**游戏目录 `.minecraft/` 保留在 exe 同级**（`<exe 目录>/.minecraft`，含版本、资源、存档）；其余运行期数据在 exe 同级的 **CLY** 数据目录下平铺生成：`config.json`、`account.json`、`version_manifest_cache.json`、`loader_support_cache.json`、`music/`、`wallpaper/`、`content_search/` 与自定义 logo（`.minecraft` 与 CLY 均不打进 exe，缺失时自动创建）。

## 打包产物部署约定

- 当前运行版：`D:\云朵启动器\exe\云朵启动器.exe`
- 历史版本 exe：`D:\云朵启动器\exe\云朵启动器-vX.X.X.X.exe`
- 历史版本源码包：`D:\云朵启动器\压缩包\云朵启动器-vX.X.X.X.zip`
- 所有历史版本 exe 与 zip 均保留，不删除。
