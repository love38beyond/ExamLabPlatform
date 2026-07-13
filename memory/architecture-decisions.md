---
name: architecture-decisions
description: Key architectural decisions and their rationale
metadata:
  type: project
---

核心设计决策：

1. **Guacamole 网关（非 noVNC 直连）**：Guacamole 是 Apache 顶级 HTML5 远程桌面方案，支持 RDP 协议，统一代理所有连接。管理服务器通过内网 RDP 到 Windows VM，考试 VM 无需公网 IP。

2. **安全组隔离（非子网隔离）**：每学员一个腾讯云安全组，组内同组互通，不同组间默认拒绝。30 个安全组管理成本远低于 30 个子网。

3. **Linux SSH-only（非 VNC 桌面）**：学员从 Windows 管理机 SSH 到 Linux 服务器操作，省去每台 Linux 装 VNC。

4. **Windows VM 可选**：支持纯 Linux 考试场景。

5. **每台 Linux 独立规格**：不同角色需要不同资源（DB 服务器需更多内存）。

6. **Django Admin 作为管理后台**：MVP 阶段利用 Django 内置 Admin，自定义 Widget 和 Action 满足需求。

7. **Whitenoise 静态文件**：Docker 容器内直接 serve 静态资源，无需 CDN。

8. **Guacamole 双重管理**：REST API 创建连接 + 直接 PostgreSQL SQL 操作底层数据。

**Why:** 这些决策使得系统部署简单（单台管理 CVM）、成本低（考试 VM 无公网 IP）、安全可控（学员间完全隔离）。

**How to apply:** 新增功能时遵循这些约束——不引入额外网关、不暴露考试 VM 公网、优先利用 Django Admin。

**Related:** [[project-overview]] [[tencent-cloud-infra]]
