#!/bin/bash

# 生产模式启动脚本

set -e

echo "========================================"
echo "启动生产环境"
echo "========================================"

# 检查是否已构建前端
if [ ! -d "frontend/dist" ]; then
    echo "前端未构建，正在构建..."
    cd frontend
    npm run build
    cd ..
fi

# 启动后端（生产模式）
start_backend() {
    echo "启动后端服务（生产模式）..."
    cd backend
    source venv/bin/activate
    
    # 使用gunicorn或uvicorn启动（带workers）
    if command -v gunicorn &> /dev/null; then
        gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 &
    else
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 &
    fi
    
    BACKEND_PID=$!
    echo "后端PID: $BACKEND_PID"
    cd ..
}

# 使用nginx或http-server提供前端静态文件
start_frontend() {
    echo "启动前端服务..."
    cd frontend
    
    if command -v python3 &> /dev/null; then
        python3 -m http.server 3000 -d dist &
        FRONTEND_PID=$!
        echo "前端PID: $FRONTEND_PID"
    else
        echo "警告: 未找到合适的静态文件服务器"
        echo "建议使用nginx配置前端"
    fi
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
echo "生产环境已启动"
echo "后端: http://0.0.0.0:8000"
echo "前端: http://0.0.0.0:3000"
echo "========================================"
echo "按 Ctrl+C 停止所有服务"
echo ""

# 保持脚本运行
wait

