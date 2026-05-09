"""本地LLM支持"""
import json
import requests
from typing import Optional, Dict
from loguru import logger

from ..utils.config import get_config


class LocalLLMClient:
    """本地LLM客户端（如Ollama）"""
    
    def __init__(self, endpoint: str = None, model: str = None):
        config = get_config()
        local_config = config.ai_analysis.get('local_llm', {})
        
        self.enabled = local_config.get('enabled', False)
        self.endpoint = endpoint or local_config.get('endpoint', 
            'http://localhost:11434/api/generate')
        self.model = model or local_config.get('model', 'llama3')
        
        self.prompt_config = config.ai_analysis.get('analysis_prompt', {})
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.enabled:
            return False
        
        try:
            response = requests.get(
                self.endpoint.replace('/api/generate', '/api/tags'),
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def generate(self, prompt: str, system: str = None) -> Optional[str]:
        """生成文本"""
        if not self.is_available():
            logger.warning("本地LLM服务不可用")
            return None
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"本地LLM请求失败: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("本地LLM请求超时")
            return None
        except Exception as e:
            logger.error(f"本地LLM请求异常: {e}")
            return None
    
    def analyze_content(self, title: str, author: str, content: str) -> Optional[Dict]:
        """分析文章内容"""
        system_prompt = self.prompt_config.get('system', 
            '你是一个专业的内容质量评估专家，专门评估知乎文章的质量和价值。输出JSON格式。')
        
        user_template = self.prompt_config.get('user_template', 
            '请分析以下知乎文章，判断其质量。输出JSON：\n标题：{title}\n作者：{author}\n内容：{content}\n\n评估：质量1-5星，是否高质量，是否广告，摘要100字内，是否推荐。')
        
        user_prompt = user_template.format(title=title, author=author, content=content[:4000])
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = self.generate(full_prompt)
        
        if response:
            try:
                # 尝试提取JSON
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    return json.loads(response[json_start:json_end])
                else:
                    # 尝试直接解析
                    return json.loads(response)
            except json.JSONDecodeError:
                logger.warning("JSON解析失败")
                return {'raw_response': response, 'quality_score': 3}
        
        return None
