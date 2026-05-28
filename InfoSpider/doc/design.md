# InfoSpider - 智能信息采集系统设计文档

> 版本: v0.1 | 更新: 2026-05-28
> 定位: 像智能文秘一样，深度了解用户喜好和目标，按需搜集和筛选信息

---

## 1. 项目愿景

InfoSpider 是从 ZhihuReader 演进而来的新一代智能信息采集系统。核心升级方向：

| 维度 | ZhihuReader（现状） | InfoSpider（目标） |
|------|---------------------|---------------------|
| 信息源 | 仅知乎 | 知乎 / B站 / YouTube / GitHub / 会议论文 / 可扩展 |
| 前端 | CLI 命令行 | Web / 小程序 / 手机App / CLI |
| 匹配策略 | 关键字 + 三层规则过滤 | 关键字 → 语义匹配 → 推荐系统 |
| 用户模型 | 单用户硬编码画像 | 多用户独立画像，持续学习 |
| 后端部署 | 本地运行 | 多云部署（腾讯云/阿里云），支持私有化 |
| 数据存储 | 本地JSON/Excel | 远端数据库 + 本地缓存 |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌──────────────────────────────────────────────────────────┐
│                      客户端层 (Clients)                    │
│  ┌────────┐  ┌──────────┐  ┌────────┐  ┌──────────────┐ │
│  │ Web App│  │ 小程序    │  │ 手机App│  │ CLI (开发调试)│ │
│  └───┬────┘  └────┬─────┘  └───┬────┘  └──────┬───────┘ │
│      └─────────────┴────────────┴──────────────┘         │
│                        │ REST API / WebSocket             │
├────────────────────────┼─────────────────────────────────┤
│                    API 网关层                              │
│  ┌────────────────────┴────────────────────────────┐     │
│  │  API Gateway (认证/鉴权/限流/路由)               │     │
│  └────────────────────┬────────────────────────────┘     │
├────────────────────────┼─────────────────────────────────┤
│                   业务服务层 (Services)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │采集服务   │ │匹配服务   │ │用户服务   │ │通知服务    │  │
│  │Collector │ │Matcher   │ │User      │ │Notifier   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       │             │            │              │         │
├───────┴─────────────┴────────────┴──────────────┴─────────┤
│                   核心引擎层 (Core)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │爬虫引擎   │ │AI引擎    │ │推荐引擎   │ │调度引擎    │  │
│  │Crawler   │ │AI Engine │ │Recommender│ │Scheduler  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
├───────────────────────────────────────────────────────────┤
│                   数据层 (Data)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │用户数据库 │ │内容数据库 │ │向量数据库 │ │对象存储    │  │
│  │PostgreSQL│ │PostgreSQL│ │Milvus/   │ │COS/OSS    │  │
│  │          │ │          │ │ChromaDB  │ │           │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
├───────────────────────────────────────────────────────────┤
│                   基础设施层 (Infra)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  腾讯云       │  │  阿里云       │  │  本地开发环境  │  │
│  │  CVM/COS/TDSQL│  │  ECS/OSS/RDS │  │  Docker      │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### 2.2 分层职责

| 层次 | 职责 | 关键设计原则 |
|------|------|-------------|
| 客户端层 | 用户交互、配置管理、结果展示 | 薄客户端，逻辑下沉服务层 |
| API网关层 | 认证鉴权、限流、路由分发 | 统一入口，协议无关 |
| 业务服务层 | 采集/匹配/用户/通知等业务逻辑 | 微服务化，独立部署 |
| 核心引擎层 | 爬虫/AI/推荐/调度等核心能力 | 插件化，可扩展 |
| 数据层 | 持久化存储、向量检索 | 读写分离，缓存加速 |
| 基础设施层 | 云资源、容器、CI/CD | 多云抽象，一键部署 |

---

## 3. 核心模块设计

### 3.1 爬虫引擎（Crawler Engine）

#### 3.1.1 统一爬虫接口

从 ZhihuReader 的 `ZhihuClient` 抽象出通用接口：

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass

@dataclass
class CrawlItem:
    """统一爬取结果数据结构"""
    source: str           # 来源平台: zhihu/bilibili/youtube/github/paper
    item_type: str        # 类型: article/answer/video/repo/paper
    title: str
    url: str
    author: str
    content: str = ""     # 正文/描述
    metadata: dict = None # 平台特有字段
    voteup: int = 0       # 统一的互动指标
    comment_count: int = 0
    published_at: str = ""
    crawled_at: str = ""

