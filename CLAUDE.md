# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

ExamLabPlatform is a **production-ready MVP** — an online exam/lab platform for Linux system administration exams. Students log in via browser, see their assigned VMs (1 Windows management machine + N Linux target servers), and connect to the Windows machine via browser-based RDP through Apache Guacamole. All deployed on Tencent Cloud.

## Tech Stack

- **Backend:** Python 3.11 + Django 4.2
- **Database:** PostgreSQL 15
- **Remote Desktop:** Apache Guacamole 1.5.5 (Tomcat + guacd)
- **Reverse Proxy:** Nginx 1.25
- **Deployment:** Docker Compose (5 services: nginx, backend, db, guacamole, guacd)
- **Cloud:** Tencent Cloud CVM + VPC + SDK
- **Static Files:** Whitenoise (no separate CDN needed)

## Repository State

- Git repository on `main` branch, 22+ commits
- Remote: `https://github.com/love38beyond/ExamLabPlatform.git`
- Docker Compose for deployment
- Code pushed and up-to-date with `origin/main`

## Key Commands

```bash
# Start all services
docker compose up -d --build

# Database migrations
docker compose exec backend python manage.py migrate

# Create admin user
docker compose exec backend python manage.py createsuperuser

# Sync VM IPs and status from Tencent Cloud
docker compose exec backend python manage.py sync_vm_status

# View logs
docker compose logs -f backend

# Backup database
docker compose exec db pg_dump -U examlab examlab > backup.sql
```

## Architecture

```
Browser (HTTPS) → Nginx (:443) → Django (:8000) + Guacamole Tomcat (:8080)
                                                ↓
                                        guacd (:4822) → RDP → Windows VM (private IP)
                                                                      ↓ SSH
                                                                  Linux VMs (private IP)
```

### Django Apps
- `accounts` — Student model (extends AbstractUser), CSV import, login/logout
- `exams` — Exam/VmGroup/VmInstance models, Tencent Cloud SDK, Guacamole API, admin widgets

### Key Source Files

| File | Purpose |
|------|---------|
| `backend/exams/services/tencent.py` | Tencent Cloud CVM API: security groups, instance lifecycle, batch creation with UserData |
| `backend/exams/services/guacamole.py` | Guacamole connection management: direct PostgreSQL SQL + REST API |
| `backend/exams/models.py` | Core models: Exam (JSON vm_spec), VmGroup, VmInstance |
| `backend/exams/admin.py` | Django admin with custom widgets, batch student assignment, VM status overview |
| `backend/exams/forms.py` | Custom VmSpecWidget for structured JSON editing |
| `backend/exams/views.py` | DashboardView (student VM list + timer) and ConnectView (redirect to Guacamole) |
| `backend/examlab/settings.py` | Project config with Whitenoise, Tencent Cloud + Guacamole settings |
| `init/guacamole-init.sql` | Guacamole PostgreSQL schema |

### Per-Student VM Topology
- 1 Windows management machine (optional) + N Linux target servers (dynamic count)
- All VMs in same security group → intra-group communication, inter-group isolation
- Each Linux server has individually configurable CPU/RAM/disk
- Linux accounts auto-created via UserData cloud-init scripts

## Documentation

| File | Content |
|------|---------|
| `docs/user-manual.md` | Full user manual (admin + student usage) |
| `docs/deploy-tencent-cloud.md` | Complete deployment guide with FAQ |
| `docs/tencent-cloud-setup.md` | Step-by-step Tencent Cloud infrastructure creation |
| `docs/image-preparation-guide.md` | Windows + Linux VM image creation |
| `docs/deploy-commands.md` | Command reference for operations |
| `docs/infrastructure-setup.md` | Chinese summary of one-time setup |
| `docs/windows-image-setup.ps1` | PowerShell automation for Windows image |
| `docs/unattend.xml` | Windows Sysprep answer file |
| `docs/superpowers/specs/` | System design document |
| `docs/superpowers/plans/` | Implementation plan (13 tasks) |
