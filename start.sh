#!/bin/bash

echo "正在检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python! 请先安装Python 3.8或更高版本."
    exit 1
fi

echo "正在检查依赖包..."
pip3 install -r requirements.txt

echo "启动监控程序..."
python3 main.py 