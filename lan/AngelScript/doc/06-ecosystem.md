# 生态：谁在用 AngelScript

> 数据来源：官方《Applications using AngelScript》页 https://angelcode.com/angelscript/users.html + Wikipedia + 各项目站点。

## 1. 已发布游戏（官方用户列表摘录，按影响力排序）

### 一线 / 高知名度

| 游戏 | 开发商 | 备注 |
| --- | --- | --- |
| **It Takes Two（双人成行）** | Hazelight Studios | 2021 TGA 年度游戏；**大部分玩法用 AngelScript 写成**（UE 插件） |
| **Split Fiction** | Hazelight Studios | 2025；**170 万+ 行 AS、16,000+ 脚本文件** |
| **The Finals / ARC Raiders** | Embark Studios | 使用 Hazelight 的 UE-AS 插件 |
| **Amnesia: The Dark Descent / Rebirth / A Machine for Pigs** | Frictional Games / The Chinese Room | HPL Engine |
| **SOMA** | Frictional Games | HPL3 |
| **Penumbra 系列** | Frictional Games | 最早一批 adopter（2004 末起） |
| **Overgrowth** | Wolfire Games | 移动/AI/战斗系统全用 AS |
| **Paper Mario: The Thousand-Year Door（Switch）** | Nintendo | 官方用户列表收录 |
| **SpellForce 3 / Soul Harvest / Fallen God** | Grimlore Games / THQ Nordic | — |
| **Turok / Turok 2: Seeds of Evil / Blood: Fresh Supply** | Nightdive Studios | KEX Engine |
| **SuperTuxKart** | 开源 | 赛道脚本 |
| **Sven Co-op** | 开源/社区 | 地图脚本生态极活跃（GitHub topic 里最多的类别之一） |
| **Rigs of Rods** | 开源 | 软体物理沙盒 |
| **King Arthur's Gold** | — | — |
| **Dustforce / Heroes of Hammerwatch / Serious Sam's Bogus Detour** | Hitbox / Crackshell / Croteam | — |
| **Sine Mora, Puddle, Warsow, Jazz Jackrabbit 2 Plus, Star Ruler, Amy, Gekkeiju Online, Magic Portals** | 各家 | — |
| **Beyond All Reason / Warfork / OpenSpades** | 开源社区 | RTS / FPS |
| **Fighting Ex Layer** | Arika | 格斗游戏 |
| **Book of Demons** | Thing Trunk | — |

## 2. 引擎 / 库（作为脚本层）

| 引擎 | 链接 | 备注 |
| --- | --- | --- |
| **UnrealEngine AngelScript（Hazelight）** | https://angelscript.hazelight.se/ | **最重要**：UE5 的 AS 脚本层 |
| **Urho3D** | http://urho3d.github.io/ | AS 与 Lua 双脚本支持，最经典的嵌入范例 |
| **HPL Engine（Frictional）** | https://wiki.frictionalgames.com/ | 恐怖游戏专用 |
| **KEX Engine（Nightdive）** | https://www.nightdivestudios.com/kex/ | 重制老游戏 |
| **ezEngine** | https://github.com/ezEngine/ezEngine | — |
| **Thunder Engine** | https://github.com/thunder-engine/thunder | 模块化 |
| **qfusion / Warfork** | https://github.com/Warsow/qfusion | — |
| **FOnline** | http://www.fonline.ru | 开源在线 RPG 框架 |
| **Ethanon Engine** | http://ethanonengine.com/ | — |
| **Openplanet** | https://openplanet.dev/ | Trackmania mod 平台 |
| **3D Rad / Piko3D / Sirrf / Cattle Engine / NLS** | 各自站点 | — |
| **NVGT** | https://nvgt.dev | 音频游戏（无障碍）开发 |

## 3. 非游戏应用 / 工具（说明 AS 不只是游戏语言）

