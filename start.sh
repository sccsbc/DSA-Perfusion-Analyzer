#!/usr/bin/env bash
#
# DSA 灌注分析系统启动脚本
# 用法: ./start.sh [--backend-only|--frontend-only]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# 颜色输出
red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }

cleanup() {
    echo ""
    yellow "正在关闭服务..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    green "服务已关闭"
}
trap cleanup EXIT INT TERM

start_backend() {
    green ">>> 启动后端 FastAPI 服务 (端口 $BACKEND_PORT)..."

    # 检测 conda 环境
    if command -v conda &>/dev/null; then
        PYTHON="conda run -n dsa-perfusion python"
        if ! conda env list 2>/dev/null | grep -q "dsa-perfusion"; then
            red "错误: conda 环境 'dsa-perfusion' 不存在，请先创建环境:"
            echo "  conda env create -f $BACKEND_DIR/environment.yml"
            exit 1
        fi
    else
        # 回退到系统 python
        if [ -d "$BACKEND_DIR/.venv" ]; then
            PYTHON="$BACKEND_DIR/.venv/bin/python"
        else
            PYTHON="python3"
        fi
        yellow "未检测到 conda，使用系统 Python: $PYTHON"
    fi

    cd "$BACKEND_DIR"
    $PYTHON -m uvicorn src.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
    BACKEND_PID=$!
    cd "$SCRIPT_DIR"
    green "  后端已启动 (PID: $BACKEND_PID)"
}

start_frontend() {
    green ">>> 启动前端 Vite 开发服务器 (端口 $FRONTEND_PORT)..."

    if ! command -v npm &>/dev/null; then
        red "错误: 未找到 npm，请先安装 Node.js"
        exit 1
    fi

    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        yellow "  正在安装前端依赖..."
        npm install
    fi
    npx vite --host 0.0.0.0 --port "$FRONTEND_PORT" &
    FRONTEND_PID=$!
    cd "$SCRIPT_DIR"
    green "  前端已启动 (PID: $FRONTEND_PID)"
}

case "${1:-}" in
    --backend-only)
        start_backend
        ;;
    --frontend-only)
        start_frontend
        ;;
    *)
        start_backend
        sleep 2
        start_frontend
        ;;
esac

echo ""
green "========================================="
green "  DSA 灌注分析系统"
green "========================================="
[ -n "$BACKEND_PID" ] && echo "  后端 API:  http://localhost:$BACKEND_PORT"
[ -n "$FRONTEND_PID" ] && echo "  前端界面:  http://localhost:$FRONTEND_PORT"
echo ""
yellow "按 Ctrl+C 停止所有服务"
echo ""

# 保持前台运行
wait
