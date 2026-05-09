"""知乎API客户端 - 使用 Playwright 实现"""
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from ..utils.config import get_config


class ZhihuClient:
    """知乎客户端 - 使用 Playwright 绕过反爬"""
    
    BASE_URL = "https://www.zhihu.com"
    USER_DATA_DIR = "data/browser_data"  # Cookie 持久化目录
    
    def __init__(self, headless: bool = True):
        """
        初始化知乎客户端
        
        Args:
            headless: 是否无头模式（True=后台运行，False=显示浏览器）
        """
        self.headless = headless
        self.user_data_dir = Path(self.USER_DATA_DIR)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self.config = get_config()
        self.rate_limit = self.config.get('crawler.zhihu.rate_limit', {})
        self.requests_per_minute = self.rate_limit.get('requests_per_minute', 20)
        self._request_count = 0
        self._minute_start = time.time()
    
    def __enter__(self):
        """上下文管理器入口"""
        self._start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def _start_browser(self):
        """启动浏览器（持久化 Cookie + stealth 反检测）"""
        logger.info("[STEP 1/8] 启动 Playwright + 浏览器")
        self.playwright = sync_playwright().start()
        logger.info(
            f"[STEP 1/8] 准备启动浏览器: headless={self.headless}, user_data_dir={self.user_data_dir.resolve()}"
        )
        
        # 使用持久化上下文（自动保存/加载 Cookie）
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            java_script_enabled=True,
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        
        # 使用 playwright-stealth 隐藏自动化特征
        stealth = Stealth()
        stealth.apply_stealth_sync(self.context)
        
        logger.info(f"[STEP 1/8] 浏览器已启动（stealth 模式），Cookie 存储: {self.user_data_dir.resolve()}, 当前页面数: {len(self.context.pages)}")
    
    def _check_login_required(self) -> bool:
        """检查是否需要登录"""
        logger.info(f"[STEP 2/8] 访问 {self.BASE_URL}/hot 检查登录状态")
        try:
            # 访问知乎首页，检查是否已登录
            self.page.goto(f"{self.BASE_URL}/hot", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            
            login_btn_count = self.page.locator('button:has-text("登录")').count()
            current_url = self.page.url
            logger.info(f"[STEP 2/8] 当前页面: url={current_url}, 登录按钮数={login_btn_count}")
            
            # 检查是否存在登录按钮（未登录标志）
            if login_btn_count > 0:
                logger.warning("[STEP 2/8] 检测到登录按钮，需要登录")
                return True
            
            # 检查 URL 是否被重定向到登录页
            if 'signin' in current_url:
                logger.warning(f"[STEP 2/8] URL 包含 signin，需要登录: {current_url}")
                return True
            
            logger.info("[STEP 2/8] 已登录")
            return False
        except Exception as e:
            logger.warning(f"[STEP 2/8] 检查登录状态时出错: {e}")
            return True
    
    def ensure_logged_in(self):
        """确保已登录（如果需要，提示用户手动登录）"""
        logger.info("[STEP 2/8] 验证知乎登录状态")
        if self._check_login_required():
            logger.warning("=" * 60)
            logger.warning("需要登录知乎！")
            logger.warning("请在浏览器中完成登录（扫码或账号密码）")
            logger.warning("登录完成后，程序会自动继续...")
            logger.warning("=" * 60)
            
            # 切换到有头模式（如果当前是无头模式）
            if self.headless:
                logger.info("切换到有头模式以完成登录...")
                self.close()
                self.headless = False
                self._start_browser()
                self.page.goto(f"{self.BASE_URL}/hot", wait_until="domcontentloaded", timeout=30000)
            
            # 等待用户登录
            self._wait_for_login()
    
    def _wait_for_login(self, timeout: int = 300):
        """
        等待用户登录
        
        Args:
            timeout: 超时时间（秒）
        """
        logger.info("等待登录中...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 检查是否已登录
                if self.page.locator('button:has-text("登录")').count() == 0 and 'signin' not in self.page.url:
                    logger.info("登录成功！")
                    return
            except:
                pass
            
            time.sleep(2)
        
        logger.error("登录超时！请重试。")
        raise TimeoutError("登录超时")
    
    def _rate_limit(self):
        """速率限制"""
        self._request_count += 1
        elapsed = time.time() - self._minute_start
        
        if self._request_count >= self.requests_per_minute:
            if elapsed < 60:
                sleep_time = 60 - elapsed
                logger.debug(f"速率限制，等待 {sleep_time:.1f} 秒")
                time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()
    
    def _request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """发送请求（使用 Playwright）"""
        self._rate_limit()
        
        if self.page is None or self.context is None:
            logger.error(f"[STEP 3/8] 请求失败: 浏览器尚未初始化，method={method}, url={url}")
            return None
        
        headers = kwargs.get('headers', {}) or {}
        body = kwargs.get('json', None)
        payload = {
            'url': url,
            'method': method,
            'headers': headers,
            'body': body
        }
        
        try:
            current_url = self.page.url or ''
            if not current_url.startswith(self.BASE_URL):
                logger.info(f"[STEP 3/8] 当前页面不在知乎域名，先进入知乎页面: current_url={current_url}")
                self.page.goto(f"{self.BASE_URL}/hot", wait_until="domcontentloaded", timeout=30000)
                time.sleep(1)
            
            logger.info(f"[STEP 3/8] 发起知乎接口请求: {method} {url}")
            logger.debug(f"[STEP 3/8] 请求来源页面 page_url={self.page.url}")
            
            try:
                # 使用 page.evaluate 发送请求。Playwright 只能传一个 arg，因此用 payload 打包参数。
                response = self.page.evaluate("""
                    async ({ url, method, headers, body }) => {
                        const response = await fetch(url, {
                            method: method,
                            headers: headers,
                            credentials: 'include',
                            body: body ? JSON.stringify(body) : undefined
                        });
                        
                        const text = await response.text();
                        let data = null;
                        try {
                            data = JSON.parse(text);
                        } catch {
                            data = { text: text };
                        }
                        
                        return {
                            status: response.status,
                            data: data,
                            url: response.url,
                            source: 'page.fetch'
                        };
                    }
                """, payload)
            except Exception as page_error:
                logger.warning(f"页面 fetch 失败，改用 BrowserContext.request 重试: {page_error}")
                if method.upper() == 'GET':
                    api_response = self.context.request.get(url, headers=headers, timeout=30000)
                else:
                    api_response = self.context.request.fetch(
                        url,
                        method=method,
                        headers=headers,
                        data=json.dumps(body) if body is not None else None,
                        timeout=30000
                    )
                
                text = api_response.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {'text': text}
                
                response = {
                    'status': api_response.status,
                    'data': data,
                    'url': api_response.url,
                    'source': 'context.request'
                }
            
            data = response.get('data')
            data_count = len(data.get('data', [])) if isinstance(data, dict) and isinstance(data.get('data'), list) else 'unknown'
            logger.info(
                f"[STEP 3/8] 知乎请求完成: source={response.get('source')}, status={response.get('status')}, "
                f"final_url={response.get('url')}, data_count={data_count}"
            )
            
            if response['status'] == 200:
                return response['data']
            elif response['status'] == 401:
                logger.error("[STEP 3/8] 知乎 Cookie 失效，请删除 data/browser_data 目录后重新运行 first_run.py 登录")
                return None
            elif response['status'] == 403:
                logger.error("[STEP 3/8] 请求被拒绝 (403)，可能需要重新登录或被反爬拦截")
                return None
            else:
                logger.warning(f"[STEP 3/8] 请求失败: status={response['status']}, URL={url}")
                return None
        
        except Exception as e:
            logger.warning(f"[STEP 3/8] 请求异常: {e}")
            return None
    
    def get_hot_content(self, limit: int = 100) -> List[Dict]:
        """获取热门内容"""
        logger.info(f"[STEP 3/8] 开始获取热门内容，目标条数: {limit}")
        
        articles = []
        offset = 0
        batch_size = 20
        
        while len(articles) < limit:
            url = f"{self.BASE_URL}/api/v4/search_v3?t=general&q=%E7%83%AD%E9%97%A8&correction=1&offset={offset}&limit={batch_size}&search_source=Normal_Search"
            
            logger.info(f"[STEP 3/8] 热门内容分页请求: offset={offset}, limit={batch_size}")
            data = self._request('GET', url)
            if not data or 'data' not in data:
                logger.warning(
                    f"[STEP 3/8] 热门内容分页无有效数据: offset={offset}, response_keys={list(data.keys()) if isinstance(data, dict) else None}"
                )
                break
            
            batch = data.get('data', [])
            logger.info(f"[STEP 3/8] 热门内容分页返回: offset={offset}, batch_count={len(batch)}")
            if not batch:
                logger.warning(f"[STEP 3/8] 热门内容分页返回空列表: offset={offset}")
                break
            
            articles.extend(batch)
            logger.info(f"[STEP 3/8] 累计已获取 {len(articles)} 条原始数据")
            
            offset += len(batch)
            
            if len(batch) < batch_size:
                break
        
        logger.info(f"[STEP 3/8] 热门接口抓取结束: 累计 {len(articles)} 条原始数据，将截取前 {limit} 条")
        return articles[:limit]
    
    def get_article_content(self, url: str) -> Optional[str]:
        """获取文章/回答内容"""
        try:
            if self.page is None:
                logger.warning(f"[STEP 6/8] 获取正文失败: 浏览器页面尚未初始化，url={url}")
                return None
            
            logger.info(f"[STEP 6/8] 打开文章页面抓取正文: {url}")
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            logger.info(f"[STEP 6/8] 页面加载完成: final_url={self.page.url}")
            
            # 尝试提取内容
            content = self.page.evaluate("""
                () => {
                    // 尝试多种选择器
                    const selectors = [
                        '.Post-RichTextContainer',
                        '.RichText',
                        '.QuestionAnswer-content',
                        'article',
                        '.ContentItem-content'
                    ];
                    
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el) return { selector, text: el.innerText };
                    }
                    
                    return null;
                }
            """)
            
            if content and content.get('text'):
                text = content['text']
                logger.info(
                    f"[STEP 6/8] 文章正文获取成功: selector={content.get('selector')}, len={len(text)}, url={url}"
                )
                return text
            else:
                logger.warning(f"[STEP 6/8] 文章正文为空，可能是登录态过期或反爬: url={url}")
                return None
        except Exception as e:
            logger.warning(f"[STEP 6/8] 获取正文失败: {e}, url={url}")
            return None
    
    def search(self, keyword: str, limit: int = 50) -> List[Dict]:
        """搜索内容"""
        logger.info(f"搜索关键词: {keyword}")
        
        articles = []
        offset = 0
        batch_size = 20
        
        while len(articles) < limit:
            import urllib.parse
            query = urllib.parse.quote(keyword)
            url = f"{self.BASE_URL}/api/v4/search_v3?t=general&q={query}&correction=1&offset={offset}&limit={batch_size}&search_source=Normal_Search"
            
            data = self._request('GET', url)
            if not data or 'data' not in data:
                break
            
            batch = data.get('data', [])
            if not batch:
                break
            
            articles.extend(batch)
            logger.info(f"已获取 {len(articles)} 条搜索结果")
            
            offset += len(batch)
            
            if len(batch) < batch_size:
                break
        
        return articles[:limit]
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
