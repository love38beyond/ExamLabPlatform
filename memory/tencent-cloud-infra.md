---
name: tencent-cloud-infra
description: Tencent Cloud infrastructure layout and setup
metadata:
  type: reference
---

腾讯云基础设施布局：

**VPC:** examlab-vpc, CIDR 10.0.0.0/16
- 公有子网 10.0.1.0/24 — 管理服务器（唯一有公网 IP 的机器）
- 私有子网 10.0.2.0/23 — 考试 VM（~512 个 IP）

**管理服务器:** 1 台 CVM，公有子网，建议 4核8G（最少 2核4G），弹性公网 IP。跑 Docker Compose 全套服务。

**NAT 网关:** 私有子网路由到 NAT 网关，使考试 VM 能访问外网（yum/apt）。

**安全组:**
- sg-mgmt：管理服务器（SSH 22 + HTTP 80 + HTTPS 443）
- sg-{student}：每学员一个，同组内全通，组间默认拒绝
- 安全组规则：组内 Ingress/Egress 全放行

**API 密钥:** 通过 CAM 创建 SecretId/SecretKey，填入 .env 文件。

**考试 VM:** 按量计费，无公网 IP，通过自定义镜像创建。

**Why:** 管理服务器与考试 VM 同 VPC，利用内网直连 RDP/SSH，不需要公网 IP——设备安全且便宜。

**How to apply:** 详见 docs/tencent-cloud-setup.md 分步指南。新增考试地域时复用此 VPC 结构。

**Related:** [[project-overview]] [[architecture-decisions]] [[deployment-workflow]]
