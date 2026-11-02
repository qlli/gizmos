# 学习路线（面向 UE / C++ 开发者）

## 1. 先想清楚：你要用 AS 做什么？

| 你的目标 | 推荐路径 |
| --- | --- |
| A. 在 UE5 里用脚本写玩法（最贴近本仓库其它工作） | **路径 A：UE-Angelscript** |
| B. 给自己的 C++ 引擎/工具加脚本层 | **路径 B：原生嵌入** |
| C. 只是想理解这门语言本身 | **路径 C：语言本体** |

## 2. 路径 A：UE-Angelscript（推荐给 UE 开发者）

### 阶段 0：准备（最耗时的一步）

- ⚠️ **关键认知**：Hazelight 版 UE-AS **不是即插即用插件**，而是**引擎源码 fork**，必须走源码编译 UE 的路线。
  - 折中方案：`ueworks/UE-Angelscript`（重构成单插件，基于 UE 5.4.2，适配原版引擎）。
- 环境：UE 源码权限 + Visual Studio 2022（实测比更新版本稳）+ VSCode + `Unreal Angelscript` 扩展。
- 仓库：`git clone https://github.com/Hazelight/UnrealEngine-Angelscript.git`
- 文档站：https://angelscript.hazelight.se/
- 社区：Hazelight Discord https://discord.gg/39wmC2e

### 阶段 1：最小闭环（1~2 天）

| 目标 | 验收标准 |
| --- | --- |
| 写一个脚本 Actor | 在 Place Actors 里能搜到 |
| BeginPlay 打印 | 日志输出可见 |
| Tick 更新 | 每帧行为变化 |
| VSCode 补全/跳转可用 | 绑定类型能自动补全 |

### 阶段 2：像写 C++ 一样写 UE

- UPROPERTY 暴露到 Details 面板与蓝图
- UFUNCTION / BlueprintOverride：与蓝图互通
- Function Libraries → 脚本命名空间
- Actors & Components / Properties & Accessors
- 练习：Moving Platform（可配置速度/路径）、Spawner（`TSubclassOf` 指向蓝图子类并 Spawn）

### 阶段 3：架构三件套（分水岭）

- Delegates / Events（事件驱动解耦）
- Gameplay Tags（全项目语义标签）
- Subsystems（模块化、生命周期清晰）
- 练习：写一个"交互系统"——触发 → 广播委托 → UI/音效/任务系统响应

### 阶段 4：工具开发（TA 主战场）

- Editor Utility Widgets（EUW）
- Scripting & Automating the Unreal Editor
- Asset Registry（扫描/查询未加载资产）
- Slate（复杂工具 UI）
- Editor-only 脚本：`#if EDITOR`

### UE-AS 常见坑（务必记住）

| 坑 | 正确做法 |
| --- | --- |
| `.as` 里写 `#include` | ❌ 没有 include |
| `.as` 里写 `GENERATED_BODY()` | ❌ 没有宏 |
| 用 `->` | ❌ 一律用 `.` |
| 以为 `Super::Foo()` 能调到 C++ 父类 | ❌ 只能调到 AS 父类 |
| 用 `UInterface` | ❌ AS 侧不支持，用组合或 `UFUNCTION(BlueprintEvent)` |
| 手写 `GetLifetimeReplicatedProps` | ❌ `Replicated` 说明符即可 |
| 把 Hazelight fork 与预编译二进制插件混用 | ❌ fork 不兼容二进制插件，插件必须源码编译 |
| 只用"编译通过"判断功能完成 | ❌ 必须 `Print()` + 跑测试 + 亲自读日志 |

### UE-AS 类型心智模型

| UE 侧 | AS 侧 |
| --- | --- |
| 基本类型 / UStruct（FVector、FString、FName、FText）/ 枚举 | 值类型（赋值拷贝） |
| UObject 及其子类（AActor、UActorComponent） | 引用类型（Handle，等价于 C++ 的 `UObject*`） |
| 结构体参数 | 自动按 `const &` 传递（不拷贝） |
| `FName` 字面量 | `n"MyName"` |
| 格式化字符串 | `f"Actor: {GetName()}"`（Python 风格 f-string） |

