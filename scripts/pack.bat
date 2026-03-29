@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo [1/3] 关闭正在运行的 DocFlow...
taskkill /f /im DocFlow.exe >nul 2>&1

echo [2/3] 激活虚拟环境...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo 错误：未找到虚拟环境，请先执行 python -m venv .venv 并安装依赖
    pause
    exit /b 1
)

echo [3/3] 开始打包...
pyinstaller main.spec --clean -y
if errorlevel 1 (
    echo.
    echo 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo 打包成功！输出文件：dist\DocFlow.exe
pause
