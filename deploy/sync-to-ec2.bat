@echo off
REM Windows 批处理脚本 - 同步代码到 EC2
REM 用途：在 Windows 上运行，通过 Git Bash 同步代码到 EC2

echo ==========================================
echo TTQuant 本地到 EC2 同步 (Windows)
echo ==========================================
echo.

REM 检查是否在项目根目录
if not exist "docker\docker-compose.yml" (
    echo [错误] 请在 TTQuant 项目根目录下运行此脚本
    pause
    exit /b 1
)

REM 检查 Git Bash 是否安装
where bash >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Git Bash
    echo 请确保已安装 Git for Windows
    pause
    exit /b 1
)

REM 调用 bash 脚本
echo 调用 Git Bash 执行同步...
echo.
bash deploy/sync-to-ec2.sh

pause
