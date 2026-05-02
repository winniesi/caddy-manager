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


def parse_caddyfile(content):
    """解析 Caddyfile，提取域名配置"""
    domains = []
    # 匹配 @name host xxx.winnie.si 和 reverse_proxy @name ip:port
    pattern = r'@(\w+)\s+host\s+(\S+)\s*\n\s*reverse_proxy\s+@\w+\s+(\S+)'
    matches = re.findall(pattern, content)

    for name, host, target in matches:
        # 从 host 提取子域名
        subdomain = host.replace('.winnie.si', '')
        # 提取端口
        port_match = re.search(r':(\d+)', target)
        port = int(port_match.group(1)) if port_match else 80

        domains.append({
            'name': name,
            'domain': host,
            'subdomain': subdomain,
            'port': port,
        })

    return domains


def generate_caddyfile(domains):
    """根据域名列表生成 Caddyfile"""
    if not domains:
        return ""

    lines = ["*.winnie.si:8443 {"]
    lines.append("    tls {")
    lines.append("        dns cloudflare {env.CLOUDFLARE_API_TOKEN}")
    lines.append("    }")
    lines.append("")

    for domain in domains:
        name = domain['name']
        host = domain['domain']
        port = domain['port']
        lines.append(f"    @{name} host {host}")
        lines.append(f"    reverse_proxy @{name} 192.168.0.114:{port}")
        lines.append("")

    lines.append("}")
    return "\n".join(lines)


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

        domains = parse_caddyfile(content)
        return jsonify({'success': True, 'config': content, 'domains': domains})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'domains': []})


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


@app.route('/api/domains', methods=['POST'])
def save_domains():
    """保存域名配置（从域名列表生成 Caddyfile）"""
    try:
        data = request.json
        domains = data.get('domains', [])

        config = generate_caddyfile(domains)

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


@app.route('/api/restart_and_sync', methods=['POST'])
def restart_and_sync():
    """重启 Caddy 并同步 DDNS"""
    try:
        data = request.json
        domains = data.get('domains', [])

        # 1. 保存配置
        config = generate_caddyfile(domains)
        with open(CADDYFILE_PATH, 'w', encoding='utf-8') as f:
            f.write(config)

        # 2. 重启 Caddy
        cmd = f"docker restart {CADDY_CONTAINER_NAME}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return jsonify({'success': False, 'error': f'重启失败: {result.stderr}'})

        # 3. 同步 DDNS
        time.sleep(2)  # 等待 Caddy 启动
        cmd = f"python3 {DDNS_SCRIPT_PATH}"
        ddns_result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/data/ddns',
        )

        return jsonify({
            'success': True,
            'message': '配置已保存，Caddy 已重启，DDNS 已同步',
            'restart': {'success': True},
            'ddns': {'success': ddns_result.returncode == 0, 'output': ddns_result.stdout + ddns_result.stderr},
        })
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


@app.route('/api/ddns_log', methods=['GET'])
def get_ddns_log():
    """获取 DDNS 日志"""
    try:
        lines = request.args.get('lines', 50, type=int)

        if os.path.exists(DDNS_LOG_PATH):
            cmd = f"tail -n {lines} {DDNS_LOG_PATH}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return jsonify({'success': True, 'log': result.stdout})
        else:
            return jsonify({'success': True, 'log': '日志文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ddns_logs', methods=['GET'])
def get_ddns_logs():
    """获取 DDNS 日志（兼容旧接口）"""
    return get_ddns_log()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
