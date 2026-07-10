# ExamLabPlatform 系统设计方案

> 上机考试系统 — 基于腾讯云 + Apache Guacamole 的远程虚拟机考试平台
>
> 日期：2026-07-10 | 状态：已确认

---

## 1. 项目概述

### 1.1 目标

搭建一套上机考试系统：管理员提前为学员分配若干台虚拟机（Windows + Linux），学员通过浏览器远程桌面登录 Windows 管理机进行运维操作。系统部署在腾讯云上。

### 1.2 核心需求摘要

| 维度 | 决策 |
|------|------|
| 考试类型 | Linux 系统运维（RHCE / 运维认证类） |
| 学员规模 | 单场 20-50 人 |
| VM 配置 | 每学员 1 台 Windows 管理机 + N 台 Linux 目标服务器（N 可自由增减） |
| VM 生命周期 | 考前预分配，考后手动回收 |
| 远程连接 | 浏览器内 HTML5 远程桌面（Guacamole RDP 代理 Windows，Linux 通过 SSH 访问） |
| 认证方式 | 管理员批量导入账号（CSV），用户名+密码登录 |
| 部署环境 | 腾讯云 |
| 开发策略 | MVP 先行，后续迭代扩展 |

---

## 2. 系统架构

### 2.1 总体架构（三层）

```
接入层（浏览器）
  ├── 学员端：登录 → 考试面板 → 远程桌面
  └── 管理端：考试管理 → VM 管理 → 学员管理

        ↓ HTTPS / WSS

服务层（腾讯云 CVM · 1 台 · 4核8G · 公有子网）
  ├── Nginx        — 反向代理、SSL 终结、WebSocket 代理
  ├── Django App   — 管理后台、REST API、腾讯云 SDK
  ├── Guacamole    — Tomcat(WebSocket) + guacd(VNC/RDP 代理)
  └── PostgreSQL   — 业务数据库

        ↓ RDP 3389（内网）

资源层（腾讯云 CVM · 按量计费 · 私有子网）
  ├── Win-VM-1  Linux-1-1  Linux-1-2  Linux-1-3  ← 学员A
  ├── Win-VM-2  Linux-2-1  Linux-2-2  Linux-2-3  ← 学员B
  └── ... 共 30 组，~120 台 VM
```

### 2.2 技术选型

| 项目 | 选型 | 理由 |
|------|------|------|
| 后端框架 | Python Django | Admin 开箱即用，ORM 成熟，腾讯云 SDK 支持好 |
| 数据库 | PostgreSQL | Django 最佳搭档，JSON 字段灵活存储 VM 配置 |
| 远程桌面网关 | Apache Guacamole | VNC/RDP → HTML5 Canvas，无需客户端，支持会话录制 |
| Windows 远程协议 | RDP | Windows 原生支持，Guacamole 内置 RDP 代理 |
| Linux 访问方式 | SSH（无需 GUI） | 学员从 Windows 管理机通过 SSH 操作 Linux |
| 反向代理 | Nginx | SSL 终结、WebSocket 代理（Guacamole 需要） |
| 部署方式 | Docker Compose | 统一编排，一条命令启停 |
| 云平台 | 腾讯云 | 用户指定 |

---

## 3. 网络架构

### 3.1 VPC 规划

| 组件 | 配置 | 说明 |
|------|------|------|
| VPC | 1 个 | 包含所有资源 |
| 公有子网 | 10.0.1.0/24 | 仅管理服务器，绑定公网 IP |
| 私有子网 | 10.0.2.0/23 | 120 台考试 VM，无公网 IP |
| NAT 网关 | 1 个 | 私有子网出站访问（yum/apt 等） |
| 安全组 | ~31 个 | 管理组 + 每学员一个独立安全组 |

### 3.2 学员隔离方案

核心思路：**每学员一个独立安全组，组内互通，组间默认隔离。**

- 学员 N 的 4 台 VM 全部加入安全组 `sg-student-N`
- 安全组规则：同组内全部放行，不同组间无规则（腾讯云默认拒绝）
- IP 分配规整：学员 N 的 Windows IP = `10.0.2.(N×10+0)`，Linux IP = `10.0.2.(N×10+1)` ~ `10.0.2.(N×10+N_linux)`

### 3.3 访问规则

| 流量方向 | 规则 | 实现 |
|----------|------|------|
| 学员 → 管理平台 | ✅ HTTPS 443 | 公网，Nginx 代理 |
| Guacamole → Windows VM | ✅ RDP 3389 | 同 VPC 内网，安全组放行 |
| Windows VM → 同组 Linux | ✅ SSH 22 | 同安全组内互通 |
| 学员-A VM → 学员-B VM | ❌ 拒绝 | 不同安全组，默认隔离 |
| VM → 外网 | ✅ 出站 | NAT 网关 |
| 外网 → 考试 VM | ❌ 不可达 | 无公网 IP |

