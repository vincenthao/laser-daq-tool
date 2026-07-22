#!/bin/bash
# =============================================================================
# 激光数据标注工具 — 打包构建脚本
# 用法:
#   ./scripts/build.sh          # 当前平台构建
#   ./scripts/build.sh clean    # 清理构建产物
# =============================================================================

set -e  # 出错即停
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
DIST_DIR="$PROJECT_ROOT/dist"

# ---- 清理 ----
if [ "${1:-}" = "clean" ]; then
    echo "清理构建产物..."
    rm -rf build/ dist/ *.spec.bak
    echo "完成。"
    exit 0
fi

# ---- 构建 ----
echo "=== 激光数据标注工具 — PyInstaller 打包 ==="
echo ""

# 确保 PyInstaller 已安装
if ! "$VENV_PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "安装 PyInstaller..."
    "$VENV_PYTHON" -m pip install pyinstaller -q
fi

echo "开始构建..."
"$VENV_PYTHON" -m PyInstaller laser_daq.spec --clean --noconfirm

echo ""
echo "=== 构建完成 ==="
echo "输出位置: $DIST_DIR/"
ls -lh "$DIST_DIR/" 2>/dev/null || echo "(输出目录为空)"
echo ""

# 平台检测
case "$(uname -s)" in
    Linux*)  echo "Linux 可执行文件: dist/laser-daq-tool" ;;
    Darwin*) echo "macOS 可执行文件: dist/laser-daq-tool" ;;
    *)       echo "可执行文件: dist/laser-daq-tool" ;;
esac
