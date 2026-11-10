# 官方资源

## 1. 站点地图

| 类别 | 名称 | URL |
| --- | --- | --- |
| 🏠 官方主页 | AngelScript | https://angelcode.com/angelscript/ |
| 🏠 站点根 | AngelCode.com（Andreas Jönsson 自 2001 维护） | https://angelcode.com |
| 📖 在线手册 | AngelScript Manual（当前对应 2.38.0） | https://angelcode.com/angelscript/sdk/docs/manual/index.html |
| 📖 手册入口 | Overview | https://angelcode.com/angelscript/sdk/docs/manual/doc_overview.html |
| 📖 脚本语言参考 | The script language | https://angelcode.com/angelscript/sdk/docs/manual/doc_script.html |
| 📄 许可 | zlib License | https://angelcode.com/angelscript/sdk/docs/manual/doc_license.html |
| 📦 SDK 下载 | angelscript_2.38.0.zip | https://www.angelcode.com/angelscript/sdk/files/angelscript_2.38.0.zip |
| 📜 变更历史 | Changes | https://angelcode.com/angelscript/changes.php |
| 👥 使用者列表 | Applications using AngelScript | https://angelcode.com/angelscript/users.html |
| 🔧 更多资源 | Further resources & support | https://angelcode.com/angelscript/resources.html |
| 💬 官方论坛 | AngelCode Forums | https://angelcode.com/forums/ |
| 💬 GameDev.net 版块 | AngelCode（作者本人活跃，网名 WitchLord） | https://www.gamedev.net/forums/forum/34-angelcode/ |
| ✉️ 联系作者 | Contact | https://angelcode.com/contact.html |
| ☕ 捐赠 | Donate | https://angelcode.com/donate.html |
| 💻 官方源码仓库 | GitHub（2025-08 从 SourceForge 迁入） | https://github.com/anjo76/angelscript |
| 📦 旧 SVN（历史） | SourceForge | https://svn.code.sf.net/p/angelscript/code/trunk |
| 🪞 社区镜像 | codecat/angelscript-mirror | https://github.com/codecat/angelscript-mirror |

> 作者同站的其它工具：BMFont（位图字体生成器）、AngelCode Texture Generator、RefDB（开发者资源库）、Tower（小游戏）。

## 2. 在线手册章节结构（学习顺序建议即此顺序）

官方手册分两大块：**Using AngelScript（宿主集成）** 与 **The script language（脚本语言）**。

核心页面（均为 `https://angelcode.com/angelscript/sdk/docs/manual/` 下）：

| 页面 | 主题 |
| --- | --- |
| `doc_overview.html` | 总览 |
| `doc_script.html` | 脚本语言参考（总入口） |
| `doc_register_func.html` | 注册函数（含调用约定、类型差异）—— 集成必读 |
| `doc_addon.html` / `doc_addon_application.html` / `doc_addon_script.html` | Add-on 总览 / 应用模块 / 脚本扩展 |
| `doc_license.html` | zlib 许可 |

> 手册页面众多（含 `doc_script_*`、`doc_api_*`、`doc_adv_*` 系列），建议直接从 `index.html` 起顺着目录读，或本地下载 SDK 后离线浏览 `sdk/docs/manual/`。

## 3. SDK Add-on 清单（`/sdk/add_on/`）

### 3.1 应用模块（Application modules）—— 宿主侧

| Add-on | 说明 | 文档 |
| --- | --- | --- |
| Script builder | 脚本构建器：多文件、#include 处理、元数据、模块加载 | `doc_addon_build.html` |
| Context manager | 脚本上下文池管理（便于并发/复用） | `doc_addon_ctxmgr.html` |
| Debugger | 标准调试器 add-on（2.21.0 引入） | `doc_addon_debugger.html` |
| Serializer | 序列化/反序列化（保存字节码、对象状态） | `doc_addon_serializer.html` |
| Helper functions | 常用辅助函数集合 | `doc_addon_helpers.html` |
| Automatic wrapper functions | 自动包装器（简化注册） | `doc_addon_autowrap.html` |

### 3.2 脚本扩展（Script extensions）—— 脚本侧标准库

| Add-on | 说明 | 文档 |
| --- | --- | --- |
| string object | `string` 类型（2.38.0 起支持 `format`/`scan` 变参、`regexFind`） | `doc_addon_std_string.html` |
| array template object | `array<T>` 模板数组（2.38.0 起支持 foreach） | `doc_addon_array.html` |
| any object | `any` 任意类型容器 | `doc_addon_any.html` |
| ref object | `ref` 句柄包装 | `doc_addon_handle.html` |
| weakref object | `weakref` 弱引用 | `doc_addon_weakref.html` |
| dictionary object | `dictionary` 键值容器（2.38.0 起支持 foreach） | `doc_addon_dict.html` |
| file object | 文件读写 | `doc_addon_file.html` |
| filesystem object | 文件系统遍历 | `doc_addon_filesystem.html` |
| math functions | 数学函数 | `doc_addon_math.html` |
| grid template object | `grid<T>` 二维网格 | `doc_addon_grid.html` |
| datetime object | 日期时间 | `doc_addon_datetime.html` |
| socket object | **2.38.0 新增** socket 网络 | `doc_addon_socket.html` |
| Exception routines | 异常例程 | `doc_addon_helpers_try.html` |