### 3.4 学员访问路径

```
学员浏览器 → [HTTPS] → Nginx → [WSS] Guacamole → [RDP:3389] Windows VM → [SSH:22] Linux VM
```

学员全程无需知道任何 IP 地址，只需在浏览器中点击「连接」。

---

## 4. 数据库设计

### 4.1 核心表结构

```
exam (考试场次)
├── id (PK)
├── name              — 考试名称
├── exam_time         — 考试开始时间
├── duration_minutes  — 考试时长（分钟）
├── status            — draft / ready / running / finished
├── vm_spec           — JSON: Windows + Linux[] 的规格配置
└── created_at

student (学员)
├── id (PK)
├── username          — 登录名
├── password_hash     — 密码哈希
├── name              — 真实姓名
├── is_active         — 是否启用
└── created_at

vm_image (镜像模板)
├── id (PK)
├── name              — 模板名称
├── os_type           — windows / linux
├── tencent_image_id  — 腾讯云镜像 ID
├── presets           — JSON: 预装软件列表
└── created_at

vm_group (学员考试 VM 组)
├── id (PK)
├── exam_id (FK)      — 所属考试
├── student_id (FK)   — 所属学员
├── security_group_id — 腾讯云安全组 ID
├── subnet_ip_base    — IP 基址（如 10.0.2.10）
└── created_at

vm_instance (单台虚拟机)
├── id (PK)
├── group_id (FK)     — 所属 VM 组
├── vm_type           — windows / linux_server (带序号)
├── role_label        — 角色标签（Web 服务器 / 应用服务器 / 数据库服务器）
├── cpu / ram / disk  — 资源配置
├── cvm_instance_id   — 腾讯云实例 ID
├── private_ip        — 内网 IP
├── status            — creating / running / stopped / terminated
├── guacamole_connection_id — Guacamole 连接配置 ID
└── created_at

connection_log (连接日志)
├── id (PK)
├── vm_id (FK)
├── student_id (FK)
├── connected_at
├── disconnected_at
└── created_at
```

### 4.2 exam.vm_spec JSON 结构

```json
{
  "windows": {
    "cpu": 2,
    "ram": 4,
    "disk": 50,
    "image_id": "img-xxx"
  },
  "linux_servers": [
    { "role": "Web服务器",   "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-yyy" },
    { "role": "应用服务器",  "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-yyy" },
    { "role": "数据库服务器", "cpu": 2, "ram": 4, "disk": 50, "image_id": "img-zzz" }
  ]
}
```

`linux_servers` 为数组，支持任意数量、每台独立配置资源和角色。

---

## 5. 功能模块

### 5.1 P0 功能（MVP 必备）

| 模块 | 功能点 |
|------|--------|
| **学员管理** | CSV 批量导入、账号启用/禁用、重置密码 |
| **考试管理** | 创建考试、配置 VM 规格（Windows + 动态 Linux 列表）、分配学员、一键批量创建 VM |
| **远程连接** | Guacamole RDP 集成，浏览器内 HTML5 远程桌面 |
| **学员面板** | 登录、查看自己的 VM 列表（含状态）、一键连接 Windows 管理机、考试倒计时 |

### 5.2 P1 功能（后续迭代）

| 模块 | 功能点 |
|------|--------|
| **镜像管理** | 创建/管理自定义镜像模板，关联预装软件清单 |
| **VM 生命周期** | 开机/关机/销毁操作、批量状态监控 |
| **操作日志** | 连接记录、会话时长统计 |

### 5.3 管理员界面

- **考试列表页**：考试列表（名称/时间/人数/状态），支持创建/编辑/删除
- **创建考试页**：基本信息 + VM 规格配置（Windows 固定 1 台，Linux 服务器动态增减，每台独立规格） + 学员 CSV 导入 + 一键创建 VM
- **学员管理页**：学员列表、CSV 导入、启用/禁用

### 5.4 学员界面

- **登录页**：用户名 + 密码
- **考试面板**：考试倒计时、VM 卡片列表（Windows 管理机 + N 台 Linux 各显状态）、连接按钮

---

## 6. 镜像制作

### 6.1 Windows 管理机镜像

