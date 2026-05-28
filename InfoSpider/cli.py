"""InfoSpider CLI - 智能信息采集命令行入口"""
import asyncio
from typing import List, Optional

import typer
from loguru import logger

app = typer.Typer(
    name="infospider",
    help="InfoSpider - 智能信息采集系统",
    add_completion=False
)


def _setup():
    """初始化配置和日志"""
    from src.utils.config import get_config
    from src.utils.logger import setup_logger
    
    config = get_config()
    config.load()
    setup_logger()


@app.command()
def collect(
    sources: List[str] = typer.Option(["bilibili"], "--source", "-s", help="信息源(可多次指定): zhihu, bilibili"),
    keywords: List[str] = typer.Option([], "--keyword", "-k", help="搜索关键词(可多次指定)"),
    limit: int = typer.Option(20, "--limit", "-l", help="每个源的最大采集数量"),
    trending: bool = typer.Option(False, "--trending", "-t", help="获取热门内容(不指定关键词时)"),
    user: str = typer.Option("default", "--user", "-u", help="用户ID"),
    no_report: bool = typer.Option(False, "--no-report", help="不自动打开HTML报告"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="浏览器无头模式"),
):
    """采集信息 - 从指定源搜索或获取热门内容"""
    _setup()
    
    # 注册爬虫（触发模块导入）
    _register_crawlers()
    
    from src.core.pipeline.collector import CollectorStage
    from src.core.crawler.registry import CrawlerRegistry
    
    # 验证源
    available = CrawlerRegistry.list_sources()
    for s in sources:
        if s not in available:
            typer.echo(f"错误: 未知的信息源 '{s}'，可用: {available}")
            raise typer.Exit(1)
    
    task_type = "trending" if trending else "search"
    
    if task_type == "search" and not keywords:
        typer.echo("提示: 未指定关键词，将使用热门模式")
        task_type = "trending"
    
    typer.echo(f"开始采集: 源={sources}, 关键词={keywords or '热门'}, 数量={limit}")
    
    async def _run():
        async with CollectorStage() as stage:
            results = await stage.run(
                sources=sources,
                keywords=keywords if keywords else None,
                limit=limit,
                task_type=task_type,
                user_id=user,
                auto_open_report=not no_report,
            )
            return results
    
    results = asyncio.run(_run())
    
    typer.echo(f"\n采集完成! 共 {len(results)} 条匹配结果")
    if results:
        typer.echo("\n前5条结果:")
        for i, item in enumerate(results[:5], 1):
            typer.echo(f"  {i}. [{item.source}/{item.item_type}] {item.title}")
            typer.echo(f"     {item.url}")
            typer.echo(f"     👍{item.voteup} 👁{item.view_count} 💬{item.comment_count}")


@app.command()
def sources():
    """列出所有可用的信息源"""
    _setup()
    _register_crawlers()
    
    from src.core.crawler.registry import CrawlerRegistry
    
    all_sources = CrawlerRegistry.list_all()
    
    typer.echo("可用的信息源:")
    typer.echo("-" * 40)
    for name, cls in all_sources.items():
        typer.echo(f"  {name:<12} ({cls.source_type}) - {cls.__doc__.strip().split(chr(10))[0] if cls.__doc__ else ''}")


@app.command()
def profile(
    user: str = typer.Option("default", "--user", "-u", help="用户ID"),
    add_interest: Optional[str] = typer.Option(None, "--add", help="添加兴趣标签 (格式: tag:weight)"),
    remove_interest: Optional[str] = typer.Option(None, "--remove", help="移除兴趣标签"),
    show: bool = typer.Option(True, "--show/--no-show", help="显示画像信息"),
):
    """管理用户画像"""
    _setup()
    
    from src.models.user import UserProfile
    from src.utils.config import get_config
    
    config = get_config()
    profiles_dir = config.get('storage.profiles_path', 'data/profiles')
    
    user_profile = UserProfile.load(user, profiles_dir)
    
    if add_interest:
        parts = add_interest.split(":")
        tag = parts[0]
        weight = float(parts[1]) if len(parts) > 1 else 0.5
        user_profile.interests.add_interest(tag, weight)
        user_profile.save(profiles_dir)
        typer.echo(f"已添加兴趣: {tag} (权重={weight})")
    
    if remove_interest:
        user_profile.interests.remove_interest(remove_interest)
        user_profile.save(profiles_dir)
        typer.echo(f"已移除兴趣: {remove_interest}")
    
    if show:
        typer.echo(f"\n用户画像: {user_profile.user_id}")
        typer.echo("-" * 40)
        typer.echo(f"  职业: {user_profile.profession or '未设置'}")
        typer.echo(f"  学历: {user_profile.education or '未设置'}")
        typer.echo(f"  启用源: {user_profile.source_prefs.enabled_sources}")
        typer.echo(f"  兴趣标签:")
        if user_profile.interests.tags:
            for tag, weight in sorted(user_profile.interests.tags.items(), key=lambda x: -x[1]):
                bar = "█" * int(weight * 10)
                typer.echo(f"    {tag:<16} {weight:.2f} {bar}")
        else:
            typer.echo("    (空)")


@app.command()
def init_profile(
    user: str = typer.Option("default", "--user", "-u", help="用户ID"),
    profession: str = typer.Option("", "--profession", "-p", help="职业"),
    education: str = typer.Option("", "--education", "-e", help="学历"),
    interests: List[str] = typer.Option([], "--interest", "-i", help="兴趣标签(可多次)"),
):
    """初始化用户画像"""
    _setup()
    
    from src.models.user import UserProfile
    from src.utils.config import get_config
    
    config = get_config()
    profiles_dir = config.get('storage.profiles_path', 'data/profiles')
    
    user_profile = UserProfile(user_id=user)
    user_profile.profession = profession
    user_profile.education = education
    
    for interest in interests:
        user_profile.interests.add_interest(interest, 0.7)
    
    user_profile.save(profiles_dir)
    typer.echo(f"用户画像已创建: {user} (兴趣: {interests})")


def _register_crawlers():
    """导入所有爬虫模块以触发注册"""
    import src.core.crawler.zhihu  # noqa: F401
    import src.core.crawler.bilibili  # noqa: F401
    import src.core.crawler.github  # noqa: F401



if __name__ == "__main__":
    app()
