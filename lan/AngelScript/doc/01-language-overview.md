# AngelScript 语言速览

## 1. 基本档案

| 项目 | 内容 |
| --- | --- |
| 名称 | AngelScript（AngelCode Scripting Library） |
| 类型 | 嵌入式（embeddable）脚本库 / 编译型脚本语言 |
| 范式 | 多范式：过程式、面向对象、指令式 |
| 类型系统 | 静态 + 强类型 |
| 作者 | Andreas Jönsson（AngelCode） |
| 首次出现 | 2003 年（2 月开工，3 月 28 日首个公开版，6 月底 1.0） |
| 当前稳定版 | **2.38.0（2025-08-08）** |
| 前一版本 | 2.37.0（2024-07-20） |
| 许可 | zlib License（免费商用，可闭源，仅要求署名） |
| 平台 | 跨平台（Windows / Linux / macOS / 主机 / 移动 / WASM 等，靠社区移植与 native calling convention 支持） |
| 实现语言 | C++（约 90%） |
| 官方站 | https://angelcode.com/angelscript/ |

## 2. 设计哲学

1. **贴合 C++**：语法几乎照搬 C++，宿主注册 C++ 类型/函数时**几乎不需要写代理函数（proxy/wrapper）**——这是它区别于 Lua/Python/V8 嵌入的最大卖点。
2. **零依赖嵌入**：本质是"库"而不是独立运行时，宿主注册什么，脚本就有什么。
3. **不做 GC 停顿**：引用计数为主 + 增量式 GC 只用于检测/回收**循环引用**。
4. **脚本作者无需关心指针与内存泄漏**。

## 3. 核心语言特性

| 特性 | 说明 | 引入版本 |
| --- | --- | --- |
| 基础类型 | `int8/16/32/64`、`uint8/16/32/64`、`float`、`double`、`bool` | 早期 |
| 脚本类 | 最初叫 "struct" | 2.2.0（2005-06） |
| 接口 interface | 用于实现"多重继承"的效果 | 2.7.0（2006） |
| 单继承 | 类继承 | 2.15.2（2009） |
| 运算符重载 | 含二元/一元运算符 | 2.16.3（2009-07） |
| JIT 接口 | 外部 JIT 编译器接入点 | 2.17.0（2009-08） |
| 函数指针 / funcdef | 委托机制 | 2.18.2（2010） |
| 自动 GC（循环引用） | 执行期自动回收；同版本加入标准调试器 add-on | 2.21.0（2011-07-03） |
| 命名空间 / 作用域运算符 | `namespace`、`::` | 2.22.2（2012-01-29） |
| 多个模板子类型 | 模板增强 | 2.26.1（2013-03-02） |
| 自动生成拷贝构造、显式排除默认构造/拷贝构造/赋值、新 JIT 接口 |  | 2.37.0（2024-07-20） |
| **变参函数注册、foreach、模板函数注册、`using namespace`、构造器中成员显式初始化、script socket add-on、std::string 的 format/scan 变参** | 作者称"可能是史上最大更新" | **2.38.0（2025-08-08）** |

### 值得一提的语法点

- **对象句柄 `@`**：`Object@ obj;` 类似 C++ 指针，但引用计数管理，可置 `null`，用 `@` 赋值（`@obj = other;`）。
- **引用参数的 in/out/inout**：`void f(const T&in a, T&out b, T&inout c)` —— 比 C++ 多一步"方向"声明。
- **mixin 类**：把一组方法混入其它类，实现代码复用。
- **funcdef + 委托**：`funcdef void Callback(int);` 后可声明 `Callback@ cb;` 并调用。
- **property accessor**：`get_/set_` 前缀方法即可伪装成属性。
- **关键字全集**（HPL3 wiki 列出）：`and abstract auto bool break case cast class const continue default do double else enum false final float for from funcdef function get if import in inout int interface int8 int16 int32 int64 is mixin namespace not null or out override private protected return set shared super switch this true typedef uint uint8 uint16 uint32 uint64 void while xor`