1. 基于腾讯云 Windows Server 2019/2022 公共镜像
2. 安装 OpenSSH Client（SSH 访问 Linux 用）
3. 安装 Chrome 或 Firefox 浏览器
4. 将考试 bat 脚本放到 `C:\ExamScripts\` 目录
5. 可选：安装 VS Code、Notepad++
6. 配置 Windows 防火墙允许 RDP (3389)
7. 开启远程桌面
8. Sysprep → 创建自定义镜像

### 6.2 Linux 目标服务器镜像

1. 基于腾讯云 CentOS 7/8 或 Ubuntu 20.04 公共镜像
2. 安装 openssh-server
3. 预装考试目标软件（Nginx、MySQL、Docker 等，视考试内容而定）
4. 创建考试专用账号 + 初始密码
5. 配置 sudo 权限
6. 开放 SSH 22 端口
7. 创建自定义镜像

---

## 7. 腾讯云部署

### 7.1 资源清单

| 资源 | 规格 | 数量 | 计费方式 |
|------|------|------|----------|
| CVM 管理服务器 | 4核8G · 100GB SSD | 1 台 | 包年包月 |
| CVM 考试 Windows | 2核4G · 50GB SSD | 30 台 | 按量计费 |
| CVM 考试 Linux | 2核2G · 40GB SSD（基准） | ~90 台 | 按量计费 |
| NAT 网关 | 小型 | 1 个 | 按量+流量 |
| 公网 IP (EIP) | BGP | 1 个 | 按量 |
| VPC | — | 1 个 | 免费 |
| 安全组 | — | ~31 个 | 免费 |

### 7.2 费用估算

**单场 2 小时考试（30 人 × 4 台 VM）：**

| 项目 | 计算 | 费用 |
|------|------|------|
| Windows 30 台 | 0.27 元/时 × 30 × 2 | ~16 元 |
| Linux 90 台 | 0.09 元/时 × 90 × 2 | ~16 元 |
| NAT 网关 | ~1.2 元/时 × 2 | ~2 元 |
| **合计** | | **~35 元** |

⚠️ 关机后仍收磁盘费（~8 元/天/120台），考完确认后及时销毁。

**月度固定费用**：管理服务器（~300 元）+ 公网 IP（~80 元）+ 流量（~50-200 元）= **约 500 元/月**。

### 7.3 管理服务器部署

```
examlab/
├── docker-compose.yml      ← 一键启动
├── nginx/
│   ├── nginx.conf          ← 反向代理 + SSL + WSS
│   └── ssl/
├── backend/                ← Django
│   ├── Dockerfile
│   └── examlab/
├── guacamole/
│   └── guacamole.properties
├── init/
│   └── init-db.sql
└── .env                    ← 腾讯云 SecretId/Key
```

容器编排：Nginx(:443) → Django(:8000) + Guacamole Tomcat(:8080) + PostgreSQL(:5432) + guacd(:4822)

---

## 8. 考试执行流程

```
准备阶段                      考前                          考试中                      考后
┌──────────┐              ┌──────────┐                 ┌──────────┐              ┌──────────┐
│① 制作镜像 │──────────────→│⑤ 一键创建 │────────────────→│⑧ 学员登录│──────────────→│⑪ 关机 VM │
│② 导入学员 │              │  120台VM  │                │  远程操作 │              │⑫ 确认成绩│
│③ 创建考试 │              │⑥ 等待就绪 │                │⑨ 管理员  │              │⑬ 销毁 VM │
│④ 配置规格 │              │⑦ 通知学员 │                │  实时监控 │              │  释放资源 │
└──────────┘              └──────────┘                 │⑩ 倒计时  │              └──────────┘
                                                       └──────────┘
```

---

## 9. 设计决策记录

| 决策点 | 所选方案 | 备选方案 | 理由 |
|--------|----------|----------|------|
| 远程桌面网关 | Apache Guacamole | noVNC 直连 / ttyd 终端 | Guacamole 是成熟 HTML5 方案，支持 RDP/VNC 多协议，有会话录制能力 |
| 后端框架 | Django | Go / Spring Boot | Admin 后台开箱即用，Python 生态丰富，MVP 开发效率高 |
| 网络隔离 | 安全组隔离 | 子网隔离 | 30 个安全组 vs 30 个子网，管理复杂度更低 |
| VM 计费 | 按量计费 | 包年包月 | 考试 VM 使用时间短，按量更经济 |
| 部署 | Docker Compose | 传统安装 | 一键启停，依赖锁定，便于维护 |
| Linux 访问 | SSH（从 Windows 机发起） | VNC 桌面 | 运维考试场景只需命令行，省去每台 Linux 装 VNC 的开销 |
| Linux 服务器数量 | 动态自由增减 | 固定 3 台 | 适应不同考试科目的需求 |
| Linux 服务器规格 | 每台独立配置 | 统一规格 | 不同角色的服务器需要不同资源（如 DB 服务器需更多内存） |

---

## 10. 后续扩展方向（超出 MVP 范围）

- 考试题库管理与自动评分
- 会话录制与回放（Guacamole 原生支持）
- 微信扫码登录
- 定时自动创建/销毁 VM
- 学员自主注册 + 管理员审核
- 大规模考试支持（Kubernetes 编排）
