#!/bin/bash
# Caddy Manager 停止脚本

if [ -f /tmp/caddy-manager.pid ]; then
    PID=$(cat /tmp/caddy-manager.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "Caddy Manager 已停止 (PID: $PID)"
    else
        echo "进程不存在"
    fi
    rm -f /tmp/caddy-manager.pid
else
    echo "PID 文件不存在，尝试查找进程..."
    pkill -f "gunicorn.*app:app" && echo "已停止" || echo "未找到运行中的进程"
fi