## 3. 路径 B：原生嵌入到自己的 C++ 工程

| 阶段 | 内容 | 产出 |
| --- | --- | --- |
| B1 | 下载 SDK（2.38.0），编译库，跑通 `samples/` 里的示例 | 能编译执行第一个脚本 |
| B2 | 读手册 "Registering a function" 等注册章节 | 掌握 `asFUNCTION` / `asMETHOD` / `asFUNCTIONPR` / 6 种调用约定 |
| B3 | 注册自己的值类型（如 Vec2）与引用类型 | 脚本能操作 C++ 对象 |
| B4 | 接入 add-on：script builder（多文件/元数据）+ std::string + array + dictionary | 有可用的标准库 |
| B5 | 接入 context manager / debugger / serializer | 支持并发、调试、存盘 |
| B6 | 考虑绑定库：`asbind20`（C++20，可省掉大量样板代码） | 注册代码量大幅下降 |
| B7 | 性能敏感时接 JIT（`bluecataudio/AngelScript-JIT-Compiler` 或 `angelsea`） | 1.5×~3× 提速 |

**最小可用骨架（伪代码）**

```cpp
asIScriptEngine* engine = asCreateScriptEngine(ANGELSCRIPT_VERSION);
engine->SetMessageCallback(asFUNCTION(MessageCallback), nullptr, asCALL_CDECL);
engine->SetEngineProperty(asEP_OPTIMIZE_BYTECODE, 1);

RegisterStdString(engine);        // add_on/scriptstdstring
RegisterScriptArray(engine, true); // add_on/scriptarray

// 注册值类型
engine->RegisterObjectType("Vec2", sizeof(Vec2),
    asOBJ_VALUE | asOBJ_POD | asOBJ_APP_CLASS_ALLFLOATS);
engine->RegisterObjectProperty("Vec2", "float x", asOFFSET(Vec2, x));
engine->RegisterObjectBehaviour("Vec2", asBEHAVE_CONSTRUCT, "void f()",
    asFUNCTION(Vec2DefaultConstructor), asCALL_CDECL_OBJFIRST);

// 编译 + 执行
```

> ⚠️ 调 `RegisterObjectBehaviour` 时注意 `asCALL_CDECL_OBJFIRST` / `asCALL_THISCALL` 别写错——写错是运行时栈崩溃，不是编译错误。

## 4. 路径 C：只学语言本身

1. HPL3 Wiki《AngelScript Fundamentals》第 1~9 章通读（英文，零基础向，约半天）
   - https://wiki.frictionalgames.com/page/HPL3/Scripting/AngelScript_Fundamentals/Chapter_1_-_Introduction
2. 官方手册 "The script language" 部分逐章对照（当作参考书，不必通读）
   - https://angelcode.com/angelscript/sdk/docs/manual/doc_script.html
3. 用 `samples/asrun`（或任意宿主）跑片段，验证：句柄语义、`&in/&out`、interface、funcdef 委托、mixin、foreach（2.38.0）、变参（2.38.0）
4. 中文辅助：https://dins.site/navi-coding-chs/（概念建立），但**所有 API 细节回官方核对**（中文资料多停留在 2010 前后）

## 5. 建议的本地实践目录

```
D:\proj\gizmos\lan\AngelScript\
├── doc\            # 本文档集
├── sdk\            # 解压官方 SDK（angelcode.com/angelscript/sdk/files/）
├── sandbox\        # 自己搭的最小宿主：注册 Vec2 / Player，跑脚本
└── notes\          # 读源码与手册时的笔记
```

## 6. 里程碑自检

| 里程碑 | 能回答的问题 |
| --- | --- |
| M1 跑通 | 我能让宿主加载并执行一个 `.as` 文件吗？ |
| M2 注册 | 我能把 C++ 类和函数暴露给脚本并正确选择调用约定吗？ |
| M3 双向 | 我能从 C++ 调用脚本函数、并管理脚本对象生命周期吗？ |
| M4 工程化 | 我有 script builder / 调试器 / 热重载吗？ |
| M5 性能 | 我是否接了 JIT？热路径是否已下沉到 C++？ |
| M6 架构 | 我的脚本边界清晰吗（哪些必须 C++、哪些可脚本）？ |
