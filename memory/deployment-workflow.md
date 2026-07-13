---
name: deployment-workflow
description: How to deploy, upgrade, and operate the platform
metadata:
  type: reference
---

部署与运维核心流程：

**初次部署：**
1. 腾讯云控制台创建 VPC + 子网 + NAT 网关 + 安全组 + 管理 CVM + API 密钥
2. SSH 登录管理服务器，安装 Docker + Docker Compose
3. `git clone` 代码 → 配置 `.env`（腾讯云密钥、VPC ID、子网 ID）→ `docker compose up -d --build`
4. `docker compose exec backend python manage.py migrate`
5. `docker compose exec backend python manage.py createsuperuser`

**日常运维：**
- `docker compose ps` 查看状态
- `docker compose logs -f backend` 查看日志
- `docker compose exec backend python manage.py sync_vm_status` 同步 VM IP/状态
- 数据库备份：`docker compose exec db pg_dump -U examlab examlab > backup.sql`

**升级：**
- `git pull` → `docker compose build backend` → `docker compose up -d` → `docker compose exec backend python manage.py migrate`

**关键注意事项：**
- 管理服务器上需要安装 Docker 而非 Docker Desktop（用官方脚本 `curl -fsSL https://get.docker.com`）
- CentOS 7 需要 privileged mode (`privileged: true`)，Ubuntu 22.04 不需要
- Guacamole 初始化依赖 `init/guacamole-init.sql` 中的 PostgreSQL schema
- 考试 VM 的 Linux 账号通过 UserData cloud-init 在创建时自动生成

**Why:** 标准化部署流程，确保管理服务器可以快速重建。

**How to apply:** 详见 docs/deploy-commands.md 和 docs/deploy-tencent-cloud.md。

**Related:** [[tencent-cloud-infra]] [[project-overview]]
