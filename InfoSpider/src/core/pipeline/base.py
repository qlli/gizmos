"""Pipeline 基类"""
from abc import ABC, abstractmethod
from typing import Any


class BasePipelineStage(ABC):
    """流水线阶段基类
    
    使用 async 上下文管理器确保资源正确释放:
        async with CollectorStage() as stage:
            result = await stage.run(params)
    """
    
    @abstractmethod
    async def setup(self) -> None:
        """阶段初始化（启动资源）"""
    
    @abstractmethod
    async def teardown(self) -> None:
        """阶段清理（释放资源）"""
    
    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """执行阶段逻辑"""
    
    async def __aenter__(self):
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()
