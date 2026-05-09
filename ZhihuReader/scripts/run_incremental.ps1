# 运行增量内容抓取

# 切换到项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Resolve-Path "$ScriptDir\.."
Set-Location $ProjectDir

# 运行增量内容抓取
python main.py --incremental --hot --limit 50
