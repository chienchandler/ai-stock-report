#!/usr/bin/env bash
# AI Stock Report - 修改配置并启动（Mac/Linux）
set -e
cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

echo "正在打开配置页面..."
$PY -c "from web_config import run_config_server; run_config_server(open_browser=True, wait_for_save=True)"

if [ ! -f config.yaml ]; then
    echo "配置未保存，退出。"
    exit 1
fi

echo ""
echo "配置已保存，正在启动服务..."
echo ""
$PY app.py
