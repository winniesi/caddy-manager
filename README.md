# Caddy Manager

一个简洁优雅的 Caddy 反向代理 Web 管理工具，支持自动 DDNS 同步。

## 功能特性

- ✅ Web UI 管理 Caddy 配置
- ✅ 自动扫描主机端口
- ✅ 一键重启 Caddy
- ✅ 自动 DDNS 同步
- ✅ DDNS 日志查看
- ✅ 响应式设计，支持移动端

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/winniesi/caddy-manager.git
cd caddy-manager
```

### 2. 修改配置

编辑 `docker-compose.yml`，修改卷挂载路径：

```yaml
volumes:
  # Caddy 配置文件路径
  - /your/path/to/Caddyfile:/data/Caddyfile
  # DDNS 脚本目录
  - /your/path/to/ddns:/data/ddns
  # Docker socket
  - /var/run/docker.sock:/var/run/docker.sock
```

### 3. 启动服务

```bash
# 创建网络（如果不存在）
docker network create caddy-net

# 启动服务
docker-compose up -d
```

### 4. 访问管理界面

打开浏览器访问：`http://your-nas-ip:8080`

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CADDYFILE_PATH` | `/data/Caddyfile` | Caddy 配置文件路径 |
| `DDNS_SCRIPT_PATH` | `/data/ddns/caddy_ddns_sync.py` | DDNS 脚本路径 |
| `DDNS_VENV_PATH` | `/data/ddns/venv/bin/python` | DDNS Python 虚拟环境路径 |
| `DDNS_LOG_PATH` | `/data/ddns/caddy_ddns.log` | DDNS 日志文件路径 |
| `CADDY_CONTAINER_NAME` | `caddy-cloudflare` | Caddy 容器名称 |

### 卷挂载

| 容器路径 | 主机路径 | 说明 |
|----------|----------|------|
| `/data/Caddyfile` | Caddyfile 路径 | Caddy 配置文件 |
| `/data/ddns` | DDNS 脚本目录 | DDNS 同步脚本 |
| `/var/run/docker.sock` | Docker socket | 用于重启 Caddy 容器 |

## 使用说明

### 添加域名

1. 输入子域名（例如：`emby`）
2. 输入目标端口（例如：`8096`）或点击"扫描端口"选择
3. 点击"添加"
4. 点击"保存配置"

### 删除域名

1. 在域名列表中点击删除按钮
2. 确认删除
3. 点击"保存配置"

### 扫描端口

点击"扫描端口"按钮，会自动扫描主机上所有监听的端口，包括：
- Docker 容器端口
- 系统服务端口
- 常见服务自动识别

### DDNS 同步

- 保存配置时会自动触发 DDNS 同步
- 也可以手动点击"立即同步"
- 点击"查看日志"查看同步详情

## 前置要求

- Docker
- Docker Compose
- Caddy 容器（已配置 Cloudflare DNS）
- DDNS 脚本

## 目录结构

```
caddy-manager/
├── app.py                 # Flask 主应用
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 构建文件
├── docker-compose.yml     # Docker Compose 配置
├── .gitignore             # Git 忽略文件
├── README.md              # 项目说明
├── templates/
│   └── index.html         # 主页面模板
└── static/
    ├── css/
    │   └── style.css      # 样式文件
    └── js/
        └── app.js         # JavaScript 逻辑
```

## 开发

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
python app.py
```

### 构建镜像

```bash
docker build -t winniesi/caddy-manager:latest .
```

## 许可证

MIT License

## 作者

winniesi