class BaseCrawler(ABC):
    """爬虫基类 - 所有平台爬虫必须实现此接口"""
    
    source_name: str      # 平台标识
    source_type: str      # feed/video/code/academic
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """认证/登录"""
    
    @abstractmethod
    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """按关键词搜索"""
    
    @abstractmethod
    async def get_trending(self, category: str = "", limit: int = 20) -> AsyncIterator[CrawlItem]:
        """获取热门/趋势内容"""
    
    @abstractmethod
    async def get_content(self, item: CrawlItem) -> str:
        """获取完整内容"""
    
    @abstractmethod
    async def get_item_url(self, item: CrawlItem) -> str:
        """生成可访问的正确URL"""
```

#### 3.1.2 各平台爬虫设计

| 平台 | 实现策略 | 反爬方案 | 数据获取方式 | 优先级 |
|------|---------|---------|-------------|--------|
| **知乎** | 移植ZhihuReader | Playwright+Stealth | search_v3 API + 页面渲染 | P0 |
| **B站** | BilibiliClient | Playwright+Cookie | search API + wbi签名 | P1 |
| **YouTube** | YouTubeClient | yt-dlp + API Key | Data API v3 / 页面抓取 | P1 |
| **GitHub** | GitHubClient | Token认证 | REST API v3 / GraphQL | P2 |
| **会议论文** | PaperClient | DBLP/SemanticScholar API | REST API | P2 |

#### 3.1.3 爬虫注册与发现

```python
class CrawlerRegistry:
    """爬虫注册中心 - 插件化加载"""
    
    _crawlers: Dict[str, Type[BaseCrawler]] = {}
    
    @classmethod
    def register(cls, source_name: str):
        """装饰器：注册爬虫"""
        def wrapper(crawler_cls):
            cls._crawlers[source_name] = crawler_cls
            return crawler_cls
        return wrapper
    
    @classmethod
    def get_crawler(cls, source_name: str, config: dict) -> BaseCrawler:
        """获取爬虫实例"""
        crawler_cls = cls._crawlers.get(source_name)
        if not crawler_cls:
            raise ValueError(f"未注册的爬虫: {source_name}")
        return crawler_cls(config)
    
    @classmethod
    def list_sources(cls) -> List[str]:
        """列出所有已注册的爬虫"""
        return list(cls._crawlers.keys())
```

### 3.2 匹配引擎（Matcher Engine）

#### 3.2.1 三级匹配策略

```
Level 1: 关键字匹配（MVP，立即可用）
    ↓
Level 2: 语义匹配（向量检索，中期目标）
    ↓  
Level 3: 推荐系统（协同过滤+深度学习，远期目标）
```

#### 3.2.2 Level 1 - 关键字匹配

从 ZhihuReader 的三层过滤器链演化：

```python
class KeywordMatcher:
    """关键字匹配器 - 沿用ZhihuReader三层过滤架构"""
    
    def match(self, item: CrawlItem, user_profile: UserProfile) -> MatchResult:
        # 第一层：硬过滤（黑名单/最低赞/垃圾词）
        # 第二层：质量评分（幂律分档 + 内容质量检测）
        # 第三层：兴趣匹配（关键词命中 + 偏好权重）
```

#### 3.2.3 Level 2 - 语义匹配

```python
class SemanticMatcher:
    """语义匹配器 - 基于向量检索"""
    
    def __init__(self, vector_store: VectorStore, embedder: Embedder):
        self.vector_store = vector_store  # ChromaDB / Milvus
        self.embedder = embedder          # text2vec / OpenAI embedding
    
    async def match(self, item: CrawlItem, user_profile: UserProfile) -> MatchResult:
        # 1. 将 item 内容向量化
        # 2. 与用户兴趣向量做相似度检索
        # 3. 与用户历史阅读向量做相似度检索（排除已读）
        # 4. 综合评分
```

#### 3.2.4 Level 3 - 推荐系统

```python
class RecommendationEngine:
    """推荐引擎 - 个性化推荐"""
    
    async def recommend(self, user_id: str, candidates: List[CrawlItem]) -> List[RankedItem]:
        # 协同过滤：相似用户的阅读偏好
        # 内容推荐：基于用户画像的深度匹配
        # 时序推荐：考虑信息时效性和用户活跃时段
        # 多样性控制：避免信息茧房
