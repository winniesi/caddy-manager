#!/usr/bin/env python3
"""
Caddy Manager - Web UI for managing Caddy reverse proxy configuration
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 配置
CADDYFILE_PATH = os.getenv('CADDYFILE_PATH', '/data/Caddyfile')
DDNS_SCRIPT_PATH = os.getenv('DDNS_SCRIPT_PATH', '/data/ddns/caddy_ddns_sync.py')
DDNS_LOG_PATH = os.getenv('DDNS_LOG_PATH', '/data/ddns/caddy_ddns.log')
CADDY_CONTAINER_NAME = os.getenv('CADDY_CONTAINER_NAME', 'caddy-cloudflare')

# 端口服务名称映射
PORT_SERVICE_NAMES = {
    1200: "RSSHub",
    2019: "Caddy API",
    5700: "青龙面板",
    7000: "frps",
    7890: "Mihomo HTTP",
    8005: "Jellyfin",
    8080: "HTTP Alt",
    8081: "MetaTube",
    8097: "Emby",
    8443: "HTTPS",
    9091: "Transmission",
}


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """读取 Caddyfile 配置"""
    try:
        with open(CADDYFILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'config': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/config', methods=['POST'])
def save_config():
    """保存 Caddyfile 配置"""
    try:
        data = request.json
        config = data.get('config', '')

        with open(CADDYFILE_PATH, 'w', encoding='utf-8') as f:
            f.write(config)

        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/scan_ports', methods=['GET'])
def scan_ports():
    """扫描 Docker 容器端口"""
    try:
        cmd = "docker ps --format '{{.Names}}\t{{.Ports}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        ports = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                container = parts[0]
                ports_str = parts[1]

                # 解析端口
                port_matches = re.findall(r'0\.0\.0\.0:(\d+)->', ports_str)
                for port in port_matches:
                    port_num = int(port)
                    service = PORT_SERVICE_NAMES.get(port_num, container)
                    ports.append({
                        'container': container,
                        'port': port_num,
                        'service': service,
                    })

        # 按端口号排序
        ports.sort(key=lambda x: x['port'])

        return jsonify({'success': True, 'ports': ports})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'ports': []})


@app.route('/api/restart_caddy', methods=['POST'])
def restart_caddy():
    """重启 Caddy 容器"""
    try:
        cmd = f"docker restart {CADDY_CONTAINER_NAME}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Caddy 已重启'})
        else:
            return jsonify({'success': False, 'error': result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/sync_ddns', methods=['POST'])
def sync_ddns():
    """触发 DDNS 同步"""
    try:
        # 在容器内直接执行 DDNS 脚本
        cmd = f"python3 {DDNS_SCRIPT_PATH}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/data/ddns',
        )

        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ddns_logs', methods=['GET'])
def get_ddns_logs():
    """获取 DDNS 日志"""
    try:
        lines = request.args.get('lines', 50, type=int)

        if os.path.exists(DDNS_LOG_PATH):
            cmd = f"tail -n {lines} {DDNS_LOG_PATH}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return jsonify({'success': True, 'logs': result.stdout})
        else:
            return jsonify({'success': True, 'logs': '日志文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
