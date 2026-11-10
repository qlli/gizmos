# GitHub 知名开源工程

> 星标数为 2026-11 检索时的观测值，仅供量级参考，实际请以仓库页面为准。

## 1. 语言本体与镜像

| 仓库 | 说明 | 备注 |
| --- | --- | --- |
| https://github.com/anjo76/angelscript | **官方仓库**（2025-08 从 SourceForge 迁入，含完整历史） | 3,100+ commits；CI 覆盖多平台多编译器 |
| https://github.com/codecat/angelscript-mirror | 社区 Git 镜像 | 迁移前的主要 Git 入口 |
| https://svn.code.sf.net/p/angelscript/code/trunk | 历史 SVN（SourceForge） | 已停止作为主仓库 |

## 2. 引擎 / 框架（用 AS 作为脚本层）

| 仓库 | 说明 | 星标（观测） |
| --- | --- | --- |
| https://github.com/Hazelight/UnrealEngine-Angelscript | **Hazelight 的 UE 引擎 fork + AngelScript 插件**，《双人成行》《Split Fiction》的基础 | 数千级，AS 生态最大工程 |
| https://github.com/urho3d/urho3d | 跨平台 2D/3D 游戏引擎，**AS 是一等公民脚本语言**（另有 Lua） | 最经典的"如何把 AS 嵌进引擎"参考实现 |
| https://github.com/thunder-engine/thunder | 模块化跨平台 2D/3D 引擎，支持裁剪模块 | ★ ~655 |
| https://github.com/ezEngine/ezEngine | ezEngine，官方用户列表收录 | — |
| https://github.com/Warsow/qfusion （及 TeamForbiddenLLC/warfork-qfusion） | qfusion 引擎（Warsow / Warfork） | — |
| https://github.com/samtupy/nvgt | **NVGT（NonVisual Gaming Toolkit）**：用 AS 写音频游戏的跨平台引擎，活跃开发中 | 2026 年仍高频提交 |
| https://github.com/Cattle-Engine/Runtime | Cattle Engine | — |
| https://github.com/mutgos/mutgos_server | MUD/文字冒险服务器 | — |
| Openplanet（官网 https://openplanet.dev/） | Trackmania 系列的 mod 平台，脚本语言即 AS；插件源码多分布在 GitHub 个人仓库 | — |
| https://github.com/zieiony/ghurund | DirectX 12 引擎 + 编辑器 | — |

## 3. 游戏（开源）

| 仓库 | 说明 | 星标（观测） |
| --- | --- | --- |
| https://github.com/RigsOfRods/rigs-of-rods | 软体车辆物理沙盒 | ★ ~1.2k |
| https://github.com/Beyond-All-Reason | Beyond All Reason（RTS） | — |
| https://github.com/yvt/openspades | OpenSpades | — |
| https://github.com/svkaiser/PowerslaveEX | Powerslave EX | — |
| https://github.com/skeletonxf/star-ruler-2-mod-ce | Star Ruler 2 的 Colonisation Expansion mod | — |
| https://github.com/BlindMindStudios/StarRuler2-Source | Star Ruler 2 开源发行版（AS 重度使用） | ★ ~1.5k |

## 4. 创意编程 / 应用框架

| 仓库 | 说明 | 星标（观测） |
| --- | --- | --- |
| https://github.com/Siv3D/OpenSiv3D | C++20 创意编程框架，脚本层用 AS | ★ ~1.2k |
| https://github.com/Wing-summer/WingHexExplorer2 | 跨平台十六进制编辑器，用 AS 做扩展脚本 | — |
| https://github.com/MayaPosch/NymphCast | 媒体投射 | — |
| https://github.com/xfcanyue/DuiLib_DuiEditor | DuiLib 界面编辑器 | — |

## 5. 绑定 / 集成工具（宿主侧）

| 仓库 | 说明 | 备注 |
| --- | --- | --- |
| https://github.com/HenryAWE/asbind20 | **C++20 绑定库，pybind11 风格**，模板自动生成构造/析构/运算符/属性注册 | 有 README.zh-CN.md；文档 https://asbind20.readthedocs.io/；CI 覆盖 MSVC/GCC/Clang/macOS/Emscripten；已进 xmake-repo |
| https://github.com/marcakafoddex/angelscript-docgen | 从注册处生成脚本 API 文档 | 官方 resources 推荐 |
| https://github.com/only-a-ptr/RefCountingObject-AngelScript | C++/AS 互通的智能指针 | — |
| https://github.com/Sami-Vuorela/aatc | AATC：vector/list/set/map 等 STL 风格模板容器 add-on | — |
| https://github.com/oktonion/astd | C++ 标准库的 AS 移植 | — |
| https://github.com/romanpunia/aspromise | Promise / async-await | — |
| https://github.com/romanpunia/asx | Node.js & NPM 风格的 AS 运行时环境（addon/stdlib/vm/preprocessor/debugger） | — |
| https://github.com/Sebight/as-reflect | 运行时反射（reflect 命名空间） | — |
| https://github.com/bluecataudio/angelscript-addons | ScriptXML（tinyxml2） | — |
| https://github.com/hanan619/angelscript-addons | ScriptJson（nlohmann::json） | — |
| https://github.com/SpehleonLP/Zodiac | 变参 print 示例 | — |
| https://angelcode.com/angelscript/extras/angelscript_clib_2.36.1.zip | 官方 C 接口（给 C/Delphi/Pascal 用） | 最后更新 2.36.1 |

