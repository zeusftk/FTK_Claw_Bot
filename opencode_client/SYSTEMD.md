# Systemd 服务配置说明

将 `opencode-client` 配置为 systemd 服务，实现开机自启动和自动重启。

## 前置条件

1. 已安装 opencode CLI
2. 已安装 Python 依赖：
```bash
cd /path/to/opencode_client
pip install -e ".[server]"
```

## 创建服务文件

### 1. 创建 systemd 服务配置

```bash
sudo nano /etc/systemd/system/opencode-router.service
```

写入以下内容（根据实际情况修改路径）：

```ini
[Unit]
Description=OpenCode LLM Router - OpenAI Compatible API
Documentation=https://github.com/opencode-ai/opencode-client
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/opencode_client
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# 启动命令（选择一种方式）

# 方式1: 直接运行
ExecStart=/usr/bin/python3 /path/to/opencode_client/router.py

# 方式2: 使用 uvicorn（推荐）
# ExecStart=/usr/local/bin/uvicorn router:app --host 0.0.0.0 --port 8000

# 自动重启配置
Restart=always
RestartSec=5

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=opencode-router

# 资源限制（可选）
# LimitNOFILE=65535
# MemoryMax=1G

[Install]
WantedBy=multi-user.target
```

### 2. 重载 systemd 配置

```bash
sudo systemctl daemon-reload
```

### 3. 启动并启用服务

```bash
# 启动服务
sudo systemctl start opencode-router

# 设置开机自启
sudo systemctl enable opencode-router

# 查看状态
sudo systemctl status opencode-router
```

## 常用命令

```bash
# 启动服务
sudo systemctl start opencode-router

# 停止服务
sudo systemctl stop opencode-router

# 重启服务
sudo systemctl restart opencode-router

# 查看状态
sudo systemctl status opencode-router

# 查看日志
sudo journalctl -u opencode-router -f

# 查看最近100行日志
sudo journalctl -u opencode-router -n 100

# 禁用开机自启
sudo systemctl disable opencode-router
```

## 日志管理

### 查看实时日志
```bash
sudo journalctl -u opencode-router -f
```

### 查看特定时间日志
```bash
# 今天
sudo journalctl -u opencode-router --since today

# 最近1小时
sudo journalctl -u opencode-router --since "1 hour ago"

# 指定时间范围
sudo journalctl -u opencode-router --since "2026-02-19 10:00" --until "2026-02-19 12:00"
```

### 日志持久化

默认日志存储在 `/var/log/journal/`。如需单独存储：

```bash
# 创建日志目录
sudo mkdir -p /var/log/opencode-router

# 修改服务配置添加日志输出
sudo nano /etc/systemd/system/opencode-router.service
```

在 `[Service]` 添加：
```ini
StandardOutput=append:/var/log/opencode-router/access.log
StandardError=append:/var/log/opencode-router/error.log
```

## 完整示例配置

以下是一个完整的、可直接使用的配置：

```ini
[Unit]
Description=OpenCode LLM Router - OpenAI Compatible API
Documentation=https://github.com/opencode-ai/opencode-client
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root

# 修改为你的实际路径
WorkingDirectory=/opt/opencode_client
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONDONTWRITEBYTECODE=1"

# 使用 uvicorn 运行（更稳定）
ExecStart=/usr/local/bin/uvicorn router:app --host 0.0.0.0 --port 8000 --workers 1

# 重启策略
Restart=always
RestartSec=10
StartLimitIntervalSec=60
StartLimitBurst=5

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=opencode-router

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

# 资源限制
LimitNOFILE=65535
# MemoryMax=2G
# CPUQuota=200%

# 健康检查（需要额外脚本）
# ExecStartPost=/bin/sleep 5
# ExecStartPost=/usr/bin/curl -f http://localhost:8000/health || exit 1

[Install]
WantedBy=multi-user.target
```

## 验证服务

```bash
# 检查服务状态
sudo systemctl status opencode-router

# 测试 API
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# 使用 OpenAI SDK 测试
python3 -c "
from openai import OpenAI
client = OpenAI(base_url='http://localhost:8000/v1', api_key='dummy')
print(client.models.list())
"
```

## 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u opencode-router -n 50 --no-pager

# 检查配置语法
sudo systemd-analyze verify /etc/systemd/system/opencode-router.service

# 手动测试启动
cd /path/to/opencode_client
python3 router.py
```

### 端口被占用

```bash
# 查看 8000 端口占用
sudo lsof -i :8000
# 或
sudo netstat -tlnp | grep 8000

# 修改端口（编辑服务文件中的 --port 参数）
sudo systemctl daemon-reload
sudo systemctl restart opencode-router
```

### opencode 服务未启动

router 会自动启动 `opencode serve`，但如果遇到问题：

```bash
# 手动启动 opencode
opencode serve --port 4096 &

# 检查 opencode 服务
curl http://127.0.0.1:4096/global/health
```

## Nginx 反向代理（可选）

如需通过域名访问或添加 HTTPS：

```nginx
# /etc/nginx/sites-available/opencode-router
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 流式响应支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/opencode-router /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 快速部署脚本

创建 `install-service.sh`：

```bash
#!/bin/bash
set -e

# 配置变量
INSTALL_DIR="${1:-/opt/opencode_client}"
SERVICE_USER="${2:-root}"

echo "=== OpenCode Router Service Installer ==="
echo "Install directory: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"

# 创建服务文件
cat << EOF | sudo tee /etc/systemd/system/opencode-router.service
[Unit]
Description=OpenCode LLM Router - OpenAI Compatible API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/local/bin/uvicorn router:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 重载并启动
sudo systemctl daemon-reload
sudo systemctl enable opencode-router
sudo systemctl start opencode-router

echo "=== Service installed and started ==="
sudo systemctl status opencode-router --no-pager
```

使用：
```bash
chmod +x install-service.sh
sudo ./install-service.sh /path/to/opencode_client
```
