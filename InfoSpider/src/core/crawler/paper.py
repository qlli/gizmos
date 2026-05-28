"""论文爬虫 - 使用 Semantic Scholar Graph API 搜索论文"""
import asyncio
import os
import time
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional

import httpx
from loguru import logger

from .base import BaseCrawler, CrawlItem
from .registry import CrawlerRegistry
from ...utils.config import get_config


@CrawlerRegistry.register("paper")
class PaperCrawler(BaseCrawler):
    """论文爬虫

    基于 Semantic Scholar Graph API 搜索论文摘要、作者、会议/期刊、引用数等元数据。
    """

    source_name = "paper"
    source_type = "academic"

    API_BASE = "https://api.semanticscholar.org/graph/v1"
    SEARCH_URL = f"{API_BASE}/paper/search"
    PAPER_URL = f"{API_BASE}/paper/{{paper_id}}"
    FIELDS = ",".join([
        "paperId",
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "url",
        "citationCount",
        "influentialCitationCount",
        "openAccessPdf",
        "publicationDate",
        "externalIds",
        "fieldsOfStudy",
        "publicationTypes",
    ])

    DEFAULT_HEADERS = {
        "User-Agent": "InfoSpider/0.2",
    }

    def __init__(self, **kwargs):
        self.config = get_config()
        self.source_config = self.config.get_source_config("paper")

        auth_cfg = self.source_config.get("auth", {})
        self.api_key = kwargs.get("api_key") or auth_cfg.get("api_key") or os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

        rate_cfg = self.source_config.get("rate_limit", {})
        self.requests_per_minute = int(rate_cfg.get("requests_per_minute", 20) or 20)
        self._request_count = 0
        self._minute_start = 0.0

        search_cfg = self.source_config.get("search", {})
        self.per_page = int(search_cfg.get("per_page", 20) or 20)
        self.min_citations = int(search_cfg.get("min_citations", 0) or 0)
        self.year = str(search_cfg.get("year", "") or "")
        self.fields_of_study = search_cfg.get("fields_of_study", []) or []

        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        headers = dict(self.DEFAULT_HEADERS)
        if self.api_key:
            headers["x-api-key"] = self.api_key

        self._client = httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True)
        self._minute_start = time.time()
        logger.info("[paper] HTTP客户端已初始化")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info("[paper] HTTP客户端已关闭")

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
        try:
            resp = await self._client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()

            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("retry-after", "")
                suffix = f"，建议等待 {retry_after} 秒" if retry_after else ""
                logger.warning(f"[paper] API限流或权限不足{suffix}")
                return None

            logger.warning(f"[paper] HTTP错误: status={resp.status_code}, body={resp.text[:200]}")
            return None
        except Exception as e:
            logger.warning(f"[paper] 请求异常: {e}")
            return None

    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """搜索论文"""
        logger.info(f"[paper] 搜索论文: keyword={keyword}, limit={limit}")

        min_citations = int(filters.get("min_citations", self.min_citations) or 0)
        year = str(filters.get("year", self.year) or "")
        fields_of_study = filters.get("fields_of_study", self.fields_of_study) or []

        yielded = 0
        offset = 0
        page_size = min(max(self.per_page, 1), 100)

        while yielded < limit:
            params = {
                "query": keyword,
                "fields": self.FIELDS,
                "limit": min(page_size, limit - yielded),
                "offset": offset,
            }
            if year:
                params["year"] = year
            if fields_of_study:
                params["fieldsOfStudy"] = ",".join(fields_of_study)

            data = await self._get(self.SEARCH_URL, params=params)
            if not data:
                break

            papers = data.get("data", [])
            if not papers:
                break

            for raw in papers:
                if yielded >= limit:
                    break
                if int(raw.get("citationCount", 0) or 0) < min_citations:
                    continue
                item = self._parse_paper_item(raw)
                if item:
                    yielded += 1
                    yield item

            offset += len(papers)
            if len(papers) < page_size:
                break

        logger.info(f"[paper] 搜索完成: keyword={keyword}, 结果={yielded}")

    async def get_trending(self, category: str = "", limit: int = 20) -> AsyncIterator[CrawlItem]:
        """获取近期论文；Semantic Scholar 无官方趋势API，这里用近期年份+引用阈值近似"""
        trending_cfg = self.source_config.get("trending", {})
        query = category or trending_cfg.get("default_query", "artificial intelligence")
        recent_years = int(trending_cfg.get("recent_years", 3) or 3)
        min_citations = int(trending_cfg.get("min_citations", self.min_citations) or 0)

        current_year = datetime.now().year
        year_range = f"{current_year - recent_years + 1}-{current_year}"

        async for item in self.search(query, limit=limit, year=year_range, min_citations=min_citations):
            yield item

    async def get_content(self, item: CrawlItem) -> str:
        """获取论文详情；当前主要返回摘要和开放PDF链接"""
        paper_id = item.item_id
        if not paper_id:
            return item.excerpt

        data = await self._get(self.PAPER_URL.format(paper_id=paper_id), params={"fields": self.FIELDS})
        if not data:
            return item.excerpt

        parsed = self._parse_paper_item(data)
        if not parsed:
            return item.excerpt

        open_pdf = parsed.metadata.get("open_access_pdf", "")
        parts = [parsed.excerpt]
        if open_pdf:
            parts.append(f"OpenAccessPDF: {open_pdf}")
        return "\n".join(p for p in parts if p)

    def _parse_paper_item(self, raw: Dict) -> Optional[CrawlItem]:
        """解析 Semantic Scholar 论文为统一 CrawlItem"""
        try:
            authors = raw.get("authors") or []
            author_names = [a.get("name", "") for a in authors if isinstance(a, dict) and a.get("name")]
            abstract = raw.get("abstract") or ""
            fields_of_study = raw.get("fieldsOfStudy") or []
            open_pdf = raw.get("openAccessPdf") or {}
            external_ids = raw.get("externalIds") or {}
            paper_id = raw.get("paperId", "")

            url = raw.get("url") or ""
            if not url and paper_id:
                url = f"https://www.semanticscholar.org/paper/{paper_id}"

            metadata = {
                "venue": raw.get("venue", ""),
                "year": raw.get("year"),
                "fields_of_study": fields_of_study,
                "publication_types": raw.get("publicationTypes") or [],
                "external_ids": external_ids,
                "doi": external_ids.get("DOI", "") if isinstance(external_ids, dict) else "",
                "open_access_pdf": open_pdf.get("url", "") if isinstance(open_pdf, dict) else "",
                "influential_citation_count": raw.get("influentialCitationCount", 0),
            }

            excerpt_parts: List[str] = []
            if abstract:
                excerpt_parts.append(abstract[:1200])
            if raw.get("venue"):
                excerpt_parts.append(f"Venue: {raw.get('venue')}")
            if fields_of_study:
                excerpt_parts.append("Fields: " + ", ".join(fields_of_study[:5]))

            return CrawlItem(
                source="paper",
                item_type="paper",
                item_id=paper_id,
                title=raw.get("title", ""),
                url=url,
                author=", ".join(author_names[:5]),
                content=abstract,
                excerpt="\n".join(excerpt_parts),
                metadata=metadata,
                voteup=int(raw.get("citationCount", 0) or 0),
                comment_count=int(raw.get("influentialCitationCount", 0) or 0),
                view_count=int(raw.get("citationCount", 0) or 0),
                published_at=raw.get("publicationDate") or str(raw.get("year") or ""),
            )
        except Exception as e:
            logger.warning(f"[paper] 解析论文失败: {e}")
            return None
