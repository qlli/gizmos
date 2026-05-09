# ZhihuReader - 知乎高质量内容阅读器

> 专为高知识水平技术人员设计的知乎内容筛选与管理工具

## 项目概述

ZhihuReader 是一款智能知乎内容阅读器，旨在从海量知乎内容中筛选高质量、有价值的信息，帮助用户高效获取知识。

### 核心特性

- **存量与增量分离**：区分历史积累内容和实时新增内容
- **多阶段流水线处理**：搜集 → 分析 → 扩展 → 汇总
- **AI辅助分析**：调用大模型进行深度内容分析
- **预算控制**：设置每日Token消耗上限（默认20$/天）
- **智能过滤**：剔除低质量、广告、AI生成内容
- **个性化适配**：基于用户背景（游戏/AI/3D技术领域）优化推荐

## 爬虫执行步骤与日志排查

完整流程从启动到正确抓取知乎文章正文，分为 8 个步骤。每个步骤的关键日志都带有 `[STEP X/8]` 前缀，便于快速定位失败位置。

| 步骤 | 名称 | 关键模块 | 关键日志 | 失败常见原因 |
|------|------|----------|----------|--------------|
| 1 | 启动 Playwright + 浏览器 | `src/crawler/zhihu_client.py: _start_browser` | `[STEP 1/8] 启动 Playwright + 浏览器` / `[STEP 1/8] 浏览器已启动` | Playwright 未安装、Chromium 未下载（运行 `python -m playwright install chromium`） |
| 2 | 验证知乎登录状态 | `src/crawler/zhihu_client.py: ensure_logged_in` | `[STEP 2/8] 访问 .../hot 检查登录状态` / `[STEP 2/8] 已登录` | Cookie 失效，需删除 `data/browser_data/` 后重新执行 `python first_run.py` |
| 3 | 调用知乎搜索/热门接口 | `src/crawler/zhihu_client.py: _request / get_hot_content` | `[STEP 3/8] 发起知乎接口请求` / `[STEP 3/8] 知乎请求完成: status=200, data_count=...` | 接口 401/403、被反爬拦截、当前页面不在知乎域名 |
| 4 | 解析并过滤元数据 | `src/crawler/article_collector.py: collect_hot_feed` | `[STEP 4/8] 知乎热门接口返回原始条目: ...` / `[STEP 4/8] 解析完成: 原始 X, 过滤 Y, 保留 Z` | `min_upvote` 等过滤条件过严、`object` 字段嵌套结构变化 |
| 5 | 保存原始 JSON | `src/pipeline/collector.py: save_for_processing` | `[STEP 5/8] 搜集结果已保存: data/raw/stock/collected_*.json` | 没有可保存数据（上一步过滤掉了所有结果） |
| 6 | 抓取文章正文 | `src/crawler/zhihu_client.py: get_article_content` + `src/pipeline/analyzer.py: fetch_content` | `[STEP 6/8] 打开文章页面抓取正文` / `[STEP 6/8] 文章正文获取成功: selector=..., len=...` | 浏览器未初始化、URL 缺失、登录态过期、页面结构变更 |
| 7 | 质量过滤 + AI 分析 | `src/pipeline/analyzer.py: analyze_article` | `[STEP 7/8] 分析文章` / `[STEP 7/8] AI分析成功` 或 `[STEP 7/8] 跳过AI分析` | OpenAI Key 未配置（`config/setting.json` 里仍是 `YOUR_OPENAI_API_KEY`）、预算耗尽 |
| 8 | 归档到 Excel | `src/pipeline/archiver.py: archive_articles` + `src/storage/excel_storage.py: save_articles` | `[STEP 8/8] 筛选出 N 篇高质量文章` / `[STEP 8/8] Excel 写入完成: data/archive/articles.xlsx` | 高质量文章数量为 0（质量评分未达 `min_quality`）、`articles.xlsx` 被 Excel 锁定 |

### 排查思路

按编号顺序检查日志：

