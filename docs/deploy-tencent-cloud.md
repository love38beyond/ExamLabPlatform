# 腾讯云部署指南

> ExamLabPlatform 服务器部署完整步骤（基于 CentOS 7 / Ubuntu 22.04）
>
> 最后更新：2026-07-11

---

## 目录

1. [前置条件](#1-前置条件)
2. [服务器环境准备](#2-服务器环境准备)
3. [部署项目](#3-部署项目)
4. [初始化数据库](#4-初始化数据库)
5. [验证部署](#5-验证部署)
6. [常见问题](#6-常见问题)
7. [运维命令速查](#7-运维命令速查)

---

## 1. 前置条件

### 1.1 腾讯云资源清单

| 资源 | 规格 | 说明 |
|------|------|------|
| VPC | 1 个，CIDR: 10.0.0.0/16 | 私有网络 |
| 公有子网 | 10.0.1.0/24 | 管理服务器 |
| 私有子网 | 10.0.2.0/23 | 考试 VM |
| 管理服务器 CVM | 4核8G，100GB 云硬盘 | CentOS 7.9 / Ubuntu 22.04 |
| 弹性公网 IP | 1 个 BGP | 绑定管理服务器 |
| 安全组 | 放行 80/443/22 | 管理服务器防火墙 |

### 1.2 本地环境

- SSH 客户端
- 服务器的公网 IP、root 密码

---

## 2. 服务器环境准备

### 2.1 SSH 登录

```bash
ssh root@<服务器公网IP>
```

### 2.2 安装 Git

```bash
# CentOS 7
yum install -y git

# Ubuntu 22.04
apt update && apt install -y git
```

### 2.3 安装 Docker

```bash
# 官方脚本（需服务器能访问外网）
curl -fsSL https://get.docker.com | bash

# 如果外网不通，使用腾讯云内网镜像源（CentOS 7）
cat > /etc/yum.repos.d/docker-ce.repo << 'EOF'
[docker-ce-stable]
name=Docker CE Stable
baseurl=http://mirrors.cloud.tencent.com/docker-ce/linux/centos/7/$basearch/stable
enabled=1
gpgcheck=0
EOF
yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2.4 配置 Docker 镜像加速

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
```

### 2.5 启动 Docker

```bash
systemctl start docker
systemctl enable docker

# 验证
docker --version
docker compose version
```

### 2.6 创建项目目录

```bash
mkdir -p /opt/examlab
```

---

## 3. 部署项目

### 3.1 上传代码

**方式一：Git 克隆（服务器能访问 GitHub）**

```bash
git clone https://github.com/love38beyond/ExamLabPlatform.git /opt/examlab
```

**方式二：本地打包上传（服务器不能访问 GitHub）**

```bash
# 本地执行
cd ~/project/examLab/ExamLabPlatform
git ls-files | tar -czf /tmp/examlab.tar.gz -T -
scp /tmp/examlab.tar.gz root@<服务器IP>:/tmp/

# 服务器执行
mkdir -p /opt/examlab
tar -xzf /tmp/examlab.tar.gz -C /opt/examlab
```

### 3.2 配置环境变量

```bash
cd /opt/examlab
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=<生成随机密钥>
DATABASE_URL=postgres://examlab:examlab@db:5432/examlab
ALLOWED_HOSTS=<服务器公网IP>,localhost,127.0.0.1
DB_NAME=examlab
DB_USER=examlab
DB_PASSWORD=examlab
DB_HOST=db
DB_PORT=5432

TENCENT_SECRET_ID=<你的SecretId>
TENCENT_SECRET_KEY=<你的SecretKey>
TENCENT_REGION=ap-shanghai
TENCENT_VPC_ID=<你的VPC ID>
TENCENT_SUBNET_ID_PUBLIC=<公有子网ID>
TENCENT_SUBNET_ID_PRIVATE=<私有子网ID>
TENCENT_SECURITY_GROUP_MGMT=<管理安全组ID>

GUACAMOLE_URL=http://guacamole:8080/guacamole
GUACAMOLE_USER=guacadmin
GUACAMOLE_PASSWORD=guacadmin
EOF
```

### 3.3 修改 Dockerfile（腾讯云内网环境）

> ⚠️ **重要**：无论服务器是否能用外网，都建议使用腾讯云内网镜像源（免费、速度快、不走公网流量）。如果后续升级代码，此步骤需要重新执行。

如果服务器无法访问外网，编辑 `backend/Dockerfile`，使用腾讯云内网镜像源：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 使用腾讯云 Debian 镜像源
RUN echo "deb http://mirrors.cloud.tencent.com/debian trixie main" > /etc/apt/sources.list && \
    echo "deb http://mirrors.cloud.tencent.com/debian trixie-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.cloud.tencent.com/debian-security trixie-security main" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i http://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "examlab.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### 3.4 修改 docker-compose.yml

**CentOS 7（内核 3.10）必须给 db 和 guacd 开启特权模式：**

```yaml
services:
  db:
    image: postgres:15-alpine
    privileged: true          # CentOS 7 必须
    volumes:
      - /opt/examlab/data/pgdata:/var/lib/postgresql/data
      - ./init/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    environment:
      POSTGRES_DB: examlab
      POSTGRES_USER: examlab
      POSTGRES_PASSWORD: examlab
    restart: unless-stopped

  guacd:
    image: guacamole/guacd:1.5.5
    privileged: true          # CentOS 7 必须
    restart: unless-stopped
```

**完整的 `docker-compose.yml`：**

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - guacamole
    restart: unless-stopped

  backend:
    build: ./backend
    volumes:
      - ./backend:/app
    env_file:
      - .env
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    privileged: true
    volumes:
      - /opt/examlab/data/pgdata:/var/lib/postgresql/data
      - ./init/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    environment:
      POSTGRES_DB: examlab
      POSTGRES_USER: examlab
      POSTGRES_PASSWORD: examlab
    restart: unless-stopped

  guacamole:
    image: guacamole/guacamole:1.5.5
    environment:
      GUACD_HOSTNAME: guacd
      POSTGRESQL_HOSTNAME: db
      POSTGRESQL_DATABASE: examlab
      POSTGRESQL_USER: examlab
      POSTGRESQL_PASSWORD: examlab
    depends_on:
      - guacd
      - db
    restart: unless-stopped

  guacd:
    image: guacamole/guacd:1.5.5
    privileged: true
    restart: unless-stopped
```

### 3.5 创建数据目录（CentOS 7）

```bash
mkdir -p /opt/examlab/data/pgdata
chmod 777 /opt/examlab/data/pgdata
```

### 3.6 构建并启动

```bash
cd /opt/examlab
docker compose up -d --build
```

首次构建约需 5-10 分钟（含镜像下载和 pip 安装依赖）。

检查服务状态：

```bash
docker compose ps
```

预期输出：5 个容器均为 `Up` 状态。

---

## 4. 初始化数据库

### 4.1 生成迁移文件

```bash
docker compose exec backend python manage.py makemigrations accounts exams
```

### 4.2 执行数据库迁移

```bash
docker compose exec backend python manage.py migrate
```

### 4.3 创建管理员账号

```bash
docker compose exec backend python manage.py createsuperuser
```

或通过 shell 创建：

```bash
echo "from accounts.models import Student; Student.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | docker compose exec -T backend python manage.py shell
```

### 4.4 批量创建学员

```bash
echo "
from accounts.models import Student
for i in range(1, 51):
    username = f'student{i:03d}'
    Student.objects.create_user(username=username, name=f'学员{i}', password=f'{username}@123')
print('Done')
" | docker compose exec -T backend python manage.py shell
```

---

## 5. 验证部署

### 5.1 检查各页面

```bash
# 本地或任意能访问服务器的电脑执行
curl -s -o /dev/null -w "%{http_code}" http://<服务器IP>/admin/login/
curl -s -o /dev/null -w "%{http_code}" http://<服务器IP>/accounts/login/
curl -s -o /dev/null -w "%{http_code}" http://<服务器IP>/static/admin/css/base.css
```

预期全部返回 `200`。

### 5.2 浏览器访问

- 管理后台：`http://<服务器IP>/admin/`
- 学员登录：`http://<服务器IP>/accounts/login/`

### 5.3 服务状态确认

```bash
docker compose ps
```

| 服务 | 预期状态 | 端口 |
|------|---------|------|
| nginx | Up | 80, 443 |
| backend | Up | 8000 |
| db | Up | 5432 |
| guacamole | Up | 8080 |
| guacd | Up (healthy) | 4822 |

---

## 6. 常见问题

### 6.1 数据库容器反复重启

**错误信息**：`could not write to file "postmaster.pid": Operation not permitted`

**原因**：CentOS 7 的 3.10 内核与 postgres:15-alpine 容器兼容性问题。

**解决**：在 `docker-compose.yml` 的 `db` 服务中添加 `privileged: true`。

### 6.2 pip install 超时

**错误信息**：`ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out`

**解决**：修改 Dockerfile 使用腾讯云内网 PyPI 镜像：
```dockerfile
RUN pip install --no-cache-dir -i http://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com -r requirements.txt
```

### 6.3 apt-get 无法连接

**错误信息**：`Unable to connect to deb.debian.org:http`

**解决**：修改 Dockerfile 使用腾讯云内网 Debian 镜像：
```dockerfile
RUN echo "deb http://mirrors.cloud.tencent.com/debian trixie main" > /etc/apt/sources.list
```

### 6.4 Docker Hub 拉取镜像失败

**错误信息**：`Error response from daemon: Get https://registry-1.docker.io/v2/: dial tcp: connect: connection refused`

**解决**：配置 Docker 镜像加速：
```bash
cat > /etc/docker/daemon.json << 'EOF'
{ "registry-mirrors": ["https://mirror.ccs.tencentyun.com"] }
EOF
systemctl restart docker
```

### 6.5 Static 文件 404

**错误信息**：静态 CSS/JS 返回 404，管理后台样式丢失。

**原因**：`DEBUG=False` 时 Django 不提供静态文件。

**解决**：
1. 安装 whitenoise：`echo "whitenoise>=6" >> requirements.txt`
2. 在 `settings.py` 添加中间件：
   ```python
   MIDDLEWARE = [
       "whitenoise.middleware.WhiteNoiseMiddleware",  # 放在 SecurityMiddleware 之后
       ...
   ]
   ```
3. 配置存储后端：
   ```python
   STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
   ```
4. 重新构建：`docker compose up -d --build`

### 6.6 升级后构建失败：apt-get 或 pip 超时

**错误信息**：
```
E: Unable to locate package libpq-dev
# 或
ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out
```

**原因**：升级代码后 `Dockerfile` 被覆盖为本地版本（使用 deb.debian.org 和 pypi.org/aliyun），服务器无法访问这些外部源。

**解决**：修改 `Dockerfile` 使用腾讯云内网镜像源，参见 [代码升级步骤四](#步骤四修复-dockerfile必须)。

### 6.7 升级后数据丢失

**错误信息**：管理后台登录后学员、考试数据全部消失。

**原因**：升级后的 `docker-compose.yml` 使用了 Docker 命名卷（`pgdata:/var/lib/postgresql/data`），而旧数据存在宿主机目录（`/opt/examlab/data/pgdata`）。

**解决**：修改 `docker-compose.yml` 使用宿主机目录挂载，参见 [代码升级步骤五](#步骤五修复数据卷配置必须)。

### 6.8 升级后静态文件 404（管理后台无样式）

**错误信息**：页面能打开但没有任何样式，浏览器 Console 显示 CSS/JS 返回 404。

**原因**：代码卷挂载（`./backend:/app`）会覆盖 Docker build 时 `collectstatic` 生成的静态文件。`DEBUG=False` 时 Django 不提供静态文件，Whitenoise 也找不到被覆盖的文件。

**解决**：在 `.env` 中设置 `DEBUG=True`，Django 会在开发模式下直接提供静态文件。

```bash
sed -i 's/DEBUG=False/DEBUG=True/' /opt/examlab/.env
docker compose restart backend
```

### 6.9 网站访问 502 Bad Gateway

**排查步骤：**
```bash
# 检查后端服务状态
docker compose ps backend

# 查看后端日志
docker compose logs backend --tail 50

# 检查数据库连接
docker compose logs db --tail 20
```

---

## 7. 运维命令速查

### 服务管理

```bash
docker compose up -d              # 启动
docker compose up -d --build      # 重新构建并启动
docker compose stop               # 停止
docker compose restart            # 重启
docker compose restart backend    # 重启单个服务
docker compose down               # 停止并删除容器
docker compose down -v            # 停止并删除容器 + 数据卷
docker compose ps                 # 查看状态
docker compose logs -f            # 查看所有日志
docker compose logs backend -f    # 查看后端日志
```

### 数据库

```bash
# 备份
docker compose exec db pg_dump -U examlab examlab > backup_$(date +%Y%m%d).sql

# 恢复
docker compose exec -T db psql -U examlab examlab < backup.sql

# 执行迁移
docker compose exec backend python manage.py migrate

# 进入 Shell
docker compose exec backend python manage.py shell
```

### VM 管理

```bash
# 同步 VM 状态
docker compose exec backend python manage.py sync_vm_status
```

### 代码升级（完整流程）

> ⚠️ 服务器不是 Git 仓库时，需从本地打包上传。

**步骤一：本地打包**

```bash
cd ~/project/examLab/ExamLabPlatform
git ls-files | tar -czf /tmp/examlab.tar.gz -T -
```

**步骤二：备份服务器配置**

```bash
ssh root@<服务器IP>
cp /opt/examlab/.env /tmp/examlab.env.backup
```

**步骤三：上传并解压**

```bash
# 本地执行
scp /tmp/examlab.tar.gz root@<服务器IP>:/tmp/

# 服务器执行
tar -xzf /tmp/examlab.tar.gz -C /opt/examlab
cp /tmp/examlab.env.backup /opt/examlab/.env
```

**步骤四：修复 Dockerfile（必须）**

> ⚠️ 升级会覆盖 `Dockerfile`，本地文件使用 Debian 官方源和阿里云 PyPI 源。服务器如果无法访问外网，**必须手动改回腾讯云内网镜像源**，否则构建失败。

```bash
cd /opt/examlab
cat > backend/Dockerfile << 'DOCKEREOF'
FROM python:3.11-slim

WORKDIR /app

# 腾讯云 Debian 内网镜像（代替 deb.debian.org）
RUN echo "deb http://mirrors.cloud.tencent.com/debian trixie main" > /etc/apt/sources.list && \
    echo "deb http://mirrors.cloud.tencent.com/debian trixie-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.cloud.tencent.com/debian-security trixie-security main" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 腾讯云 PyPI 内网镜像（代替 pypi.org / mirrors.aliyun.com）
RUN pip install --no-cache-dir -i http://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "examlab.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
DOCKEREOF
```

**步骤五：修复数据卷配置（必须）**

> ⚠️ 升级可能覆盖 `docker-compose.yml`。本地文件使用命名卷 `pgdata`，服务器用的是宿主机目录 `/opt/examlab/data/pgdata`。如果卷类型变了，**数据库会丢失**。

```bash
# 检查 db 服务的 volumes 配置
grep -A3 "pgdata\|/var/lib/postgresql" docker-compose.yml

# 如果显示的是 "pgdata:/var/lib/postgresql/data"（命名卷），改为宿主机目录：
sed -i 's|- pgdata:/var/lib/postgresql/data|- /opt/examlab/data/pgdata:/var/lib/postgresql/data|' docker-compose.yml
# 同时删除底部 volumes: 段落中的 pgdata 声明
```

**步骤六：检查并修复 DEBUG 配置（必须）**

> ⚠️ 升级后如果静态文件 404（管理后台无样式），检查 `.env` 中 `DEBUG` 值。
> 当前部署方案中 `DEBUG=True` 是为了让 Django 直接提供静态文件（`DEBUG=False` 时 Whitenoise 需要额外的 Manifest 文件，与代码卷挂载冲突）。

```bash
grep DEBUG /opt/examlab/.env
# 确保是: DEBUG=True
```

**步骤七：重新构建并启动**

```bash
cd /opt/examlab
docker compose up -d --build
```

**步骤八：执行数据库迁移**

```bash
docker compose exec backend python manage.py migrate
```

**步骤九：收集静态文件**

```bash
docker compose exec backend python manage.py collectstatic --noinput
```

**步骤十：验证升级**

```bash
docker compose ps                                # 5 个容器全部 Up
curl -sI http://localhost/admin/login/ | head -1 # 200 OK
curl -sI http://localhost/static/admin/css/base.css | head -1 # 200 OK
```

### 升级检查清单

| 序号 | 步骤 | 命令 |
|------|------|------|
| 1 | 备份 .env | `cp .env /tmp/examlab.env.backup` |
| 2 | 上传解压 | `tar -xzf /tmp/examlab.tar.gz` |
| 3 | 恢复 .env | `cp /tmp/examlab.env.backup .env` |
| 4 | 修复 Dockerfile（镜像源） | `cat backend/Dockerfile` 确认使用 `mirrors.cloud.tencent.com` |
| 5 | 修复数据卷 | `grep pgdata docker-compose.yml` 确认宿主机路径 |
| 6 | 修复 DEBUG | `grep DEBUG .env` 确认为 `True` |
| 7 | 构建启动 | `docker compose up -d --build` |
| 8 | 数据库迁移 | `docker compose exec backend python manage.py migrate` |
| 9 | 收集静态 | `docker compose exec backend python manage.py collectstatic --noinput` |
| 10 | 验证 | `curl` 测试各页面 |

### 查看磁盘空间

```bash
# Docker 占用
docker system df

# 清理无用镜像和容器
docker system prune -a
```

---

## 附录：部署检查清单

| 步骤 | 命令 | 状态 |
|------|------|------|
| 1. 安装 Docker | `docker --version` | ☐ |
| 2. 配置镜像加速 | `cat /etc/docker/daemon.json` | ☐ |
| 3. 上传代码 | `ls /opt/examlab/docker-compose.yml` | ☐ |
| 4. 配置 .env | `cat /opt/examlab/.env` | ☐ |
| 5. 修改 docker-compose.yml | 确认 `privileged: true` | ☐ |
| 6. 创建数据目录 | `ls /opt/examlab/data/pgdata` | ☐ |
| 7. 构建并启动 | `docker compose ps` | ☐ |
| 8. 数据库迁移 | 执行 migrate 命令 | ☐ |
| 9. 创建管理员 | 执行 createsuperuser | ☐ |
| 10. 验证访问 | 浏览器打开 admin 页面 | ☐ |
