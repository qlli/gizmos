# 配置化驱动的游戏开发 · 可落地设计方案

> Schema 即契约 → 生成可序列化代码 → 多形态编辑（Excel / 按需 uasset / 图）↔ SSOT 文本 → 分端运行时 bytes + 热更新 + AI 协同

**标签**：Proto / XML 双前端 Schema · 独立自研 · Luban 仅作参考 · 统一中间表示（IR） · 字段级分组裁剪 · SSOT 文本 · UE / Unity 插件 · bytes + manifest 热更 · 节点图（蓝图式） · MCP + Knowledge

| 项 | 值 |
| --- | --- |
| 方案代号 | **CDP**（Config-Driven Pipeline） |
| 版本 | v1.5 · 2026-09 |
| 适用 | UE5 / Unity / 自研引擎 · 服务端 + 客户端 |

## 目录

1. [方案概览与设计目标](#1-方案概览与设计目标)
2. [参考与借鉴](#2-参考与借鉴)
3. [总体架构与数据流](#3-总体架构与数据流)
4. [Schema 体系](#4-schema-体系)
5. [SSOT 文本与编辑视图](#5-ssot-文本与编辑视图)
6. [代码生成（多语言 / 引擎）](#6-代码生成多语言--引擎)
7. [运行时数据与热更新](#7-运行时数据与热更新)
8. [UE 插件集成](#8-ue-插件集成)
9. [Unity 与其他宿主](#9-unity-与其他宿主)
10. [节点图（蓝图式流程）](#10-节点图蓝图式流程)
11. [AI 协作层](#11-ai-协作层)
12. [工程流程与 CI/CD](#12-工程流程与-cicd)
13. [落地路线图](#13-落地路线图)
14. [风险与决策](#14-风险与决策)
15. [附录](#15-附录)

---

## 1. 方案概览与设计目标

本方案面向内容规模大、端多、语言多、需要频繁改配置并热更的游戏项目。目标是把**策划数据、数值、节点图**放进一条可校验、可回溯、可自动化的流水线，并且让 AI 能安全地改文本实例。

### 1.1 这套方案好在哪里

> **能交给各款游戏长期用的原因：** CDP 的编译器、IR、校验、生成器和运行时均独立自研；只参考成熟配表工具的分组、target、校验和模板化做法。工具仓库里只有内核和适配器，每款游戏自带 schema 和文本并锁定 CDP 工具版本，下一款游戏不继承上一款的表和节点。

- **策划、程序、AI 看同一份数据**：权威副本是 JSON/YAML 等文本。Git 能 diff，评审能看行，AI 能打补丁。Excel 和确有引擎原生编辑需求的 uasset 视图坏了可以从文本重建。
- **改一次结构，各端一起变**：表用 proto 描述。C++、C#、TypeScript、Python、UE 的 USTRUCT、Unity 的序列化类从同一份中间表示生成，不用手写第二套结构体。
- **表格习惯保留，文本仍然是源**：需要 Excel 时从文本生成临时工作簿，改完导回。策划不用改工作方式，程序不用把 xlsx 当提交物。
- **客户端拿不到不该有的字段**：同一份 schema 生成 client / server 两套 bytes。掉落、定价等服务器字段不会出现在客户端类型里。两边模拟必须一致的字段单独标成 sim，避免热更后对局分叉。
- **蓝图节点只定义一次**：节点类型留在 C++。工具用显式注册抽取类型，再校验图实例。不用在 proto 里抄一份蓝图定义。
- **运行时和 schema 是同一套**：线上 bytes 默认就是 protobuf。各语言用官方解码器。UE 将 protobuf DTO 一次性转换为不可变的 UE View 快照，Blueprint 读取拷贝或安全 View。某个引擎要自己的二进制，只在它的适配器里多打一份，不再另写一套 schema。
- **视图敢用，是因为回环会失败**：每种编辑器都要自动做「文本 → 视图 → 文本」。丢字段、改数值、挪动节点坐标，CI 直接红。通用规则由编辑器和 CI 共用 cfgc；UE 资产检查由 Editor 适配器/Commandlet 执行，并统一输出结构化错误。

### 1.2 要付出的代价

- CDP 不引用 Luban 代码。proto 前端、IR、数据加载、校验、模板生成和编码均由本项目实现并维护；Luban 仅作为公开设计参考。
- 回环只保证**约定子集**。普通数值表不生成 uasset；节点图和复杂原生资产视图中的 GUID、缩略图、导入时间不进文本，也不参与对比。
- Excel 只覆盖标量、枚举、引用、一层结构体和简单列表。节点图不走 Excel。
- 默认线上格式是 protobuf 二进制。某个引擎要再打一份自己的 bytes，由该引擎适配器负责，内核不维护第二套解码器。
- 热更清单由工具生成。CDN、灰度比例、渠道包是游戏自己的发布器，不写进 cfgc。
- 节点图编译成现有逻辑（蓝图、Verse、C++）能读的数据，不另做一套图虚拟机。
- 第一款接入的游戏要补齐自己的适配器和样例回环。之后的游戏只加 schema 和缺的适配器。

### 1.3 一句话定义

> **CDP = 一套 Schema 驱动的编译型配置管线**：以 Schema 为唯一契约，编译出各语言/引擎的可序列化类型与运行时 bytes；以**文本为 SSOT**，Excel 是普通表视图，uasset 只承载节点图或复杂原生资产视图；以 **manifest + 差量 bytes** 支撑分端加载与热更新。

### 1.4 设计目标（Goals）

#### G1 · 单一契约

- Schema 一处定义，C++ / C# / TS / Python / UE USTRUCT / Verse 全部由它生成。
- 改 Schema 必须走编译流程，禁止手写运行时结构体。

#### G2 · SSOT 文本化

- 数据实例的权威副本是 JSON/YAML 等文本，便于 Git diff、Code Review、AI 读写。
- Excel 是普通表的临时视图；uasset 仅用于节点图或确需引擎原生编辑的复杂数据。所有启用的视图均可从文本重建（`views/` 可 gitignore）。

#### G3 · 分端裁剪

- 表级 / 字段级 / 记录级三级裁剪。客户端类型里不存在服务器字段（掉落率、价格）。
- 另有 `sim` 分组：客户端和服务器的模拟逻辑必须加载同一份 bytes。标进 sim 的字段禁止只下发一端。

#### G4 · 强校验

- 引用完整性（ref）、范围（range）、唯一索引、路径存在性（path）。
- 错误必须带文件、主键、字段名。来自 Excel 时再带工作表和单元格。通用规则调用同一份 `cfgc check`；UE 资产引用通过 AssetRegistry 快照或 Editor Commandlet 校验，并归一为同一错误格式。

#### G5 · 热更新与兼容

- v1 只允许数据内容热更。任何 Schema 变化（包括新增字段）都必须重新生成代码、重编并发布程序；各 target 的 bytes 与生成代码的 schemaHash 必须严格相等。
- 工具只产出 manifest 文件。运行时以不可变快照按代加载，通过 RAII/引用计数句柄自动保活旧代；不向游戏逻辑暴露可跨代缓存的裸指针，也不要求手工 Release。

#### G6 · AI 可协作

- Schema + 文本实例 + MCP 工具链，让 AI 能"读得懂、改得对、错了能被拦住"。
- AI 输出只能落在 SSOT 文本 patch 上，且必须过编译器与 CI 门禁。

### 1.5 非目标（Non-goals）

- 不取代引擎本身的资产系统（UE uasset / Unity Addressables）。只为节点图或确需原生编辑的复杂数据提供双向桥接，普通数值表不生成 uasset。
- 不实现通用脚本语言；Lisp/DSL 仅用于配置中的表达式与图节点参数，编译成数据而非解释执行。
- 不做运行时数据库；本方案是"编译期数据"，运行期只读。
- 不做多语言文案管线。字段值直接写在数据实例里，不要求另建文案表，也不把本地化 key 当作校验项。
- 不另做一套与 protobuf 平行的默认二进制。引擎专用格式只留在该引擎适配器。不把 CDN、灰度比例、渠道包做进工具。
- 不实现新的图虚拟机，不编辑三维场景。
- 不把任何一款游戏的表、节点或资源路径写进工具仓库。

---

## 2. 参考与借鉴

| 来源 | 做法 | 借鉴点 | 本方案取舍 |
| --- | --- | --- | --- |
| **Luban** | XML/Excel 定义表 → 生成 10+ 语言代码 + bin/json 数据；支持分组、多态 bean、ref 校验、path 校验、tag、Excel/JSON/Lua/XML 多数据源。 | 分组（`c/s/e`）、target 概念、多数据格式 loader、`--errorFormat json`、Excel 多行表头约定（`##`）。 | **仅参考做法，不使用、不引用、不分叉 Luban。** CDP 独立实现 proto 前端、IR、加载、校验、模板生成、编码、文本权威副本、回环和宿主适配器。 |
| **TDR** | XML 描述结构 → 生成 C/C++ 结构与读写代码，强调版本兼容（version/字段增删规则）、紧凑二进制。 | 版本号 + 兼容规则、字段 tag 化、紧凑编码、跨平台 C++ 运行时。 | 兼容规则写入附录 A，作用在 protobuf 字段号上。不另做 TLV。引擎专用二进制由适配器另打。 |
| **HOOK 项目** | 表走 proto + Excel/JSON → bin；Action、Buff 流程的作者提交物是 JSON 或 Lisp 文本，uasset 与 bytes 由文本重建。需要表格时，从文本生成临时 Excel，改完导回。 | 文本与 uasset 的回环、临时 Excel 编辑、图实例用 sidecar 保存逻辑和布局。 | 节点图不单开模块：抽类型和编译在 Schema 工具，图资产与文本互转在 UE Editor。manifest 由 Schema 工具产出，加载更新在 UE Runtime。见第 13 节。 |
| **UE DT + 蓝图 / Verse** | DataTable 承载行数据、蓝图承载逻辑；复杂组合数据用 UObject + 自定义编辑器。 | 编辑器体验、Detail 面板、资产引用（软引用路径）、蓝图可见类型。 | 生成 `FTableRowBase` 派生结构体兼容既有 DT；复杂结构生成 UObject + 自定义编辑器；DT/资产只是视图。 |
| **protobuf 生态** | proto3 定义 → 多语言代码，IDE/CI 支持好。 | 跨语言一致性、扩展 option 机制、成熟的 lint/breaking-change 检查（buf）。 | Schema 和默认运行时都用 protobuf，并用 buf 做破坏性变更检查。引擎专用格式是适配器的额外产物（见 7.1）。 |

> **关键结论：** 工具分成三块，才能给下一款游戏继续用。内核是独立自研的 schema 前端、中间表示、校验、文本、protobuf bytes 和 manifest 文件，不包含任何 Luban 运行时或代码依赖。游戏包是该游戏自己的 proto 和数据文本。UE、Unity、Excel 是可选适配器，可以在 protobuf 之外再打该引擎自己的二进制。某一款游戏的节点或发行渠道进了内核，这个工具就不能再给别的游戏用。

---

## 3. 总体架构与数据流

### 3.1 主干流水线

```
① Schema（*.proto / *.xml → IR）
        ↓
② Codegen（C++ / C# / TS / USTRUCT）
        ↓
③ 编辑视图（Excel · 原生复杂资产 · 图）
        ⇅
④ SSOT 文本（JSON/YAML 等文本）
        ↓
⑤ Compiler（校验 · 裁剪 · 编码）
        ↓
⑥ Runtime bytes（client / server 分端）
```

反向（发布与热更）：

```
manifest（版本 · hash · 分组）
        ↓
CDN / 包体（差量下发）
        ↓
运行时句柄（按代切换，旧代仍可读）
        ↓
游戏逻辑（只读访问）
```

> **IR** 是 Intermediate Representation（中间表示）。proto、XML、Excel 表头，以及用注册宏从 C++ 抽出的节点类型，都先解析成同一份内存结构，代码生成、校验和编码只读这份结构。后文写的「统一 IR」就是它，不是另一种给策划填写的文件格式。

### 3.2 分层架构

- **L6 协作层**：MCP Server · Knowledge Base · AI Patch Review · Web 配置后台（可选）
- **L5 工程化**：CI/CD · pre-commit hook · 版本与灰度 · 冒烟测试（反序列化全表）
- **L4 宿主集成**：UE 插件（Editor + Runtime） · Unity 包 · 节点图编辑器 · Excel 临时工作簿
- **L3 运行时**：bytes 解码器（C++/C#/TS/Go/Rust…） · TableMgr / 索引 · 热重载（按代句柄） · 节点图数据
- **L2 编译器**：Schema 前端（proto/xml/excel 表头） · IR · 数据 Loader（json/yaml/xlsx/lua/xml/csv） · Validator · Group 裁剪 · Codegen（模板 .sbn） · Encoder（bin/json/msgpack）
- **L1 资产源**：`schema/` · `data/`（SSOT 文本） · `views/`（xlsx · 原生复杂资产 · 节点图）

### 3.3 核心不变量（Invariants）

1. **文本即真相**：`data/` 下的 JSON/YAML 等文本是唯一权威数据；任何视图丢失都可 `cfgc view-gen` 重建。
2. **Schema 即契约**：类型、主键、引用语义不可为"让生成通过"而随意改；变更需评审 + 版本号递增。
3. **生成物不入脑**：`gen/` 与 `out/`（bytes）不由人手编辑；例外需白名单。
4. **失败即中断**：任何校验错误（含警告级策略开启后）都导致 CI 红，不允许"带着错误发布"。
5. **分端最小化**：客户端 bytes 不包含仅服务器字段。构建期扫描生成代码和 bytes。标成 `sim` 的字段只生成一份 canonical bytes，由客户端与服务器共同消费。
6. **同一套校验契约**：编辑器、pre-commit 和 CI 的通用规则都调用同一个 `cfgc`；只有 AssetRegistry 等引擎专属事实由 Editor 适配器提供，结果统一进入 cfgc 的结构化错误模型，禁止重写一份同名通用规则。
7. **热更不悬挂指针**：对外只提供通过 RAII/引用计数绑定某一代不可变快照的句柄或 View。换代表后，旧快照由现存持有者自动保活，最后一个持有者释放时自动回收。

---

## 4. Schema 体系

### 4.1 前端选择：proto 为主，XML/Excel 为可选前端

| 前端 | 适用 | 优点 | 代价 |
| --- | --- | --- | --- |
| **.proto**（推荐） | 跨端/跨语言核心结构、服务器与客户端共享的类型 | 生态成熟（IDE、buf lint、breaking 检查）、天然跨语言、可复用既有 proto 资产 | 表达能力需靠自定义 option 扩展（表、索引、引用、分组、范围） |
| **XML（兼容前端）** | 策划可读、表定义与 Excel 表头强绑定 | 表达力强（多态、变体、tag、多主键）、策划易上手 | 需自建 IDE 支持与 lint；与 proto 资产并存时要双向同步 |
| **Excel 表头** | 快速原型、小表 | 零学习成本 | 类型表达弱、diff 困难，仅作为"视图 schema"，最终归一化到 IR |

> **落地建议：** 统一收敛到 **IR（中间表示）**。proto、兼容 XML，以及从 C++ 抽出的类型，都只是 CDP 自研 IR 的前端；代码生成、校验、编码全部只依赖 IR。这样后期可替换前端，也能按需接入已有 XML，但不引入第三方工具依赖。

### 4.2 自定义 option（proto 扩展）

```protobuf
// cfg/options.proto
syntax = "proto3";
package cfg;
import "google/protobuf/descriptor.proto";

extend google.protobuf.MessageOptions { CfgTable table = 50001; }
extend google.protobuf.FieldOptions   { CfgField field = 50002; }
extend google.protobuf.EnumOptions    { CfgEnum  enums = 50003; }

message CfgTable {
  string name = 1;              // 表全名，如 "item.TbItem"
  string mode = 2;              // map | list | singleton
  repeated string index = 3;    // 主键字段（支持复合）
  repeated string groups = 4;   // 表级导出分组: c / s / e / sim
  string comment = 5;
}
message CfgField {
  bool index = 1;               // 参与索引
  bool unique = 2;              // 唯一约束
  repeated string groups = 3;   // 字段级分组，默认继承表
  string ref = 4;               // 引用校验: "item.TbItem.id" | "path:Texture2D"
  string range = 5;             // 值域: "[0,100]" 或表达式
  string editor = 6;            // 编辑器提示: slider / color / asset-picker
  string comment = 7;
}
message CfgEnum { repeated string groups = 1; }
```

### 4.3 表定义示例

```protobuf
syntax = "proto3";
package cfg.item;
import "cfg/options.proto";

enum EItemQuality {
  option (cfg.enums) = { groups: ["c","s","e"] };
  WHITE = 0; GREEN = 1; BLUE = 2; PURPLE = 3; GOLDEN = 4;
}

message Bonus {                       // 可复用 bean
  int32 type = 1;
  int32 value = 2;
}

message TbItem {
  option (cfg.table) = {
    name: "item.TbItem"
    mode: "map"
    index: ["id"]
    groups: ["c","s","e"]
  };

  int32  id        = 1 [(cfg.field) = { index: true, unique: true }];
  string name      = 2 [(cfg.field) = { comment: "显示名" }];
  EItemQuality q   = 3;
  int32  price     = 4 [(cfg.field) = { groups: ["s"], range: "[0,999999]" }];  // 仅服务器
  float  dropRate  = 5 [(cfg.field) = { groups: ["s"] }];       // 仅服务器，禁止下发客户端
  string icon      = 6 [(cfg.field) = { ref: "path:Texture2D" }];
  repeated Bonus bonus = 7;
}
```

### 4.4 IR：编译器内部的中间表示

IR（Intermediate Representation，中间表示）是编译器在「读完各种定义」和「写出 C++/C#/bytes」之间使用的唯一结构。它不是策划提交的文件，也不会进版本库当数据。proto 里的 message、兼容 XML 里的 bean、用注册宏声明的蓝图节点，进编译器后都变成下面这棵树。

```text
SchemaIR
├── Enums      { name, values[{name, alias, value, groupMask}], comment }
├── Beans      { name, fields[], isPolymorphic, variants[], origin }
├── Tables     { fullName, mode, indexKeys[], groupMask, fields[], source, tags[] }
└── Field      { name, type, tag, groupMask, ref, range, default, editorHint, origin }

origin: proto | xml | cpp          // 这条类型从哪来
groupMask: c=1 s=2 e=4 sim=8     // sim 必须同时出现在客户端和服务器产物中
```

### 4.5 类型定义从哪来

| 数据 | 定义源 | 实例源 |
| --- | --- | --- |
| 数值表、掉落、价格 | 手写 proto（或 CDP 兼容 XML），编译进 IR | JSON/YAML 等文本 |
| UE 蓝图、自定义节点图 | **C++ 显式注册**。只抽取标了注册宏的类型，不扫描全部 UFUNCTION。蓝图通配引脚、构造函数里临时改的默认值，以宏声明为准。 | 图实例仍是文本：节点、连线、参数、布局。类型对不上代码时校验失败。 |
| C++ 里的纯数据 USTRUCT | 以代码为准，用同一套抽取生成 IR，供 Excel/JSON 和 bytes 使用。 | JSON/YAML 等文本 |

> **不要把蓝图节点类型再写进 proto。** 蓝图的契约已经在 C++ 里。proto 再写一遍会有两份定义源。Schema 层要做的是：代码变更后重新抽取 IR，用新的 IR 校验已有图实例。

### 4.6 裁剪规则

| 层级 | 表达方式 | 效果 | 典型场景 |
| --- | --- | --- | --- |
| **表级** | `option.groups = ["s"]` | 整表不出现在客户端 bytes/代码 | GM 表、掉落表、内部定价表 |
| **字段级** | `field.groups = ["s"]` | 客户端结构体中该字段被裁掉（生成独立精简类型） | 价格、掉落率、审核状态 |
| **模拟级** | `groups` 含 `sim` | 客户端与服务器 bytes 中该字段都在，且内容相同 | 命中判定、技能时间、随机种子消耗 |
| **记录级** | 行上的 tag | 按 tag 过滤行，例如只进开发包 | 测试道具 |

> **注意：** 字段级裁剪若采用"同一结构体 + 运行时判空"，客户端包体里仍会留下字段语义（可被反推）。本方案要求**为客户端生成独立精简结构体**（`Item_C` / `Item_S`），从物理上隔离，并在 CI 加"敏感字段泄露扫描"。

---

## 5. SSOT 文本与编辑视图

### 5.1 为什么 SSOT 必须是文本

- **Git 友好**：Excel 与 uasset 是二进制，diff/merge/review 全废；文本可 PR、可 blame、可回滚。
- **AI 友好**：LLM 读不了 xlsx 单元格语义，但能精准读写 JSON patch。
- **工具友好**：校验、批量改写、跨表重构（改名）都可用脚本完成。

### 5.2 SSOT 文件组织

```text
config/data/
├── item/
│   ├── TbItem.json            # 表数据（数组）或分片 TbItem.001.json
│   └── TbItem.meta.json       # 可选：表级元信息（分组覆盖、备注、owner）
├── skill/
│   ├── TbSkill.json
│   └── graph/                 # 节点图实例（蓝图式流程，不是三维场景）
│       └── skill.fireball.json
```

**表数据示例（TbItem.json）**

```json
{
  "$schema": "item.TbItem",
  "rows": [
    { "id": 1001, "name": "短弓", "q": "GREEN",
      "price": 100, "dropRate": 0.05, "icon": "UI/Icon/item_1001",
      "bonus": [ { "type": 1, "value": 10 } ] },
    { "id": 1002, "name": "长弓", "q": "BLUE", "price": 300 }
  ]
}
```

- 省略字段 = 使用默认值（compact 编码时也不占空间）。
- 枚举可用名字或值；CI 统一格式化为名字（`cfgc fmt`）。
- 大表支持分片（每片 ≤ N 行），文件级 diff 更友好，也便于多人并行编辑。

### 5.3 视图同步协议（视图 ⇄ SSOT）

```
SSOT 文本 → pull / view-gen → 人在视图里改（Excel / UE Editor） → push / view-sync → diff 评审（PR + CI）
```

| 命令 | 作用 | 说明 |
| --- | --- | --- |
| `cfgc pull` | SSOT → 视图 | 重建 Excel，以及已声明的节点图/复杂原生资产视图；覆盖本地视图前提示未 push 的改动 |
| `cfgc push` | 视图 → SSOT | 导出文本并立即 `check`；失败则拒绝写回 |
| `cfgc sync-status` | 三方比对 | 用 `.sync-state.json`（lastSyncHash）判断脏数据，防覆盖 |
| `cfgc fmt` | 规范化 | 字段顺序、枚举写法、缩进统一，保证 diff 稳定 |

> **冲突策略：** 以 SSOT 为权威。若视图的 lastSyncHash 与当前 SSOT 不一致（说明有人直接改了文本），`push` 要求先 `pull` 并三方合并；Excel 侧提供"按主键合并"而非整表覆盖，避免策划协作互相踩踏。

> **回环测试是这条协议的验收，不是可选项。** 对每一种实际启用的视图都要自动跑「文本 → 视图 → 文本」：普通表生成 Excel；节点图或复杂原生资产才生成 uasset，再由 `push` 导回。对比的是规范化之后的文本：主键、字段值、默认值省略、枚举写法，以及节点图的坐标、注释和连线。允许的差别只有 `fmt` 规定的空白和字段顺序。uasset 的 GUID、缩略图、导入时间不进文本，也不参与对比。丢字段、改数值、重排节点，都算视图实现失败，CI 直接红。

### 5.4 Excel 是临时编辑面

策划可以只用 Excel。工具从文本生成一份临时工作簿，改完再导回文本。提交的仍然是文本，临时 Excel 不作为权威副本。HOOK 的配表就是这样做的。

Excel 适配器只接受约定子集：标量、枚举、引用、点号展开的一层结构体、简单列表。节点图、任意深的多态树、带公式的单元格一律拒绝导入，并报出工作表和单元格。不在子集里的数据继续用文本或节点图编辑器改。

- Sheet 首格以 `##` 开头表示字段行；第二行为类型行，第三行为分组行，第四行起为数据。
- 多级字段用 `.`（如 `bonus.type`），数组用 `[i]` 或 `*` 展开。
- 表登记：新增表必须写入 `__tables__.xlsx` 或 schema 文件，否则不被收集（强制约定，防漏配）。

---

## 6. 代码生成（多语言 / 引擎）

### 6.1 目标矩阵

| 目标 | code target | 产物 | 用途 |
| --- | --- | --- | --- |
| C++ (UE) | `cpp-ue` | `USTRUCT`/`UCLASS` + `FCfg*Table` 访问器 + Blueprint 函数库 | 客户端游戏逻辑、蓝图可读 |
| C++ (Server) | `cpp-svr` | POD struct + 只读访问器（无反射） | 服务器高性能、无 GC |
| C# | `cs-bin` / `cs-dotnet-json` | struct/class + TableMgr + JSON/bin 反序列化 | Unity、工具、服务器（.NET） |
| TypeScript | `ts-bin` / `ts-json` | interface + 加载器 | 小游戏、H5、工具链前端 |
| Python / Go / Rust / Java / Lua / PHP / Dart | `py-json` 等 | 数据类 + 加载器 | 服务器、工具、脚本、GM 后台 |
| 运行时数据 | `protobuf3` | 分端 bytes | 默认线上格式，与 schema 同一套字段号 |
| 引擎专用数据 | 由该引擎适配器决定 | 可选的第二份 bytes | UE、Unity 等已有加载器时再打，不替代 protobuf |
| Verse（前瞻） | `verse-json` | JSON 数据 + 类型声明草案 | UE 6.0 后 Verse 侧消费 |

### 6.2 生成的 UE 结构体（示例）

```cpp
// Gen/Cfg/Item/TbItem.h
USTRUCT(BlueprintType)
struct FCfgItemRow_C : public FTableRowBase   // 继承 FTableRowBase → 可直接塞进 DataTable
{
  GENERATED_BODY()

  UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 Id = 0;
  UPROPERTY(EditAnywhere, BlueprintReadOnly) FString Name;
  UPROPERTY(EditAnywhere, BlueprintReadOnly) ECfgItemQuality Q = ECfgItemQuality::WHITE;
  UPROPERTY(EditAnywhere, BlueprintReadOnly) FSoftObjectPath Icon;  // 资产软引用
  UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FCfgBonus_C> Bonus;
  // 注意：price / dropRate 属于 s 分组，客户端结构体中不存在
};

UCLASS(BlueprintType)
class UCfgItemTable_C : public UObject
{
  GENERATED_BODY()
public:
  FCfgItemRowView_C FindView(int32 Id) const;     // C++：View 自带当前代快照的共享所有权
  bool FindCopy(int32 Id, FCfgItemRow_C& OutValue) const; // Blueprint：返回安全拷贝
};
```

- 生成物带 `// <auto-generated/>` 标记，IDE/编辑器不格式化、不手工改。
- 生成代码同时产出 client/sim 对应的 `CfgSchema.hash` 常量，运行时与目标 bytes 头部逐 target 比对，不匹配直接拒绝加载。

### 6.3 代码生成策略

- **模板化**：自研生成器使用 Scriban（`.sbn`）模板；模板本身纳入版本管理，可项目级覆盖。选择 Scriban 只代表复用通用模板引擎，不引入 Luban 代码。
- **幂等 + 增量**：内容未变则不写盘（避免触发引擎大规模重编）。
- **双份类型**：`_C`（客户端）/ `_S`（服务器）与 `_Shared`；共享类型只在 groupMask 全包含时生成。
- **访问器自动保活代际**：C++ 的 `FindView` 返回持有快照共享所有权的只读 View；Blueprint 使用 `FindCopy` 获取值拷贝。禁止向角色或 UI 暴露可跨代缓存的行裸指针。

---

## 7. 运行时数据与热更新

### 7.1 编码格式

> **默认运行时就是 protobuf 二进制。** Schema 已经是 proto，字段号和各语言解码器都是这一套。`cfgc` 按分组裁剪后生成彼此独立的 client/server Descriptor 与 protobuf bytes；客户端 proto 里没有服务器字段，客户端包里也就没有这些字段。v1 不允许 Schema 热更，每个 target 的 schemaHash 与对应生成代码不一致时都拒绝加载。

- C++、C#、TypeScript、Python、Go 用官方 protobuf 运行时解码。默认路径不再自写解码器，也不再维护第二份 schema。
- 调试和 AI 阅读用 JSON/YAML 等文本，不拿它当线上格式。
- 某个引擎可以再打一份自己的二进制，例如 UE 灌进 DataTable，或该引擎已经在用的 FlatBuffers / 既有 bin。这是适配器的额外产物，从同一份中间表示生成，不替代默认的 protobuf，也不进内核。

### 7.2 工具产出什么

一次 `cfgc gen` 写出分端 bytes 和一份 manifest。client/server 裁剪后的 Descriptor 不同，因此分别记录 schemaHash。sim 产物只规范化生成一次，由发布器把同一个文件交给两端消费，不允许两端各自生成后再赌序列化结果一致。manifest 只描述文件名、消费者、分组、大小、sha256 和各 target 的 schemaHash。谁来下载、按什么比例灰度、打进哪种包，由游戏自己的发布器决定。

```json
{
  "schemaHashes": {
    "client": "c-ab12…",
    "server": "s-cd34…",
    "sim": "sim-ef56…"
  },
  "contentVersion": "2026.09.23-003",
  "files": [
    { "table": "item.TbItem", "group": "c", "consumers": ["client"], "schemaHash": "c-ab12…", "file": "c/item.bytes", "sha256": "…", "size": 184320 },
    { "table": "item.TbItem", "group": "s", "consumers": ["server"], "schemaHash": "s-cd34…", "file": "s/item.bytes", "sha256": "…", "size": 201114 },
    { "table": "item.TbItem", "group": "sim", "consumers": ["client","server"], "schemaHash": "sim-ef56…", "file": "sim/item.bytes", "sha256": "…", "size": 44012 }
  ]
}
```

`sim` 只有一份 canonical 产物。客户端包和服务器包引用同一个 sha256；CI 校验发布清单没有为任一端生成替代文件。

### 7.3 版本

| 字段 | 说明 |
| --- | --- |
| `schemaHashes` | client/server/sim 各自的结构哈希。对应 target 的 bytes 只允许由带有相同哈希的程序加载 |
| `contentVersion` | 数据内容版本。发布器用它决定要不要换文件 |

> **v1 发布边界：** 只有未改变 Schema 的数据内容变更可以热更。新增字段即使在线协议上兼容，也必须重新生成代码、重编并发布程序；删除字段、改类型、改主键或复用字段号同样如此。这样 schemaHash 可以保持严格相等，不在首版引入跨 Schema 兼容矩阵。

### 7.4 热更时指针怎么活

```
① 游戏拿到新 manifest（发布器负责下载）
        ↓
② 校验 sha256（失败就留在旧代）
        ↓
③ 加载为新一代（旧一代继续可读）
        ↓
④ 原子安装新句柄（旧代由引用计数自动保活）
```

- 每一代都是不可变快照。`CfgHandle`、C++ RowView 和异步任务通过 RAII/引用计数共享持有该快照；最后一个持有者离开作用域后自动回收，不提供手工 Release。
- Blueprint 返回值拷贝或安全句柄。游戏逻辑、UI、角色不得缓存行裸指针；只缓存主键时，每次使用都向当前句柄重新查询。
- 安装新代使用原子切换。运行时记录滞留代数和内存，超过预算时告警并拒绝继续叠加新代，避免旧 View 长期持有造成无界增长。
- 对应 target 的 `schemaHash` 不匹配时不切换，并给出文件名、target 和两边的哈希。

### 7.5 运行时 API

```cpp
// 句柄代表一代不可变快照。Install 原子切换当前代；已有句柄/View 自动保活旧代。
CfgHandle next = CfgRuntime.Load(manifestPath, CfgGroup.Client | CfgGroup.Sim);
CfgRuntime.Install(next);
ItemRow item = next.Item.GetCopy(1001);
// next、RowView 和异步任务离开作用域后自动释放引用，无手工 Release。
```

---

## 8. UE 插件集成

插件目前只有 UE，并且只分两块。Runtime 负责 protobuf DTO 的加载、UE View 快照转换和按代更新。Editor 只负责节点图/复杂原生资产与文本的转换，以及依赖 AssetRegistry 的验证；普通数值表继续使用文本/Excel。生成出来的结构体属于 Schema 工具，不是第三块插件。

### 8.1 模块划分

**Schema 生成物（非插件模块）**

- protoc 生成的 protobuf DTO，以及 CDP 生成的 `USTRUCT`/`UCLASS`/`UENUM` View 类型
- 反射注册、蓝图可见类型
- 按 client/sim target 生成的 `CfgSchema.hash` 常量

**ConfigRuntime（Runtime）**

- 官方 protobuf 运行时解码 DTO，再一次性转换为不可变 UE View 快照
- `UCfgSubsystem` 原子保存当前 RAII 句柄
- 异步加载、热重载委托
- `UCfgBlueprintLib` 返回值拷贝或安全 View，不返回跨代裸指针
- 把节点图 bytes 交给现有蓝图或 C++ 逻辑，不自带执行器

**ConfigEditor（Editor）**

- 按需资产类型：`UCfgComplexAsset` / `UCfgGraphAsset`；普通数值表不生成 uasset
- 命令行：`Config.Sync`、`Config.Validate`、`Config.Gen`
- 仅监听已声明的复杂资产/节点图目录，防止普通表产生保存循环
- Detail 面板定制（asset picker、范围滑块、枚举别名）
- Source Control 钩子（submit 前自动导出文本）

> **UE 数据落地路径：** `protobuf bytes → 官方解码得到 DTO → 校验 target schemaHash → 转换为不可变 UE View 快照 → 原子安装到 UCfgSubsystem`。DTO 只服务反序列化，游戏与 Blueprint 只读取 View；转换完成后可按内存策略释放 DTO，避免长期保留两份完整数据。

### 8.2 原生复杂资产/节点图 ⇄ 文本 双向桥

```text
普通数值表：config/data/item/TbItem.json ⇄ 临时 Excel（不生成 uasset）
复杂原生数据：Content/Config/complex/*.uasset ⇄ config/data/complex/*.json
节点图：Content/Config/skill/graph/*.uasset ⇄ config/data/skill/graph/*.json
```

| 操作 | 触发 | 行为 |
| --- | --- | --- |
| **Import** | 已声明的复杂资产/节点图文本变更（watcher）/ 手动 | 文本 → 重建对应 uasset（按稳定 ID 匹配，保留明确列入白名单的引擎侧元数据） |
| **Export** | 复杂资产/节点图保存或提交前 | uasset → 文本（规范化字段顺序 + 校验 + 写 `.sync-state`） |
| **Validate** | 编辑器内 / CI Commandlet | 用 AssetRegistry 验证 UE 资产引用，并跑已启用视图的回环；普通范围/ref 校验仍由 cfgc 完成 |
| **Diff** | 提交前 | uasset 侧展示"文本 diff"，避免二进制盲合 |

### 8.3 与既有 DT + 蓝图工作流的兼容

1. **DT 兼容**：生成的结构体继承 `FTableRowBase`，可以直接当 DataTable 的行结构。把旧 DataTable 转成文本是可选工具，管线本身不依赖这次迁移。
2. **蓝图继续可用**：通过 `UCfgBlueprintLib` 暴露 `GetItem(Id)` 等节点；性能敏感路径走 C++ 直接访问。
3. **复杂组合数据**：多态/嵌套结构生成 `UObject` 派生 + 自定义 Detail（`IDetailCustomization`）+ 可选 `FInstancedStruct` 容器；这些都是"视图"，文本仍是 SSOT。
4. **Verse 前瞻**：额外导出 `*-verse.json`（扁平化 map 结构），供 UE6 Verse 侧直接消费；类型声明待 Verse 生态稳定后补。

### 8.4 UE 侧的打包与热更

- 构建期：bytes 作为 **Non-Asset 附加文件**（或打包进 pak 的 `Config/` 目录），随包发布一版基线。
- 运行期：优先读取可写目录（下载热更），不存在则回落包内基线。
- 编辑器 PIE：直接读 `config/out/bytes`，实现"改配置 → 立即生效"的迭代循环（配合 watcher 自动重编译）。

---

## 9. Unity 与其他宿主

这些不在当前要做的四块里。以后新宿主按同样方式拆：运行时只管加载更新，编辑器只管该宿主资产与文本的转换和验证。

**Unity**

- 生成 C# `struct/class` + `Tables` 管理器；API 风格由 CDP 自己定义并保持向后兼容。
- 视图：`ScriptableObject` 资产 ⇄ JSON 文本，Inspector 自定义绘制。
- 打包：bytes 走 Addressables 或 StreamingAssets；热更走 Addressables catalog + manifest。
- 编辑器窗口：Import / Export / Validate / Reload（Play Mode 热重载）。

**服务器（C++/Go/Rust/Java）**

- 共享同一份 IR，生成服务端类型（含敏感字段）。
- bytes 常驻内存 + mmap；支持 SIGHUP/管理指令触发热重载。
- GM 后台：直接用 `py-json`/`ts-json` 目标读写 SSOT 文本，避免二次建模。

> **一致性原则：** 同一 target 的所有宿主共享同一份 bytes 和对应 schemaHash；client/server 使用各自裁剪后的哈希，sim 共享唯一 canonical 文件及哈希。任何宿主加载失败都先报告 target 与 schemaHash，避免隐性版本不一致。

---

## 10. 节点图（蓝图式流程）

这里的「图」是**节点连线图**，和 UE 蓝图、Buff 流程图是同一类：节点、引脚、连线、参数、注释框坐标。它不是三维场景编辑，也不包含地形、光照、关卡里摆放 Actor。

「图编辑器」是编辑这张节点图的可视化界面。可以是 UE 里的蓝图编辑器或自定义 Slate 图，也可以是 Web 上的节点画布。编辑器改的是图实例，保存时写回文本。

> **节点类型不要再写进 proto。** UE 蓝图的定义源是 C++：节点、引脚和参数类型来自 UCLASS / UFUNCTION。编译器从代码抽取 IR，再用这份 IR 校验图实例。策划配置的是「哪几个节点、怎么连、参数是什么」，不是节点类型本身。纯数据表仍然用手写 proto。

### 10.1 两层定义

```cpp
// 节点类型：只抽取注册宏，不扫描全部 UFUNCTION
CFG_NODE(ApplyDamage)
static void ApplyDamage(float Scale);
```

```json
// 图实例（SSOT 文本）。布局和逻辑都在这里。
{
  "id": "skill.fireball",
  "variables": [ { "name": "damage", "type": "int", "value": 100 } ],
  "nodes": [
    { "uid": 1, "type": "PlayAnim", "params": { "anim": "cast_fire" }, "pos": { "x": 0, "y": 0 } },
    { "uid": 2, "type": "ApplyDamage", "params": { "scale": 1.5 }, "pos": { "x": 240, "y": 0 } },
    { "uid": 3, "type": "Branch", "params": { "cond": "(and (> hp 30) (has-tag \"elite\"))" }, "pos": { "x": 480, "y": 0 } }
  ],
  "edges": [ { "from": "1:Out", "to": "2:In" }, { "from": "2:Out", "to": "3:In" } ]
}
```

### 10.2 表达式：Lisp/DSL → 数据

- 条件与公式统一用 S-表达式书写，**编译期**解析为表达式对象树或字节码（不是运行期解释字符串）。
- 编译期做：语法检查、类型检查、函数白名单、引用字段校验（引用的配置字段必须存在）。
- AI 友好：S-表达式结构明确、可枚举、易生成，非常适合 LLM 产出与静态校验。

### 10.3 图编译流水线

```
图文本（SSOT）
    ↓
结构校验（端口类型 · 环检测 · 必连）
    ↓
子图内联（复用展开）
    ↓
拓扑排序（稳定顺序）
    ↓
扁平化编码（节点数组 + 连接索引 + 常量池）
    ↓
图 bytes（交给现有逻辑读取）
```

### 10.4 编辑器形态（分阶段）

下表都是节点图编辑器，不是三维视口。

| 阶段 | 形态 | 说明 |
| --- | --- | --- |
| P1 | 文本 + 从代码抽出的类型校验 | 先改图实例文本，CI 按 C++ 抽出的节点类型校验 |
| P2 | Web 节点画布 | 直接读写 SSOT 文本，跨引擎复用 |
| P3 | UE 蓝图或自定义节点图 | 复用蓝图编辑器，或用 Slate / 引擎 Graph 控件自绘。资产与文本双向同步，并做回环测试 |

---

## 11. AI 协作层

### 11.1 四要素

- **Knowledge**：Schema 摘要、字段注释、枚举取值、示例行、历史变更、团队约定（命名/数值区间/禁区）。
- **Schema**：机器可读的 JSON Schema / IR dump，供模型精确理解类型与约束。
- **JSON**：SSOT 实例；AI 以 patch 形式产出，天然可 diff、可回滚。
- **Lisp**：条件/公式/图参数的可枚举表达式，编译期强校验。

### 11.2 MCP 工具集

| Tool | 入参 → 出参 | 用途 |
| --- | --- | --- |
| `list_tables` | group? → 表清单（名/注释/行数） | 定位目标表 |
| `get_schema` | table → 字段/类型/约束/枚举/示例 | 精确理解契约 |
| `read_rows` | table + filter/ids → 行数据 | 读取上下文 |
| `search_ref` | value → 引用它的表/字段 | 影响面分析（改名前必查） |
| `validate_patch` | json patch → 结构化错误列表 | AI 自我纠错（`--errorFormat json`） |
| `apply_patch` | patch + dryRun → diff | 落地修改（默认 dryRun） |
| `gen` | targets → 生成结果 | 本地验证生成是否通过 |
| `diff_versions` | v1,v2 → 变更摘要 | 变更说明、changelog 生成 |

### 11.3 AI 工作流与护栏

```
需求（自然语言）
    ↓
检索 Knowledge（相关表 + 示例）
    ↓
产出 JSON patch（不写代码）
    ↓
validate_patch（编译器强校验）
    ↓
PR + 人工 Review（敏感字段需审批）
    ↓
CI 生成 + 冒烟（门禁）
```

> **护栏（硬性）：**
>
> - AI 只能修改 `config/data/**` 的 SSOT 文本，禁止写 `gen/`、`out/` 与 schema（schema 变更需人工评审）。
> - 所有 AI 产出必须过 `cfgc check --strict --errorFormat json`，失败自动回喂给模型重试（最多 N 次）。
> - 敏感字段（价格、掉落率、付费相关）标记 `review:required`，命中则强制人工审批。
> - 审计：每次 AI 改动记录 prompt 摘要 + patch + 校验结果，可回滚到上一个 contentVersion。

---

## 12. 工程流程与 CI/CD

### 12.1 本地与提交门禁

```bash
# 校验（含 ref / range；UE 资产路径使用 Editor 导出的 AssetRegistry 快照）
cfgc check --conf config/cfgc.conf --strict --errorFormat json \
     -x assetRegistrySnapshot=out/asset-registry.json

# 生成（分端）
cfgc gen -t client -c cpp-ue -d bin -x outputCodeDir=Source/Cfg/Gen -x outputDataDir=out/bytes/c
cfgc gen -t server -c cpp-svr -d bin -x outputCodeDir=server/gen  -x outputDataDir=out/bytes/s
```

| 阶段 | 动作 | 失败处理 |
| --- | --- | --- |
| pre-commit | 改动表校验 + `sync-status` 检查（视图未 push 则拒绝提交）+ `fmt` | 阻断提交 |
| CI · validate | `cfgc check --strict` + schema lint（proto 用 buf breaking） | Pipeline 红 |
| CI · gen | 生成全端代码 + 全端 bytes，检查生成物无 diff（幂等） | Pipeline 红 |
| CI · build | 引擎/服务器编译 | Pipeline 红 |
| CI · test | 冒烟：加载全部表、随机抽样反序列化、节点图可执行性、敏感字段泄露扫描、**每种视图的回环测试** | Pipeline 红 |
| CI · publish | 生成 manifest（含 sha256/差量基线）→ 上传 CDN → 打 tag | 回滚上一版 |
| 发布 | 工具写出 manifest。游戏的发布器决定下载和灰度。cfgc 不实现渠道和熔断 | 发布器自己的策略 |

### 12.2 关键质量门禁（建议默认开启）

- **敏感字段泄露扫描**：客户端 bytes 与生成代码中出现 `s` 组字段 → 直接失败。
- **引用完整性**：所有 `ref` 命中（表引用用表全名，路径引用在 `rootDir` 下存在）。
- **数值基线**：关键数值（如总掉落率、经济产出）用回归断言守护，防止误改破坏平衡。

### 12.3 命令速查

| 命令 | 说明 |
| --- | --- |
| `cfgc schema-dump` | 导出 IR/JSON Schema（供 AI 与工具消费） |
| `cfgc pull / push` | SSOT ⇄ 视图同步。CI 用同一对命令做回环测试 |
| `cfgc fmt` | 规范化文本，稳定 diff |
| `cfgc gen` | 生成代码 + 数据（`-t` target / `-c` code / `-d` data） |
| `cfgc check` | 校验（`--strict --errorFormat json`） |
| `cfgc migrate` | 可选。把旧 Excel / 老 DT 转成文本。转不了就重做数据，不阻塞工具本身 |
| `cfgc publish` | 打包 manifest + 差量包 |
| `cfgc mcp` | 启动 MCP Server（`list_tables` 等） |

---

## 13. 落地路线图

当前要做的就是下面四块。M0–M5 只是这四块里的排期编号，不是协议名，也不是额外的模块。

### 13.1 四块模块

| 模块 | 对照 | 做什么 | 不做什么 |
| --- | --- | --- | --- |
| **Schema 工具** | 参考 Luban 等成熟工具的做法，代码完全自研 | proto → 中间表示 → 多语言代码和 protobuf bytes。校验、分组裁剪、临时 Excel 进出、manifest 都在这里。 | 不进游戏进程，不编辑 uasset，不调用模型。 |
| **AI 辅助** | 参考成熟配表 AI 工作流与 HOOK D2C | Knowledge、schema 摘要、对文本打 patch，再用和 CI 相同的校验拦住错误。 | 不改 schema，不直接改 uasset 或 bytes。 |
| **UE Runtime** | 插件运行时 | 加载 protobuf DTO 并转换为不可变 UE View，通过 RAII 句柄原子换代；旧代由现存 View 自动保活。 | 不生成代码，不把 uasset 转成文本。 |
| **UE Editor** | 插件编辑器 | 节点图/复杂原生资产与文本互转，并用 AssetRegistry 做 UE 引用校验和回环；普通表不生成 uasset。 | 不负责运行时加载和热更。 |

> 插件目前只有 UE。Unity、Verse、Web 后台以后再加，新宿主仍按「运行时加载、编辑器转换」拆开，不进这四块。节点图也不单开：抽类型和编译属于 Schema 工具，图资产与文本互转属于 UE Editor，加载属于 UE Runtime。

### 13.2 排期

- **M3**：节点图。Schema 工具从 C++ 抽出节点类型并编译图 bytes；UE Editor 做图资产与文本的转换和验证。
- **M4**：Schema 工具写出 manifest。UE Runtime 按这份清单加载更新。下载、灰度和回滚留在游戏发布器。

Schema 工具先独立跑通「schema → 代码 → 文本 → bytes」。M0 同时完成一个最小 UE 垂直技术探针，证明「protobuf DTO → 不可变 UE View → Blueprint 安全读取」闭环，但不在 M0 建完整 Runtime。旧数据能迁就迁，不能迁就重做，不把迁移当成完成条件。

| 模块 | 里程碑 | 周期 | 交付物 | 验收标准 |
| --- | --- | --- | --- | --- |
| Schema 工具 + UE Runtime 探针 | **M0 规范** | 2 周 | Schema 规范、文本格式、`cfgc check`、一张样例表、最小 UE DTO→View 探针 | 从零走通一张表，生成带独立 schemaHash 的 client/server bytes；UE 可解码并由 Blueprint 安全读取拷贝，不要求迁入旧表 |
| Schema 工具 | **M1 编译器** | 4 周 | 中间表示、C++/C#/TS 代码、protobuf bytes、分组裁剪 | 客户端/服务器两套 bytes 生成成功；C++ 与 C# 可加载并抽样比对 |
| UE Editor | **M2 转换与验证** | 3 周 | 节点图/复杂原生资产 ⇄ 文本、AssetRegistry 校验、回环 | 普通表不生成 uasset；复杂资产或节点图在编辑器保存后导出文本，语义回环通过 |
| UE Runtime | **M2 加载与更新** | 2 周 | protobuf DTO→不可变 UE View、RAII 句柄、原子换代、PIE 里更新 | 换一份同 Schema bytes 后 PIE 读到新一代；旧 View 自动保活旧快照，无裸指针和手工 Release |
| Schema 工具 + UE Editor | **M3 节点图** | 4 周 | 从 C++ 抽节点类型、图 bytes、图资产与文本互转 | 图保存后文本回环通过；节点类型以代码为准 |
| Schema 工具 + UE Runtime | **M4 manifest** | 2 周 | manifest、分端 bytes、唯一 sim canonical 产物；Runtime 按清单更新 | client/server 使用各自 schemaHash，两个包都引用同一 sim 文件与 sha256；下载和灰度不在工具里 |
| AI 辅助 | **M5** | 3 周 | Knowledge、schema 摘要、文本 patch、MCP。校验与 `cfgc check` 相同 | AI 改文本能被校验拦住；通过的 patch 能导回 |

> 顺序是 Schema 工具先能独立出代码和 bytes，再接 UE Editor 和 UE Runtime，AI 放在文本和校验稳定之后。

---

## 14. 风险与决策

### 14.1 关键决策（ADR 摘要）

| 议题 | 备选 | 结论 | 理由 |
| --- | --- | --- | --- |
| Schema 源 | proto / XML / Excel | **proto 为主 + IR 抽象** | 生态成熟、跨语言、可 lint；IR 让 XML/Excel 前端随时可插拔 |
| 运行时编码 | 统一 protobuf / 每引擎各一种 | **默认 protobuf，引擎可再打一份** | schema 和 bytes 共用字段号与官方解码器。UE 将 DTO 转为不可变 View；引擎已有自己的加载器时，适配器从同一份中间表示再打，不进内核 |
| SSOT 形态 | Excel / 文本 | **JSON/YAML 等文本** | Git 与 AI 读写文本。Excel 是普通表视图；uasset 只用于节点图或复杂原生资产 |
| 字段裁剪实现 | 同结构判空 / 双结构 | **双结构（_C / _S）** | 物理隔离敏感字段，可扫描验证 |
| 工具链底座 | 完全自研 / 引用第三方配表内核 | **完全自研** | Luban 等工具只作为公开设计参考，不使用、不引用、不分叉其代码。proto 前端、IR、加载、校验、生成和编码均由 CDP 维护 |
| 图编辑器 | 引擎内蓝图 / Web 节点画布 | **先文本校验，再 Web 节点画布，后 UE 蓝图或自定义节点图** | 都是节点图，不是三维场景编辑。节点类型从 C++ 抽取 |
| AI 边界 | 可改 schema / 仅改数据 | **仅 SSOT 数据，强制校验** | 契约变更需人工评审，避免语义漂移 |

### 14.2 风险与对策

| 风险 | 等级 | 对策 |
| --- | --- | --- |
| 视图与文本回环丢数据 | 高 | 每种视图都做「文本 → 视图 → 文本」回环。语义不一致即失败。按主键合并，禁止整表覆盖 |
| Schema 频繁变更导致兼容地狱 | 中 | 三段版本号 + 兼容规则（附录 A）+ buf breaking 检查 + 破坏性变更走评审 |
| 热更导致客户端/服务器数据不一致 | 高 | client/server/sim 分 target schemaHash 强校验；sim 只生成一个 canonical 文件；manifest 原子提交、失败回滚、灰度观测 |
| 生成代码规模大，编译慢 | 中 | 增量与幂等写盘、按模块拆分、Unity asmdef / UE 模块划分 |
| AI 产出错误配置混入 | 中 | 只改数据 + 强校验 + 敏感字段人工审批 + 审计回滚 |
| 与旧工具并存 | 低 | 工具必须能独立从零生成代码、文本、视图和 bytes。旧数据能转就转；不能转就重做，不双轨硬迁 |

### 14.3 工具要独立完备

验收看工具自己能不能走完这条流水线：定义 schema，生成 C++/C# 等代码，普通表用 Excel 编辑、节点图或复杂原生资产按需用 uasset 编辑，回环到文本，打出 client/server bytes。迁移旧工程是附加能力。迁不动不影响这套工具成立，数据按新格式重做即可。

---

## 15. 附录

### A. bytes 兼容规则

> **v1 不做跨 Schema 热更。** 下表的 protobuf 线协议兼容性只用于评审和迁移判断；任何 Schema 变化都要求重新生成代码、重编并发布程序。只有"仅改数据内容"可以沿用当前程序热更。

| 变更类型 | 兼容级别 | 处理 |
| --- | --- | --- |
| 新增表 | 线协议可兼容 | 仍需重新生成代码、重编并发布；不作为配置热更 |
| 新增 optional 字段 | 线协议可兼容 | 旧 protobuf reader 可跳过未知 tag，但 CDP v1 仍要求重新生成代码、重编并发布 |
| 新增业务必填字段 | Major | proto3 没有普通 required 字段；"必填"是 CDP 自定义校验语义，需数据回填、重编代码并发布 |
| 删除字段 / 改类型 / 改主键 | Major | 强制升级 + 数据回填脚本 |
| 改枚举值（复用旧号） | Major | 禁止；枚举只允许追加 |
| 仅改数据内容 | Patch | 只递增 contentVersion，可热更 |

### B. 推荐仓库布局

```text
repo/
├── config/
│   ├── schema/              # *.proto（或 *.xml），Schema 契约
│   │   ├── options.proto
│   │   └── item/ skill/ ai/ ...
│   ├── data/                # SSOT 文本（权威，入库）
│   │   └── item/TbItem.json ...
│   ├── views/               # 视图（可从文本重建）
│   │   ├── excel/           # 临时工作簿，不作为权威副本
│   │   └── ue/              # 按需与 Content/Config 同步的复杂原生资产、节点图
│   └── cfgc.conf            # CDP 自有配置：groups / targets / schemaFiles / dataDir
├── gen/                     # 生成代码（可按项目策略入库或 ignore）
├── out/
│   ├── bytes/{c,s}/
│   └── manifest/
├── tools/
│   ├── cfgc/                # 独立自研编译器（proto/XML 前端、IR、校验、生成、编码）
│   ├── codegen-templates/   # .sbn 模板
│   ├── ue-plugin/           # ConfigRuntime / ConfigEditor；Schema 类型由 cfgc 生成到 gen/
│   ├── unity-package/
│   └── mcp/                 # MCP Server
└── .githooks/pre-commit     # 校验 + sync-status + fmt
```

### C. 与 Luban 概念映射（仅用于理解和迁移）

本节只说明概念对应，便于有 Luban 使用经验的团队理解或迁移数据；CDP 不调用、不链接、不打包 Luban，也不要求安装 Luban。

| Luban 概念 | 本方案对应 |
| --- | --- |
| `groups`（c/s/e/t） | CDP 自研实现中的表级/字段级 groupMask；只参考分组思想 |
| `targets`（client/server/all） | CDP 自有 target：客户端/服务器/编辑器/测试 |
| `-c` code target | 新增 `cpp-ue` / `cpp-svr` / `verse-json` 等 |
| `-d` data target | 默认 `protobuf3`。json 用于调试。引擎适配器可以再输出该引擎自己的二进制，不替代默认的 protobuf |
| `pathValidator` | 普通文件路径由 cfgc 自研校验器检查；UE 资产引用由 AssetRegistry 快照或 Editor Commandlet 校验。不做多语言文案校验 |
| Excel / json / lua / xml 数据源 | Excel 等是临时编辑视图。权威副本是 JSON/YAML 等文本 |
| `--errorFormat json` | 成为 MCP `validate_patch` 的底层能力 |

### D. 验收 Checklist（上线前）

- 所有表登记在 schema（无"孤岛表"）；新表不登记即 CI 失败。
- `cfgc check --strict` 零错误；`cfgc gen` 幂等无 diff。
- 客户端 bytes 通过敏感字段泄露扫描。
- 全表加载 + 随机抽样反序列化冒烟通过；节点图可执行性校验通过；Excel 与所有实际启用的复杂资产/节点图视图回环通过。
- 热更流程演练：下载 → 校验 → 替换 → 重载 → 失败回滚，全部可观测。
- AI 改动链路演练：patch → validate → PR → CI → 发布 → 可回滚。

---

文档版本 v1.5 · 方案代号 CDP · 2026-09 · 本文档由自包含单页 HTML 转换为 Markdown，无外部网络资源依赖。