1. 找不到 `[STEP 1/8] 浏览器已启动` → Playwright 安装问题
2. `[STEP 2/8] 检测到登录按钮` → 删除 `data/browser_data/` 重新登录
3. `[STEP 3/8] status=401/403` 或 `知乎请求完成: data_count=0` → 登录态失效或被反爬
4. `[STEP 4/8] 保留 0` → 调低 `config/setting.json` 中 `crawler.filters.min_upvote` 等阈值
5. 找不到 `[STEP 5/8] 搜集结果已保存` → 上一步没有数据
6. 找不到 `[STEP 6/8] 文章正文获取成功` → 检查文章 URL 和登录态
7. `[STEP 7/8] 跳过AI分析` → 配置 OpenAI Key（可选，跳过时使用基础规则）
8. `[STEP 8/8] 没有符合归档条件的高质量文章` → 调低 `min_quality` 或配置 AI

### 数据落点

| 数据类型 | 路径 |
|----------|------|
| Cookie / 浏览器数据 | `data/browser_data/` |
| 原始抓取结果 | `data/raw/stock/` 或 `data/raw/incremental/` |
| 文章正文缓存 | `data/processed/contents/` |
| 分析后的文章 | `data/processed/analyzed_*.json` |
| 最终归档 | `data/archive/articles.xlsx` |
| 运行日志 | `logs/zhihu_reader.log` |

## 项目结构

```
ZhihuReader/
├── config/                    # 配置目录
│   └── setting.json           # 主配置文件
├── doc/                       # 文档目录
│   └── readme.md              # 本文档
├── data/                      # 数据目录
│   ├── raw/                   # 原始抓取数据
│   │   ├── stock/             # 存量内容
│   │   └── incremental/       # 增量内容
│   ├── processed/              # 处理后数据
│   │   ├── high_quality/      # 高质量内容存档
│   │   └── filtered/          # 已过滤内容
│   └── archive/               # 最终存档
│       └── articles.xlsx      # 存档Excel
├── src/                       # 源代码目录
│   ├── __init__.py
│   ├── crawler/               # 爬虫模块
│   │   ├── __init__.py
│   │   ├── zhihu_client.py    # 知乎API客户端
│   │   ├── article_collector.py # 文章搜集器
│   │   └── filters.py         # 过滤器
│   ├── pipeline/              # 流水线模块
│   │   ├── __init__.py
│   │   ├── collector.py       # 搜集阶段
│   │   ├── analyzer.py        # 分析阶段
│   │   ├── expander.py        # 扩展阶段
│   │   └── archiver.py        # 汇总阶段
│   ├── ai/                    # AI分析模块
│   │   ├── __init__.py
│   │   ├── openai_client.py    # OpenAI客户端
│   │   ├── local_llm.py       # 本地LLM支持
│   │   └── budget_controller.py # 预算控制器
│   ├── storage/               # 存储模块
│   │   ├── __init__.py
│   │   ├── excel_storage.py   # Excel存储
│   │   └── json_storage.py    # JSON存储
│   └── utils/                 # 工具模块
│       ├── __init__.py
│       ├── logger.py          # 日志工具
│       └── config.py          # 配置加载
├── scripts/                   # 脚本目录
│   ├── run_stock.sh           # 运行存量内容抓取
│   └── run_incremental.sh     # 运行增量内容抓取
├── logs/                      # 日志目录
├── requirements.txt           # Python依赖
├── main.py                    # 主入口
└── README.md                  # 项目说明
```

## 核心设计

### 1. 存量与增量分离

- **分界线**：用户首次运行时选择，作为存量和增量的分界时间
- **存量内容**：分界线之前的内容，重点深度分析和精选存档
- **增量内容**：分界线之后的内容，快速浏览和时效性处理

### 2. 四阶段流水线

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   搜集阶段   │ -> │   分析阶段   │ -> │   扩展阶段   │ -> │   汇总阶段   │
│ Collection  │    │  Analysis   │    │  Expansion  │    │  Archiving  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