## 4. 官方"Further resources"里点名的第三方资源（完整搬运）

| 类别 | 资源 | 链接 |
| --- | --- | --- |
| 社区 | 官方论坛 | https://angelcode.com/forums/ |
| 社区 | IRC `#angelscript`（freenode webchat） | http://webchat.freenode.net |
| 社区 | 社区 Wiki（pbworks） | http://angelscript.pbworks.com |
| 社区 | **中文站 DinS（含教程）** | https://dins.site/navi-coding-chs/ |
| 文档生成 | angelscript-docgen（Foddex） | https://github.com/marcakafoddex/angelscript-docgen |
| JIT | Blind Mind Studios JIT（经典，x86/x64） | https://github.com/BlindMindStudios/AngelScript-JIT-Compiler |
| JIT | BlueCat 的 fork（含尚未合并的修复） | https://github.com/bluecataudio/AngelScript-JIT-Compiler |
| JIT | angelsea（另一个 JIT，asumagic） | https://github.com/asumagic/angelsea |
| 调试 | asdbg 远程调试器（codecat，GUI 为 C#） | https://github.com/codecat/asdbg |
| 调试 | RemoteDebuggerVSX + AngelScript-DebugServer（VS 插件，作者 Li Zhuang） | https://github.com/lizuan1992/RemoteDebuggerVSX · https://github.com/lizuan1992/AngelScript-DebugServer |
| IDE | IntelliJ 插件（Matt Hornung） | https://plugins.jetbrains.com/plugin/18276-angelscript-language-support · https://github.com/hmatt1/angelscript-intellij |
| 容器库 | AATC（Sami Vuorela，vector/list/set/map…） | https://github.com/Sami-Vuorela/aatc |
| 标准库 | astd（oktonion，C++ STL 风格移植） | https://github.com/oktonion/astd |
| 异步 | aspromise（romanpunia，Promise） | https://github.com/romanpunia/aspromise |
| 反射 | as-reflect（Sebight，运行时反射） | https://github.com/Sebight/as-reflect |
| XML | ScriptXML（bluecataudio，基于 tinyxml2） | https://github.com/bluecataudio/angelscript-addons |
| JSON | ScriptJson（Hanan Arshad，基于 nlohmann::json） | https://github.com/hanan619/angelscript-addons |
| 智能指针 | aswrapper.zip（SiCrane 的模板自动包装） | https://angelcode.com/angelscript/extras/aswrapper.zip |
| 智能指针 | RefCountingObject-AngelScript（Petr Ohlídal） | https://github.com/only-a-ptr/RefCountingObject-AngelScript |
| 容器 | STL 风格 array（Squared'D） | http://articles.squaredprogramming.com/2014/01/c-stl-style-array-thats-compatible-with.html |
| 打印 | 变参 print（Patrick Jeeves） | https://github.com/SpehleonLP/Zodiac/tree/main/example |
| 预处理 | AngelJuice IDE 内含的预处理器（Anthony Casteel, 2005） | https://github.com/kunitoki/angeljuice |
| 预处理 | ccpp（codecat 通用预处理器） | https://github.com/codecat/ccpp |
| 编辑器 | Sublime Text 语法高亮 | https://github.com/wronex/sublime-angelscript |
| 编辑器 | **angel-lsp（VSCode 通用 Language Server）** | https://marketplace.visualstudio.com/items?itemName=sashi0034.angel-lsp · https://github.com/sashi0034/angel-lsp |
| 绑定库 | **asbind20（C++20 绑定库，作者 HenryAWE）** | https://github.com/HenryAWE/asbind20 |
| 语言桥接 | 官方 C 接口（供 C/Delphi/Pascal 使用，末次更新 2.36.1） | https://angelcode.com/angelscript/extras/angelscript_clib_2.36.1.zip |
| 翻译 | **日文手册（sashi0034，Zenn）** | https://zenn.dev/sashi0034/books/angelscript-docs-ja |

## 5. 源码仓库现状（2025 迁移后）

- 官方仓库：https://github.com/anjo76/angelscript
- 迁移公告（作者亲发，2025-08-12）：https://gamedev.net/forums/topic/719020-angelscript-is-now-on-github/
- 迁移时保留了**完整提交历史**（3,100+ commits）。
- 已启用 GitHub Actions CI（多平台/多编译器自动测试），作者明确表示目标之一是覆盖自己不常测的平台。
- 目录结构：`sdk/`（库源码 + add_on + docs + tests）、`.github/`（CI）、`LICENSE.md`、`README.md`；SDK 内同时提供 CMake 与其它构建脚本（各 fork 有 premake5 适配版）。
- 语言构成（观测）：C++ ~89.7%、HTML ~4.2%、C ~3.7%、汇编 ~1.2%。
