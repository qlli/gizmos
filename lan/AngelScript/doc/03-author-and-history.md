# 作者、组织与发展史

## 1. 创建者

| 项 | 内容 |
| --- | --- |
| 姓名 | **Andreas Jönsson**（瑞典，常写作 Andreas Jonsson） |
| 网名 / 论坛 ID | **WitchLord** |
| 名义组织 | **AngelCode**（个人品牌，非公司实体） |
| 站点 | https://angelcode.com（自 **2001** 年起维护） |
| 联系方式 | 论坛 https://angelcode.com/forums/ 或 https://angelcode.com/contact.html |
| 商业模式 | zlib 免费开源 + 自愿捐赠（https://angelcode.com/donate.html），作者原话："I only ask for your recognition, nothing else." |

**关键定性**：AngelScript 是**典型的单人长期开源项目**——自 2003 年起由同一人持续维护 20+ 年，至今仍在 GameDev.net 论坛亲自答疑（2025 年的帖子中仍能看到 WitchLord 逐条回复并承诺把用户建议加入 to-do）。这既是它稳定性的来源，也是它演进速度受限的原因。

## 2. 起源与动机

- 2003 年 2 月作为**爱好项目**启动，动机是填补当时嵌入式脚本语言的空缺：
  - 当时的方案（Lua、Python、GameMonkey 等）语法对 C++ 程序员不友好；
  - 或者需要大量**代理函数（proxy function）**才能把 C++ 类型暴露给脚本。
- 目标：C++ 程序员**零学习曲线**上手，且宿主能**直接用原生调用约定**调用已注册的 C++ 函数/对象。
- 进度：2003-03-28 发布仅含基础功能的首版；**2003 年 6 月底发布 1.0**（首个编号公开版本），已支持注册 C++ 函数、编译为字节码在 VM 上执行。

## 3. 时间线

| 时间 | 事件 |
| --- | --- |
| 2001 | Andreas Jönsson 建立 AngelCode.com |
| 2003-02 | AngelScript 开始开发 |
| 2003-03-28 | 首个公开版本 |
| 2003-06 | 1.0 发布；同期在 GameDev.net 开设论坛收集反馈 |
| 2004 末 | Frictional Games 的 HPL Engine 采纳 AngelScript |
| 2005-06-08 | **2.2.0**：脚本类（初称 struct）、自动析构、更好的编译错误提示、增量 GC |
| 2006 | **2.7.0**：接口（interface）；同年 Game Programming Gems 6 收录 AngelScript 章节 |
| 2007–2008 | Penumbra 系列（Frictional Games） |
| 2009 | **2.15.2** 单继承；**2.16.3** 运算符重载；**2.17.0** 外部 JIT 编译器接口 |
| 2010 | **2.18.2** 脚本函数指针；Amnesia: The Dark Descent 发售 |
| 2011-07-03 | **2.21.0** 执行期自动 GC（循环引用）+ 标准调试器 add-on |
| 2012-01-29 | **2.22.2** 命名空间与 `::` |
| 2012-02 | Blind Mind Studios 发布第一个可用的 JIT 编译器（1.5×~3× 提速） |
| 2013-03-02 | **2.26.1** 多模板子类型 |
| 2015 | SOMA 发售 |
| 2021 | Hazelight Studios《It Takes Two》发售，绝大部分玩法用 AngelScript（UE 插件）写成 |
| 2024-07-20 | **2.37.0**：新 JIT 接口（支持全局优化）、自动生成拷贝构造、可显式排除默认/拷贝构造与赋值 |
| 2025-03 | sashi0034 发布 VSCode 通用 Language Server（angel-lsp），作者将其加入官方 resources 页 |
| 2025-08-08 | **2.38.0**：变参函数、foreach、模板函数注册、`using namespace`、构造器中成员初始化、socket add-on 等 |
| 2025-08-12 | **源码从 SourceForge SVN 迁至 GitHub**（`anjo76/angelscript`），保留完整历史，启用 GitHub Actions CI |
| 2025 | Hazelight《Split Fiction》—— **170 万+ 行 AngelScript，16,000+ 脚本文件** |

## 4. 推动生态的关键组织

| 组织 | 角色 | 代表作品/产出 |
| --- | --- | --- |
| **Frictional Games**（瑞典） | 最早的深度用户，HPL Engine 全系脚本层 | Penumbra / Amnesia 系列 / SOMA；并产出**最好的免费 AS 入门教程**（HPL3 Wiki） |
| **Wolfire Games** | 评估多种脚本后选 AS（看中 C++ 语法 + 原生集成 + 运算符重载） | Overgrowth |
| **Blind Mind Studios** | 实现**第一个可用的 AS JIT 编译器** | Star Ruler / Star Ruler 2；JIT 已开源 |
| **Hazelight Studios**（瑞典） | 维护 **UnrealEngine-Angelscript** fork，把 AS 带入 UE5 生态 | It Takes Two、Split Fiction |
| **Embark Studios** | 采用 Hazelight 的 UE-AS 插件 | The Finals、ARC Raiders |
| **Nightdive Studios** | KEX Engine 使用 AS | Turok 重制、Blood: Fresh Supply、System Shock 系列相关 |
| **Nintendo（外部合作）** | 纸片马里奥：千年之门（Switch 重制）在官方用户列表中被列为 AS 使用者 | — |
| **sashi0034**（个人） | angel-lsp（VSCode LSP）+ 日文手册翻译 | — |
| **HenryAWE**（个人） | asbind20（C++20 绑定库，pybind11 风格），CI 覆盖多平台 | — |

## 5. 治理与许可

- **zlib License**：可商用、可闭源、可修改，唯一实质要求是不得谎称原创（不删除许可声明）。对游戏项目极其友好。
- **决策集中**：功能优先级由作者一人拍板；他明确承诺**向后兼容**（可预见会破坏旧脚本的改动，会提供 engine property 保留旧行为，例如 `asEP_PROPERTY_ACCESSOR_MODE`）。
- **社区参与路径**：论坛发帖 → 作者回应 → 进 to-do / 下个版本；2025 迁 GitHub 后新增 Issue / PR 渠道（作者表示暂不关闭）。
