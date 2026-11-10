# 编译器实现与库生态

> 整理日期：2026-11-02
> 本篇聚焦"实现层面"：AngelScript 的编译管线是怎么搭的、有哪些 JIT/AOT、有哪些绑定库与标准库、怎么构建分发。

## 0. 一句话概览

**AngelScript 只有一个官方编译器前端实现（C++ 手写递归下降），没有第三方重写的前端。**
围绕它的"实现生态"分四层：①官方编译管线（Tokenizer→Parser→Builder→Compiler→Bytecode→VM）；②JIT/AOT 层（3 个 JIT + Hazelight 的 C++ 转译）；③绑定/标准库层；④工具链层（LSP/调试器/构建）。

## 1. 官方编译管线

### 1.1 流水线

```
源码文本
   │
   ▼  asCTokenizer                       词法分析 → Token 流
   ▼  asCParser                          语法分析 → AST（asCScriptNode 树）
   ▼  asCBuilder                         构建编排（总协调者）
        ├─ RegisterTypesFromScript()     注册类型声明
        ├─ DetermineTypeRelations()      解析继承/模板关系
        ├─ CompileInterfaces()           编译接口
        ├─ CompileClasses()              编译类
        ├─ CompileGlobalVariables()      编译全局变量
        └─ CompileFunctions()            编译函数体
   ▼  asCCompiler                        语义分析 + 字节码生成
        ├─ asCExprContext / asCExprValue 表达式上下文（类型、LValue、临时量、栈偏移）
        ├─ asCVariableScope              作用域与栈分配
        ├─ CompileStatementBlock / CompileExpression / CompileFunctionCall …
        └─ FinalizeFunction()
   ▼  asCByteCode                        字节码指令序列（含 asBC_JitEntry 入口点）
   ▼  asCWriter / asCReader              字节码序列化 / 反序列化（asIBinaryStream）
   ▼  asCScriptFunction / Module         可执行模块
   ▼  asCContext                         虚拟机执行（栈 + 调用栈）
```

### 1.2 关键源码文件（`sdk/angelscript/source/`）

| 文件 | 职责 |
| --- | --- |
| `as_tokenizer.cpp` / `.h` | 词法分析 |
| `as_parser.cpp` / `.h` | 语法分析，产出 `asCScriptNode` |
| `as_builder.cpp` / `.h` | 编译编排、类型注册、依赖解析、错误/警告输出（`WriteError` 等） |
| `as_compiler.cpp` / `.h` | **核心**：语义分析 + 字节码生成 |
| `as_bytecode.cpp` / `.h` | 字节码容器与指令 |
| `as_context.cpp` / `.h` | 虚拟机执行、调用栈、挂起/恢复、行回调（调试基础） |
| `as_scriptengine.cpp` / `.h` | 引擎、类型注册 API、GC |
| `as_module.cpp` / `.h` | 脚本模块 |
| `as_texts.h` | 统一错误/警告消息模板 |
| `as_config.h` | **编译期开关总表**（见下节） |
| `as_callfunc.cpp` / `as_callfunc_x64.cpp` 等 | 原生调用约定（各平台/ABI 的汇编 shim） |

### 1.3 `as_config.h` 编译期开关（裁剪与移植的关键）

| 宏 | 效果 | 典型用途 |
| --- | --- | --- |
| **`AS_NO_COMPILER`** | **编译库时不包含脚本编译器**，只能加载预编译字节码 → 显著减小可执行文件体积 | 发行版只跑预编译脚本（NVGT 的 `angelscript-nc` 就是这么干的） |
| **`AS_MAX_PORTABILITY`** | 关闭全部平台相关代码，**只保留 `asCALL_GENERIC`** | Emscripten / 无原生调用约定支持的平台（通常由 `as_config.h` 自动定义） |
| `AS_NO_THREADS` | 关闭多线程支持，略提性能 | 单线程宿主 |
| `AS_NO_EXCEPTIONS` | 关闭异常处理 | 异常不可用平台 / 体积优化 |
| `AS_NO_CLASS_METHODS` | 禁用类方法注册，提高可移植性 | 极简嵌入 |
| `AS_USE_COMPUTED_GOTOS` | 启用 computed goto 优化 VM 指令分发（GCC/Clang） | 性能 |
| `AS_USE_NAMESPACE` | 把声明放进 AngelScript 命名空间 | 避免符号冲突 |
| `AS_DEPRECATED` | 保留向后兼容的废弃功能 | 老项目 |
| `AS_NO_MEMBER_INIT` | 禁用类成员声明处直接初始化（兼容 2.26.0 之前行为） | 老脚本兼容 |
| `AS_DEBUG` | 库内部额外输出 | 调试库自身 |
| `AS_DOUBLEBYTE_CHARSET` | 双字节字符集解析（推荐直接用 UTF-8，原生支持） | 旧编码 |

