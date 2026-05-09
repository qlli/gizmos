"""
首次运行脚本 - 用于登录知乎并保存 Cookie

使用方法：
1. 运行此脚本：python first_run.py
2. 浏览器会自动打开
3. 在浏览器中登录知乎（扫码或账号密码）
4. 登录成功后，关闭浏览器
5. 之后运行 main.py 时会自动使用保存的 Cookie
"""
from src.crawler.zhihu_client import ZhihuClient
from src.utils.logger import setup_logger

def main():
    # 设置有头模式（显示浏览器）
    setup_logger(log_file="logs/first_run.log", level="INFO")
    
    print("=" * 60)
    print("首次运行 - 知乎登录")
    print("=" * 60)
    print("\n浏览器即将打开...")
    print("请在浏览器中完成登录（扫码或账号密码）")
    print("登录成功后，关闭浏览器即可。\n")
    
    # 创建客户端（有头模式）
    client = ZhihuClient(headless=False)
    
    try:
        # 启动浏览器
        client._start_browser()
        
        # 访问知乎首页
        client.page.goto("https://www.zhihu.com", wait_until="domcontentloaded", timeout=30000)
        
        print("\n请在浏览器中完成登录...")
        print("登录成功后，按 Enter 键继续...")
        input()
        
        print("\n" + "=" * 60)
        print("Cookie 已保存到 data/browser_data")
        print("之后运行程序时会自动加载 Cookie")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
