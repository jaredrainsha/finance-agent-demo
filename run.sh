#!/usr/bin/env bash
# 财务报销审核 Agent Demo 启动脚本
# 用法：在终端里执行  ./run.sh
set -e
cd "$(dirname "$0")"

ST="../rag-agent/venv/bin/streamlit"

if [ ! -x "$ST" ]; then
  echo "找不到 streamlit，请先安装依赖："
  echo "  ../rag-agent/venv/bin/pip install streamlit Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple"
  exit 1
fi

echo "▶ 启动财务报销审核 Agent Demo ..."
echo "  浏览器访问：http://localhost:8501"
echo "  停止服务：按 Ctrl+C"
echo ""
exec "$ST" run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
