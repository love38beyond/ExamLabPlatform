# 腾讯云管理服务器创建步骤

## 概览

需要创建的资源清单：

| 序号 | 资源 | 说明 |
|------|------|------|
| 1 | VPC | 私有网络，10.0.0.0/16 |
| 2 | 公有子网 | 放管理服务器，10.0.1.0/24 |
| 3 | 私有子网 | 放考试 VM，10.0.2.0/23 |
| 4 | NAT 网关 | 私有子网访问外网 |
| 5 | 安全组 | 管理服务器防火墙规则 |
| 6 | 管理服务器 CVM | 4核8G，部署 Docker 服务 |
| 7 | 弹性公网 IP | 绑定管理服务器 |
| 8 | API 密钥 | 程序调用腾讯云 API |

---

## 第一步：创建 VPC 和子网

### 1.1 进入私有网络控制台

登录 [腾讯云控制台](https://console.cloud.tencent.com/)，顶部搜索「私有网络」进入。

### 1.2 创建 VPC

点击 **新建**：

| 字段 | 填写 |
|------|------|
| 地域 | 华南地区（广州）`ap-guangzhou` |
| 名称 | `examlab-vpc` |
| IPv4 CIDR | `10.0.0.0/16` |
| 子网名称 | `examlab-public` |
| 子网 IPv4 CIDR | `10.0.1.0/24` |
| 可用区 | 默认 |

创建完成后，在 VPC 列表中找到 `examlab-vpc`，点击进入详情。

### 1.3 创建私有子网

在 VPC 详情页 → **子网** → **新建**：

| 字段 | 填写 |
|------|------|
| 名称 | `examlab-private` |
| VPC | examlab-vpc |
| IPv4 CIDR | `10.0.2.0/23` |
| 可用区 | 默认 |

---

## 第二步：创建 NAT 网关

考试 VM 处于私有子网，没有公网 IP。NAT 网关让它们能访问外网（安装软件、更新系统）。

### 2.1 创建 NAT 网关

控制台搜索「NAT 网关」→ **新建**：

| 字段 | 填写 |
|------|------|
| 名称 | `examlab-nat` |
| 地域 | 广州 |
| 所属网络 | examlab-vpc |
| 类型 | 小型（满足 120 台 VM 需求） |
| 出带宽上限 | 50 Mbps |

### 2.2 配置路由表

创建完成后，进入 **路由表** 控制台：

1. 找到 `examlab-vpc` 的**私有子网路由表**（不是默认的那个）
2. 点击路由表名称 → **新增路由策略**：

| 字段 | 填写 |
|------|------|
| 目的端 | `0.0.0.0/0` |
| 下一跳类型 | NAT 网关 |
| 下一跳 | examlab-nat |

---

## 第三步：创建安全组

### 3.1 管理服务器安全组

控制台搜索「安全组」→ **新建**：

| 字段 | 填写 |
|------|------|
| 名称 | `examlab-mgmt-sg` |
| 模板 | 自定义 |

创建后点击**修改规则**，添加入站规则：

| 类型 | 来源 | 协议端口 | 说明 |
|------|------|----------|------|
| Linux 登录 | 你的办公 IP/32 | TCP:22 | SSH 管理 |
| HTTP | 0.0.0.0/0 | TCP:80 | 网站（后续加 HTTPS） |
| HTTPS | 0.0.0.0/0 | TCP:443 | 网站 |

> 安全起见，SSH 建议限制为你的办公 IP 地址。出站规则保持默认（全部放行）。

---

## 第四步：创建管理服务器 CVM

控制台搜索「云服务器」→ **新建**：

### 4.1 基础配置

| 字段 | 填写 |
|------|------|
| 计费模式 | **包年包月** |
| 地域 | 广州 |
| 可用区 | 默认 |

### 4.2 机型配置

| 字段 | 填写 |
|------|------|
| 机型 | 标准型 S5 |
| 规格 | **4核 8GB**（S5.MEDIUM8） |
| 镜像 | Ubuntu Server 22.04 LTS / CentOS 7.9 |
| 系统盘 | 高性能云硬盘 100GB |
| 数据盘 | 不需要 |

### 4.3 网络配置

| 字段 | 填写 |
|------|------|
| 网络 | examlab-vpc |
| 子网 | examlab-public（10.0.1.0/24） |
| 安全组 | examlab-mgmt-sg |
| 公网 IP | **分配独立公网 IP**（弹性 IP） |

### 4.4 登录方式

| 字段 | 填写 |
|------|------|
| 登录方式 | 密钥对（推荐） |
| 密钥对 | 点击「新建」，名称 `examlab-key`，下载 .pem 文件到本地 |

> 如果选密码登录，设置一个强密码并记下。

### 4.5 确认购买

检查配置摘要：
- 地域：广州
- 机型：S5.MEDIUM8（4核8G）
- 镜像：Ubuntu 22.04
- 系统盘：100GB 高性能云硬盘
- 网络：examlab-vpc / examlab-public
- 公网 IP：分配

点击**立即购买** → **确认支付**。

---

## 第五步：绑定弹性公网 IP

如果购买时已分配公网 IP，此步可跳过。

如果购买时未分配：

1. 控制台搜索「弹性公网 IP」→ **申请**
2. 地域：广州，数量：1
3. 申请后点击**绑定** → 选择管理服务器 CVM

记下分配到的**公网 IP 地址**（例如 `119.xx.xx.xx`）。

---

## 第六步：创建 API 密钥

程序需要通过 API 创建/管理考试 VM。

1. 控制台搜索「访问管理」→ **API 密钥管理**
2. 点击 **新建密钥**
3. 弹出窗口显示 `SecretId` 和 `SecretKey`，**立即复制保存**
4. 填写到 `.env` 文件：

```bash
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
TENCENT_REGION=ap-guangzhou
TENCENT_VPC_ID=vpc-xxxxxxxx
TENCENT_SUBNET_ID_PUBLIC=subnet-xxxxxxxx
TENCENT_SUBNET_ID_PRIVATE=subnet-xxxxxxxx
```

---

## 第七步：SSH 登录管理服务器

```bash
# 使用密钥登录
ssh -i examlab-key.pem ubuntu@119.xx.xx.xx

# 或使用密码登录
ssh root@119.xx.xx.xx
```

登录后先更新系统：

```bash
# Ubuntu
sudo apt update && sudo apt upgrade -y

# CentOS
sudo yum update -y
```

---

## 第八步：安装 Docker

```bash
# 安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sudo bash

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER

# 安装 Docker Compose 插件
sudo apt install -y docker-compose-plugin   # Ubuntu
# sudo yum install -y docker-compose-plugin # CentOS

# 重新登录使权限生效
exit
ssh -i examlab-key.pem ubuntu@119.xx.xx.xx

# 验证安装
docker --version
docker compose version
```

---

## 第九步：部署 ExamLabPlatform

```bash
# 克隆代码
git clone https://github.com/love38beyond/ExamLabPlatform.git /opt/examlab
cd /opt/examlab

# 配置环境变量
cp .env.example .env
nano .env  # 填入腾讯云 API 密钥、VPC ID 等

# 启动全部服务
docker compose up -d --build

# 初始化数据库
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

---

## 第十步：验证

浏览器打开 `http://119.xx.xx.xx/admin/`，用刚才创建的管理员账号登录。

能正常显示 Django Admin 界面即部署成功。

---

## 费用参考

| 资源 | 计费方式 | 月费 |
|------|----------|------|
| CVM S5.MEDIUM8（4核8G） | 包年包月 | ~300 元 |
| 系统盘 100GB 高性能云硬盘 | 包年包月 | ~35 元 |
| 弹性公网 IP | 按量 | ~80 元 |
| NAT 网关 | 按量 + 流量 | ~50 元 |
| **合计** | | **~465 元/月** |

> 以上为广州地域参考价，实际以腾讯云官网为准。