```

### 3.3 用户画像系统（User Profile）

#### 3.3.1 数据模型

```python
@dataclass
class UserProfile:
    """用户画像 - 核心数据结构"""
    user_id: str
    basic_info: BasicInfo           # 基础信息（职业/学历/年龄段）
    interests: InterestGraph        # 兴趣图谱（标签+权重+关联）
    reading_history: ReadingHistory # 阅读历史（点击/停留/收藏/跳过）
    content_prefs: ContentPrefs     # 内容偏好（深度/长度/类型/语言）
    source_prefs: SourcePrefs       # 来源偏好（平台权重/信任度）
    feedback: FeedbackLog           # 反馈记录（点赞/踩/屏蔽/纠正）
    
@dataclass
class InterestGraph:
    """兴趣图谱"""
    tags: Dict[str, float]          # 标签 → 权重 (0-1)
    tag_relations: Dict[str, List[str]]  # 标签关联（游戏开发 → Unreal → 渲染）
    update_time: str
    
    def add_interest(self, tag: str, weight: float = 0.5):
        """添加/更新兴趣标签"""
    
    def decay(self, days: int = 7):
        """兴趣衰减 - 长期不互动的兴趣逐渐降低权重"""
    
    def boost_from_feedback(self, tag: str, action: str):
        """根据用户反馈调整权重"""
```

#### 3.3.2 画像更新机制

```
用户行为 → 事件采集 → 画像更新
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
 显式反馈             隐式反馈             时效衰减
 (点赞/收藏/屏蔽)   (点击/停留时长/    (兴趣权重随时间
                     跳过/分享)          自然衰减)
```

### 3.4 调度引擎（Scheduler）

```python
class Scheduler:
    """任务调度引擎"""
    
    async def schedule(self, user_id: str, task: CrawlTask) -> ScheduleResult:
        """调度采集任务"""
        # 1. 解析任务需求（关键词/来源/数量/时间范围）
        # 2. 分配爬虫实例
        # 3. 控制并发和频率
        # 4. 合并去重
        # 5. 触发匹配引擎
    
    async def periodic_scan(self, user_id: str):
        """定期扫描 - 根据用户画像自动生成采集任务"""
        # 基于用户兴趣图谱，定期搜索新内容
        # 基于历史阅读模式，推荐最佳推送时段
```

### 3.5 通知服务（Notifier）

```python
class BaseNotifier(ABC):
    """通知基类"""
    @abstractmethod
    async def send(self, user_id: str, items: List[RankedItem]) -> bool:

class EmailNotifier(BaseNotifier): ...      # 邮件推送
class WechatNotifier(BaseNotifier): ...     # 微信推送（服务号/模板消息）
class WebhookNotifier(BaseNotifier): ...    # Webhook回调
class AppNotifier(BaseNotifier): ...        # App推送
```

---

## 4. 数据库设计

### 4.1 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    user_id     VARCHAR(36) PRIMARY KEY,
    username    VARCHAR(64) UNIQUE NOT NULL,
    email       VARCHAR(128),
    password_hash VARCHAR(256),
    created_at  TIMESTAMP DEFAULT NOW(),
    settings    JSONB          -- 用户个性化设置
);

-- 用户画像表
CREATE TABLE user_profiles (
    user_id     VARCHAR(36) PRIMARY KEY REFERENCES users(user_id),
    basic_info  JSONB,         -- 基础信息
    interests   JSONB,         -- 兴趣图谱
    content_prefs JSONB,       -- 内容偏好
    source_prefs JSONB,        -- 来源偏好
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- 采集源配置表
CREATE TABLE source_configs (
    config_id   SERIAL PRIMARY KEY,
    user_id     VARCHAR(36) REFERENCES users(user_id),
    source_name VARCHAR(32) NOT NULL,  -- zhihu/bilibili/youtube/github/paper
    config      JSONB NOT NULL,         -- 平台特有配置（关键词/过滤/频率）
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 采集结果表
CREATE TABLE crawl_items (
    item_id     VARCHAR(64) PRIMARY KEY,  -- source:type:platform_id
    source      VARCHAR(32) NOT NULL,
    item_type   VARCHAR(32) NOT NULL,
    title       TEXT,
    url         TEXT NOT NULL,
    author      VARCHAR(128),
    content     TEXT,
    metadata    JSONB,
    voteup      INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    crawled_at  TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_crawl_source ON crawl_items(source);
CREATE INDEX idx_crawl_voteup ON crawl_items(voteup);

-- 用户-内容交互表
CREATE TABLE user_interactions (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(36) REFERENCES users(user_id),
    item_id     VARCHAR(64) REFERENCES crawl_items(item_id),
    action      VARCHAR(16) NOT NULL,  -- view/like/dislike/save/skip/share
    duration    INTEGER,               -- 阅读时长（秒）
    created_at  TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_interaction_user ON user_interactions(user_id);

-- 用户采集任务表
CREATE TABLE crawl_tasks (
    task_id     VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(36) REFERENCES users(user_id),
    task_type   VARCHAR(32),           -- search/trending/periodic
    source      VARCHAR(32),
    params      JSONB,
    status      VARCHAR(16) DEFAULT 'pending',  -- pending/running/completed/failed
    result_count INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    started_at  TIMESTAMP,
    completed_at TIMESTAMP
);

-- 向量索引（配合向量数据库）
-- 内容向量存储在 ChromaDB/Milvus 中，以 item_id 为 key
-- 用户兴趣向量存储在 ChromaDB/Milvus 中，以 user_id 为 key
```

