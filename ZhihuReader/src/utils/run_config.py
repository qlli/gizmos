"""运行配置加载工具。

运行配置用于描述一次爬虫任务的输入条件。当前仅支持 keywords，后续可扩展更多字段。
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
COLLECTION_CONFIG_DIR = CONFIG_DIR / "collections"


class RunConfigError(ValueError):
    """运行配置错误。"""


def _candidate_paths(config_name_or_path: str) -> List[Path]:
    """根据名称或路径生成候选配置路径。"""
    raw = Path(config_name_or_path)
    candidates = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([
            Path.cwd() / raw,
            CONFIG_DIR / raw,
            CONFIG_DIR / f"{config_name_or_path}.json",
            COLLECTION_CONFIG_DIR / raw,
            COLLECTION_CONFIG_DIR / f"{config_name_or_path}.json",
        ])

    # 去重且保持顺序
    unique = []
    seen = set()
    for path in candidates:
        resolved_key = str(path.resolve())
        if resolved_key not in seen:
            seen.add(resolved_key)
            unique.append(path)
    return unique


def resolve_run_config_path(config_name_or_path: str) -> Path:
    """解析运行配置路径。"""
    for path in _candidate_paths(config_name_or_path):
        if path.exists() and path.is_file():
            return path

    tried = "\n".join(f"  - {p}" for p in _candidate_paths(config_name_or_path))
    raise RunConfigError(f"运行配置不存在: {config_name_or_path}\n已尝试:\n{tried}")


def load_run_config(config_name_or_path: Optional[str]) -> Dict[str, Any]:
    """加载运行配置 JSON。

    配置格式当前支持：
    {
      "name": "tech",
      "keywords": ["Unity", "Unreal"]
    }
    """
    if not config_name_or_path:
        logger.info("[RUN_CONFIG] 未指定运行配置，使用命令行参数和默认配置")
        return {}

    config_path = resolve_run_config_path(config_name_or_path)
    logger.info(f"[RUN_CONFIG] 加载运行配置: {config_path.resolve()}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RunConfigError(f"运行配置 JSON 格式错误: {config_path}, error={e}") from e
    except Exception as e:
        raise RunConfigError(f"运行配置加载失败: {config_path}, error={e}") from e

    if not isinstance(data, dict):
        raise RunConfigError(f"运行配置根节点必须是对象: {config_path}")

    keywords = data.get("keywords", [])
    if keywords is None:
        keywords = []
    if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
        raise RunConfigError("运行配置字段 keywords 必须是字符串数组")

    # 规整关键词，去除空字符串和重复项。
    normalized_keywords = []
    seen = set()
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword and keyword not in seen:
            seen.add(keyword)
            normalized_keywords.append(keyword)

    data["keywords"] = normalized_keywords
    data["_config_path"] = str(config_path.resolve())

    logger.info(
        f"[RUN_CONFIG] 运行配置加载完成: name={data.get('name', config_path.stem)}, "
        f"keywords_count={len(normalized_keywords)}, keywords={normalized_keywords}"
    )
    return data