### 1.4 预编译字节码

- 从 **2.22.2（2012）** 起作者开始系统性推进"预编译字节码完全平台无关"：新增专用于指针操作的字节码指令，移除旧指令；后续目标是消除对 CPU 指针大小的依赖。
- 配套 `AS_NO_COMPILER` 让只加载字节码的应用可以大幅瘦身。
- ⚠️ **Hazelight 的警告**：预编译脚本里**硬编码了 C++ 属性的字节偏移和结构大小**，`PrecompiledScript.Cache` 必须与生成它的那个二进制严格配对；每次重新打包 exe 都要重新生成。反过来则不必——改 `.as` 脚本后可只重建 cache 而不重编二进制。
- Hazelight 生成命令：`ProjectName.exe -as-generate-precompiled-data` → 产出 `Script/PrecompiledScript.Cache`；开发态可用 `-as-development-mode` 绕过它（否则热重载被禁用）。

## 2. JIT 与 AOT 层

### 2.1 官方 JIT 接口

| 接口 | 版本 | 说明 |
| --- | --- | --- |
| `asIJITCompiler` | 2.17.0(2009) 起 | 老接口：逐个函数编译 |
| **`asIJITCompilerV2`** | **2.37.0(2024) 起** | 新接口：可一次拿到**全部脚本函数**统一编译，让 JIT 做全局优化；旧接口保留以兼容现有 JIT |
| 启用方式 | | `engine->SetEngineProperty(asEP_INCLUDE_JIT_INSTRUCTIONS, 1)` + `engine->SetJITCompiler(jit)` |
| 机制 | | 字节码函数带有 **JIT entry point**（`asBC_JitEntry`），JIT 可从入口接管；遇到不支持的指令仍可落回 VM |

### 2.2 三个 JIT 横向对比

| | **BlindMindStudios JIT** | **bluecataudio fork** | **angelsea** |
| --- | --- | --- | --- |
| 仓库 | `BlindMindStudios/AngelScript-JIT-Compiler` | `bluecataudio/AngelScript-JIT-Compiler` | `asumagic/angelsea` |
| 技术路线 | C++11 + 手写伪汇编（virtual_asm），直接发射机器码 | 同左 + 未合并进原版的关键修复 | **C++20：AS 字节码 → C 源码 → c2mir 编译 → MIR JIT 发射机器码** |
| 维护状态 | ⚠️ 已停更（作者说 Blind Mind 不再支持） | 官方 resources 页推荐使用 | ✅ 活跃（2025-08 起，alpha） |
| 兼容 AS 版本 | 声明兼容 2.31.0 | 同上 | **要求 2.37.0+**（依赖 `asIJITCompilerV2`） |
| 架构 | x86 / x86_64（Win MSVC、Linux GCC） | 同左 | x86-64 Linux/Windows（MinGW 实测、MSVC 未实测）、aarch64（实验）、**32 位 x86 不支持**（MIR 限制） |
| 性能 | 常见 1.5×~3×；大循环算术 4×、二叉树 2×、冒泡排序 2.5× | 同左 | 相比 BMS JIT **+0~40%**；generic 调用百万次基准约 **5×** |
| 特色 | 代码量小、易嵌入；线程安全 | 修复若干 | **惰性编译**（计数器达阈值才编译，默认开）、**异步编译**（`SetCompileCallback`）、超大函数默认跳过、`experimental_stack_elision` |
| 授权 | MIT | MIT | BSD-2-Clause |
| 依赖 | 无 | 无 | AngelScript 2.37.0+、fmt、MIR v1.0（用下游 fork）、可选 Catch2/nanobench |
| 备注 | 建造 flag 丰富：`JIT_NO_SUSPEND`、`JIT_SYSCALL_FPU_NORESET`、`JIT_ALLOC_SIMPLE`、`JIT_FAST_REFCOUNT` 等 | | 作者曾尝试 LLVM JIT 后放弃，改用更轻量的 MIR |

