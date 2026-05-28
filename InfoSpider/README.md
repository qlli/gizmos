# InfoSpider - 智能信息采集系统

> 像智能文秘一样，深度了解你的喜好和目标，按需搜集和筛选信息。

## 快速开始

### 1. 安装依赖

```bash
cd InfoSpider
pip install -r requirements.txt
playwright install chromium
```

### 2. 初始化用户画像

```bash
python cli.py init-profile --user default --profession "游戏开发工程师" \
    -i "游戏开发" -i "AI" -i "Unreal" -i "图形学"
```

### 3. 采集信息

```bash
# B站热门视频
python cli.py collect -s bilibili --trending --limit 30

# B站关键词搜索
python cli.py collect -s bilibili -k "游戏开发" -k "Unreal" --limit 20

# 知乎搜索（需要先登录）
python cli.py collect -s zhihu -k "游戏引擎" --limit 20

# GitHub 仓库搜索
python cli.py collect -s github -k "unreal engine" --limit 20

# GitHub 近期高星仓库（趋势近似）
python cli.py collect -s github --trending --limit 20

# 多源同时采集
python cli.py collect -s bilibili -s zhihu -s github -k "AI" --limit 30

```

### 4. 查看可用信息源

```bash
python cli.py sources
```

### 5. 管理兴趣标签

```bash
# 查看画像
python cli.py profile

# 添加兴趣
python cli.py profile --add "深度学习:0.8"

# 移除兴趣
python cli.py profile --remove "某标签"
```

## 项目结构

```
InfoSpider/
├── cli.py                  # CLI 入口
├── config/
│   ├── default.yaml        # 全局配置
│   └── sources/            # 各信息源配置
│       ├── zhihu.yaml
│       └── bilibili.yaml
├── src/
│   ├── core/
│   │   ├── crawler/        # 爬虫引擎
│   │   │   ├── base.py     # BaseCrawler 抽象接口
│   │   │   ├── registry.py # 爬虫注册中心
│   │   │   ├── zhihu.py    # 知乎爬虫
│   │   │   └── bilibili.py # B站爬虫
│   │   ├── matcher/        # 匹配引擎
│   │   │   ├── base.py     # BaseMatcher 抽象接口
│   │   │   └── keyword.py  # 关键字匹配器
│   │   └── pipeline/       # 流水线
│   │       ├── base.py     # 阶段基类
│   │       └── collector.py# 采集阶段
│   ├── models/             # 数据模型
│   │   ├── user.py         # 用户画像
│   │   └── task.py         # 采集任务
│   ├── storage/            # 存储
│   │   ├── json_storage.py # JSON 持久化
│   │   └── html_report.py  # HTML 报告
│   └── utils/              # 工具
│       ├── config.py       # 配置管理
│       └── logger.py       # 日志
├── data/                   # 运行时数据（.gitignore）
├── doc/
│   └── design.md           # 设计文档
└── requirements.txt
```

## 架构概述

### 爬虫插件化

新增信息源只需：

1. 实现 `BaseCrawler` 接口
2. 用 `@CrawlerRegistry.register("name")` 注册
3. 添加 `config/sources/name.yaml`

```python
from src.core.crawler.base import BaseCrawler, CrawlItem
from src.core.crawler.registry import CrawlerRegistry

@CrawlerRegistry.register("my_source")
class MyCrawler(BaseCrawler):
    source_name = "my_source"
    source_type = "feed"
    
    async def initialize(self): ...
    async def close(self): ...
    async def search(self, keyword, limit=20, **filters): ...
    async def get_trending(self, category="", limit=20): ...
    async def get_content(self, item): ...
```

### 三层匹配过滤

1. **硬过滤**: 黑名单关键词/作者/垃圾内容
2. **质量评分**: 基于互动数据的幂律分档 (0-0.5)
3. **兴趣匹配**: 用户画像标签命中评分 (0-0.5)

综合分 ≥ 0.3 通过。

### 数据流

```
CLI命令 → 加载配置 → CollectorStage
  → CrawlerRegistry 获取爬虫
  → 爬虫执行 search/trending → AsyncIterator[CrawlItem]
  → KeywordMatcher 过滤评分
  → 保存 JSON + 生成 HTML 报告
```

## 配置

### 全局配置 (config/default.yaml)

日志级别、存储路径、AI 设置（Phase 2+）等。

### 源配置 (config/sources/*.yaml)

每个信息源独立配置：速率限制、搜索参数、过滤阈值。

## 路线图

- [x] Phase 1: 核心引擎 (爬虫插件/匹配/CLI)
- [ ] Phase 2: 多源扩展 (GitHub/YouTube/论文) + 语义匹配
- [ ] Phase 3: 后端服务化 (FastAPI + Web前端)
- [ ] Phase 4: 多云部署 + 推荐系统
- [ ] Phase 5: 移动端 + 高级推荐
