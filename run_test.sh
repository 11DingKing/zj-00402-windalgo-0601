#!/bin/bash

echo "========================================"
echo "告警链路检验脚本"
echo "========================================"

echo ""
echo "检查服务状态..."
curl -s http://localhost:8000/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "服务未启动，请先运行: ./start.sh"
    exit 1
fi

echo ""
echo "服务已就绪，开始测试..."
echo ""

python scripts/test_alert_chain.py