> **反直觉知识点**：原版 AS 里**原生调用约定（asCALL_CDECL 等）其实比 generic 约定做更多工作**——参数都在 AS 栈上，native 还要走复杂的 C++ ABI 模拟 shim；generic 只是每次取参都走虚函数调用。angelsea 通过针对性生成代码 + 池化 `asCGeneric`，把 generic 调用做得很快。选 native 还是 generic 要实测（asbind20 有 benchmark 可查）。

### 2.3 AOT 风格：Hazelight 的 C++ 转译（UE-AS）

这是**目前唯一成熟的"AS → 本地代码"产品级方案**，严格说不是 JIT 而是"脚本转 C++"：

1. `ProjectName.exe -as-generate-precompiled-data`
2. 除 `PrecompiledScript.Cache` 外，还产出 **`AS_JITTED_CODE/`** 目录（每个脚本文件一个 C++ 文件）
3. 把该目录拷进工程源码（模块需在 `Build.cs` 里依赖 `AngelscriptCode`），重新编译 exe
4. 新 exe + cache 一起用，运行时会**挂到 AngelScript 的 JIT 编译系统上，用原生 C++ 替代字节码执行**
5. 效果：官方表述为"approaches native C++ performance"（明显快于蓝图）

> ⚠️ 若改了 `.as` 重建 cache，旧二进制里的转译 C++ 将不匹配、不再生效，需要用新的 `AS_JITTED_CODE` 重新编译二进制。

### 2.4 关于"独立编译器"

- 作者明确说过：**AngelScript 不是为做独立编程语言设计的，它是嵌入库**，没有官方 AS→exe 编译器。
- 2014 年论坛有用户尝试用 LLVM 做 AOT，作者回应"没用过 LLVM，理论上可以把字节码翻译成 LLVM 能理解的东西"，该用户最终放弃了；angelsea 作者也提到自己"几年前的 LLVM JIT 尝试"因范围过大而放弃。
- 结论：**想做 AS→原生可执行文件，目前只能自己搭，社区无成品。**

## 3. 前端与预处理

| 类别 | 项目 | 说明 |
| --- | --- | --- |
| 官方前端 | `as_parser.cpp`（C++） | **唯一实现**。作者 2008 年建议：若要做 IntelliSense，可基于 `as_parser.cpp` 自己写扫描器（因为要在脚本还不可编译时就能扫出符号） |
| IDE 用前端 | `sashi0034/angel-lsp`（TypeScript） | 为做语言服务**独立重写了一套 AS 词法/语法分析与类型检查**；靠 `as.predefined` 描述宿主 API |
| 预处理器 | `kunitoki/angeljuice` | 内含 Anthony Casteel 2005 年写的 AS 预处理器 |
| 预处理器 | `codecat/ccpp` | 通用预处理器，对 AS 可用 |
| 预处理器 | `rotators/angelscript-preprocessor` | rotators 组织维护 |
| 预处理器 | `romanpunia/asx` | 含 preprocessor 的运行时环境 |
| 模板/元编程 | 无 | AS 无宏系统，社区靠预处理器或代码生成补位 |

## 4. 库（脚本侧）

### 4.1 官方 SDK Add-on（19 个，见 02 文档）

`string` / `array<T>` / `any` / `ref` / `weakref` / `dictionary` / `file` / `filesystem` / `math` / `grid<T>` / `datetime` / `socket` / `Exception routines`（脚本扩展）；
`Script builder` / `Context manager` / `Debugger` / `Serializer` / `Helper functions` / `Automatic wrapper functions`（应用模块）。

