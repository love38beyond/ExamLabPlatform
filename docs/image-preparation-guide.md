# 考试镜像制作指南

> 如何制作 Windows 管理机镜像和 Linux 服务器镜像，并获取 Image ID
>
> 最后更新：2026-07-11

---

## 目录

1. [概述](#1-概述)
2. [Windows 管理机镜像](#2-windows-管理机镜像)
3. [Linux 服务器镜像](#3-linux-服务器镜像)
4. [获取 Image ID](#4-获取-image-id)
5. [镜像 ID 配置](#5-镜像-id-配置)
6. [常见问题](#6-常见问题)

---

## 1. 概述

### 什么是 Image ID

Image ID 是腾讯云自定义镜像的唯一标识，格式为 `img-xxxxxxxx`。系统通过 Image ID 指定创建 VM 时使用的操作系统镜像。

### 为什么需要自定义镜像

- 预装考试所需软件（SSH、浏览器、Docker 等）
- 预配置考试账号和环境
- 避免每次创建 VM 时手动安装软件
- 保证所有学员环境一致

### 制作流程总览

```
公共镜像 → 启动临时 CVM → 登录配置环境 → 关机 → 创建自定义镜像 → 获取 Image ID
```

---

## 2. Windows 管理机镜像

### 2.1 启动 Windows CVM

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/cvm)
2. 点击 **新建** → 按量计费
3. 选择配置：

| 参数 | 推荐值 |
|------|--------|
| 地域 | 与考试 VPC 一致（如 `ap-shanghai`） |
| 镜像 | **Windows Server 2019 数据中心版** 或 **Windows Server 2022** |
| 规格 | 2核4G（S5.MEDIUM2） |
| 系统盘 | 高性能云硬盘 50GB |
| 网络 | examlab-vpc → 公有子网（方便远程配置） |
| 安全组 | 放行 RDP 3389 |

4. 设置密码，点击购买

### 2.2 远程登录 Windows

**方式一：腾讯云控制台网页登录**

1. CVM 列表 → 点击实例 → 远程连接 → RDP 文件
2. 下载 `.rdp` 文件，双击用远程桌面打开
3. 输入设置的密码

**方式二：本地远程桌面**

- Mac：Microsoft Remote Desktop（App Store 下载）
- Windows：Win+R → `mstsc` → 输入公网 IP

### 2.3 安装必要软件

登录后依次安装以下软件：

#### a) Chrome 或 Firefox 浏览器

```powershell
# Chrome（PowerShell 管理员模式）
Invoke-WebRequest -Uri https://dl.google.com/chrome/install/latest/chrome_installer.exe -OutFile C:\chrome_installer.exe
Start-Process C:\chrome_installer.exe -Wait
Remove-Item C:\chrome_installer.exe
```

#### b) OpenSSH Client

```powershell
# Windows Server 2019+ 自带，检查是否已安装
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'

# 如未安装：
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

#### c) VS Code（可选）

下载安装：https://code.visualstudio.com/

#### d) Notepad++（可选）

下载安装：https://notepad-plus-plus.org/

### 2.4 放置考试脚本

```powershell
# 创建考试脚本目录
mkdir C:\ExamScripts

# 例如：创建 SSH 连接脚本
@"
@echo off
echo ============================
echo   Exam Lab Environment
echo ============================
echo.
echo Web Server:    ssh root@10.0.2.11
echo App Server:    ssh root@10.0.2.12
echo DB Server:     ssh root@10.0.2.13
echo.
echo Exam Scripts Directory: C:\ExamScripts
"@ > C:\ExamScripts\exam-info.bat
```

### 2.5 配置 Windows 防火墙

```powershell
# 确认 RDP 3389 端口已放行
netsh advfirewall firewall show rule name="Remote Desktop"

# 如果没有规则，添加：
netsh advfirewall firewall add rule name="Remote Desktop" dir=in protocol=TCP localport=3389 action=allow

# 放行出站 SSH 22（连接 Linux 用）
netsh advfirewall firewall add rule name="SSH Out" dir=out protocol=TCP remoteport=22 action=allow
```

### 2.6 启用远程桌面

1. Win+R → `sysdm.cpl` → 远程 选项卡
2. 勾选 **允许远程连接到此计算机**
3. 取消勾选 "仅允许运行使用网络级别身份验证..."（兼容性更好）

### 2.7 Sysprep 并创建镜像

```powershell
# 以管理员身份运行 CMD
cd C:\Windows\System32\Sysprep
sysprep.exe /oobe /generalize /shutdown
```

> Sysprep 会清除 SID、计算机名等唯一信息，执行后系统自动关机。

**Sysprep 完成后**，回到腾讯云控制台：

1. CVM 列表 → 找到该 Windows 实例
2. 点击右侧 **更多** → **镜像** → **创建自定义镜像**
3. 填写镜像名称：`examlab-windows-2019`
4. 点击确定，等待 5-10 分钟

---

## 3. Linux 服务器镜像

### 3.1 启动 Linux CVM

| 参数 | 推荐值 |
|------|--------|
| 镜像 | CentOS 7.9 或 Ubuntu 22.04 |
| 规格 | 2核2G（S5.MEDIUM4） |
| 系统盘 | 高性能云硬盘 40GB |
| 网络 | examlab-vpc → 公有子网 |
| 安全组 | 放行 SSH 22 |

### 3.2 SSH 登录

```bash
ssh root@<公网IP>
```

### 3.3 安装基础软件

**CentOS 7：**
```bash
yum install -y openssh-server vim wget curl net-tools
systemctl enable sshd
```

**Ubuntu 22.04：**
```bash
apt update
apt install -y openssh-server vim wget curl net-tools
systemctl enable ssh
```

### 3.4 预装考试目标软件

根据考试内容选择性安装：

```bash
# Nginx
yum install -y nginx          # CentOS
apt install -y nginx           # Ubuntu

# MySQL / MariaDB
yum install -y mariadb-server # CentOS
apt install -y mysql-server    # Ubuntu

# Docker
curl -fsSL https://get.docker.com | bash

# Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -  # CentOS
yum install -y nodejs
```

### 3.5 配置 SSH

> **注意**：无需在镜像中创建考试账号。系统创建 VM 时会通过 [腾讯云 UserData](https://cloud.tencent.com/document/product/213/17525) 自动注入 cloud-init 脚本，为每位学员生成独立的 Linux 账号和密码。镜像只需确保 SSH 服务可用即可。

```bash
# 确保 SSH 22 端口开放
sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin no/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl restart sshd
```

### 3.6 清理并创建镜像

```bash
# 清理系统日志和缓存
yum clean all                   # CentOS
apt clean                       # Ubuntu
rm -rf /var/log/*.log
rm -rf /tmp/*
history -c

# 关机
shutdown -h now
```

关机后，在腾讯云控制台：
1. CVM 列表 → 找到该 Linux 实例
2. 点击右侧 **更多** → **镜像** → **创建自定义镜像**
3. 填写镜像名称：`examlab-centos7`
4. 点击确定

---

## 4. 获取 Image ID

### 4.1 控制台获取

1. 登录腾讯云控制台
2. 左侧导航 → **镜像** → **自定义镜像**
3. 列表中每个镜像的 ID 列即为 Image ID

```
┌─────────────────────────────────────────────────────┐
│ 镜像名称              │ 镜像ID        │ 状态         │
├─────────────────────────────────────────────────────┤
│ examlab-windows-2019  │ img-abc12345  │ 正常         │
│ examlab-centos7       │ img-def67890  │ 正常         │
│ examlab-ubuntu22      │ img-ghi11223  │ 正常         │
└─────────────────────────────────────────────────────┘
```

### 4.2 命令行获取

在管理服务器上通过 API 获取：

```bash
cd /opt/examlab
docker compose exec backend python manage.py shell
```

```python
from tencentcloud.common import credential
from tencentcloud.cvm.v20170312 import cvm_client, models

cred = credential.Credential("你的SecretId", "你的SecretKey")
client = cvm_client.CvmClient(cred, "ap-shanghai")

req = models.DescribeImagesRequest()
req.Filters = [{"Name": "image-type", "Values": ["PRIVATE_IMAGE"]}]
resp = client.DescribeImages(req)

for img in resp.ImageSet:
    print(f"{img.ImageId}  {img.ImageName}  {img.OsName}")
```

### 4.3 公共镜像 ID

部分公共镜像 ID（仅供参考，可能变更）：

| 镜像 | Image ID 格式 | 说明 |
|------|-------------|------|
| Windows Server 2019 数据中心版 | 查询控制台 | 每个地域不同 |
| Windows Server 2022 数据中心版 | 查询控制台 | 每个地域不同 |
| CentOS 7.9 | 查询控制台 | 每个地域不同 |
| Ubuntu 22.04 LTS | 查询控制台 | 每个地域不同 |

> 公共镜像 ID 也可通过 [腾讯云 API DescribeImages](https://cloud.tencent.com/document/api/213/15715) 查询。

---

## 5. 镜像 ID 配置

### 5.1 在管理后台配置

编辑考试时，在 VM 规格表单中填入镜像 ID：

```
🖥️ Windows Management Machine
├── CPU Cores: 2
├── RAM (GB): 4
├── Disk (GB): 50
├── Image ID: img-abc12345    ← 填 Windows 镜像 ID

🐧 Linux Target Servers
├── Role: Web服务器
│   ├── Image ID: img-def67890  ← 填 Linux 镜像 ID
├── Role: 应用服务器
│   ├── Image ID: img-def67890  ← 可复用同一个
└── Role: 数据库服务器
    ├── Image ID: img-ghi11223  ← 或使用不同镜像
```

### 5.2 JSON 格式（API/Shell 操作时）

```json
{
  "windows": {
    "cpu": 2,
    "ram": 4,
    "disk": 50,
    "image_id": "img-abc12345"
  },
  "linux_servers": [
    { "role": "Web服务器",   "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-def67890" },
    { "role": "应用服务器",  "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-def67890" },
    { "role": "数据库服务器", "cpu": 2, "ram": 4, "disk": 50, "image_id": "img-ghi11223" }
  ]
}
```

### 5.3 通过 Shell 批量更新

```bash
cd /opt/examlab
docker compose exec backend python manage.py shell
```

```python
from exams.models import Exam

# 更新所有考试的镜像 ID
for exam in Exam.objects.all():
    spec = exam.vm_spec
    spec["windows"]["image_id"] = "img-abc12345"
    for linux in spec["linux_servers"]:
        linux["image_id"] = "img-def67890"
    exam.vm_spec = spec
    exam.save(update_fields=["vm_spec"])
    print(f"Updated: {exam.name}")
```

### 5.4 注意事项

| 注意点 | 说明 |
|--------|------|
| 地域匹配 | 镜像 ID 必须与考试 VM 在同一地域 |
| 镜像状态 | 镜像必须是「正常」状态 |
| 系统盘大小 | 创建 VM 时的系统盘不能小于镜像的系统盘 |
| 跨地域复制 | 如多地部署，需在各地域分别制作镜像或使用跨地域复制功能 |

---

## 6. 常见问题

### Q：制作镜像需要多长时间？

A：3-5 分钟（Sysprep 完成后）+ 5-10 分钟（创建镜像）。总共约 15 分钟。

### Q：镜像收费吗？

A：自定义镜像本身免费，但镜像占用的快照按容量收费（约 0.12 元/GB/月）。

### Q：可以基于已有镜像更新吗？

A：可以。使用现有镜像启动 CVM → 更新软件 → 关机 → 创建新镜像。

### Q：创建 VM 时提示镜像不存在？

A：检查：
1. 镜像 ID 是否正确复制（不含空格）
2. 镜像所在区域是否与 `TENCENT_REGION` 一致
3. 镜像是否被误删除
4. 如果是跨账号，是否已共享镜像

### Q：不想制作自定义镜像，能用公共镜像吗？

A：可以，公共镜像的 Image ID 在腾讯云控制台或 API 文档中查询。但学员登录后环境是"空白"的，需手动安装软件。

### Q：考试账号需要在镜像里创建吗？

A：**不需要**。系统创建 VM 时会通过腾讯云 UserData（cloud-init）自动注入脚本，为每位学员生成独立的 Linux 账号和随机密码。镜像只需确保 SSH 服务正常、防火墙放行 22 端口即可。账号创建逻辑见 `backend/exams/services/tencent.py` 中的 `create_vms_for_exam()` 函数。

---

## 附录：完整镜像制作步骤检查清单

### Windows 镜像

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 启动 Windows CVM（按量计费） | ☐ |
| 2 | 远程桌面登录 | ☐ |
| 3 | 安装 Chrome/Firefox | ☐ |
| 4 | 确认 OpenSSH Client | ☐ |
| 5 | 可选：安装 VS Code、Notepad++ | ☐ |
| 6 | 放置考试脚本到 C:\ExamScripts | ☐ |
| 7 | 配置防火墙（放行 RDP 3389） | ☐ |
| 8 | 启用远程桌面 | ☐ |
| 9 | 执行 Sysprep | ☐ |
| 10 | 创建自定义镜像 | ☐ |
| 11 | 记录 Image ID | ☐ |

### Linux 镜像

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 启动 Linux CVM（按量计费） | ☐ |
| 2 | SSH 登录 | ☐ |
| 3 | 安装基础软件（ssh、vim 等） | ☐ |
| 4 | 安装考试目标软件 | ☐ |
| 5 | 配置 SSH 和防火墙 | ☐ |
| 6 | 清理日志和缓存 | ☐ |
| 7 | 关机 | ☐ |
| 8 | 创建自定义镜像 | ☐ |
| 9 | 记录 Image ID | ☐ |

### 配置

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 在考试 VM 规格中填入 Image ID | ☐ |
| 2 | 验证 Image ID 和地域匹配 | ☐ |
| 3 | 测试创建一台 VM 验证镜像可用 | ☐ |
