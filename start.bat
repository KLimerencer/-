@echo off
echo 正在检查Python环境...
python --version 2>nul
if errorlevel 1 (
    echo 错误: 未找到Python! 请先安装Python 3.8或更高版本.
    pause
    exit /b
)

echo 正在检查依赖包...
pip install -r requirements.txt

echo 启动监控程序...
python main.py

pause 