# 书籍、译文与论文

## 0. 先说结论

> **截至 2026-11，市面上没有一本专门讲 AngelScript 的出版书籍。**
> 英文、中文、日文均无。原因是它属于"嵌入式库"而非独立语言，用户群小且高度集中于游戏行业，作者本人也没有出书。
> 因此**权威学习材料只有三类**：①官方在线手册；②Frictional Games 的 HPL3 Wiki 教程；③具体宿主引擎的脚本文档（Urho3D / Sven Co-op / Openplanet / UE-Angelscript）。

## 1. 提到 AngelScript 的正式出版物

| 名称 | 年份 | 作者/出版 | 说明 | ISBN |
| --- | --- | --- | --- | --- |
| **Game Programming Gems 6** | 2006 | Michael Dickheiser 主编，Charles River Media | 其中一个章节讲 AngelScript 的嵌入与用法（维基百科将其列为 AS 类语法"无需代理函数"这一论断的引用来源）。年代久远，**API 细节已过时**，仅适合了解设计思想 | 1584504501 |
| ACCU 期刊文章：*Simplifying the C++/Angelscript Binding Process* | 2010-02 | Stuart Golodetz | 讲如何简化 C++↔AS 绑定流程；思路对今天仍有参考价值（现成方案可看 asbind20） | — |

## 2. 学术论文（AS 作为工具出现在研究中）

| 论文 | 年份 | 作者 | 用途 |
| --- | --- | --- | --- |
| *ViennaIPD - An Input Control Language for Scientific Computing* | 2010 | Josef Weinbub, Karl Rupp, Siegfried Selberherr（维也纳工业大学） | 用 AngelScript 做科学计算的输入控制语言 —— **非游戏领域的典型应用** |
| *Join token: A language mechanism for programming interactive games* | 2012-05 | Taketoshi Nishimori, Yasushi Kuno | Entertainment Computing 3(2):19–25，doi:10.1016/j.entcom.2011.09.001 |
| *Cultural transmission in robotic swarms through RFID cards* | 2009 | Josh Brandoff, Hiroki Sayama | IEEE ALife'09，pp.171–178 —— 用 AS 编写**机器人行为规则** |

> 补充：德国乌尔姆大学（University of Ulm）曾在交互 3D 动画课程中使用 AS（"Animal Race" 项目，2005）。

## 3. 免费教程（推荐度排序）

| 优先级 | 资源 | 语言 | 说明 |
| --- | --- | --- | --- |
| ★★★★★ | **AngelScript 官方在线手册** | 英 | https://angelcode.com/angelscript/sdk/docs/manual/index.html —— 唯一权威，含脚本语言参考 + 宿主集成 + 全部 add-on |
| ★★★★★ | **HPL3 AngelScript Fundamentals（Frictional Games Wiki）** | 英 | 9 章从零基础讲起（变量/运算符/流程控制/函数/跨脚本调用/类/高级特性），**公认最好的免费入门教程** → https://wiki.frictionalgames.com/page/HPL3/Scripting/AngelScript_Fundamentals/Chapter_1_-_Introduction |
| ★★★★☆ | HPL3 旧 Wiki 上的《AngelScript Tutorial》 | 英 | SOMA/Amnesia mod 实战向（含完整脚本骨架） → https://oldwiki.frictionalgames.com/hpl3/community/scripting/angelscript_tutorial |
| ★★★★☆ | **AngelScript 日文手册翻译**（sashi0034） | 日 | https://zenn.dev/sashi0034/books/angelscript-docs-ja —— 完整翻译官方手册，结构清晰，可用浏览器翻译阅读 |
| ★★★☆☆ | **DinS 中文站**（官方 resources 页点名的中文站） | 中 | https://dins.site/navi-coding-chs/ —— 官方唯一认可的中文社区教程站 |
| ★★★☆☆ | 《[翻译]AngelScript 实用手册之概述》 | 中 | http://www.cppblog.com/besterChen/archive/2010/02/26/108518.aspx —— 2010 年的中文节译，**内容已过时**，仅作中文术语参考 |
| ★★★☆☆ | Urho3D 脚本文档 | 英 | 站在"引擎宿主"视角看 AS 用法 |
| ★★★☆☆ | Sven Co-op / Openplanet / NVGT 的脚本 API 文档 | 英 | 真实项目里的 AS 用法，适合对照学习 |
| ★★☆☆☆ | CSDN / 博客园零散文章 | 中 | 质量参差；UE-Angelscript 相关的近年文章相对有价值（如《【UE】【AngelScript】学习路径与资料库》） |

## 4. 视频/音频类

| 资源 | 说明 |
| --- | --- |
| Overgrowth Weekly #86（2014-11-30，17m40s 起） | Wolfire Games 讨论为何选 AngelScript 而非 Lua/V8 → https://www.youtube.com/watch?v=99T-7NeEH8s |
| GameDev.net 历史讨论帖 | 例如"First fully functional JIT compiler for AngelScript available"（2012-02-15），作者与 JIT 作者同帖讨论性能细节 |

## 5. 选书建议（给想系统学的人）

1. **不要去找"AngelScript 书"——不存在。**
2. 主干教材 = 官方手册 + HPL3 Wiki 教程。
3. 想理解"为什么这样设计"，读 *Game Programming Gems 6* 相关章节 + Golodetz 的 ACCU 文章。
4. 想理解"如何在真工程里落地"，直接读 `urho3d/urho3d` 或 `Hazelight/UnrealEngine-Angelscript` 的绑定代码。
5. 中文读者：先用 DinS 中文站建立概念，再切回官方手册（中文资料普遍停留在 2010 年前后，务必回官方核对 API）。