### 4.2 社区库

| 库 | 仓库 | 定位 |
| --- | --- | --- |
| **AATC** | `Sami-Vuorela/aatc` | STL 风格模板容器：vector / list / set / unordered_set / map / unordered_map |
| **astd** | `oktonion/astd` | C++ 标准库的 AS 移植，让脚本写法尽量贴近 C++ |
| **aspromise** | `romanpunia/aspromise` | Promise / async 语义 |
| **asx** | `romanpunia/asx` | 类 Node.js + NPM 的运行时环境（addon / stdlib / vm / preprocessor / debugger 打包） |
| **as-reflect** | `Sebight/as-reflect` | 运行时反射：`reflect` 命名空间下检视脚本类属性、读写字段、动态调用方法 |
| ScriptXML | `bluecataudio/angelscript-addons` | 基于 tinyxml2 的 XML 解析/写入 |
| ScriptJson | `hanan619/angelscript-addons` | 基于 nlohmann::json 的 JSON |
| 变参 print | `SpehleonLP/Zodiac` | 支持最多 16 个变参的 print |

## 5. 绑定库（宿主侧）

### 5.1 asbind20（首选）

- 仓库 `HenryAWE/asbind20`，C++20，header-only（核心部分），API 设计参考 **pybind11**。
- 自动按 type traits 生成默认构造/拷贝构造/析构/赋值；自动生成 `opEquals`/`opCmp`；自动推导包装函数的调用约定（`asCALL_CDECL_OBJFIRST/OBJLAST/GENERIC`）。
- **Generic wrapper**：`use_generic` 标签可强制生成 `asCALL_GENERIC` 包装——**Emscripten 等无原生调用约定平台的关键能力**；支持变参类型 `?`（`var_type`）、composite 成员（`composite()`）、`ForceGeneric` 开关（在编译期暴露"本平台不该用 native"的 bug）。
- 可用 `has_max_portability()` 检查 `asGetLibraryOptions()` 是否含 `AS_MAX_PORTABILITY`。
- CI 覆盖：MSVC(x86/x64)、Clang-Cl、GCC 12~14、Clang 15/18/19、Linux arm64、macOS arm64、Emscripten；有 nightly 脚本跟踪 AS WIP 版本。
- 分发：直接拷 `include/`、CMake（submodule / FetchContent / install）、**已收录进 xmake-repo**（`add_requires("asbind20")`）、有 `vcpkg.json`。
- 有中文 README（`README.zh-CN.md`）；文档 https://asbind20.readthedocs.io/。

### 5.2 其它绑定 / 跨语言

| 方案 | 仓库 / 资源 | 说明 |
| --- | --- | --- |
| 官方 C 接口 | `angelcode.com/angelscript/extras/angelscript_clib_2.36.1.zip` | 给 C / Delphi / Pascal 等非 C++ 语言用；非标准 SDK 组成，**最后更新 2.36.1**，需自己跟进 |
| 自动包装器（add-on） | SDK `doc_addon_autowrap.html` | 官方自带，免手写 wrapper |
| 智能指针自动包装 | `angelcode.com/angelscript/extras/aswrapper.zip` | SiCrane 的模板方案 |
| RefCountingObject | `only-a-ptr/RefCountingObject-AngelScript` | C++/AS 互通的智能指针 |
| **Rust** | `dsobotta/rust-angelscript`（含 `angelscript-sys`、`angelscript_derive`） | ★12，2021 年后停更；MIT |
| **D** | `KitsunebiGames/dangel` | D 绑定 + OOP 封装，支持 D 字符串；**依赖打了 D ABI 补丁的 AS 与 C 绑定**，WIP |
| **C#** | `EasyT-T/ccb` + `EasyT-T/ccb-rust` | AngelScript↔C# 绑定生成器 + Rust 中间层（起 .NET 虚拟机）+ 插件加载器；含 DI（`[Injectable]`） |
| Delphi / Pascal | 官方 C 接口 | — |

## 6. 调试与工具

