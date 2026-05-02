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
CADDYFILE_PATH = os.environ.get("CADDYFILE_PATH", "/data/Caddyfile")
DDNS_SCRIPT_PATH = os.environ.get("DDNS_SCRIPT_PATH", "/data/ddns/caddy_ddns_sync.py")
DDNS_VENV_PATH = os.environ.get("DDNS_VENV_PATH", "/data/ddns/venv/bin/python")
DDNS_LOG_PATH = os.environ.get("DDNS_LOG_PATH", "/data/ddns/caddy_ddns.log")
CADDY_CONTAINER_NAME = os.environ.get("CADDY_CONTAINER_NAME", "caddy-cloudflare")
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")

# 常见服务端口映射
COMMON_SERVICES = {
    80: "HTTP",
    443: "HTTPS",
    8080: "HTTP Alt",
    8443: "HTTPS Alt",
    3000: "MoviePilot",
    3001: "MoviePilot Alt",
    5700: "青龙面板",
    5666: "fnhome",
    8005: "fnjellyfin",
    8096: "Emby",
    8097: "Emby",
    9091: "Transmission",
    2283: "Immich",
    8081: "MetaTube",
    8388: "Shadowsocks",
    9090: "Mihomo",
    1200: "RSSHub",
    18060: "小红书 MCP",
    2019: "Caddy API",
    7890: "Mihomo HTTP",
    9097: "Metacubexd",
}


def read_caddyfile():
    """读取 Caddyfile 内容"""
    try:
        with open(CADDYFILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def write_caddyfile(content):
    """写入 Caddyfile 内容"""
    with open(CADDYFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def parse_caddyfile(content):
    """解析 Caddyfile，提取域名配置"""
    domains = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        line = line.strip()
        # 匹配 @name host domain.winnie.si
        match = re.match(r"@(\w+)\s+host\s+([\w.-]+)", line)
        if match:
            name = match.group(1)
            domain = match.group(2)
            # 找对应的 reverse_proxy 行
            port = None
            for j in range(i + 1, min(i + 5, len(lines))):
                proxy_match = re.match(
                    r"reverse_proxy\s+@\w+\s+[\d.]+:(\d+)", lines[j].strip()
                )
                if proxy_match:
                    port = int(proxy_match.group(1))
                    break
            if port:
                # 提取子域名
                subdomain = domain.replace(".winnie.si", "")
                domains.append(
                    {
                        "name": name,
                        "domain": domain,
                        "subdomain": subdomain,
                        "port": port,
                    }
                )

    return domains


def update_caddyfile(domains):
    """根据域名列表更新 Caddyfile"""
    lines = [
        "*.winnie.si:8443 {",
        "    tls {",
        "        dns cloudflare {env.CLOUDFLARE_API_TOKEN}",
        "    }",
        "",
    ]

    for domain in domains:
        lines.append(f"    @{domain['name']} host {domain['domain']}")
        lines.append(f"    reverse_proxy @{domain['name']} 192.168.0.114:{domain['port']}")
        lines.append("")

    lines.append("}")
    return "\n".join(lines)


def scan_ports():
    """扫描主机所有监听端口"""
    ports = []
    try:
        # 使用 ss 命令扫描
        result = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "LISTEN" in line:
                    parts = line.split()
                    # 提取端口
                    addr = parts[3] if len(parts) > 3 else ""
                    port_match = re.search(r":(\d+)$", addr)
                    if port_match:
                        port = int(port_match.group(1))
                        # 提取进程名
                        process = ""
                        proc_match = re.search(r"users:\(\(\"([^\"]+)\"", line)
                        if proc_match:
                            process = proc_match.group(1)

                        # 获取服务名
                        service = COMMON_SERVICES.get(port, process or "Unknown")

                        ports.append(
                            {
                                "port": port,
                                "process": process,
                                "service": service,
                            }
                        )
    except Exception as e:
        print(f"扫描端口失败: {e}")

    # 去重并排序
    seen = set()
    unique_ports = []
    for p in sorted(ports, key=lambda x: x["port"]):
        if p["port"] not in seen:
            seen.add(p["port"])
            unique_ports.append(p)

    return unique_ports


def restart_caddy():
    """重启 Caddy Docker 容器"""
    try:
        result = subprocess.run(
            ["docker", "restart", CADDY_CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def run_ddns_sync():
    """运行 DDNS 同步脚本"""
    try:
        # 使用虚拟环境的 Python
        python_path = DDNS_VENV_PATH
        if not os.path.exists(python_path):
            python_path = "python3"

        result = subprocess.run(
            [python_path, DDNS_SCRIPT_PATH],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.dirname(DDNS_SCRIPT_PATH),
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def get_ddns_log(lines=50):
    """获取 DDNS 日志"""
    try:
        if os.path.exists(DDNS_LOG_PATH):
            with open(DDNS_LOG_PATH, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        return "日志文件不存在"
    except Exception as e:
        return f"读取日志失败: {e}"


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    """获取当前配置"""
    content = read_caddyfile()
    domains = parse_caddyfile(content)
    return jsonify({"success": True, "domains": domains, "raw": content})


@app.route("/api/config", methods=["POST"])
def save_config():
    """保存配置"""
    data = request.json
    domains = data.get("domains", [])

    # 生成新的 Caddyfile
    content = update_caddyfile(domains)

    # 备份旧配置
    if os.path.exists(CADDYFILE_PATH):
        backup_path = f"{CADDYFILE_PATH}.bak.{int(time.time())}"
        try:
            with open(CADDYFILE_PATH, "r") as f:
                old_content = f.read()
            with open(backup_path, "w") as f:
                f.write(old_content)
        except Exception:
            pass

    # 写入新配置
    write_caddyfile(content)

    return jsonify({"success": True, "message": "配置已保存"})


@app.route("/api/scan_ports")
def get_ports():
    """扫描端口"""
    ports = scan_ports()
    return jsonify({"success": True, "ports": ports})


@app.route("/api/restart", methods=["POST"])
def restart():
    """重启 Caddy"""
    success, output = restart_caddy()
    return jsonify({"success": success, "output": output})


@app.route("/api/sync_ddns", methods=["POST"])
def sync_ddns():
    """触发 DDNS 同步"""
    success, output = run_ddns_sync()
    return jsonify({"success": success, "output": output})


@app.route("/api/ddns_log")
def ddns_log():
    """获取 DDNS 日志"""
    lines = request.args.get("lines", 50, type=int)
    log = get_ddns_log(lines)
    return jsonify({"success": True, "log": log})


@app.route("/api/restart_and_sync", methods=["POST"])
def restart_and_sync():
    """重启 Caddy 并同步 DDNS"""
    # 保存配置
    data = request.json
    domains = data.get("domains", [])
    content = update_caddyfile(domains)
    write_caddyfile(content)

    # 重启 Caddy
    restart_success, restart_output = restart_caddy()

    # 等待 Caddy 启动
    time.sleep(3)

    # 同步 DDNS
    ddns_success, ddns_output = run_ddns_sync()

    return jsonify(
        {
            "success": restart_success and ddns_success,
            "restart": {"success": restart_success, "output": restart_output},
            "ddns": {"success": ddns_success, "output": ddns_output},
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
