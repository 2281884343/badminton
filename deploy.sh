#!/bin/bash

# 羽毛球游戏 - Linux部署脚本

set -e

echo "========================================"
echo "羽毛球游戏 - 自动部署脚本"
echo "========================================"
echo ""

# 检查Python版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "✓ Python3已安装: $PYTHON_VERSION"
    else
        echo "✗ 未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
}

# 检查Node.js版本
check_node() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo "✓ Node.js已安装: $NODE_VERSION"
    else
        echo "✗ 未找到Node.js，请先安装Node.js 16+"
        exit 1
    fi
}

# 安装后端依赖
setup_backend() {
    echo ""
    echo "========== 配置后端 =========="
    cd backend
    
    if [ ! -d "venv" ]; then
        echo "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    echo "激活虚拟环境..."
    source venv/bin/activate
    
    echo "安装Python依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "创建数据目录..."
    mkdir -p data/players
    
    cd ..
    echo "✓ 后端配置完成"
}

# 安装前端依赖
setup_frontend() {
    echo ""
    echo "========== 配置前端 =========="
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        echo "安装Node.js依赖..."
        npm install
    else
        echo "✓ Node.js依赖已安装"
    fi
    
    cd ..
    echo "✓ 前端配置完成"
}

# 构建前端
build_frontend() {
    echo ""
    echo "========== 构建前端 =========="
    cd frontend
    
    echo "打包前端资源..."
    npm run build
    
    cd ..
    echo "✓ 前端构建完成"
}

# 主流程
main() {
    echo "开始检查系统环境..."
    check_python
    check_node
    
    setup_backend
    setup_frontend
    
    read -p "是否构建前端生产版本？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_frontend
    fi
    
    echo ""
    echo "========================================"
    echo "✓ 部署完成！"
    echo "========================================"
    echo ""
    echo "启动服务："
    echo "  开发模式: ./start-dev.sh"
    echo "  生产模式: ./start-prod.sh"
    echo ""
    echo "或使用systemd服务："
    echo "  sudo cp badminton-game.service /etc/systemd/system/"
    echo "  sudo systemctl enable badminton-game"
    echo "  sudo systemctl start badminton-game"
    echo ""
}

main