| 工具 | 仓库 | 要点 |
| --- | --- | --- |
| SDK Debugger add-on | `/sdk/add_on/debugger` | 2.21.0 起内置；基于 line callback + suspend |
| **angelscript-debugger** | `Paril/angelscript-debugger`（★19） | **DAP（Debug Adapter Protocol）**实现，可与 angel-lsp 或任意 DAP 客户端配合；需 **AS 2.38.0+**、C++17、fmtlib、cppdap；`asIDBWorkspace` / `asIDBDebugger` / `asIDBCache` 三层，可自定义类型求值器（Evaluate/Expand）；零开销设计（无工作时调试器不消耗）；WIP，无稳定发布 |
| asdbg | `codecat/asdbg` | 远程调试器，GUI 用 C# 写，易集成 |
| VS 调试 | `lizuan1992/AngelScript-DebugServer` + `RemoteDebuggerVSX` | 在 Visual Studio 里断点/单步 AS |
| **ASIDE** |（Qt 写的通用 AS IDE）| 基于 Qt 的桌面 IDE：语法高亮、补全、调试、项目管理、插件机制 |
| angel-lsp | `sashi0034/angel-lsp` | VSCode Language Server（见 02/05 文档） |
| docgen | `marcakafoddex/angelscript-docgen` | 从注册点直接生成脚本 API 文档，随接口演进易维护 |

## 7. 构建与分发

| 渠道 | 状态 |
| --- | --- |
| **vcpkg** | `vcpkg install angelscript`，当前 **2.38.0#0**（2025-10-13 发布）；feature `addons` 可安装全部 add-on |
| **Conan Center** | `angelscript/2.38.0`，CMake 包名 `Angelscript`、target `Angelscript::angelscript`；选项 `shared`、`fPIC`、`no_exceptions` |
| **xmake** | AS 本体可经 xmake-repo；**asbind20 已被官方收录** |
| **CMake** | SDK 内自带；asbind20 要求 CMake ≥ 3.20 |
| Premake5 | 社区 fork（如 `Spiderhund/angelscript`）提供，可用 `as_addon_*` 选项精细裁剪 add-on |
| 官方源码 | `git clone https://github.com/anjo76/angelscript`，`.github/workflows` 含多平台多编译器 CI（2025-11 还在加 Clang、补测试用例） |
| 测试套件 | `sdk/tests/test_feature`（含 `test_compiler.cpp`、`test_optimize.cpp`、`test_debug.cpp` 等）—— 学实现的绝佳入口 |

## 8. 平台与移植要点

| 平台 | 状态 |
| --- | --- |
| Windows / Linux / macOS（x86、x64、arm64） | ✅ 官方支持原生调用约定 |
| Emscripten / WASM | ⚠️ 无原生调用约定支持 → 自动落 `AS_MAX_PORTABILITY`，必须走 `asCALL_GENERIC` + autowrapper（Urho3D 社区有 preprocessor 黑魔法方案；asbind20 官方支持并用 CI 验证） |
| 主机（PlayStation / Xbox / Nintendo） | 靠社区端口与 add-on，官方 SDK 不直接覆盖 |
| iOS / Android / Windows Mobile | 同上 |
| 32 位 x86 | angelsea 不支持（MIR 限制）→ 用 BlindMindStudios JIT |

## 9. 想深入源码时的阅读顺序

1. `as_config.h` —— 先看开关，理解裁剪维度
2. `as_tokenizer.cpp` → `as_parser.cpp` —— 前端
3. `as_builder.cpp` 的 `Build()` —— 看清编译分阶段（这是理解"为什么 AS 要求先声明后使用"的关键）
4. `as_compiler.cpp` 的 `CompileFunction` / `CompileExpression` / `FinalizeFunction`
5. `as_bytecode.h` —— 指令集与 `asBC_JitEntry`
6. `as_context.cpp` —— VM 执行、栈管理、挂起
7. `as_callfunc*.cpp` —— 各 ABI 的原生调用 shim（也是"native 未必比 generic 快"的根源）
8. `sdk/tests/test_feature/source/test_compiler.cpp` —— 对照测试看边界行为
9. 想看 JIT 怎么接：`as_jit.h`（BMS）或 angelsea 的 `Jit` 类
