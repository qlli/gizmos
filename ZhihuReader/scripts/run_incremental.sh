#!/bin/bash
# 运行增量内容抓取

cd "$(dirname "$0")/.." || exit

python main.py --incremental --hot --limit 50
