@echo off
chcp 65001 >nul
echo ====================================
echo 自动宽带拨号程序
echo ====================================
echo.
echo 正在启动程序...
echo 请确保已创建名为"Netkeeper"的宽带连接
echo.

REM 使用Python启动器
py --version
if errorlevel 1 (
    echo 错误: Python启动器无法运行
    pause
    exit /b 1
)

echo.
echo 程序正在运行...
echo 按 Ctrl+C 可以停止程序
echo.

py auto_dial.py

pause