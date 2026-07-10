# ExamLabPlatform 打包与部署命令

## 环境要求

- Docker >= 24.0
- Docker Compose >= 2.20
- Git

---

## 一、初次部署

### 1. 克隆仓库

```bash
git clone <仓库地址> /opt/examlab
cd /opt/examlab
```

### 2. 配置环境变量

```bash
# 从模板复制环境变量文件
cp .env.example .env

# 编辑 .env，填入实际值
nano .env
```

`.env` 中必须配置的项：

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | Django 密钥 | 随机字符串 |
| `TENCENT_SECRET_ID` | 腾讯云 API SecretId | `AKIDxxxx` |
| `TENCENT_SECRET_KEY` | 腾讯云 API SecretKey | `xxxx` |
| `TENCENT_REGION` | 腾讯云地域 | `ap-guangzhou` |
| `TENCENT_VPC_ID` | VPC ID | `vpc-xxxxxxxx` |
| `TENCENT_SUBNET_ID_PRIVATE` | 私有子网 ID | `subnet-xxxxxxxx` |

### 3. 构建并启动

```bash
# 构建镜像并启动所有服务（后台运行）
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看各服务日志
docker compose logs -f
```

### 4. 初始化数据库

```bash
# 执行数据库迁移
docker compose exec backend python manage.py migrate

# 创建管理员账号
docker compose exec backend python manage.py createsuperuser
```

### 5. 收集静态文件

```bash
docker compose exec backend python manage.py collectstatic --noinput
```

### 6. 验证部署

```bash
# 检查 Django 配置
docker compose exec backend python manage.py check --deploy

# 测试访问
curl http://localhost/admin/
curl http://localhost/accounts/login/
```

---

## 二、日常运维

### 服务管理

```bash
# 启动全部服务
docker compose up -d

# 停止全部服务
docker compose stop

# 重启全部服务
docker compose restart

# 重启单个服务
docker compose restart backend
docker compose restart nginx

# 停止并删除容器（保留数据卷）
docker compose down

# 停止并删除容器 + 数据卷（重置全部数据）
docker compose down -v
```

### 日志查看

```bash
# 查看全部日志（实时跟踪）
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail 100

# 查看单个服务日志
docker compose logs backend -f
docker compose logs nginx
docker compose logs guacamole

# 查看最近 10 分钟日志
docker compose logs --since 10m backend
```

### 后端操作

```bash
# 进入 Django shell
docker compose exec backend python manage.py shell

# 执行数据库迁移
docker compose exec backend python manage.py migrate

# 查看待执行的迁移
docker compose exec backend python manage.py migrate --plan

# 创建新迁移文件（模型变更后）
docker compose exec backend python manage.py makemigrations

# 同步 VM 状态（获取 IP 和运行状态）
docker compose exec backend python manage.py sync_vm_status

# 修改管理员密码
docker compose exec backend python manage.py changepassword admin
```

### 数据库备份与恢复

```bash
# 备份数据库
docker compose exec db pg_dump -U examlab examlab > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker compose exec -T db psql -U examlab examlab < backup_20260101_120000.sql
```

---

## 三、升级部署

### 更新代码并重启

```bash
cd /opt/examlab

# 拉取最新代码
git pull origin master

# 重新构建镜像（依赖变更时）
docker compose build backend

# 重启服务
docker compose up -d

# 执行新迁移（如有）
docker compose exec backend python manage.py migrate

# 收集静态文件（如有变更）
docker compose exec backend python manage.py collectstatic --noinput
```

### 仅重启后端（无代码变更）

```bash
docker compose restart backend
```

---

## 四、国产服务器适配（ARM 架构）

如果使用华为鲲鹏、飞腾等 ARM 架构服务器：

```bash
# 构建时指定 ARM 平台
docker compose build --build-arg TARGETPLATFORM=linux/arm64

# 或在 docker-compose.yml 中 backend 服务添加
# platform: linux/arm64
```

---

## 五、HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 certbot
apt update && apt install -y certbot

# 生成证书（需要域名已解析到服务器 IP）
certbot certonly --standalone -d your-domain.com

# 证书文件位置
# 证书: /etc/letsencrypt/live/your-domain.com/fullchain.pem
# 私钥: /etc/letsencrypt/live/your-domain.com/privkey.pem

# 复制到 nginx ssl 目录
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# 修改 nginx/nginx.conf 添加 443 监听，然后重启
docker compose restart nginx
```

### 自动续期

```bash
# 添加 crontab 定时任务
0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/examlab/nginx/ssl/cert.pem && cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/examlab/nginx/ssl/key.pem && docker compose restart nginx
```

---

## 六、故障排查

### 服务无法启动

```bash
# 查看详细错误日志
docker compose logs backend --tail 50
docker compose logs db --tail 50

# 检查端口占用
netstat -tlnp | grep -E '80|443|8000|5432'
```

### 数据库连接问题

```bash
# 测试数据库连接
docker compose exec backend python -c "
import psycopg2
conn = psycopg2.connect(host='db', dbname='examlab', user='examlab', password='examlab')
print('Database connection OK')
conn.close()
"
```

### Guacamole 连接失败

```bash
# 检查 guacd 服务状态
docker compose exec guacamole curl -s http://guacd:4822/ | head -1

# 查看 Guacamole 日志
docker compose logs guacamole --tail 50
docker compose logs guacd --tail 50
```

### 重置管理员密码

```bash
docker compose exec backend python manage.py shell << EOF
from accounts.models import Student
user = Student.objects.get(username='admin')
user.set_password('new-password')
user.save()
print('Password reset OK')
EOF
```

---

## 七、完全卸载

```bash
cd /opt/examlab

# 停止并删除所有容器和网络
docker compose down -v

# 删除镜像（可选）
docker rmi examlabplatform-backend

# 删除代码
rm -rf /opt/examlab
```

---

## 命令速查表

| 操作 | 命令 |
|------|------|
| 构建并启动 | `docker compose up -d --build` |
| 查看状态 | `docker compose ps` |
| 查看日志 | `docker compose logs -f` |
| 重启服务 | `docker compose restart` |
| 停止服务 | `docker compose stop` |
| 执行迁移 | `docker compose exec backend python manage.py migrate` |
| 创建管理员 | `docker compose exec backend python manage.py createsuperuser` |
| 同步 VM 状态 | `docker compose exec backend python manage.py sync_vm_status` |
| 进入 shell | `docker compose exec backend python manage.py shell` |
| 备份数据库 | `docker compose exec db pg_dump -U examlab examlab > backup.sql` |
