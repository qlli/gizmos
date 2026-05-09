"""OpenAI客户端"""
import json
from typing import Optional, Dict, List
from loguru import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..utils.config import get_config
from .budget_controller import BudgetController


class OpenAIClient:
    """OpenAI API客户端"""
    
    def __init__(self, api_key: str = None, model: str = None):
        if OpenAI is None:
            raise ImportError("请安装 openai 库: pip install openai")
        
        config = get_config()
        openai_config = config.ai_analysis.get('openai', {})
        
        self.api_key = api_key or openai_config.get('api_key', '')
        self.model = model or openai_config.get('model', 'gpt-4o-mini')
        self.max_tokens = openai_config.get('max_tokens', 2000)
        self.temperature = openai_config.get('temperature', 0.3)
        
        self.prompt_config = config.ai_analysis.get('analysis_prompt', {})
        
        if not self.api_key or self.api_key == 'YOUR_OPENAI_API_KEY' or self.api_key.startswith('YOUR_'):
            logger.warning("OpenAI API Key 未配置，AI分析将自动跳过并使用基础规则评分")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
        self.budget_controller = BudgetController()
    
    def is_available(self) -> bool:
        """OpenAI 客户端是否可用"""
        return self.client is not None
    
    def analyze_content(self, title: str, author: str, content: str) -> Optional[Dict]:
        """分析文章内容"""
        if not self.client:
            logger.warning("OpenAI客户端未初始化，跳过AI分析")
            return None
        
        # 检查预算
        if not self.budget_controller.can_proceed():
            logger.warning("预算不足，跳过分析")
            return None
        
        # 构建提示
        system_prompt = self.prompt_config.get('system', 
            '你是一个专业的内容质量评估专家，专门评估知乎文章的质量和价值。')
        
        user_template = self.prompt_config.get('user_template', 
            '请分析以下知乎文章，判断其质量：\n\n标题：{title}\n作者：{author}\n内容：{content}\n\n请评估：\n1. 内容质量（1-5星）\n2. 是否为高质量内容\n3. 是否可能包含广告或低质内容\n4. 主要内容摘要（100字内）\n5. 是否推荐阅读\n\n请以JSON格式输出。')
        
        user_prompt = user_template.format(title=title, author=author, content=content[:8000])
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # 获取token使用量
            usage = response.usage
            usage_record = self.budget_controller.record_usage(
                usage.prompt_tokens,
                usage.completion_tokens,
                self.model
            )
            
            logger.debug(f"Token使用: {usage_record['total_tokens']}, 成本: ${usage_record['cost']:.4f}")
            
            # 解析响应
            content_text = response.choices[0].message.content
            result = json.loads(content_text)
            
            result['_usage'] = usage_record
            return result
            
        except Exception as e:
            error_text = str(e)
            if '401' in error_text or 'invalid_api_key' in error_text or 'Incorrect API key' in error_text:
                logger.error("OpenAI API Key 无效，后续文章将跳过AI分析并使用基础规则评分")
                self.client = None
            else:
                logger.error(f"OpenAI API调用失败: {e}")
            return None
    
    def summarize_content(self, content: str, max_length: int = 200) -> Optional[str]:
        """总结内容"""
        if not self.client:
            return None
        
        if not self.budget_controller.can_proceed(estimated_cost=0.001):
            return None
        
        system_prompt = "你是一个专业的文章摘要生成器，请简洁地总结文章要点。"
        user_prompt = f"请用不超过{max_length}字总结以下文章：\n\n{content[:8000]}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            usage = response.usage
            self.budget_controller.record_usage(
                usage.prompt_tokens,
                usage.completion_tokens,
                self.model
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return None
    
    def batch_analyze(self, articles: List[Dict], content_key: str = 'content') -> List[Dict]:
        """批量分析"""
        results = []
        
        for i, article in enumerate(articles):
            logger.info(f"分析进度: {i+1}/{len(articles)}")
            
            content = article.get(content_key, '')
            if not content:
                content = article.get('excerpt', '')
            
            analysis = self.analyze_content(
                title=article.get('title', ''),
                author=article.get('author', ''),
                content=content
            )
            
            if analysis:
                result = {**article, 'analysis': analysis}
                results.append(result)
            else:
                # 预算不足时停止
                if not self.budget_controller.can_proceed():
                    logger.warning("预算不足，停止分析")
                    break
            
            # 添加延迟避免限流
            import time
            time.sleep(0.5)
        
        return results
