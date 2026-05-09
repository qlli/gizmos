#!/usr/bin/env python3
"""
ZhihuReader 主程序
知乎高质量内容阅读器

Usage:
    python main.py                    # 运行完整流水线
    python main.py --collect         # 仅搜集
    python main.py --analyze         # 仅分析
    python main.py --archive         # 仅存档
    python main.py --stock           # 存量内容处理
    python main.py --incremental     # 增量内容处理
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger, get_logger
from src.utils.config import get_config
from src.pipeline.collector import CollectorStage
from src.pipeline.analyzer import AnalyzerStage
from src.pipeline.expander import ExpanderStage
from src.pipeline.archiver import ArchiverStage
from src.ai.budget_controller import BudgetController


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='ZhihuReader - 知乎高质量内容阅读器')
    
    parser.add_argument('--collect', action='store_true', help='仅运行搜集阶段')
    parser.add_argument('--analyze', action='store_true', help='仅运行分析阶段')
    parser.add_argument('--archive', action='store_true', help='仅运行存档阶段')
    parser.add_argument('--expand', action='store_true', help='运行扩展阶段')
    
    parser.add_argument('--stock', action='store_true', help='处理存量内容')
    parser.add_argument('--incremental', action='store_true', help='处理增量内容')
    
    parser.add_argument('--hot', action='store_true', help='搜集热门内容')
    parser.add_argument('--keywords', nargs='*', help='按关键词搜集')
    parser.add_argument('--limit', type=int, default=100, help='搜集数量限制')
    
    parser.add_argument('--budget', action='store_true', help='显示预算状态')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--log-level', type=str, default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别')
    
    return parser.parse_args()


def run_pipeline(mode: str = 'full', headless: bool = True, **kwargs):
    """
    运行流水线
    
    Args:
        mode: 运行模式 (full/collect/analyze/expand)
        headless: 是否无头模式（True=后台运行，False=显示浏览器）
    """
    logger = get_logger("main")
    logger.info("=" * 60)
    logger.info(f"[PIPELINE] 启动流水线: {mode}")
    logger.info(f"[PIPELINE] 当前工作目录: {Path.cwd()}")
    logger.info(f"[PIPELINE] 项目根目录: {project_root.resolve()}")
    logger.info(f"[PIPELINE] 运行参数: headless={headless}, kwargs={kwargs}")
    logger.info("[PIPELINE] 流水线步骤说明:")
    logger.info("  STEP 1/8 启动 Playwright + 浏览器")
    logger.info("  STEP 2/8 验证知乎登录状态")
    logger.info("  STEP 3/8 调用知乎搜索/热门接口")
    logger.info("  STEP 4/8 解析并过滤元数据")
    logger.info("  STEP 5/8 保存原始 JSON")
    logger.info("  STEP 6/8 抓取文章正文")
    logger.info("  STEP 7/8 质量过滤 + AI 分析")
    logger.info("  STEP 8/8 归档到 Excel")
    logger.info("=" * 60)
    
    # 初始化各阶段（使用上下文管理器确保浏览器正确关闭）
    with CollectorStage(headless=headless) as collector:
        analyzer = AnalyzerStage(zhihu_client=collector.client)
        expander = ExpanderStage()
        archiver = ArchiverStage()
        
        is_stock = kwargs.get('is_stock', True)
        analyzed_articles = None
        
        if mode == 'full' or mode == 'collect':
            # 阶段1: 搜集
            logger.info("[PIPELINE] === 进入搜集阶段 (STEP 1-5) ===")
            if kwargs.get('hot'):
                logger.info(f"[PIPELINE] 搜集模式: hot, limit={kwargs.get('limit', 100)}")
                articles = collector.run(mode='hot', limit=kwargs.get('limit', 100))
            elif kwargs.get('keywords'):
                logger.info(f"[PIPELINE] 搜集模式: keywords, keywords={kwargs.get('keywords')}")
                articles = collector.run(mode='keywords', keywords=kwargs.get('keywords'))
            else:
                logger.info(f"[PIPELINE] 搜集模式: default hot, limit={kwargs.get('limit', 100)}")
                articles = collector.run(mode='hot', limit=kwargs.get('limit', 100))
            
            logger.info(f"[PIPELINE] 搜集阶段产出 {len(articles)} 篇文章")
            collector.save_for_processing(articles, is_stock=is_stock)
            
            if mode == 'collect':
                logger.info("[PIPELINE] 仅搜集模式，流水线在搜集阶段后结束")
                return articles
        
        if mode == 'full' or mode == 'analyze':
            # 阶段2: 分析
            logger.info("[PIPELINE] === 进入分析阶段 (STEP 6-7) ===")
            result = analyzer.run()
            analyzed_articles = result.get('passed', []) + result.get('failed', [])
            logger.info(
                f"[PIPELINE] 分析阶段结束: passed={len(result.get('passed', []))}, "
                f"failed={len(result.get('failed', []))}, skipped={len(result.get('skipped', []))}, "
                f"current_analyzed={len(analyzed_articles)}"
            )
            
            if mode == 'analyze':
                logger.info("[PIPELINE] 仅分析模式，流水线在分析阶段后结束")
                return result
        
        if mode == 'expand' or mode == 'full':
            # 阶段3: 扩展（低优先级）
            if kwargs.get('enable_expand', False):
                logger.info("[PIPELINE] === 进入扩展阶段 ===")
                expander.run()
        
        if mode == 'full' or mode == 'archive':
            # 阶段4: 汇总
            logger.info("[PIPELINE] === 进入归档阶段 (STEP 8) ===")
            if analyzed_articles is not None:
                logger.info(f"[PIPELINE] 归档使用本次分析结果: {len(analyzed_articles)} 篇")
                result = archiver.run(articles=analyzed_articles)
            else:
                logger.info("[PIPELINE] 未发现本次分析结果，归档阶段将加载历史 analyzed 文件")
                result = archiver.run()
            logger.info(f"[PIPELINE] 归档阶段结束: archived={len(result.get('archived', []))}")
            
            if mode == 'archive':
                logger.info("[PIPELINE] 仅存档模式，流水线在存档阶段后结束")
                return result
        
        if mode == 'full':
            # 显示预算状态
            budget = BudgetController()
            status = budget.get_status()
            logger.info(f"预算状态: 已使用 ${status['daily_cost']:.2f}/${status['daily_limit']}, "
                       f"剩余 ${status['remaining']:.2f}")
    
    return None


def show_budget_status():
    """显示预算状态"""
    budget = BudgetController()
    status = budget.get_status()
    
    print("\n" + "="*50)
    print("预算状态")
    print("="*50)
    print(f"日期: {status['date']}")
    print(f"已使用: ${status['daily_cost']:.2f}")
    print(f"每日限额: ${status['daily_limit']:.2f}")
    print(f"剩余: ${status['remaining']:.2f}")
    print(f"使用比例: {status['usage_percent']:.1f}%")
    print(f"Token使用: {status['total_tokens']:,}")
    print("="*50 + "\n")


def generate_report():
    """生成报告"""
    archiver = ArchiverStage()
    report = archiver.generate_report()
    
    print("\n" + "="*50)
    print("阅读器报告")
    print("="*50)
    print(f"生成时间: {report['generated_at']}")
    print(f"高质量文章: {report['total_archived']}")
    print(f"已评价文章: {report['total_reviewed']}")
    print(f"收藏文章: {report['total_favorites']}")
    print("\n评分分布:")
    for rating, count in report['rating_distribution'].items():
        print(f"  {rating}星: {count}")
    print(f"感兴趣: {report['interested_count']}")
    print("\n存储统计:")
    for key, value in report['storage_stats'].items():
        print(f"  {key}: {value}")
    print("="*50 + "\n")


def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志
    config = get_config()
    log_file = config.get('logging.file', 'logs/zhihu_reader.log')
    log_level = args.log_level or config.get('logging.level', 'INFO')
    
    setup_logger(log_file=log_file, level=log_level)
    logger = get_logger("main")
    
    logger.info("="*50)
    logger.info("ZhihuReader 启动")
    logger.info("="*50)
    
    # 显示预算状态
    if args.budget:
        show_budget_status()
        return
    
    # 生成报告
    if args.report:
        generate_report()
        return
    
    # 确定运行模式
    is_stock = args.stock and not args.incremental
    is_incremental = args.incremental and not args.stock
    
    # 根据参数确定模式
    if args.collect:
        mode = 'collect'
    elif args.analyze:
        mode = 'analyze'
    elif args.archive:
        mode = 'archive'
    elif args.expand:
        mode = 'expand'
    else:
        mode = 'full'
    
    kwargs = {
        'is_stock': is_stock or True,  # 默认存量
        'hot': args.hot,
        'keywords': args.keywords,
        'limit': args.limit,
        'enable_expand': args.expand
    }
    
    try:
        result = run_pipeline(mode=mode, **kwargs)
        logger.info("流水线执行完成")
        
        if result:
            if isinstance(result, list):
                logger.info(f"结果: {len(result)} 篇文章")
            elif isinstance(result, dict):
                result_items = result.get('archived') or result.get('passed') or result.get('articles') or []
                logger.info(f"结果: {len(result_items)} 篇文章")
            else:
                logger.info(f"结果: {result}")
            
    except KeyboardInterrupt:
        logger.warning("用户中断")
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise


if __name__ == '__main__':
    main()