| 应用 | 领域 | 链接 |
| --- | --- | --- |
| **OpenVSP** | NASA 开源飞机参数化建模/气动分析 | http://www.openvsp.org |
| **SimulIDE** | 电子电路仿真 | https://www.simulide.com |
| **Blue Cat's Plug'n Script** | 音频插件（用脚本写 DSP/效果器） | http://www.bluecataudio.com/Products/Product_PlugNScript/ |
| **MemBrain** | 神经网络工具 | http://www.membrain-nn.de |
| **AngelScript CSG** | CAD/几何（Carsten Arnholm） | http://arnholm.org/angelscript-csg/ |
| **Grome** | 地形建模（Quad Software） | http://www.quadsoftware.com |
| **R.U.B.E.** | Box2D 编辑器（iforce2d） | https://www.iforce2d.net/rube/ |
| **Simplex Numerica** | 科学绘图/数值 | https://www.simplexnumerica.com |
| **WingHexExplorer2** | 十六进制编辑器 | https://github.com/Wing-summer/WingHexExplorer2 |
| **OpenSiv3D** | 创意编程 | https://github.com/Siv3D/OpenSiv3D |
| **NymphCast / Vortex / cgMusic / GMovies / RaySupreme / Photo Reactor** | 媒体与图形 | — |
| **MacroWorks II for X-keys** | 硬件宏 | http://www.piengineering.com/software/mwii.php |
| **Detect-It / ModFusion / DuiEditor / Territory** | 其它工具 | — |
| **ViennaIPD** | 科学计算输入语言（学术研究） | 见 04 文档 |
| **机器人群体行为** | 学术（ALife'09） | 见 04 文档 |

## 4. 生态图谱（文字版）

```
                        Andreas Jönsson (AngelCode / WitchLord)
                                      │  2003~ 单人维护，zlib
                                      ▼
                          AngelScript 库 + SDK add-ons
                                      │
        ┌─────────────────┬───────────┼────────────────┬────────────────┐
        ▼                 ▼           ▼                ▼                ▼
   游戏引擎层        商业游戏     独立/开源游戏     非游戏工具        工具链
   ├ Urho3D          ├ It Takes Two ├ Rigs of Rods   ├ OpenVSP        ├ angel-lsp (LSP)
   ├ HPL Engine      ├ Split Fiction├ SuperTuxKart   ├ SimulIDE       ├ asbind20 (绑定)
   ├ UE-Angelscript  ├ Amnesia/SOMA ├ OpenSpades     ├ BlueCat 音频   ├ asdbg / VS 插件
   ├ KEX Engine      ├ The Finals   ├ Sven Co-op     ├ WingHex        ├ JIT (BMS/angelsea)
   ├ ezEngine        ├ ARC Raiders  ├ Beyond All Reason├ OpenSiv3D    ├ docgen / aatc / astd
   ├ Thunder         └ SpellForce 3 └ KAG / Warsow   └ CSG / Grome    └ 预处理器 / 语法高亮
   └ qfusion / FOnline
```

## 5. 生态健康度判断（2026-11）

| 维度 | 评价 |
| --- | --- |
| 语言本体活跃度 | ✅ 高。2025-08 发 2.38.0（史上最大更新），迁 GitHub，上 CI |
| 商业采用 | ✅ 强。UE-AS 把它带进 AAA（《双人成行》《Split Fiction》《The Finals》《ARC Raiders》） |
| 工具链 | ⚠️ 中等。LSP 有了（2025 起可用），IDE 支持分散，调试器有多个但都不算主流 |
| 第三方库 | ⚠️ 薄弱。容器/JSON/XML/异步靠社区小库，没有统一包管理器 |
| 中文资料 | ❌ 极薄弱。官方只认一个中文站（DinS）；UE-AS 相关的中文博客是近年唯一增量 |
| 学习成本 | ✅ 低（对 C++ 程序员）。语法 90% 与 C++ 一致 |
