# 第三方版权与署名声明（NOTICE）

本项目 **Cloudy Launcher（云朵启动器 / CLY）** 自身的全部源代码以 **GNU 通用公共许可证第 3 版（GPL v3）** 发布，完整许可证文本见根目录 `LICENSE`。本项目没有把任何第三方的源代码复制进工程；以下列出的是运行时/构建期依赖，以及随程序分发的第三方素材。依据各许可证要求，在此如实署名。

## 一、运行时依赖（不随源码包分发，由用户自行安装）

| 组件 | 版本 | 许可证 | 版权方 / 来源 |
| --- | --- | --- | --- |
| Python | 3.13 | PSF License（Python Software Foundation License，宽松许可） | Python Software Foundation，https://www.python.org |
| PySide6（Qt for Python） | 6.12 | GNU LGPL v3（同时提供 GPL v3 与商业许可选项） | The Qt Company，https://www.qt.io |
| Qt 框架（随 PySide6 提供） | 6.x | GNU LGPL v3 | The Qt Company |

说明：PySide6/Qt 采用 LGPL v3，本程序以动态链接方式使用它，不包含其源代码；用户可自行替换该库的版本。LGPL 完整文本见 https://www.gnu.org/licenses/lgpl-3.0.html。

本程序只使用 Qt 中以 LGPL v3 授权发布的核心模块（Qt Core / Gui / Widgets / Network / Svg / OpenGL / OpenGLWidgets / Multimedia / MultimediaWidgets）。Qt 6.12 中仅以 GPL v3 或商业许可发布的附加模块（Qt Charts、Qt Graphs、Qt MQTT、Qt Quick 3D、Qt Virtual Keyboard、Qt HTTP Server、Qt GRPC 等）本程序均未使用；其中 Qt Virtual Keyboard 会被 PySide6 的打包钩子无条件收集，本项目已在 `build.spec` 的打包阶段将其及其 `platforminputcontexts` 插件剔除。对 v1.3.17.0 成品的最终 PKG / PYZ / EXE 归档清单扫描结果为 0 个 GPL-only 模块，Qt Virtual Keyboard 及其插件均未进入发布的可执行文件。

## 二、构建与开发工具（仅 `tools/` 内使用，不随程序/源码包分发）

| 组件 | 版本 | 许可证 | 版权方 / 来源 |
| --- | --- | --- | --- |
| PyInstaller | 6.22 | GPL v2 或更高版本，附特殊例外条款 | PyInstaller Development Team，https://pyinstaller.org |
| Pillow（PIL） | 13.0 | HPND（历史 MIT/X 风格宽松许可） | 各贡献者，https://python-pillow.org |

## 三、随程序分发的素材

### （一）云朵启动器（`cloud_launcher/resources/`）

1. **方块等距渲染图 13 张（`resources/blocks/*.png`）**：由公开渲染服务 **blockrender.dev** 生成（https://blockrender.dev）。这些渲染图基于 **Minecraft（我的世界）** 游戏内模型与纹理制作，底层纹理版权归 **Mojang Synergies AB / Microsoft** 所有。依据 blockrender.dev 的说明，该类渲染图可用于粉丝站点、插件页面等非官方用途，但不得冒充官方 Minecraft 产品。
2. **原版角色皮肤 Steve / Alex（`resources/skins/steve.png`、`alex.png`）**：从 Mojang 官方分发的 Minecraft 1.12.2 客户端 jar 中提取的游戏内置纹理，版权归 **Mojang Synergies AB / Microsoft** 所有。
3. **品牌 Logo 与应用图标（`resources/cloud_logo.png`、`resources/app_icon.ico`）**：由作者本人提供的参考图处理生成，版权归本项目作者所有。
4. **左侧导航图标 5 张（`resources/icons/*.png`）**：由作者使用 AI 工具生成的图片处理而成，不涉及第三方图标库素材；其使用以对应 AI 工具的生成内容服务条款为准。

### （二）云朵桌宠（`desktop_pet/resources/`）

下列素材随独立桌宠程序分发。除应用图标外，均为从 Minecraft 客户端提取的游戏内置纹理，版权归 **Mojang Synergies AB / Microsoft** 所有，仅用于非商业的爱好者用途，不冒充官方 Minecraft 产品：

1. **原版角色皮肤（`resources/steve.png`）**：Minecraft 游戏内置 Steve 皮肤纹理。
2. **物品纹理 5 张（`resources/items/`）**：`bone.png`（骨头）、`raw_beef.png`（生牛肉）、`cooked_beef.png`（熟牛肉）、`raw_porkchop.png`（生猪排）、`cooked_porkchop.png`（熟猪排），均为 Minecraft 游戏内置物品纹理。
3. **狼（驯服狗）实体纹理 3 张（`resources/entity/wolf/`）**：`wolf.png`、`wolf_tame.png`、`wolf_collar.png`，均为 Minecraft 游戏内置实体纹理。
4. **应用图标（`resources/app_icon.ico`）**：与启动器同源，由作者本人提供，版权归本项目作者所有。

## 四、商标与免责声明

- **Minecraft** 名称、游戏内方块与角色纹理是 **Mojang Synergies AB / Microsoft** 的商标与版权资产。本项目是第三方独立制作的爱好者启动器，**与 Mojang、Microsoft 无隶属、赞助或认可关系**。
- 本程序通过网络调用的公开服务（按出现顺序）：Modrinth（内容搜索与下载 API）、BMCLAPI（国内镜像）、Mojang piston / 微软认证服务、Fabric Meta、MinecraftForge / NeoForge Maven、OptiFine、阿里云 / 华为云 Maven、blockrender.dev 等。这些服务仅作为数据接口被调用，其代码与内容不在本项目内分发，版权归各自所有方。
- 若任何权利人认为上述素材的使用存在异议，请联系作者，作者会在核实后移除或替换相关内容。

## 五、致谢

本项目在开发过程中受益于以下开源项目与公开服务，作者在此一并表示感谢（致谢不代表各方对本项目存在赞助或认可关系）：

- **DeepSeek**：以 MIT 协议开源 DeepSeek-R1、DeepSeek-V3 等模型与代码，为开发者提供了可自由使用、商用与蒸馏的大模型；
- **The Qt Company 与 PySide6 / Qt 开源社区**：提供 LGPL 许可的跨平台 GUI 框架；
- **Python Software Foundation 与 Python 社区**：提供 PSF 许可的编程语言与丰富的标准库；
- **Modrinth 团队**：提供开放的 Minecraft 内容搜索与下载 API；
- **BMCLAPI（bangbang93）**：提供国内可用的 Minecraft 下载镜像服务；
- **blockrender.dev**：提供基于游戏模型的方块等距渲染服务；
- **Fabric、MinecraftForge、NeoForge、OptiFine 等加载器生态的开发者**：以及所有为 Minecraft 开源生态作出贡献的人。

## 六、作者信息

- 项目名称：Cloudy Launcher（云朵启动器 / CLY）；配套独立桌宠 Cloudy Pet（云朵桌宠）
- 版权人 / 作者：小鱼（Copyright (C) 2026 小鱼）
- 许可证：GPL v3（本声明与 `LICENSE` 冲突时，以各第三方原始许可证为准）
- 每个源文件顶部均带 SPDX 版权与许可声明（`SPDX-License-Identifier: GPL-3.0-or-later`），许可范围为 GPL v3 或其后续版本。
