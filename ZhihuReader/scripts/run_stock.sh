#!/bin/bash
# 运行存量内容抓取

cd "$(dirname "$0")/.." || exit

python main.py --stock --hot --limit 200
