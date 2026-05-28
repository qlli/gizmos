"""知乎爬虫 - 从 ZhihuReader 移植，升级为 async 架构"""
import asyncio
import urllib.parse
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional
from datetime import datetime

from loguru import logger
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from .base import BaseCrawler, CrawlItem
from .registry import CrawlerRegistry
from ...utils.config import get_config


@CrawlerRegistry.register("zhihu")
class ZhihuCrawler(BaseCrawler):
    """知乎爬虫
    
    使用 Playwright 持久化上下文 + stealth 反检测，
    通过 page.evaluate(fetch) 调用知乎内部 API。
    """
    
    source_name = "zhihu"
    source_type = "feed"
    BASE_URL = "https://www.zhihu.com"
    
    def __init__(self, headless: bool = True, **kwargs):
        self.headless = headless
        self.config = get_config()
        self.source_config = self.config.get_source_config("zhihu")
        
        # 浏览器数据目录
        browser_dir = self.source_config.get("browser", {}).get(
            "user_data_dir", "data/browser/zhihu"
        )
        self.user_data_dir = Path(browser_dir)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 速率限制
        rate_cfg = self.source_config.get("rate_limit", {})
        self.requests_per_minute = rate_cfg.get("requests_per_minute", 20)
        self._request_count = 0
        self._minute_start = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        
        # Playwright 实例
        self._playwright = None
        self._context = None
        self._page = None
    
    async def initialize(self) -> None:
        """启动浏览器"""
        logger.info(f"[zhihu] 启动浏览器: headless={self.headless}, data_dir={self.user_data_dir.resolve()}")
        
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        
        # 应用 stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(self._context)
        
        logger.info(f"[zhihu] 浏览器已启动 (stealth 模式)")
    
    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("[zhihu] 浏览器已关闭")
        except Exception as e:
            logger.warning(f"[zhihu] 关闭浏览器出错: {e}")
    
    async def ensure_logged_in(self) -> bool:
        """检查并确保已登录知乎"""
        if not self._page:
            return False
        
        logger.info("[zhihu] 检查登录状态...")
        await self._page.goto(f"{self.BASE_URL}/hot", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        login_btn_count = await self._page.locator('button:has-text("登录")').count()
        current_url = self._page.url
        
        if login_btn_count > 0 or 'signin' in current_url:
            logger.warning("[zhihu] 未登录! 请先运行 first_run 完成登录")
            return False
        
        logger.info("[zhihu] 已登录")
        return True
    
    async def _rate_limit(self):
        """速率限制"""
        self._request_count += 1
        loop = asyncio.get_event_loop()
        elapsed = loop.time() - self._minute_start
        
        if self._request_count >= self.requests_per_minute:
            if elapsed < 60:
                sleep_time = 60 - elapsed
                logger.debug(f"[zhihu] 速率限制，等待 {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = loop.time()
    
    async def _request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """发送请求（通过 Playwright page.evaluate fetch）"""
        await self._rate_limit()
        
        if not self._page or not self._context:
            logger.error("[zhihu] 请求失败: 浏览器未初始化")
            return None
        
        # 确保在知乎域名上
        current_url = self._page.url or ''
        if not current_url.startswith(self.BASE_URL):
            await self._page.goto(f"{self.BASE_URL}/hot", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
        
        payload = {'url': url, 'method': method}
        
        try:
            # 首先尝试 page.evaluate fetch
            try:
                response = await self._page.evaluate("""
                    async ({ url, method }) => {
                        const response = await fetch(url, {
                            method: method,
                            credentials: 'include'
                        });
                        const text = await response.text();
                        let data = null;
                        try { data = JSON.parse(text); } catch { data = { text: text }; }
                        return { status: response.status, data: data };
                    }
                """, payload)
            except Exception as page_error:
                logger.debug(f"[zhihu] page.evaluate fetch 失败，改用 context.request: {page_error}")
                api_resp = await self._context.request.get(url, timeout=30000)
                text = await api_resp.text()
                import json
                try:
                    data = json.loads(text)
                except:
                    data = {'text': text}
                response = {'status': api_resp.status, 'data': data}
            
            if response['status'] == 200:
                return response['data']
            else:
                logger.warning(f"[zhihu] 请求失败: status={response['status']}, url={url}")
                return None
        except Exception as e:
            logger.warning(f"[zhihu] 请求异常: {e}")
            return None
    
    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """搜索知乎内容"""
        logger.info(f"[zhihu] 搜索: keyword={keyword}, limit={limit}")
        
        offset = 0
        batch_size = 20
        yielded = 0
        
        while yielded < limit:
            query = urllib.parse.quote(keyword)
            url = f"{self.BASE_URL}/api/v4/search_v3?t=general&q={query}&correction=1&offset={offset}&limit={batch_size}"
            
            data = await self._request('GET', url)
            if not data or 'data' not in data:
                break
            
            batch = data.get('data', [])
            if not batch:
                break
            
            for raw_item in batch:
                if yielded >= limit:
                    break
                
                # 解包 search_v3 的 object 包装
                content = raw_item.get('object', raw_item) if isinstance(raw_item, dict) else raw_item
                if not isinstance(content, dict):
                    continue
                
                item = self._parse_item(content)
                if item:
                    yielded += 1
                    yield item
            
            offset += len(batch)
            if len(batch) < batch_size:
                break
        
        logger.info(f"[zhihu] 搜索完成: keyword={keyword}, 结果={yielded}")
    
    async def get_trending(self, category: str = "", limit: int = 20) -> AsyncIterator[CrawlItem]:
        """获取知乎热门内容"""
        logger.info(f"[zhihu] 获取热门: limit={limit}")
        
        # 使用搜索 "热门" 作为热门内容获取方式
        async for item in self.search("热门", limit=limit):
            yield item
    
    async def get_content(self, item: CrawlItem) -> str:
        """获取文章/回答完整正文"""
        if not self._page:
            return ""
        
        try:
            await self._page.goto(item.url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            content = await self._page.evaluate("""
                () => {
                    const selectors = [
                        '.Post-RichTextContainer',
                        '.RichText',
                        '.QuestionAnswer-content',
                        'article',
                        '.ContentItem-content'
                    ];
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el) return el.innerText;
                    }
                    return null;
                }
            """)
            
            if content:
                logger.debug(f"[zhihu] 正文获取成功: len={len(content)}, url={item.url}")
                return content
            return ""
        except Exception as e:
            logger.warning(f"[zhihu] 正文获取失败: {e}, url={item.url}")
            return ""
    
    def _parse_item(self, raw: Dict) -> Optional[CrawlItem]:
        """解析知乎 API 返回的原始数据为 CrawlItem"""
        item_type = raw.get('type', '')
        item_id = str(raw.get('id', ''))
        
        if not item_id:
            return None
        
        title = ""
        url = ""
        
        # 判断类型：answer 优先于 article
        if item_type == 'answer' or 'question' in raw:
            question = raw.get('question', {}) if isinstance(raw.get('question'), dict) else {}
            title = raw.get('title', '') or question.get('name', '') or question.get('title', '')
            question_id = question.get('id', '')
            if question_id:
                url = f"https://www.zhihu.com/question/{question_id}"
            actual_type = "answer"
        elif item_type == 'article' or 'title' in raw:
            title = raw.get('title', '')
            url = f"https://zhuanlan.zhihu.com/p/{item_id}"
            actual_type = "article"
        else:
            return None
        
        if not title and not url:
            return None
        
        # 提取作者
        author = ""
        if 'author' in raw and isinstance(raw['author'], dict):
            author = raw['author'].get('name', '')
        
        # 提取数据
        voteup = raw.get('voteup_count', 0)
        comment_count = raw.get('comment_count', 0)
        excerpt = raw.get('excerpt', '') or raw.get('content', '')[:300]
        
        # 发布时间
        published_at = None
        if 'created' in raw:
            try:
                published_at = datetime.fromtimestamp(raw['created']).isoformat()
            except:
                pass
        
        return CrawlItem(
            source="zhihu",
            item_type=actual_type,
            item_id=item_id,
            title=title,
            url=url,
            author=author,
            excerpt=excerpt,
            voteup=voteup,
            comment_count=comment_count,
            published_at=published_at,
            metadata={
                "question_id": raw.get('question', {}).get('id', '') if isinstance(raw.get('question'), dict) else '',
                "answer_count": raw.get('answer_count', 0),
            }
        )
