# 腾讯云基础设施搭建指南

## 一次性初始化设置（管理员在腾讯云控制台操作）

### 1. 创建 VPC
- 名称：examlab-vpc
- CIDR：10.0.0.0/16

### 2. 创建子网
- 公有子网：10.0.1.0/24（用于管理服务器）
- 私有子网：10.0.2.0/23（用于考试 VM，约 512 个 IP）

### 3. 创建 NAT 网关
- 绑定到公有子网
- 关联私有子网的路由表
- 使考试 VM 能够访问外网（yum / apt 安装软件）

### 4. 创建管理安全组（sg-mgmt）
- 入站规则：放行你的 IP 的 SSH 22 端口，放行 0.0.0.0/0 的 HTTPS 443 端口
- 出站规则：全部放行

### 5. 创建管理服务器 CVM
- 规格：4 核 CPU、8GB 内存、100GB SSD 云硬盘
- 操作系统：CentOS 7.9 或 Ubuntu 22.04
- 放入公有子网，绑定管理安全组
- 分配并绑定一个弹性公网 IP（BGP）

### 6. 创建 API 访问密钥
- 访问管理（CAM）控制台 → API 密钥 → 新建密钥
- 将 SecretId 和 SecretKey 复制到 `.env` 文件中

### 7. 制作虚拟机镜像

#### Windows 管理机镜像
1. 基于腾讯云 Windows Server 2019/2022 公共镜像启动一台 CVM
2. 安装 OpenSSH Client（用于 SSH 访问 Linux 服务器）
3. 安装 Chrome 或 Firefox 浏览器
4. 将考试 bat 脚本复制到 `C:\ExamScripts\` 目录
5. 可选：安装 VS Code、Notepad++
6. 配置 Windows 防火墙放行 RDP（3389 端口）
7. 启用远程桌面
8. 执行 Sysprep 后创建自定义镜像
9. 记录生成的镜像 ID

#### Linux 目标服务器镜像
1. 基于腾讯云 CentOS 7/8 或 Ubuntu 20.04 公共镜像启动一台 CVM
2. 安装 openssh-server
3. 预装考试所需软件（Nginx、MySQL、Docker 等）
4. 创建考试专用账号并设置初始密码
5. 配置 sudo 权限
6. 开放 SSH 22 端口
7. 创建自定义镜像
8. 记录生成的镜像 ID

### 8. 部署应用

```bash
# 在管理服务器上执行
git clone <仓库地址> /opt/examlab
cd /opt/examlab
cp .env.example .env
# 编辑 .env，填入实际的腾讯云密钥、VPC ID、镜像 ID 等
nano .env

# 启动全部服务
docker compose up -d --build

# 创建管理员账号
docker compose exec backend python manage.py createsuperuser

# 验证
curl http://localhost/admin/
```

### 9. 部署后操作

1. 通过 `http://<公网IP>/admin/` 访问管理后台
2. 通过 CSV 批量导入学员账号
3. 在腾讯云控制台创建考试镜像模板
4. 创建第一场考试，配置 VM 规格 JSON
5. 为考试分配学员（创建 VmGroup）
6. 将考试状态改为"已就绪"并执行创建 VM
