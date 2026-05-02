#!/bin/bash
# Caddy Manager 启动脚本

cd /vol1/1000/workspace/caddy-manager

# 激活虚拟环境并启动
./venv/bin/gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --timeout 120 \
    --pid /tmp/caddy-manager.pid \
    --access-logfile /vol1/1000/workspace/caddy-manager/access.log \
    --error-logfile /vol1/1000/workspace/caddy-manager/error.log \
    --daemon \
    app:app

echo "Caddy Manager 已启动"
echo "访问地址: http://$(hostname -I | awk '{print $1}'):8080"
echo "PID: $(cat /tmp/caddy-manager.pid 2>/dev/null || echo '未知')"
