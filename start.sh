#!/bin/bash

echo "========================================"
echo "高海拔风电机组运行监控告警系统"
echo "========================================"

echo ""
echo "1. 安装依赖..."
pip install -r requirements.txt

echo ""
echo "2. 初始化机组数据..."
python scripts/init_data.py

echo ""
echo "3. 生成样本数据..."
python scripts/generate_samples.py

echo ""
echo "4. 启动服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
