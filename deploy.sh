#!/bin/bash
# Caddy Manager 部署脚本 - 在 NAS 上运行

set -e

PROJECT_DIR="/vol1/1000/workspace/caddy-manager"
REPO_URL="https://github.com/winniesi/caddy-manager.git"

echo "=== Caddy Manager 部署 ==="

# 检查项目目录
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，更新代码..."
    cd "$PROJECT_DIR"
    git pull origin master
else
    echo "克隆项目..."
    cd /vol1/1000/workspace
    git clone "$REPO_URL"
    cd caddy-manager
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 安装依赖
echo "安装依赖..."
./venv/bin/pip install -r requirements.txt

# 设置脚本权限
chmod +x start.sh stop.sh restart.sh

# 停止旧进程
if [ -f /tmp/caddy-manager.pid ]; then
    echo "停止旧进程..."
    ./stop.sh
fi

# 启动服务
echo "启动服务..."
./start.sh

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://$(hostname -I | awk '{print $1}'):8080"