### 4.2 数据库选型

| 用途 | 方案 | 理由 |
|------|------|------|
| 关系数据 | PostgreSQL (TDSQL/RDS) | JSONB支持、成熟稳定、多云可用 |
| 向量检索 | ChromaDB (轻量) / Milvus (生产) | 语义匹配、相似度检索 |
| 缓存 | Redis | 热点数据、限流计数、会话管理 |
| 对象存储 | COS(腾讯云) / OSS(阿里云) | 文章正文缓存、HTML报告、附件 |

---

## 5. API 设计

### 5.1 RESTful API 概览

```
# 认证
POST   /api/v1/auth/register          # 注册
POST   /api/v1/auth/login             # 登录
POST   /api/v1/auth/token/refresh     # 刷新Token

# 用户画像
GET    /api/v1/profile/{user_id}      # 获取画像
PUT    /api/v1/profile/{user_id}      # 更新画像
GET    /api/v1/profile/{user_id}/interests  # 获取兴趣标签
POST   /api/v1/profile/{user_id}/interests  # 添加兴趣标签

# 采集任务
POST   /api/v1/tasks                  # 创建采集任务
GET    /api/v1/tasks/{task_id}        # 查询任务状态
GET    /api/v1/tasks                  # 列出用户任务
DELETE /api/v1/tasks/{task_id}        # 取消任务

# 采集结果
GET    /api/v1/items                  # 获取推荐内容列表
GET    /api/v1/items/{item_id}        # 获取内容详情
POST   /api/v1/items/{item_id}/action # 用户交互（like/save/skip）

# 采集源
GET    /api/v1/sources                # 列出可用采集源
GET    /api/v1/sources/{source}/config  # 获取源配置
PUT    /api/v1/sources/{source}/config  # 更新源配置

# 报告
GET    /api/v1/reports/daily          # 日报
GET    /api/v1/reports/weekly         # 周报
```

### 5.2 WebSocket 接口

```
WS /api/v1/ws/tasks/{task_id}         # 实时采集进度
WS /api/v1/ws/notifications           # 实时通知推送
```

---

## 6. 多云部署设计

### 6.1 部署架构

```
┌─────────────────────────────────────────────────┐
│                  负载均衡 / DNS                    │
│            (Cloudflare / 腾讯云DNSPOD)            │
└──────────────┬──────────────────┬────────────────┘
               │                  │
    ┌──────────▼──────┐  ┌───────▼──────────┐
    │   腾讯云 CVM     │  │   阿里云 ECS      │
    │                  │  │                  │
    │ ┌──────────────┐│  │ ┌──────────────┐ │
    │ │ API Gateway  ││  │ │ API Gateway  │ │
    │ │ Collector    ││  │ │ Collector    │ │
    │ │ Matcher      ││  │ │ Matcher      │ │
    │ │ Scheduler    ││  │ │ Scheduler    │ │
    │ └──────────────┘│  │ └──────────────┘ │
    │                  │  │                  │
    │ ┌──────────────┐│  │ ┌──────────────┐ │
    │ │ TDSQL (PG)   ││  │ │ RDS (PG)     │ │
    │ │ COS 对象存储  ││  │ │ OSS 对象存储  │ │
    │ │ Redis        ││  │ │ Redis        │ │
    │ └──────────────┘│  │ └──────────────┘ │
    └──────────────────┘  └──────────────────┘
```

