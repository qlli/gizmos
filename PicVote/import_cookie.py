"""一次性把 Cookie 导入 secrets/credentials.json（结论第五次修订的配套工具）。

用法（在服务器上执行）：
    cd /opt/picvote && python3 import_cookie.py

然后粘贴以下任意一种，按回车，再按一次回车结束：
  1) Network -> Request Headers 里 `cookie:` 后面那一整串
  2) 右键请求 -> Copy -> Copy as cURL 的整条命令（单行或多行均可）
  3) Cookie-Editor -> Export -> JSON
  4) Cookie-Editor 导出的 Header String / 纯 `name=value; ...`

安全：凭证只在服务器本机内存与文件中流转，不打印、不回传、不落日志、
不进仓库；文件权限 600，目录 700。本脚本由用户本人执行。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.join(ROOT, "secrets")
TARGET = os.path.join(SECRETS, "credentials.json")
HOST = "jandan.net"


def extract(text):
    """从多种粘贴格式中提取 Cookie 串；失败返回 None。"""
    text = (text or "").strip()
    if not text:
        return None

    # Cookie-Editor 导出的 JSON（数组，或含 cookies 字段的对象）
    if text[0] in "[{":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("cookies", [])
            pairs = ["%s=%s" % (c.get("name", ""), c.get("value", ""))
                     for c in data
                     if isinstance(c, dict) and c.get("name")]
            if pairs:
                return "; ".join(pairs)
        except (ValueError, TypeError):
            pass

    # Copy as cURL: -H 'Cookie: xxx' / -H "cookie: xxx"
    m = re.search(r"-H\s+['\"]cookie\s*:\s*([^'\"]+)['\"]", text, re.I)
    if m:
        return m.group(1).strip()
    # Copy as cURL: -b 'xxx' / --cookie "xxx"
    m = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", text)
    if m:
        return m.group(1).strip()
    # 显式的 cookie: xxx 行
    m = re.search(r"(?:^|\n)\s*cookie\s*:\s*([^\n]+)", text, re.I)
    if m:
        return m.group(1).strip()
    # 纯 Cookie 串（不能是 cURL 命令，避免误把整条命令塞进请求头）
    if "=" in text and not text.lower().startswith("curl") and "\n" not in text:
        return text
    return None


def write(cookie):
    os.makedirs(SECRETS, exist_ok=True)
    try:
        os.chmod(SECRETS, 0o700)
    except OSError:
        pass
    fd = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({HOST: {"Cookie": cookie}}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    try:
        os.chmod(TARGET, 0o600)
    except OSError:
        pass


def main():
    print("粘贴 Cookie 串 / Copy as cURL / Cookie-Editor 导出的 JSON：")
    print("（粘贴后按回车，再按一次空回车结束；内容不会显示或记录）")
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line or not line.strip():
            break
        lines.append(line.rstrip("\r\n"))
    cookie = extract("\n".join(lines))
    if not cookie:
        print("未能识别：请检查粘贴内容是否包含 cookie: 行、-H 'Cookie: ...'、"
              "-b '...' 或 name=value 串")
        return 1
    write(cookie)
    print("已写入 %s（%d 字符），权限 600；内容未打印" % (TARGET, len(cookie)))
    try:
        from credentials import Credentials
        c = Credentials(TARGET, lambda m: None)
        print("校验：state=%s is_template=%s hosts=%s"
              % (c.state, c.is_template, c.status()["configured_hosts"]))
    except Exception:
        pass
    print("现在可执行：python3 app.py --job-now")
    return 0


if __name__ == "__main__":
    sys.exit(main())
