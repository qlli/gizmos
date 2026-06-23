"""HTTP 请求退避工具 - 限流重试 + 指数退避

供各爬虫复用：遇到限流(403/429)或网络异常时，按指数退避重试，
并优先尊重服务端 Retry-After / X-RateLimit-Reset 提示。
"""
import asyncio
import random
from typing import Optional, Sequence

import httpx
from loguru import logger


def _backoff_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """指数退避 + 随机抖动"""
    delay = base_delay * (2 ** attempt)
    delay = min(delay, max_delay)
    return delay + random.uniform(0, 1.0)


def _retry_after_delay(resp: httpx.Response, max_delay: float) -> Optional[float]:
    """从响应头解析服务端建议的等待秒数"""
    # 标准 Retry-After（秒）
    retry_after = resp.headers.get("retry-after")
    if retry_after:
        try:
            return min(float(retry_after), max_delay)
        except ValueError:
            pass

    # GitHub 风格的限流重置时间（epoch 秒）
    reset = resp.headers.get("x-ratelimit-reset")
    if reset:
        try:
            import time
            delta = int(reset) - int(time.time())
            if delta > 0:
                return min(float(delta), max_delay)
        except ValueError:
            pass

    return None


async def request_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[dict] = None,
    max_retries: int = 2,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    rate_limit_statuses: Sequence[int] = (403, 429),
    tag: str = "http",
) -> Optional[httpx.Response]:
    """带退避重试的 GET 请求

    Args:
        client: httpx 异步客户端
        url: 请求地址
        params: 查询参数
        max_retries: 最大重试次数（不含首次请求）
        base_delay: 退避基础秒数
        max_delay: 单次等待上限秒数
        rate_limit_statuses: 视为限流的状态码
        tag: 日志标识

    Returns:
        最终的 httpx.Response（调用方自行判断 status_code）；
        若多次网络异常仍失败则返回 None。
    """
    attempt = 0
    while True:
        try:
            resp = await client.get(url, params=params)
        except Exception as e:
            if attempt >= max_retries:
                logger.warning(f"[{tag}] 请求异常重试耗尽: {e}")
                return None
            delay = _backoff_delay(attempt, base_delay, max_delay)
            logger.warning(f"[{tag}] 请求异常, {delay:.1f}s后重试 "
                           f"({attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(delay)
            attempt += 1
            continue

        # 限流：退避后重试
        if resp.status_code in rate_limit_statuses:
            if attempt >= max_retries:
                logger.warning(f"[{tag}] 限流重试耗尽 (status={resp.status_code})")
                return resp
            delay = _retry_after_delay(resp, max_delay) or _backoff_delay(attempt, base_delay, max_delay)
            logger.warning(f"[{tag}] 限流(status={resp.status_code}), {delay:.1f}s后重试 "
                           f"({attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)
            attempt += 1
            continue

        # 其余情况（含成功与非限流错误）直接返回，由调用方处理
        return resp