#### 阶段一：搜集阶段 (Collector)
- 抓取文章URL、标题、作者、点赞数、回答数等元信息
- 初步过滤：低赞、低回答、黑名单用户
- 快速大量抓取

#### 阶段二：分析阶段 (Analyzer)
- 读取文章完整内容
- 调用AI进行深度分析
- 判断内容质量，提取摘要
- **每日Token预算控制**（默认20$上限）

#### 阶段三：扩展阶段 (Expander)
- 抓取同一作者的其他回答
- 抓取同一问题的其他答案
- 抓取同一提问者的其他提问
- 优先级低于分析阶段

#### 阶段四：汇总阶段 (Archiver)
- 汇总高质量内容
- 提供反馈评价（1-5星）
- 存档到Excel

### 3. 幂律分布处理

指标按幂律分布划分档次：
- 点赞数：1-10, 10-100, 100-1000, 1000+
- 回答数：1-5, 5-20, 20-100, 100+
- 字符数：100-500, 500-2000, 2000-5000, 5000+

### 4. 内容过滤规则

**剔除低质量内容：**
- 广告嫌疑（美容、护肤、壮阳、丰满等）
- 色情内容
- 机械拼凑内容
- 疑似AI生成内容
- 纯营销推广内容

**高质量内容特征：**
- 特定领域深入见解
- 独家消息渠道
- 与技术领域高度相关
- 专业分析和论证

### 5. 用户画像

基于用户背景优化筛选：
- 高学历、高知识水平
- 腾讯游戏中台研发工程师
- 兴趣领域：游戏开发、数字人、VR、Unity/Unreal、3D图形、AI、计算机

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config/setting.json` 文件，设置：
- 知乎登录Cookie
- AI API密钥
- Token预算
- 黑名单用户
- 关键词过滤

### 运行

```bash
# 运行主程序
python main.py

# 使用采集运行配置（按关键词抓取）
python main.py --config tech

# 使用指定路径的采集运行配置
python main.py --config config/collections/tech.json

# 只采集配置里的关键词，不做分析和归档
python main.py --collect --config tech

# 命令行 --keywords 优先级高于配置里的 keywords
python main.py --keywords Unity Unreal

# 命令行 --hot 优先级高于配置里的 keywords
python main.py --hot --config tech

# 仅抓取存量内容
./scripts/run_stock.sh

# 仅抓取增量内容
./scripts/run_incremental.sh
```

### 采集运行配置

采集运行配置是独立 JSON 文件，用于描述一次爬虫任务。当前仅使用 `keywords` 字段，后续可以继续扩展其他字段。

默认配置目录：

```text
config/collections/
```

示例：`config/collections/tech.json`

```json
{
  "name": "tech",
  "description": "技术方向内容采集配置示例。当前仅使用 keywords 字段，后续可扩展更多字段。",
  "keywords": [
    "游戏开发",
    "Unity",
    "Unreal",
    "游戏引擎",
    "计算机图形学",
    "AI人工智能"
  ]
}
```

启动时可以传配置名或路径：

```bash
python main.py --config tech
python main.py --config config/collections/tech.json
python main.py --run-config tech
python main.py --collection-config tech
```

配置解析规则：

1. 如果传入绝对/相对路径且文件存在，直接使用该文件。
2. 如果传入名称，例如 `tech`，会尝试查找 `config/collections/tech.json`。
3. 配置中的 `keywords` 会在未指定 `--hot` 和未指定 `--keywords` 时自动作为关键词采集条件。
4. 命令行 `--keywords` 和 `--hot` 优先级高于配置文件。

## 配置说明

详见 `config/setting.json` 配置文件。

## 开发计划

- [x] 项目结构设计
- [x] 核心模块框架
- [ ] 知乎API客户端实现
- [ ] 爬虫模块实现
- [ ] AI分析模块实现
- [ ] 预算控制器实现
- [ ] Excel存档模块实现
- [ ] 完整流水线集成

## 许可证

MIT License