## 4. 与 C++ 的关键差异（踩坑清单）

| # | 差异 | 影响 |
| --- | --- | --- |
| 1 | **不支持多重继承** | 用 `interface` 组合替代 |
| 2 | 方法/属性**只能在类体内声明** | 不能像 C++ 那样类外定义成员函数 |
| 3 | **所有方法（含构造/析构）都是虚函数** | 无静态绑定优化，也意味着全部可覆写 |
| 4 | 没有指针语义 | 用句柄 `@` 或引用 `&`；注册接口时要决定"引用还是句柄" |
| 5 | 引用必须声明方向 | `&in` / `&out` / `&inout` |
| 6 | 类型名不完全一致 | 例如 C++ `char` 在 AS 里是 `int8` |

## 5. 宿主集成要点（注册接口）

| 概念 | 说明 |
| --- | --- |
| 引擎创建 | `asCreateScriptEngine(ANGELSCRIPT_VERSION)` → `asIScriptEngine*` |
| 注册全局函数 | `RegisterGlobalFunction("void f(int)", asFUNCTION(f), asCALL_CDECL)` |
| 注册对象类型 | `RegisterObjectType("Vec2", sizeof(Vec2), asOBJ_VALUE \| asOBJ_POD \| ...)` |
| 注册成员方法 | `RegisterObjectMethod("obj", "void m()", asMETHOD(Obj,m), asCALL_THISCALL)` |
| 注册行为 | `RegisterObjectBehaviour(..., asBEHAVE_CONSTRUCT / asBEHAVE_ASSIGNMENT / ...)` |
| 重载消歧 | `asFUNCTIONPR` / `asMETHODPR` 宏（需要写出参数表与返回类型） |
| 调用约定 | `asCALL_CDECL`、`asCALL_STDCALL`、`asCALL_THISCALL`、`asCALL_GENERIC`、`asCALL_CDECL_OBJFIRST`、`asCALL_CDECL_OBJLAST` |
| 常用引擎属性 | `asEP_OPTIMIZE_BYTECODE`、`asEP_ALLOW_UNSAFE_REFERENCES`、`asEP_INCLUDE_JIT_INSTRUCTIONS`、`asEP_PROPERTY_ACCESSOR_MODE` |
| 常见错误 | 调用约定写错 → **栈破坏导致崩溃**，而非编译错误 |

> ⚠️ 排错常识：注册时调用约定写错几乎必然是运行时栈崩溃，优先检查 `asCALL_*` 与函数真实签名是否匹配。

## 6. 性能

- 编译为字节码在 VM 上执行，纯解释执行速度在同类脚本语言中属第一梯队。
- Blind Mind Studios 的 JIT 编译器实测：大循环算术约 **4×**，二叉树遍历约 **2×**，数组冒泡排序约 **2.5×**，整体常见区间 **1.5×~3×**，部分场景接近原生 C++。
- 2.37.0 引入新的 JIT 接口（可一次性拿到全部脚本函数做全局优化），旧的 JIT 接口保留以保持兼容。

## 7. 适用场景判断

| 场景 | 是否推荐 | 理由 |
| --- | --- | --- |
| C++ 引擎需要嵌入式脚本、希望脚本与宿主类型零摩擦 | ✅ 强烈推荐 | 这是它的设计目标 |
| 需要热重载/快速迭代的玩法逻辑 | ✅ 推荐 | UE-Angelscript 是成熟范例 |
| 需要动态类型、REPL、灵活元编程 | ❌ 不推荐 | 它是静态强类型 |
| 需要庞大第三方库生态 | ❌ 不推荐 | 生态远小于 Lua/Python |
| 需要成熟工具链（包管理、调试器、静态分析） | ⚠️ 一般 | 工具有但较分散，见 05 文档 |