### 6.2 基础设施抽象层

```python
class CloudProvider(ABC):
    """云平台抽象 - 统一腾讯云和阿里云接口"""
    
    @abstractmethod
    async def deploy_service(self, config: ServiceConfig) -> str:
        """部署服务"""
    
    @abstractmethod
    async def get_database(self, db_name: str) -> Database:
        """获取数据库连接"""
    
    @abstractmethod
    async def get_storage(self, bucket: str) -> ObjectStorage:
        """获取对象存储"""

class TencentCloudProvider(CloudProvider): ...
class AlibabaCloudProvider(CloudProvider): ...

# 配置式选择
# deploy.yaml:
#   cloud: tencent   # 或 alibaba
#   region: ap-guangzhou
```

### 6.3 部署配置

```yaml
# deploy.yaml - 部署配置文件
cloud: tencent                    # tencent / alibaba
region: ap-guangzhou              # 地域
services:
  api-gateway:
    spec: 2C4G
    replicas: 1
  collector:
    spec: 2C4G
    replicas: 1
  matcher:
    spec: 4C8G
    replicas: 1
  scheduler:
    spec: 1C2G
    replicas: 1
database:
  type: postgresql
  spec: 2C4G 100GB
cache:
  type: redis
  spec: 1C2G
storage:
  type: cos         # cos / oss
  bucket: infospider-data
```

---

## 7. 前端设计

### 7.1 多端适配策略

```
┌──────────────────────────────────────────┐
│           共享业务逻辑层                    │
│    (TypeScript/Python API Client SDK)     │
├──────────┬──────────┬──────────┬─────────┤
│ Web App  │ 小程序    │ 手机App  │ CLI     │
│ React/   │ 微信/     │ React    │ Python  │
│ Next.js  │ Taro      │ Native  │ Typer   │
└──────────┴──────────┴──────────┴─────────┘
```

### 7.2 各端功能优先级

| 功能 | Web | 小程序 | App | CLI |
|------|-----|--------|-----|-----|
| 查看推荐内容 | P0 | P0 | P1 | P0 |
| 配置采集源 | P0 | P1 | P1 | P0 |
| 管理兴趣标签 | P0 | P0 | P1 | - |
| 阅读反馈（点赞/跳过） | P0 | P0 | P1 | - |
| 查看采集报告 | P0 | P1 | P2 | P0 |
| 触发采集任务 | P0 | P2 | P2 | P0 |
| 用户设置 | P0 | P1 | P1 | P0 |

### 7.3 MVP前端方案

MVP阶段优先实现 **Web App**（开发成本最低，覆盖全功能）：

- 框架: React + Next.js
- UI组件: Ant Design / shadcn/ui
- 状态管理: Zustand
- API通信: Axios + WebSocket

---

## 8. 分期实施路线

### Phase 1: 核心引擎（2-3周）

**目标**: 可运行的多源爬虫 + 关键字匹配 + CLI

- [ ] 项目脚手架搭建（目录结构、依赖管理、配置系统）
- [ ] 从 ZhihuReader 移植核心架构（Pipeline + Crawler + Filter）
- [ ] 实现 `BaseCrawler` 接口和 `CrawlerRegistry`
- [ ] 移植知乎爬虫（ZhihuCrawler）
- [ ] 实现 B站爬虫（BilibiliCrawler）
- [ ] 实现 `KeywordMatcher`（关键字匹配）
- [ ] 实现 `UserProfile` 数据模型和本地存储
- [ ] CLI 入口（支持多源采集命令）
- [ ] 统一输出格式（HTML报告 + JSON）

### Phase 2: 多源扩展 + 语义匹配（2-3周）

**目标**: GitHub/YouTube/论文源 + 向量语义匹配

- [x] 实现 GitHub 爬虫（GitHubCrawler）
- [ ] 实现 YouTube 爬虫（YouTubeCrawler）
- [ ] 实现论文爬虫（PaperCrawler - DBLP/SemanticScholar）
- [ ] 引入 ChromaDB 向量数据库
- [ ] 实现 `SemanticMatcher`（语义匹配）
- [ ] 用户画像向量化和相似度计算
- [x] 采集结果去重和合并

### Phase 3: 后端服务化 + Web前端（3-4周）

