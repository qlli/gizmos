#!/usr/bin/env bash
# 在云服务器上执行：安装并启动 PicVote（Python >= 3.6，零第三方依赖）
# 用法： sudo APP_DIR=/opt/picvote PORT=18080 bash deploy/install.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/picvote}"
PORT="${PORT:-18080}"
HOST="${HOST:-0.0.0.0}"
TOKEN="${TOKEN:-}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v python3 >/dev/null 2>&1 \
  || { echo "缺少 python3，请先执行：yum install -y python3"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 6) else 1)' \
  || { echo "需要 Python 3.6+"; exit 1; }

mkdir -p "$APP_DIR" "$APP_DIR/data/images"
mkdir -p "$APP_DIR/secrets"
chmod 700 "$APP_DIR/secrets"
# 只创建模板，真实凭证由用户本人写入，脚本绝不读取或覆盖
if [ -f "$SRC_DIR/secrets.example.json" ] && [ ! -f "$APP_DIR/secrets.example.json" ]; then
  cp -f "$SRC_DIR/secrets.example.json" "$APP_DIR/secrets.example.json"
fi
if [ -f "$APP_DIR/secrets/credentials.json" ]; then
  chmod 600 "$APP_DIR/secrets/credentials.json"
fi

# 源码目录与安装目录相同时跳过复制，避免 cp 报 "same file"
if [ "$(readlink -f "$SRC_DIR")" != "$(readlink -f "$APP_DIR")" ]; then
  for f in app.py config.py storage.py sources.py job.py web.py \
           credentials.py import_cookie.py README.md requirements.txt \
           sources.example.txt secrets.example.json; do
    cp -f "$SRC_DIR/$f" "$APP_DIR/$f"
  done
  mkdir -p "$APP_DIR/deploy" "$APP_DIR/tests"
  cp -f "$SRC_DIR/deploy/picvote.service" "$APP_DIR/deploy/"
  cp -f "$SRC_DIR/deploy/install.sh" "$APP_DIR/deploy/"
  for t in "$SRC_DIR"/tests/*.py; do
    if [ -e "$t" ]; then cp -f "$t" "$APP_DIR/tests/"; fi
  done
fi
[ -f "$APP_DIR/sources.txt" ] || cp -f "$SRC_DIR/sources.example.txt" "$APP_DIR/sources.txt"

UNIT=/etc/systemd/system/picvote.service
sed -E \
    -e "s|^WorkingDirectory=.*|WorkingDirectory=$APP_DIR|" \
    -e "s|^Environment=PICVOTE_ROOT=.*|Environment=PICVOTE_ROOT=$APP_DIR|" \
    -e "s|^Environment=PICVOTE_PORT=.*|Environment=PICVOTE_PORT=$PORT|" \
    -e "s|^Environment=PICVOTE_HOST=.*|Environment=PICVOTE_HOST=$HOST|" \
    "$SRC_DIR/deploy/picvote.service" > "$UNIT"

if [ -n "$TOKEN" ]; then
  sed -i "/^Environment=PYTHONUNBUFFERED=1/a Environment=PICVOTE_ACCESS_TOKEN=$TOKEN" "$UNIT"
fi

systemctl daemon-reload
systemctl enable picvote >/dev/null 2>&1
systemctl restart picvote
sleep 2

if ! systemctl is-active --quiet picvote; then
  echo "错误：picvote 服务未能启动，最近日志："
  journalctl -u picvote -n 30 --no-pager
  exit 1
fi
systemctl --no-pager status picvote | head -12

echo "--- 本机健康检查 ---"
curl -fsS "http://127.0.0.1:$PORT/api/status" || {
  echo "错误：本机接口不可达"; exit 1;
}
echo
echo "完成。公网访问 http://<服务器公网IP>:$PORT/"
echo "若公网不通，需在云厂商安全组放行 TCP $PORT（本机 firewalld 未运行）。"
echo "日志：$APP_DIR/data/picvote.log"
