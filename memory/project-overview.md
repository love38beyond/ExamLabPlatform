---
name: project-overview
description: ExamLabPlatform project purpose, tech stack, and architecture
metadata:
  type: project
---

ExamLabPlatform 是一个上机考试系统 MVP。学员通过浏览器登录，查看分配给自己的虚拟机（1 台 Windows 管理机 + N 台 Linux 目标服务器），通过 Apache Guacamole 在浏览器中 RDP 连接到 Windows 机器进行操作。

**Why:** 面向 Linux 系统运维考试（RHCE 类），学员通过 bat 脚本在 Windows 管理机上部署应用到 Linux 目标服务器。

**How to apply:** 所有开发围绕 Django 后端 + Docker 部署展开，腾讯云 CVM 通过 SDK 管理。

**Tech Stack:** Python 3.11 + Django 4.2 + PostgreSQL 15 + Apache Guacamole 1.5 + Docker Compose + Tencent Cloud SDK

**Architecture:** Nginx → Django + Guacamole (Tomcat + guacd) → PostgreSQL，全部在单台管理 CVM 上 Docker Compose 编排。考试 VM 在私有子网，通过 Guacamole RDP 代理访问。

**Scale:** 单场 20-50 学员，每学员 4 台 VM（1 Win + 3 Linux 默认，数量可配置）

**Related:** [[architecture-decisions]] [[tencent-cloud-infra]] [[deployment-workflow]]
