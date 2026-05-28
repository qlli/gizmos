"""HTML 报告生成器 - 多平台采集结果可视化"""
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List

from loguru import logger

from ..core.crawler.base import CrawlItem


class HTMLReportGenerator:
    """HTML 报告生成器
    
    生成采集结果的可视化HTML报告，支持多平台内容展示。
    """
    
    def __init__(self, reports_dir: str = "data/reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, items: List[CrawlItem], title: str = "采集报告",
                 auto_open: bool = True) -> str:
        """生成HTML报告
        
        Args:
            items: 采集结果
            title: 报告标题
            auto_open: 是否自动在浏览器中打开
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.reports_dir / f"report_{timestamp}.html"
        
        html = self._build_html(items, title)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        abs_path = file_path.resolve()
        logger.info(f"[REPORT] HTML报告已生成 → {abs_path}")
        
        if auto_open:
            webbrowser.open(str(abs_path))
        
        return str(abs_path)
    
    def _build_html(self, items: List[CrawlItem], title: str) -> str:
        """构建HTML内容"""
        # 按来源分组统计
        source_stats = {}
        for item in items:
            source_stats[item.source] = source_stats.get(item.source, 0) + 1
        
        stats_html = " | ".join(f"{s}: {c}条" for s, c in source_stats.items())
        
        rows_html = ""
        for i, item in enumerate(items, 1):
            type_badge = self._get_type_badge(item.source, item.item_type)
            metrics = self._get_metrics(item)
            
            rows_html += f"""
            <tr>
                <td>{i}</td>
                <td>{type_badge}</td>
                <td><a href="{item.url}" target="_blank">{self._escape(item.title)}</a></td>
                <td>{self._escape(item.author)}</td>
                <td>{metrics}</td>
                <td class="excerpt">{self._escape(item.excerpt[:100])}</td>
            </tr>"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #f5f5f5; padding: 20px; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 10px; color: #1a1a1a; }}
        .stats {{ text-align: center; color: #666; margin-bottom: 20px; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th {{ background: #2c3e50; color: #fff; padding: 12px 8px; text-align: left; font-size: 13px; }}
        td {{ padding: 10px 8px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
        tr:hover {{ background: #f8f9fa; }}
        a {{ color: #1890ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
                 font-size: 11px; font-weight: bold; color: #fff; }}
        .badge-zhihu {{ background: #0066ff; }}
        .badge-bilibili {{ background: #fb7299; }}
        .badge-youtube {{ background: #ff0000; }}
        .badge-github {{ background: #24292e; }}
        .badge-paper {{ background: #6c5ce7; }}
        .metrics {{ color: #888; font-size: 12px; }}
        .excerpt {{ color: #666; max-width: 300px; }}
        .generated {{ text-align: center; color: #999; margin-top: 15px; font-size: 12px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    <p class="stats">共 {len(items)} 条结果 | {stats_html} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>来源</th>
                <th>标题</th>
                <th>作者</th>
                <th>数据</th>
                <th>摘要</th>
            </tr>
        </thead>
        <tbody>{rows_html}
        </tbody>
    </table>
    <p class="generated">InfoSpider v0.1.0 - 智能信息采集系统</p>
</div>
</body>
</html>"""
    
    def _get_type_badge(self, source: str, item_type: str) -> str:
        """获取来源类型标签"""
        badge_class = f"badge-{source}"
        label = f"{source}/{item_type}"
        return f'<span class="badge {badge_class}">{label}</span>'
    
    def _get_metrics(self, item: CrawlItem) -> str:
        """获取数据指标HTML"""
        parts = []
        if item.voteup:
            parts.append(f"👍{item.voteup}")
        if item.view_count:
            parts.append(f"👁{item.view_count}")
        if item.comment_count:
            parts.append(f"💬{item.comment_count}")
        return '<span class="metrics">' + " ".join(parts) + "</span>"
    
    @staticmethod
    def _escape(text: str) -> str:
        """HTML转义"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
