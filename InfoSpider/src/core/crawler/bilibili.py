"""B站爬虫 - 使用 httpx 调用 B站 API"""
import asyncio
import time
import hashlib
import urllib.parse
from typing import AsyncIterator, Dict, List, Optional
from datetime import datetime
from functools import reduce

import httpx
from loguru import logger

from .base import BaseCrawler, CrawlItem
from .registry import CrawlerRegistry
from ...utils.config import get_config


# B站 wbi 签名所需的混淆表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]


def _get_mixin_key(orig: str) -> str:
    """获取混淆密钥"""
    return reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, '')[:32]


def _wbi_sign(params: dict, img_key: str, sub_key: str) -> dict:
    """wbi 签名"""
    mixin_key = _get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    
    # 按key排序
    params = dict(sorted(params.items()))
    # 过滤特殊字符
    params = {
        k: ''.join(c for c in str(v) if c not in "!'()*")
        for k, v in params.items()
    }
    
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params


@CrawlerRegistry.register("bilibili")
class BilibiliCrawler(BaseCrawler):
    """B站爬虫
    
    使用 httpx 异步HTTP客户端调用B站搜索和热门视频 API。
    无需浏览器，通过 Cookie 和 wbi 签名获取数据。
    """
    
    source_name = "bilibili"
    source_type = "video"
    
    API_BASE = "https://api.bilibili.com"
    SEARCH_URL = f"{API_BASE}/x/web-interface/search/type"
    HOT_URL = f"{API_BASE}/x/web-interface/popular"
    VIDEO_INFO_URL = f"{API_BASE}/x/web-interface/view"
    WBI_URL = f"{API_BASE}/x/web-interface/nav"
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Origin": "https://www.bilibili.com",
    }
    
    def __init__(self, **kwargs):
        self.config = get_config()
        self.source_config = self.config.get_source_config("bilibili")
        
        # 速率限制
        rate_cfg = self.source_config.get("rate_limit", {})
        self.requests_per_minute = rate_cfg.get("requests_per_minute", 30)
        self._request_count = 0
        self._minute_start = 0.0
        
        # 过滤配置
        filters = self.source_config.get("filters", {})
        self.min_view = filters.get("min_view", 10000)
        self.min_like = filters.get("min_like", 500)
        
        # HTTP 客户端
        self._client: Optional[httpx.AsyncClient] = None
        
        # wbi 密钥缓存
        self._img_key = ""
        self._sub_key = ""
    
    async def initialize(self) -> None:
        """初始化 HTTP 客户端"""
        self._client = httpx.AsyncClient(
            headers=self.DEFAULT_HEADERS,
            timeout=30.0,
            follow_redirects=True
        )
        self._minute_start = time.time()
        
        # 获取 wbi 密钥
        await self._refresh_wbi_keys()
        logger.info(f"[bilibili] HTTP客户端已初始化")
    
    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
        logger.info("[bilibili] HTTP客户端已关闭")
    
    async def _refresh_wbi_keys(self):
        """获取/刷新 wbi 签名密钥"""
        try:
            resp = await self._client.get(self.WBI_URL)
            data = resp.json()
            wbi_img = data.get('data', {}).get('wbi_img', {})
            img_url = wbi_img.get('img_url', '')
            sub_url = wbi_img.get('sub_url', '')
            
            # 从 URL 中提取密钥
            self._img_key = img_url.rsplit('/', 1)[-1].split('.')[0] if img_url else ''
            self._sub_key = sub_url.rsplit('/', 1)[-1].split('.')[0] if sub_url else ''
            
            if self._img_key and self._sub_key:
                logger.debug(f"[bilibili] wbi密钥已获取")
            else:
                logger.warning("[bilibili] wbi密钥获取失败，搜索功能可能受限")
        except Exception as e:
            logger.warning(f"[bilibili] 获取wbi密钥失败: {e}")
    
    async def _rate_limit(self):
        """速率限制"""
        self._request_count += 1
        elapsed = time.time() - self._minute_start
        
        if self._request_count >= self.requests_per_minute:
            if elapsed < 60:
                await asyncio.sleep(60 - elapsed)
            self._request_count = 0
            self._minute_start = time.time()
    
    async def _get(self, url: str, params: dict = None) -> Optional[Dict]:
        """发送GET请求"""
        await self._rate_limit()
        
        if not self._client:
            return None
        
        try:
            resp = await self._client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    return data.get('data', {})
                else:
                    logger.debug(f"[bilibili] API错误: code={data.get('code')}, msg={data.get('message')}")
                    return None
            else:
                logger.warning(f"[bilibili] HTTP错误: status={resp.status_code}")
                return None
        except Exception as e:
            logger.warning(f"[bilibili] 请求异常: {e}")
            return None
    
    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """搜索B站视频"""
        logger.info(f"[bilibili] 搜索: keyword={keyword}, limit={limit}")
        
        order = filters.get("order", self.source_config.get("search", {}).get("order", "totalrank"))
        page = 1
        page_size = 20
        yielded = 0
        
        while yielded < limit:
            params = {
                "search_type": "video",
                "keyword": keyword,
                "order": order,
                "page": page,
                "page_size": page_size,
            }
            
            # 应用 wbi 签名
            if self._img_key and self._sub_key:
                params = _wbi_sign(params, self._img_key, self._sub_key)
            
            data = await self._get(self.SEARCH_URL, params=params)
            if not data:
                break
            
            results = data.get("result", [])
            if not results:
                break
            
            for raw in results:
                if yielded >= limit:
                    break
                
                item = self._parse_search_item(raw)
                if item:
                    yielded += 1
                    yield item
            
            page += 1
            if len(results) < page_size:
                break
        
        logger.info(f"[bilibili] 搜索完成: keyword={keyword}, 结果={yielded}")
    
    async def get_trending(self, category: str = "", limit: int = 20) -> AsyncIterator[CrawlItem]:
        """获取B站热门视频"""
        logger.info(f"[bilibili] 获取热门: limit={limit}")
        
        page = 1
        page_size = 20
        yielded = 0
        
        while yielded < limit:
            params = {"pn": page, "ps": page_size}
            data = await self._get(self.HOT_URL, params=params)
            if not data:
                break
            
            video_list = data.get("list", [])
            if not video_list:
                break
            
            for raw in video_list:
                if yielded >= limit:
                    break
                
                item = self._parse_popular_item(raw)
                if item:
                    yielded += 1
                    yield item
            
            page += 1
            if len(video_list) < page_size:
                break
        
        logger.info(f"[bilibili] 热门获取完成: 结果={yielded}")
    
    async def get_content(self, item: CrawlItem) -> str:
        """获取视频描述（B站无法获取完整视频内容，返回描述+标签）"""
        bvid = item.metadata.get("bvid", "")
        if not bvid:
            return item.excerpt
        
        data = await self._get(self.VIDEO_INFO_URL, params={"bvid": bvid})
        if not data:
            return item.excerpt
        
        desc = data.get("desc", "")
        tags = []
        # 获取标签信息
        tag_data = data.get("tags", [])  # 注意：需要另一个API
        
        content_parts = [f"标题: {item.title}"]
        if desc:
            content_parts.append(f"简介: {desc}")
        if tags:
            content_parts.append(f"标签: {', '.join(tags)}")
        
        return "\n".join(content_parts)
    
    def _parse_search_item(self, raw: Dict) -> Optional[CrawlItem]:
        """解析搜索结果为 CrawlItem"""
        bvid = raw.get("bvid", "")
        if not bvid:
            return None
        
        # 清理标题中的高亮标签
        title = raw.get("title", "")
        title = title.replace('<em class="keyword">', '').replace('</em>', '')
        
        # 播放量和点赞
        play = raw.get("play", 0)
        like = raw.get("like", 0)
        
        return CrawlItem(
            source="bilibili",
            item_type="video",
            item_id=bvid,
            title=title,
            url=f"https://www.bilibili.com/video/{bvid}",
            author=raw.get("author", ""),
            excerpt=raw.get("description", ""),
            voteup=like,
            view_count=play,
            comment_count=raw.get("comment", 0),
            published_at=datetime.fromtimestamp(raw.get("pubdate", 0)).isoformat() if raw.get("pubdate") else None,
            metadata={
                "bvid": bvid,
                "aid": raw.get("aid", 0),
                "duration": raw.get("duration", ""),
                "tag": raw.get("tag", ""),
                "favorites": raw.get("favorites", 0),
                "danmaku": raw.get("video_review", 0),
            }
        )
    
    def _parse_popular_item(self, raw: Dict) -> Optional[CrawlItem]:
        """解析热门视频为 CrawlItem"""
        bvid = raw.get("bvid", "")
        if not bvid:
            return None
        
        stat = raw.get("stat", {})
        owner = raw.get("owner", {})
        
        return CrawlItem(
            source="bilibili",
            item_type="video",
            item_id=bvid,
            title=raw.get("title", ""),
            url=f"https://www.bilibili.com/video/{bvid}",
            author=owner.get("name", ""),
            excerpt=raw.get("desc", ""),
            voteup=stat.get("like", 0),
            view_count=stat.get("view", 0),
            comment_count=stat.get("reply", 0),
            published_at=datetime.fromtimestamp(raw.get("pubdate", 0)).isoformat() if raw.get("pubdate") else None,
            metadata={
                "bvid": bvid,
                "aid": raw.get("aid", 0),
                "duration": raw.get("duration", 0),
                "favorites": stat.get("favorite", 0),
                "danmaku": stat.get("danmaku", 0),
                "coin": stat.get("coin", 0),
                "share": stat.get("share", 0),
            }
        )
