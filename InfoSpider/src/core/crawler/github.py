"""GitHub 爬虫 - 使用 GitHub REST API 搜索仓库"""
import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, Optional

import httpx
from loguru import logger

from .base import BaseCrawler, CrawlItem
from .registry import CrawlerRegistry
from .http_util import request_with_backoff
from ...utils.config import get_config


@CrawlerRegistry.register("github")
class GitHubCrawler(BaseCrawler):
    """GitHub 仓库爬虫

    使用 GitHub REST API 搜索仓库；无需登录即可使用，配置或环境变量
    `GITHUB_TOKEN` 可提升限流额度。
    """

    source_name = "github"
    source_type = "code"

    API_BASE = "https://api.github.com"
    SEARCH_REPOS_URL = f"{API_BASE}/search/repositories"
    REPO_README_URL = f"{API_BASE}/repos/{{full_name}}/readme"

    DEFAULT_HEADERS = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "InfoSpider/0.2",
    }

    def __init__(self, **kwargs):
        self.config = get_config()
        self.source_config = self.config.get_source_config("github")

        auth_cfg = self.source_config.get("auth", {})
        self.token = kwargs.get("token") or auth_cfg.get("token") or os.getenv("GITHUB_TOKEN", "")

        rate_cfg = self.source_config.get("rate_limit", {})
        self.requests_per_minute = rate_cfg.get("requests_per_minute", 20)
        self.max_retries = int(rate_cfg.get("max_retries", 2) or 2) if rate_cfg.get("retry_on_failure", True) else 0
        self._request_count = 0
        self._minute_start = 0.0

        search_cfg = self.source_config.get("search", {})
        self.default_sort = search_cfg.get("sort", "stars")
        self.default_order = search_cfg.get("order", "desc")
        self.default_min_stars = int(search_cfg.get("min_stars", 0) or 0)
        self.default_language = search_cfg.get("language", "")
        self.per_page = int(search_cfg.get("per_page", 30) or 30)

        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        headers = dict(self.DEFAULT_HEADERS)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )
        self._minute_start = time.time()
        logger.info("[github] HTTP客户端已初始化")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info("[github] HTTP客户端已关闭")

    async def _rate_limit(self) -> None:
        self._request_count += 1
        elapsed = time.time() - self._minute_start

        if self._request_count >= self.requests_per_minute:
            if elapsed < 60:
                await asyncio.sleep(60 - elapsed)
            self._request_count = 0
            self._minute_start = time.time()

    async def _get(self, url: str, params: Optional[dict] = None) -> Optional[Dict]:
        if not self._client:
            return None

        await self._rate_limit()
        resp = await request_with_backoff(
            self._client, url, params=params,
            max_retries=self.max_retries, tag="github",
        )
        if resp is None:
            return None

        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception as e:
                logger.warning(f"[github] 响应解析失败: {e}")
                return None

        if resp.status_code in (403, 429):
            reset = resp.headers.get("x-ratelimit-reset")
            if reset:
                try:
                    reset_at = datetime.fromtimestamp(int(reset)).isoformat()
                    logger.warning(f"[github] API限流(重试后仍失败)，重置时间: {reset_at}")
                except ValueError:
                    logger.warning("[github] API限流或权限不足(重试后仍失败)")
            else:
                logger.warning("[github] API限流或权限不足(重试后仍失败)")
            return None

        logger.warning(f"[github] HTTP错误: status={resp.status_code}, body={resp.text[:200]}")
        return None

    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """搜索 GitHub 仓库"""
        logger.info(f"[github] 搜索仓库: keyword={keyword}, limit={limit}")

        sort = filters.get("sort", self.default_sort)
        order = filters.get("order", self.default_order)
        min_stars = int(filters.get("min_stars", self.default_min_stars) or 0)
        language = filters.get("language", self.default_language)

        query_parts = [keyword]
        if min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")
        if language:
            query_parts.append(f"language:{language}")

        yielded = 0
        page = 1
        page_size = min(max(self.per_page, 1), 100)

        while yielded < limit:
            params = {
                "q": " ".join(query_parts),
                "sort": sort,
                "order": order,
                "page": page,
                "per_page": min(page_size, limit - yielded),
            }
            data = await self._get(self.SEARCH_REPOS_URL, params=params)
            if not data:
                break

            repos = data.get("items", [])
            if not repos:
                break

            for raw in repos:
                if yielded >= limit:
                    break
                item = self._parse_repo_item(raw)
                if item:
                    yielded += 1
                    yield item

            page += 1
            if len(repos) < page_size:
                break

        logger.info(f"[github] 搜索完成: keyword={keyword}, 结果={yielded}")

    async def get_trending(self, category: str = "", limit: int = 20) -> AsyncIterator[CrawlItem]:
        """获取近期高星仓库，作为趋势仓库近似实现"""
        trending_cfg = self.source_config.get("trending", {})
        days = int(trending_cfg.get("days", 30) or 30)
        min_stars = int(trending_cfg.get("min_stars", self.default_min_stars) or 0)
        sort = trending_cfg.get("sort", "stars")
        order = trending_cfg.get("order", "desc")

        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        query_parts = [f"created:>={since}"]
        if min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")
        if category:
            query_parts.append(category)

        logger.info(f"[github] 获取趋势仓库: days={days}, limit={limit}")

        yielded = 0
        page = 1
        page_size = min(max(self.per_page, 1), 100)

        while yielded < limit:
            params = {
                "q": " ".join(query_parts),
                "sort": sort,
                "order": order,
                "page": page,
                "per_page": min(page_size, limit - yielded),
            }
            data = await self._get(self.SEARCH_REPOS_URL, params=params)
            if not data:
                break

            repos = data.get("items", [])
            if not repos:
                break

            for raw in repos:
                if yielded >= limit:
                    break
                item = self._parse_repo_item(raw)
                if item:
                    yielded += 1
                    yield item

            page += 1
            if len(repos) < page_size:
                break

        logger.info(f"[github] 趋势仓库获取完成: 结果={yielded}")

    async def get_content(self, item: CrawlItem) -> str:
        """获取仓库 README 文本；失败时回退到描述"""
        full_name = item.metadata.get("full_name")
        if not full_name:
            return item.excerpt

        data = await self._get(self.REPO_README_URL.format(full_name=full_name))
        if not data:
            return item.excerpt

        download_url = data.get("download_url")
        if not download_url or not self._client:
            return item.excerpt

        try:
            await self._rate_limit()
            resp = await self._client.get(download_url)
            if resp.status_code == 200:
                text = resp.text.strip()
                return text[:20000]
        except Exception as e:
            logger.debug(f"[github] README获取失败: {e}")

        return item.excerpt

    def _parse_repo_item(self, raw: Dict) -> Optional[CrawlItem]:
        """解析 GitHub 仓库为统一 CrawlItem"""
        try:
            owner = raw.get("owner") or {}
            topics = raw.get("topics") or []
            description = raw.get("description") or ""
            language = raw.get("language") or ""
            license_info = raw.get("license") or {}

            metadata = {
                "full_name": raw.get("full_name", ""),
                "language": language,
                "topics": topics,
                "forks": raw.get("forks_count", 0),
                "open_issues": raw.get("open_issues_count", 0),
                "license": license_info.get("name", "") if isinstance(license_info, dict) else "",
                "created_at": raw.get("created_at"),
                "updated_at": raw.get("updated_at"),
                "pushed_at": raw.get("pushed_at"),
                "default_branch": raw.get("default_branch", ""),
            }

            excerpt_parts = [description]
            if language:
                excerpt_parts.append(f"Language: {language}")
            if topics:
                excerpt_parts.append("Topics: " + ", ".join(topics[:10]))

            return CrawlItem(
                source="github",
                item_type="repo",
                item_id=str(raw.get("id", "")),
                title=raw.get("full_name", raw.get("name", "")),
                url=raw.get("html_url", ""),
                author=owner.get("login", ""),
                content=description,
                excerpt="\n".join(p for p in excerpt_parts if p),
                metadata=metadata,
                voteup=int(raw.get("stargazers_count", 0) or 0),
                comment_count=int(raw.get("open_issues_count", 0) or 0),
                view_count=int(raw.get("watchers_count", 0) or 0),
                published_at=raw.get("created_at"),
            )
        except Exception as e:
            logger.warning(f"[github] 解析仓库失败: {e}")
            return None
