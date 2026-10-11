# 设计规则

本文件规定工程分层、依赖、书写方式和实现过程。异步资源的问题域见 [Resource.md](Resource.md)。

加载完成与生命期开始是不是同一事件，以及 `ReplaceRaw` 的实现，本文件不规定，见第 9 节。

## 1. 语言与目录

实现使用 C#，代码放在 `Assets/Scripts/` 下。

```text
Assets/Scripts/Base/      命名空间 Base
Assets/Scripts/Engine/    命名空间 Engine
Assets/Scripts/MyGame/    命名空间 MyGame
```

本工程的业务层命名空间使用 `MyGame`。换项目时，这一层改成该项目的游戏名，前两层的命名空间不变。

## 2. 三层

| 层 | 命名空间 | 职责 |
| --- | --- | --- |
| 语言和系统 | `Base` | 包装和扩展操作系统与语言。例如嵌入 Lua 虚拟机、JSON 工具，以及其他与引擎无关的功能 |
| 引擎扩展 | `Engine` | 包装和扩展 Unity。例如有组合性的异步资源系统、统一的 UI 框架、通用的时间线 |
| 游戏业务 | `MyGame` | 特定项目的玩法与内容 |

`Base` 不引用 `UnityEngine`，也不使用任何引擎 API。

UI 框架、时间线，以及 `Base` 里的 Lua、JSON 等，目前只划定归属。具体设计另写，不在本文件展开。

## 3. 依赖与启动

依赖是单向的：

```text
Base  ←  Engine  ←  MyGame
```

`Base` 不依赖 `Engine` 和 `MyGame`。`Engine` 不依赖 `MyGame`。`MyGame` 可以使用前两层。

有初始化或启动过程的模块，按 `Base`、`Engine`、`MyGame` 的顺序执行。后一层开始时，前一层已经完成启动。同一层内部的模块顺序在该层的设计里另定。

异步资源框架里的资源对象由使用方创建，不单独占一层启动步骤。Unity 异步操作如何通知完成，写在 `Engine.Resource` 的加载实现里。`Base` 不轮询引擎，也不提供驱动器。

## 4. 程序集

三层各建一个程序集，与命名空间同名，用来让第 2、3 节的依赖在编译期成立。

| 程序集 | 路径 | 引用 |
| --- | --- | --- |
| `Base` | `Assets/Scripts/Base/Base.asmdef` | 不引用 Unity 引擎。程序集设置 `noEngineReferences` |
| `Engine` | `Assets/Scripts/Engine/Engine.asmdef` | `Base`，以及该层需要的 Unity 模块 |
| `MyGame` | `Assets/Scripts/MyGame/MyGame.asmdef` | `Engine` |

`MyGame` 通过 `Engine` 使用 `Base` 中已经由引擎层转述的能力。业务代码需要直接使用 `Base` 里与引擎无关的工具时，再让 `MyGame` 引用 `Base`。

## 5. 异步资源框架的划分

问题域以 [Resource.md](Resource.md) 为准。实现按是否依赖引擎分成两部分。

| 部分 | 命名空间 | 类型 |
| --- | --- | --- |
| 与引擎无关 | `Base.Res` | `Resource`、`ResourceGroup`、`Clone`、`Reference` |
| 与引擎相关 | `Engine.Resource` | `AsyncBundle`、`AsyncAsset`、`AsyncGameObject` |

`Base.Res` 只处理抽象资源、成组、拷贝和引用计数。`Load`、`Free` 等与具体来源相关的方法在这里保持抽象。

`Engine.Resource` 实现 Bundle、Asset、GameObject 等具体来源。这些类可以使用 `UnityEngine`。

`MyGame` 把具体资源拼成该项目的资源树，不改写框架的状态规则。

## 6. 类的组织形式

一个类里的顺序固定为：

1. 成员数据
2. 成员方法。构造函数放在其他方法之前
3. 方法中先 `public`，再 `protected`，再 `private`

成员只声明，不在声明处初始化。初始化写在构造函数里。构造时各成员的初始化可能有复杂逻辑和先后依赖，声明处的初始化表达不了这些关系。

类、成员、方法需要说明时，用 `//` 注释。写给资深开发者，一句点明约束即可，不写 `///`、`<summary>`、`<param>`。

```csharp
namespace Base.Res
{
    // 抽象资源。加载与释放由派生类实现。
    public abstract class Resource
    {
        // 当前持有的原始资源，生命期属于它。
        protected object raw;

        // 使用或不使用。
        public void SetActive(bool on) { }

        // 按使用信息修改原始资源。
        protected abstract void Render(object data, object raw);
    }
}
```

上面只说明排列和注释，不是当前要提交的实现。

## 7. 分析与实现过程

先分析问题域，再写代码。分析要落到对象、状态和生命期上，并与 [Resource.md](Resource.md) 对得上。

分析缺信息时，指出缺的是哪一条、它影响哪个类型，然后停住，等补充。不用推测把缺口补上。

实现贴合已经确认的分析。一次只写当前确认过的最小一块，下一块等确认后再写。不在同一次修改里顺手补上相邻类型或未确认的状态分支。

## 8. 已经确定的资源约束

以下各项与第 9 节的两个未决问题无关，后续实现直接遵守。

- `data` 是这份资源的全部使用信息，`raw` 是当前交进来的原始资源。生命期属于 `raw`，不属于 `Resource` 对象。对象存续期间可以多次更换 `raw`。
- 使用先修改 `data`。`raw` 还没到达时，只修改 `data`。之后按当时的完整 `data` 刷新，不把错过的 `SetData` 排队回放。
- `data` 和 `raw` 的静态类型使用 `object`。`data` 允许为空，表示还没有使用信息。
- 一次使用从 `SetActive(true)` 开始，并由此触发 `Load`。同一使用周期内再次 `SetActive(true)`，不重复发起 `Load`。
- `SetActive(false)` 表示这次使用结束。加载仍在进行时打断加载；已经进入生命期的 `raw` 结束生命期并 `Free`。这次使用结束之后再次 `SetActive(true)`，重新 `Load`。
- 使用结束之后才到达的加载结果，不得开始新的生命期。
- `Load` 的完成通知只表示结果到达，随后走框架固定的刷新。完成通知里不保存上层对资源的处理流程。
- `OnActive(true)` 做初始化，`OnActive(false)` 做复原，`Render` 按 `data` 修改 `raw`。这三个方法相对加载完成的调用时机，等第 9 节确定后再写。

## 9. 暂不规定

下面两项先保持开放，不选边，也不据此写代码。

1. **读法 A / B。** 不规定叶子加载完成时，生命期是否立刻开始；不规定「已加载但未使用」的结果存放在基类还是派生类；不规定 `BreakLoad` 在「IO 已结束、生命期尚未开始」时是空操作还是丢弃结果。
2. **`ReplaceRaw`。** 不规定它的语句顺序，不规定它与 `Render` 的衔接，也不实现它。替换原始资源的问题域仍以 [Resource.md](Resource.md) 为准。

在这两项确定之前，不实现 `Resource` 的状态机，也不实现 `ResourceGroup`、`Clone`、`Reference` 以及 `Engine.Resource` 中的具体资源。