**目标**: REST API + Web界面 + 数据库持久化

- [ ] FastAPI 后端服务搭建
- [ ] PostgreSQL 数据库建表和ORM（SQLAlchemy）
- [ ] 用户认证系统（JWT）
- [ ] 用户画像CRUD API
- [ ] 采集任务API + 异步任务队列（Celery/ARQ）
- [ ] WebSocket 实时进度推送
- [ ] Web前端（React + Next.js）
- [ ] Docker 容器化

### Phase 4: 多云部署 + 推荐系统（3-4周）

**目标**: 腾讯云/阿里云部署 + 推荐引擎

- [ ] 云平台抽象层（CloudProvider）
- [ ] 腾讯云部署脚本（CVM + TDSQL + COS）
- [ ] 阿里云部署脚本（ECS + RDS + OSS）
- [ ] 一键部署工具（deploy.yaml → Terraform/脚本）
- [ ] `RecommendationEngine` 基础版（协同过滤）
- [ ] 用户行为事件采集和画像自动更新
- [ ] 定期自动扫描和推送

### Phase 5: 移动端 + 高级推荐（持续迭代）

**目标**: 小程序/App + 深度推荐

- [ ] 微信小程序（Taro）
- [ ] 推荐系统升级（深度学习模型）
- [ ] A/B测试框架
- [ ] 通知服务（邮件/微信/App推送）
- [ ] 性能监控和日志系统
- [ ] 用户反馈闭环优化

---

## 9. 项目目录结构

```
InfoSpider/
├── doc/
│   └── design.md               # 本设计文档
├── src/
│   ├── core/                   # 核心引擎
│   │   ├── crawler/            # 爬虫引擎
│   │   │   ├── base.py         # BaseCrawler 抽象基类
│   │   │   ├── registry.py     # CrawlerRegistry 注册中心
│   │   │   ├── zhihu.py        # 知乎爬虫
│   │   │   ├── bilibili.py     # B站爬虫
│   │   │   ├── youtube.py      # YouTube爬虫
│   │   │   ├── github.py       # GitHub爬虫
│   │   │   └── paper.py        # 论文爬虫
│   │   ├── matcher/            # 匹配引擎
│   │   │   ├── base.py         # BaseMatcher
│   │   │   ├── keyword.py      # 关键字匹配
│   │   │   ├── semantic.py     # 语义匹配
│   │   │   └── recommender.py  # 推荐系统
│   │   ├── pipeline/           # 流水线
│   │   │   ├── base.py         # Pipeline基类
│   │   │   ├── collector.py    # 采集阶段
│   │   │   ├── analyzer.py     # 分析阶段
│   │   │   └── archiver.py     # 归档阶段
│   │   ├── scheduler/          # 调度引擎
│   │   │   └── scheduler.py
│   │   └── ai/                 # AI引擎
│   │       ├── base.py
│   │       ├── openai_client.py
│   │       └── local_llm.py
│   ├── models/                 # 数据模型
│   │   ├── user.py             # UserProfile
│   │   ├── item.py             # CrawlItem
│   │   └── task.py             # CrawlTask
│   ├── storage/                # 存储层
│   │   ├── database.py         # PostgreSQL
│   │   ├── vector_store.py     # ChromaDB/Milvus
│   │   ├── cache.py            # Redis
│   │   └── object_storage.py   # COS/OSS
│   ├── api/                    # API层（Phase 3）
│   │   ├── main.py             # FastAPI入口
│   │   ├── auth.py             # 认证
│   │   ├── users.py            # 用户API
│   │   ├── tasks.py            # 任务API
│   │   └── items.py            # 内容API
│   ├── cloud/                  # 多云抽象（Phase 4）
│   │   ├── base.py             # CloudProvider
│   │   ├── tencent.py          # 腾讯云
│   │   └── alibaba.py          # 阿里云
│   └── utils/                  # 工具
│       ├── config.py           # 配置管理
│       └── logger.py           # 日志
├── config/
│   ├── default.yaml            # 默认配置
│   └── sources/                # 各源默认配置
│       ├── zhihu.yaml
│       ├── bilibili.yaml
│       ├── youtube.yaml
│       ├── github.yaml
│       └── paper.yaml
├── web/                        # Web前端（Phase 3）
│   └── app/                    # Next.js项目
├── deploy/                     # 部署配置（Phase 4）
│   ├── deploy.yaml
│   ├── tencent/
│   └── alibaba/
├── cli.py                      # CLI入口
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 10. 技术选型汇总

| 领域 | 技术选型 | 理由 |
|------|---------|------|
| 后端语言 | Python 3.11+ | 爬虫生态成熟，AI库丰富 |
| Web框架 | FastAPI | 异步原生，自动文档，类型安全 |
| 任务队列 | ARQ (async) / Celery | 异步采集任务调度 |
| 数据库 | PostgreSQL | JSONB + 全文检索 + 成熟稳定 |
| ORM | SQLAlchemy 2.0 | 异步支持，类型提示 |
| 向量数据库 | ChromaDB → Milvus | 开发期轻量 → 生产期高性能 |
| 缓存 | Redis | 限流/会话/热点缓存 |
| 前端 | React + Next.js | SSR + 生态丰富 |
| 小程序 | Taro | 跨端统一 |
| 爬虫 | Playwright + httpx | 浏览器渲染 + API直调双模式 |
| AI分析 | OpenAI / Ollama | 云端 + 本地双通道 |
| 容器化 | Docker + docker-compose | 一致性部署 |
| CI/CD | GitHub Actions | 自动测试和部署 |
| 云平台 | 腾讯云 + 阿里云 | 双云冗余，按需选择 |

---

## 11. 关键设计决策

### 11.1 同步 vs 异步

ZhihuReader 使用同步 Playwright。InfoSpider 需要同时调度多个平台爬虫，采用 **async/await 异步架构**：

- 爬虫内部使用 `playwright.async_api`
- API服务使用 FastAPI 异步路由
- 任务调度使用 asyncio 任务组

### 11.2 爬虫插件化

通过 `CrawlerRegistry` 装饰器注册机制，新增平台只需：
1. 实现 `BaseCrawler` 接口
2. 用 `@CrawlerRegistry.register("source_name")` 注册
3. 添加对应的 YAML 配置文件

无需修改核心调度逻辑。

### 11.3 匹配策略渐进式升级

匹配引擎采用策略模式，三级策略可独立启用：

```python
class MatcherFactory:
    @staticmethod
    def create(level: str, config: dict) -> BaseMatcher:
        if level == "keyword":
            return KeywordMatcher(config)
        elif level == "semantic":
            return SemanticMatcher(config)
        elif level == "recommend":
            return RecommendationEngine(config)
