# ExamLabPlatform 用户手册

> 上机考试系统 — 基于腾讯云 + Apache Guacamole 的远程虚拟机考试平台
>
> 版本：1.0 | 更新日期：2026-07-11

---

## 目录

1. [系统概述](#1-系统概述)
2. [快速开始](#2-快速开始)
3. [学员管理](#3-学员管理)
4. [创建考试](#4-创建考试)
5. [VM 管理](#5-vm-管理)
6. [学员端使用](#6-学员端使用)
7. [运维管理](#7-运维管理)
8. [常见问题](#8-常见问题)

---

## 1. 系统概述

### 1.1 是什么

ExamLabPlatform 是一个**浏览器内上机考试平台**。管理员创建考试并为学员分配虚拟机（Windows + Linux），学员通过浏览器远程桌面完成运维操作，全程无需安装任何客户端。

### 1.2 核心概念

```
┌──────────────────────────────────────────────────────┐
│  Exam（考试）                                         │
│  ├── 基本信息：名称、时间、时长                         │
│  ├── VM 规格：1 台 Windows + N 台 Linux 的配置         │
│  └── 学员列表（通过 VmGroup 关联）                      │
│                                                      │
│  VmGroup（学员-VM 组）                                 │
│  ├── 关联一个考试 + 一个学员                            │
│  ├── 包含一个腾讯云安全组（隔离用）                     │
│  └── 包含多个 VmInstance                               │
│                                                       │
│  VmInstance（单台虚拟机）                               │
│  ├── 类型：Windows 管理机 / Linux 目标服务器            │
│  ├── 规格：CPU、内存、磁盘、镜像                         │
│  ├── 状态：creating → running → stopped → terminated  │
│  └── 连接：通过 Guacamole 的浏览器内 RDP              │
└──────────────────────────────────────────────────────┘
```

### 1.3 访问地址

| 页面 | URL | 用途 |
|------|-----|------|
| 管理后台 | `http://<服务器IP>/admin/` | 考试管理、学员管理 |
| 学员登录 | `http://<服务器IP>/accounts/login/` | 学员登录 |
| 学员面板 | `http://<服务器IP>/exams/dashboard/` | 查看 VM、远程连接 |

---

## 2. 快速开始

### 2.1 登录管理后台

1. 打开浏览器访问 `http://<服务器IP>/admin/`
2. 输入管理员账号密码登录
3. 进入 Django Admin 管理界面

### 2.2 典型考试流程（8 步）

```
准备阶段                       考前                        考试中                  考后
┌──────────┐              ┌──────────┐                 ┌──────────┐          ┌──────────┐
│① 导入学员 │──────────────→│④ 创建考试 │────────────────→│⑦ 学员登录│──────────→│⑧ 回收 VM│
│② 制作镜像 │              │⑤ 分配学员 │                │  远程操作 │          │  标记完成│
│③ 配置环境 │              │⑥ 创建 VM  │                │  实时监控 │          └──────────┘
└──────────┘              └──────────┘                 └──────────┘
```

---

## 3. 学员管理

### 3.1 查看学员列表

导航：**Accounts → Students**

列表显示用户名、姓名、激活状态、注册时间。

### 3.2 手动添加单个学员

1. 点击右上角 **Add Student**
2. 填写用户名、姓名、密码
3. 点击 Save

### 3.3 CSV 批量导入学员

**步骤一：准备 CSV 文件**

创建一个 UTF-8 编码的 CSV 文件，包含以下列：

```csv
username,name,password
student01,张三,student01@123
student02,李四,student02@123
student03,王五,student03@123
```

> `password` 列可选，不填则默认为 `用户名@123`

**步骤二：导入**

1. 导航到 **Accounts → Students**
2. 点击右上角 **Import CSV** 按钮
3. 选择 CSV 文件，点击 Upload and Import
4. 系统自动跳过已存在的用户名，显示成功导入数量

**步骤三：验证**

导入后检查学员列表，确认数量和用户名正确。

### 3.4 启用/禁用学员

- 勾选学员
- 下拉 Actions 选择 **Enable selected students** 或 **Disable selected students**
- 点击 Go

被禁用的学员无法登录。

### 3.5 重置学员密码

1. 点击学员用户名进入编辑页
2. 点击密码字段下方的 **This form** 链接
3. 输入新密码
4. 点击 Save

---

## 4. 创建考试

### 4.1 新建考试

导航：**Exams → Exams → Add Exam**

#### 步骤一：填写考试基本信息

| 字段 | 说明 | 示例 |
|------|------|------|
| Name | 考试名称 | `Linux 运维认证考试` |
| Exam time | 考试开始时间 | `2026-07-15 14:00:00` |
| Duration minutes | 考试时长（分钟） | `120` |
| Status | 考试状态 | 新建选 `draft` |

#### 步骤二：配置 VM 规格

**Windows Management Machine：**

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| CPU Cores | 2 | 2-4 核 |
| RAM (GB) | 4 | 4-8 GB |
| Disk (GB) | 50 | 系统盘大小 |
| Image ID | `img-xxxxxxxx` | 腾讯云 Windows 镜像 ID |

**Linux Target Servers：**

点击 **+ Add Linux Server** 添加服务器，每台独立配置：

| 参数 | 说明 |
|------|------|
| Role | 服务器角色标签，如 Web服务器、数据库服务器 |
| CPU Cores | CPU 核数 |
| RAM (GB) | 内存大小 |
| Disk (GB) | 系统盘大小 |
| Image ID | 腾讯云 Linux 镜像 ID |

> **关于 Image ID**：需要先在腾讯云控制台制作好自定义镜像，然后将镜像 ID（格式：`img-xxxxxxxx`）填入。如果还未制作镜像，可以先填占位符，后续再改。

**典型 3 台 Linux 配置示例：**

| Role | CPU | RAM | Disk | 用途 |
|------|-----|-----|------|------|
| Web服务器 | 2 | 2 | 40 | Nginx/Apache |
| 应用服务器 | 2 | 2 | 40 | Tomcat/Node.js |
| 数据库服务器 | 2 | 4 | 50 | MySQL/PostgreSQL |

**VM 规格 JSON 格式参考：**

```json
{
  "windows": {
    "cpu": 2,
    "ram": 4,
    "disk": 50,
    "image_id": "img-windows2019"
  },
  "linux_servers": [
    { "role": "Web服务器", "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-centos7" },
    { "role": "应用服务器", "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-centos7" },
    { "role": "数据库服务器", "cpu": 2, "ram": 4, "disk": 50, "image_id": "img-centos7" }
  ]
}
```

#### 步骤三：分配学员

在 **Student Assignment** 区域，勾选要参加此考试的学员（复选框列表）。已分配的学员保存后会自动创建 VmGroup 记录。

#### 步骤四：保存

点击 **Save** 保存考试配置。

### 4.2 修改考试状态

考试有 4 种状态：

```
draft → ready → running → finished
  ↓       ↓        ↓         ↓
 草稿    已就绪   进行中    已结束
```

**变更状态的方式：**

1. 在考试列表页勾选考试
2. 下拉 Actions 选择对应操作：
   - **Mark as Ready** — 确认配置无误，准备创建 VM
   - **Mark as Running** — 手动标记为进行中
   - **Mark as Finished** — 考试结束
3. 点击 Go

> 通常「创建 VM」操作会自动将状态从 ready 改为 running。

---

## 5. VM 管理

### 5.1 创建虚拟机

**前提条件：**
- 考试状态为 **ready**
- `.env` 中腾讯云 API 密钥配置正确
- VPC、子网等基础资源已创建
- 镜像 ID 已填写有效的腾讯云镜像

**创建方式：**

1. 导航到考试列表页 **Exams → Exams**
2. 找到状态为 ready 的考试
3. 点击右侧 **Create VMs** 按钮
4. 确认对话框点确定

或进入考试编辑页，点击右上角 🚀 **Create VMs** 按钮。

**创建过程：**

系统会为每位学员：
1. 创建独立的腾讯云安全组（组内互通，组间隔离）
2. 创建 1 台 Windows 管理机
3. 创建 N 台 Linux 目标服务器
4. 将 VM 信息写入数据库（状态初始为 creating）

> 创建耗时：约 30 秒/学员，50 人约需 1-2 分钟。实际 VM 启动需要 2-5 分钟。

### 5.2 同步 VM 状态

VM 创建后需要等待腾讯云分配内网 IP 并完成启动。通过同步命令获取最新状态：

```bash
docker compose exec backend python manage.py sync_vm_status
```

建议每 1-2 分钟执行一次，直到所有 VM 状态变为 running。

### 5.3 查看 VM 状态

**方式一：考试编辑页 VM 状态总览**

打开考试编辑页，底部有 VM Status Overview 表格：

```
┌──────────┬──────────┬────────────────────┬──────────┬────────────────┐
│ Student  │ Windows  │ Linux VMs          │ VMs      │ Security Group │
├──────────┼──────────┼────────────────────┼──────────┼────────────────┤
│ student01│ Running  │ 🟢 Web服务器        │ 4/4      │ sg-abc123      │
│          │ 10.0.2.10│ 🟢 应用服务器       │ running  │                │
│          │          │ 🟢 数据库服务器     │          │                │
└──────────┴──────────┴────────────────────┴──────────┴────────────────┘
```

**方式二：VmGroup 列表**

导航：**Exams → Vm groups**

每个学员一行，显示关联考试、VM 运行数/总数。

**方式三：VmInstance 列表**

导航：**Exams → Vm instances**

每台 VM 一行，显示学员、考试、类型、状态指示灯、内网 IP。

### 5.4 VM 状态含义

| 状态 | 图标 | 说明 |
|------|------|------|
| creating | 🟠 | 正在创建中，等待腾讯云分配资源 |
| running | 🟢 | 运行中，已分配内网 IP，学员可连接 |
| stopped | 🔴 | 已关机 |
| terminated | ⚫ | 已销毁 |

### 5.5 学员连接 VM

1. 学员登录 `http://<服务器IP>/accounts/login/`
2. 进入考试面板，看到自己的 VM 卡片
3. Windows VM 显示 **Connect** 按钮
4. 点击后在新标签页中通过 Guacamole 打开 HTML5 远程桌面
5. 在 Windows 桌面中通过 SSH 客户端连接 Linux 服务器

### 5.6 考后回收 VM

考试结束后：

1. 确认所有学员已完成操作
2. 登录腾讯云控制台，手动销毁考试相关的 CVM 实例
3. 也可使用代码中的 `terminate_instances()` 函数批量销毁
4. 在管理后台将考试状态改为 **finished**

---

## 6. 学员端使用

### 6.1 登录

1. 打开 `http://<服务器IP>/accounts/login/`
2. 输入用户名和密码
3. 点击登录

### 6.2 考试面板

登录后看到的界面：

```
┌─────────────────────────────────────────┐
│ Welcome, student01          [Logout]    │
├─────────────────────────────────────────┤
│ Linux运维认证考试                         │
│ Remaining: 118 minutes                  │
├─────────────────────────────────────────┤
│ ┌─ Windows Management Machine ─────────┐│
│ │ 🟢 10.0.2.10 · Running              ││
│ │ 2 CPU · 4GB RAM · 50GB Disk         ││
│ │ [Connect]                            ││
│ └──────────────────────────────────────┘│
│ ┌─ Web服务器 ──────────────────────────┐│
│ │ 🟢 10.0.2.11 · Running              ││
│ │ 2 CPU · 2GB RAM · 40GB Disk         ││
│ │ SSH from Windows at 10.0.2.11       ││
│ └──────────────────────────────────────┘│
│ ┌─ 应用服务器 ─────────────────────────┐│
│ │ 🟢 10.0.2.12 · Running              ││
│ └──────────────────────────────────────┘│
│ ┌─ 数据库服务器 ────────────────────────┐│
│ │ 🟢 10.0.2.13 · Running              ││
│ └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### 6.3 远程连接

1. 点击 Windows 卡片上的 **Connect** 按钮
2. 新标签页打开，显示 Windows 远程桌面（通过 Guacamole HTML5 RDP）
3. 在 Windows 桌面中打开终端/SSH 客户端
4. SSH 连接到各 Linux 服务器（使用内网 IP）
5. 完成考试任务

### 6.4 倒计时提醒

- 剩余时间 > 15 分钟：红色显示
- 剩余时间 < 15 分钟：橙色警告
- 倒计时归零后建议停止操作

### 6.5 其他说明

- 考试期间可随时关闭连接窗口，返回面板重新点击 Connect
- Linux 服务器仅能从 Windows 管理机 SSH 访问，无直接远程桌面
- 学员之间 VM 完全网络隔离，互不可达

---

## 7. 运维管理

### 7.1 服务管理

```bash
# 启动全部服务
docker compose up -d

# 停止全部服务
docker compose stop

# 重启全部服务
docker compose restart

# 查看服务状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 查看单个服务日志
docker compose logs backend -f
docker compose logs guacamole -f
```

### 7.2 数据库操作

```bash
# 执行数据库迁移（代码更新后）
docker compose exec backend python manage.py migrate

# 创建新管理员
docker compose exec backend python manage.py createsuperuser

# 进入 Django shell
docker compose exec backend python manage.py shell

# 备份数据库
docker compose exec db pg_dump -U examlab examlab > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker compose exec -T db psql -U examlab examlab < backup.sql
```

### 7.3 VM 状态同步

```bash
# 同步所有 VM 的 IP 和状态
docker compose exec backend python manage.py sync_vm_status
```

可设置定时任务自动同步：

```bash
# 添加到 crontab（每 2 分钟同步一次）
*/2 * * * * cd /opt/examlab && docker compose exec -T backend python manage.py sync_vm_status
```

### 7.4 常用 Django Shell 操作

```bash
docker compose exec backend python manage.py shell
```

```python
# 查看某考试的 VM 状态
from exams.models import Exam, VmInstance
exam = Exam.objects.get(id=1)
for vm in VmInstance.objects.filter(group__exam=exam):
    print(f"{vm.group.student.username} | {vm.vm_type} | {vm.status} | {vm.private_ip}")

# 批量修改考试状态
Exam.objects.filter(id=1).update(status="finished")

# 统计 VM 数量
VmInstance.objects.filter(status="running").count()
```

### 7.5 创建学生脚本

```bash
cat << 'EOF' | docker compose exec -T backend python manage.py shell
from accounts.models import Student
for i in range(1, 51):
    username = f"student{i:03d}"
    Student.objects.create_user(
        username=username, name=f"学员{i}", password=f"{username}@123"
    )
    print(f"Created {username}")
EOF
```

---

## 8. 常见问题

### 8.1 登录问题

**Q：学员忘记密码怎么办？**
A：管理员在后台 **Accounts → Students** 中找到学员，点击编辑，重置密码。

**Q：学员显示「No active exam」？**
A：检查：
1. 学员是否被分配到此考试（检查 VmGroup）
2. 考试状态是否为 ready 或 running
3. 考试时间是否在有效范围内

### 8.2 VM 问题

**Q：点击 Create VMs 后报错？**
A：检查：
1. `.env` 中腾讯云 SecretId/SecretKey 是否正确
2. VPC ID、子网 ID 是否有效
3. 镜像 ID 是否存在
4. 腾讯云账号余额是否充足

**Q：VM 一直显示 creating？**
A：VM 创建需要 2-5 分钟，执行 `sync_vm_status` 同步状态。如果超过 10 分钟，登录腾讯云控制台检查实例状态。

**Q：学员点击 Connect 无法打开远程桌面？**
A：检查：
1. VM 内网 IP 是否已分配
2. Guacamole 服务是否运行：`docker compose ps guacamole`
3. Windows 防火墙是否放行 RDP 3389 端口（镜像制作时需确认）

### 8.3 费用相关

**Q：考试 VM 如何计费？**
A：使用腾讯云**按量计费**，考试期间按小时收费，关机后仅收磁盘费。

**参考费用（30 人 × 4 台 VM，2 小时考试）：**

| 项目 | 费用 |
|------|------|
| Windows 30 台 | ~16 元 |
| Linux 90 台 | ~16 元 |
| NAT 网关 | ~2 元 |
| **单场合计** | **~35 元** |

> 考完务必及时销毁 VM，否则持续计费！

**Q：月度固定费用？**
A：管理服务器 ~300 元/月 + 公网 IP ~80 元/月 + 流量 ~50-200 元/月 ≈ **~500 元/月**。

### 8.4 网络问题

**Q：Docker 镜像拉取太慢？**
A：已配置阿里云 PyPI 镜像。Docker 镜像可通过 Docker Desktop 设置国内镜像加速。

**Q：学员连接卡顿？**
A：Guacamole RDP 依赖管理服务器带宽，建议至少 5Mbps。学员-服务器-腾讯云 VM 之间的网络延迟会影响体验，建议学员和管理服务器在同一地域。

---

## 附录

### A. 考试状态流转图

```
                    ┌─────────┐
                    │  draft  │  新建考试
                    └────┬────┘
                         │ Mark as Ready
                    ┌────▼────┐
                    │  ready  │  配置完毕，显示 Create VMs 按钮
                    └────┬────┘
                         │ Create VMs（自动）
                    ┌────▼────┐
                    │ running │  学员可登录、可连接 VM
                    └────┬────┘
                         │ Mark as Finished
                    ┌────▼────┐
                    │finished │  考试结束，VM 待回收
                    └─────────┘
```

### B. 学员访问路径

```
学员浏览器
  │
  ▼ [HTTPS]
Nginx (:443)
  │
  ├── / → Django (:8000)        —— 管理后台、学员面板
  │
  └── /guacamole/ → Guacamole (:8080) —— WebSocket RDP 代理
       │
       └── guacd (:4822) —— RDP 协议转换
            │
            ▼ [RDP :3389]
      Windows VM (私有子网, 内网 IP)
            │
            ▼ [SSH :22]
      Linux VMs (同安全组内)
```

### C. 网络隔离示意

```
VPC: 10.0.0.0/16
│
├── 公有子网 10.0.1.0/24
│   └── 管理服务器 (公网 IP)
│
├── 私有子网 10.0.2.0/23
│   ├── sg-student-01 ─────────────┐
│   │   ├── Win-VM  10.0.2.10      │ 组内互通
│   │   ├── Linux-1 10.0.2.11      │
│   │   ├── Linux-2 10.0.2.12      │
│   │   └── Linux-3 10.0.2.13      │
│   ├── sg-student-02 ─────────────┤ 组间隔离 ✕
│   │   ├── Win-VM  10.0.2.20      │
│   │   └── ...                    │
│   └── ...                        │
│                                   │
└── NAT 网关 ───────────────────────┘ (出站外网访问)
```
