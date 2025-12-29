#!/bin/bash

# 开发模式启动脚本

set -e

echo "========================================"
echo "启动开发环境"
echo "========================================"

# 启动后端
start_backend() {
    echo "启动后端服务..."
    cd backend
    source venv/bin/activate
    python main.py &
    BACKEND_PID=$!
    echo "后端PID: $BACKEND_PID"
    cd ..
}

# 启动前端
start_frontend() {
    echo "启动前端开发服务器..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo "前端PID: $FRONTEND_PID"
    cd ..
}

# 清理函数
cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "服务已停止"
    exit 0
}

trap cleanup INT TERM

# 启动服务
start_backend
sleep 2
start_frontend

echo ""
echo "========================================"
echo "服务已启动"
echo "后端: http://localhost:8080"
echo "前端: http://localhost:3000"
echo "========================================"
echo "按 Ctrl+C 停止所有服务"
echo ""

# 保持脚本运行
wait

