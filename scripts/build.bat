@echo off
REM =============================================================================
REM 激光数据标注工具 — Windows 打包构建脚本
REM 用法:
REM   scripts\build.bat          # 构建
REM   scripts\build.bat clean    # 清理
REM =============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

if "%1"=="clean" (
    echo 清理构建产物...
    if exist build\ rmdir /s /q build
    if exist dist\ rmdir /s /q dist
    if exist *.spec.bak del /q *.spec.bak
    echo 完成。
    goto :eof
)

echo === 激光数据标注工具 — PyInstaller 打包 ===
echo.

REM ---- 步骤1: 创建虚拟环境（如果不存在） ----
if not exist ".venv\" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
) else (
    echo [1/4] 虚拟环境已存在
)

REM ---- 步骤2: 安装依赖 ----
echo [2/4] 安装依赖...
.venv\Scripts\python -m pip install -e . pyinstaller -q

REM ---- 步骤3: 构建 ----
echo [3/4] 开始打包...
.venv\Scripts\python -m PyInstaller laser_daq.spec --clean --noconfirm

REM ---- 步骤4: 输出 ----
echo.
echo === 构建完成 ===
echo [4/4] 输出位置: dist\
dir dist\ /b
echo.
echo 可执行文件: dist\laser-daq-tool.exe

endlocal