## 6. JIT 编译器

| 仓库 | 说明 | 星标（观测） |
| --- | --- | --- |
| https://github.com/BlindMindStudios/AngelScript-JIT-Compiler | 经典 JIT，x86/x64，Windows(MSVC)/Linux(GCC) | ★ ~248 |
| https://github.com/bluecataudio/AngelScript-JIT-Compiler | BlueCat fork，含原版未合并的修复 | 官方推荐优先看这个 |
| https://github.com/asumagic/angelsea | angelsea，另一个 JIT 实现（较新） | — |

## 7. 调试器

| 仓库 | 说明 |
| --- | --- |
| https://github.com/codecat/asdbg | 远程调试器，GUI 为 C#，易集成 |
| https://github.com/lizuan1992/AngelScript-DebugServer + https://github.com/lizuan1992/RemoteDebuggerVSX | 在 Visual Studio 里调试 AS 脚本（调试服务器 + VS 插件） |
| https://github.com/paril/angelscript-debugger | 支持 Debug Adapter Protocol (DAP) 的集成调试器 |
| SDK 内置 | `/sdk/add_on/debugger`（2.21.0 起） |

## 8. 编辑器 / IDE / 语言服务

| 仓库 | 说明 |
| --- | --- |
| https://github.com/sashi0034/angel-lsp | **通用 AngelScript Language Server（VSCode 扩展）**：语法高亮、补全、类型检查、跳转定义、查找引用、重命名、代码片段、格式化、调试器；靠项目根目录的 `as.predefined` 描述宿主 API。也发布到 Open VSX。Marketplace: `sashi0034.angel-lsp` |
| https://github.com/sashi0034/angel-intellij | 同作者的 IntelliJ 版（JetBrains 插件市场） |
| https://github.com/hmatt1/angelscript-intellij | Matt Hornung 的 IntelliJ 插件（官方 resources 收录） |
| https://github.com/wronex/sublime-angelscript | Sublime Text 语法高亮 |
| https://github.com/Hazelight/vscode-unreal-angelscript | Hazelight 官方的 **UE-Angelscript VSCode 扩展**（补全/调试/格式化） |
| https://github.com/kunitoki/angeljuice | AngelJuice IDE（内含 2005 年的 AS 预处理器） |
| https://github.com/codecat/ccpp | 通用预处理器 |
| https://github.com/rotators/angelscript-preprocessor | AS 预处理器（rotators 组织） |
| `as.predefined` 示例 | OpenSiv3D (v0.6) 版、Sven Co-op 版（@DrAbcOfficial）、TMInterface 版（@Tulis12）—— 见 angel-lsp README |

## 9. UE 生态专项（对 UE 开发者最有价值）

| 仓库 | 说明 |
| --- | --- |
| https://github.com/Hazelight/UnrealEngine-Angelscript | **主仓库**（引擎 fork 形态） |
| https://github.com/Hazelight/Docs-UnrealEngine-Angelscript | 文档站 Markdown 源（文档站：https://angelscript.hazelight.se/） |
| https://github.com/Hazelight/vscode-unreal-angelscript | VSCode 扩展 |
| https://github.com/Hazelight/EmmsUI | 真实项目级 AS 插件（immediate-mode UMG） |
| https://github.com/ueworks/UE-Angelscript | 把 Hazelight fork 重构成**单个插件**、适配原版 UE（基于 5.4.2）——想避免编译引擎源码的折中方案 |
| https://github.com/vahabahmadvand/angelscriptsessions | UE AS 5.4+ 的多人会话示例 |
| Hazelight Discord | https://discord.gg/39wmC2e （未文档化的行为多在此讨论） |

## 10. 值得关注的小型/奇特项目

| 仓库 | 说明 |
| --- | --- |
| https://github.com/romanpunia/asx | 类 Node.js 的 AS 运行时 |
| https://github.com/paril/angelscript-debugger | DAP 调试器 |
| https://github.com/pezcode/firefly | OllyDbg 的 AS 插件（逆向场景） |
| 各种 PotPlayer 插件（Bilibili 播放、字幕翻译等） | PotPlayer 的扩展脚本语言就是 AS，GitHub 上 `Language: AngelScript` 仓库里数量最多的一类 |
| Sven Co-op 生态 | `outerbeast/entities-and-gamemodes`、`rcbotcheeseh/rcbotsven5` 等大量地图/插件脚本 |
| Trackmania / Openplanet 生态 | `tm-agent`、`McpTM` 等 AI/遥测插件 |

## 11. 检索技巧

- GitHub Topic 页（按更新时间排序，可看活跃生态）：https://github.com/topics/angelscript
- 按语言过滤 AngelScript 本身：https://github.com/topics/angelscript?l=angelscript&o=desc&s=updated （约 87 个仓库）
- 定向找"用了 AS 的开源项目"：https://open-awesome.com/stacks/angelscript