```

配置文件中指定当前使用的匹配级别，无需代码改动即可切换。

### 11.4 多云部署抽象

所有云服务操作通过 `CloudProvider` 抽象层，业务代码不直接依赖特定云SDK。切换云平台只需修改 `deploy.yaml` 中的 `cloud` 字段。

---

## 12. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 反爬升级 | 爬虫失效 | 多策略备选（API/浏览器/第三方），降级方案 |
| 向量数据库运维复杂 | 延期 | 先用 ChromaDB 嵌入式，后迁 Milvus |
| 多云一致性 | 运维负担 | Terraform 统一编排，最小化云差异 |
| 推荐冷启动 | 新用户体验差 | 默认画像模板 + 引导式兴趣选择 |
| 内容合规 | 法律风险 | 敏感词过滤 + 人工审核接口 |

---

## 附录 A: 与 ZhihuReader 的兼容性

InfoSpider Phase 1 的知乎爬虫从 ZhihuReader 移植，保持核心逻辑一致：

- `ZhihuClient` → `ZhihuCrawler(BaseCrawler)` 
- `ArticleCollector` → 内聚到 `ZhihuCrawler.search()` / `get_trending()`
- 三层过滤器 → `KeywordMatcher` 内部复用
- `JSONStorage` / `ExcelStorage` → `StorageLayer` 抽象
- `HTMLReportStorage` → 统一报告输出

ZhihuReader 继续独立维护作为轻量版；InfoSpider 作为完整版。

---

## 附录 B: 术语表

| 术语 | 含义 |
|------|------|
| Crawler | 爬虫，负责从指定平台抓取内容 |
| Matcher | 匹配器，判断内容是否符合用户需求 |
| CrawlItem | 爬取结果的标准数据单元 |
| UserProfile | 用户画像，包含兴趣/偏好/历史 |
| InterestGraph | 兴趣图谱，标签及关联的有权图 |
| Pipeline | 流水线，串联多个处理阶段 |
| Scheduler | 调度器，管理采集任务的执行 |
| CloudProvider | 云平台抽象，统一多云接口 |
