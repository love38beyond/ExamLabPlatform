# ExamLabPlatform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MVP exam lab platform where admins create exams with per-student VMs (1 Windows + N Linux), students connect via browser-based RDP through Guacamole, all deployed on Tencent Cloud.

**Architecture:** Django monolith with two apps — `accounts` (auth, CSV import), `exams` (exam/VM models, Tencent Cloud SDK, Guacamole API). Docker Compose orchestrates Nginx + Django + Guacamole (Tomcat + guacd) + PostgreSQL on a single management CVM.

**Tech Stack:** Python 3.11 + Django 4.2 + PostgreSQL 15 + Apache Guacamole 1.5 + Docker Compose + Tencent Cloud Python SDK

---

## File Map

```
examlab/
├── docker-compose.yml
├── .env.example
├── nginx/
│   └── nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── examlab/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── templates/accounts/login.html
│   ├── exams/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tencent.py
│   │   │   └── guacamole.py
│   │   └── templates/exams/
│   │       ├── dashboard.html
│   │       └── admin/
│   │           └── exam_create.html
│   └── templates/
│       └── base.html
├── guacamole/
│   └── guacamole.properties
└── init/
    └── init-db.sql
```

---

## Phase 1: Project Scaffold

### Task 1: Initialize Django project and Docker skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/examlab/__init__.py` (empty)
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `nginx/nginx.conf`
- Create: `guacamole/guacamole.properties`
- Create: `init/init-db.sql`

- [ ] **Step 1: Create directory structure**

Run:
```bash
mkdir -p backend/examlab backend/accounts backend/exams/services backend/exams/templates/exams/admin backend/templates nginx guacamole init
```

- [ ] **Step 2: Write requirements.txt**

```python
# backend/requirements.txt
django>=4.2,<5.0
psycopg2-binary>=2.9
django-environ>=0.11
tencentcloud-sdk-python>=3.0
requests>=2.31
```

- [ ] **Step 3: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "examlab.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

- [ ] **Step 4: Write .env.example**

```bash
# .env.example
DEBUG=True
SECRET_KEY=change-me-in-production
DATABASE_URL=postgres://examlab:examlab@db:5432/examlab
ALLOWED_HOSTS=localhost,127.0.0.1

# Tencent Cloud API credentials
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key
TENCENT_REGION=ap-guangzhou

# Tencent Cloud infrastructure IDs (created manually once)
TENCENT_VPC_ID=vpc-xxxxxxxx
TENCENT_SUBNET_ID_PUBLIC=subnet-xxxxxxxx
TENCENT_SUBNET_ID_PRIVATE=subnet-xxxxxxxx
TENCENT_SECURITY_GROUP_MGMT=sg-xxxxxxxx

# Guacamole
GUACAMOLE_URL=http://guacamole:8080/guacamole
GUACAMOLE_USER=guacadmin
GUACAMOLE_PASSWORD=guacadmin
```

- [ ] **Step 5: Write docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.8"

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/app/static:ro
    depends_on:
      - backend
      - guacamole
    restart: unless-stopped

  backend:
    build: ./backend
    volumes:
      - ./backend:/app
      - static_volume:/app/static
    env_file:
      - .env
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    environment:
      POSTGRES_DB: examlab
      POSTGRES_USER: examlab
      POSTGRES_PASSWORD: examlab
    restart: unless-stopped

  guacamole:
    image: guacamole/guacamole:1.5.5
    environment:
      GUACD_HOSTNAME: guacd
      POSTGRESQL_HOSTNAME: db
      POSTGRESQL_DATABASE: examlab
      POSTGRESQL_USER: examlab
      POSTGRESQL_PASSWORD: examlab
    depends_on:
      - guacd
      - db
    restart: unless-stopped

  guacd:
    image: guacamole/guacd:1.5.5
    restart: unless-stopped

volumes:
  pgdata:
  static_volume:
```

- [ ] **Step 6: Write nginx.conf**

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    upstream django {
        server backend:8000;
    }

    upstream guacamole {
        server guacamole:8080;
    }

    server {
        listen 80;
        server_name _;

        # Django static files
        location /static/ {
            alias /app/static/;
        }

        # Django application
        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Guacamole WebSocket tunnel
        location /guacamole/ {
            proxy_pass http://guacamole/guacamole/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cookie_path /guacamole/ /guacamole/;
            access_log off;
        }
    }
}
```

- [ ] **Step 7: Write guacamole.properties**

```properties
# guacamole/guacamole.properties
# Guacamole will use the GUACD_HOSTNAME env var set in docker-compose
# This file is a placeholder for custom settings
```

- [ ] **Step 8: Write init-db.sql**

```sql
-- init/init-db.sql
-- Guacamole schema is auto-created by guacamole container on first boot.
-- This file is for any additional DB initialization if needed.
```

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: add project scaffold with Docker Compose"
```

---

### Task 2: Initialize Django project

**Files:**
- Create: `backend/manage.py`
- Create: `backend/examlab/settings.py`
- Create: `backend/examlab/urls.py`
- Create: `backend/examlab/wsgi.py`
- Create: `backend/examlab/__init__.py`

- [ ] **Step 1: Write manage.py**

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examlab.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write settings.py**

```python
# backend/examlab/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "exams",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "examlab.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "examlab.wsgi.application"

# Database configured via DATABASE_URL env var
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "examlab"),
        "USER": os.environ.get("DB_USER", "examlab"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "examlab"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.Student"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/exams/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Tencent Cloud
TENCENT_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
TENCENT_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
TENCENT_REGION = os.environ.get("TENCENT_REGION", "ap-guangzhou")
TENCENT_VPC_ID = os.environ.get("TENCENT_VPC_ID", "")
TENCENT_SUBNET_ID_PUBLIC = os.environ.get("TENCENT_SUBNET_ID_PUBLIC", "")
TENCENT_SUBNET_ID_PRIVATE = os.environ.get("TENCENT_SUBNET_ID_PRIVATE", "")
TENCENT_SECURITY_GROUP_MGMT = os.environ.get("TENCENT_SECURITY_GROUP_MGMT", "")

# Guacamole
GUACAMOLE_URL = os.environ.get("GUACAMOLE_URL", "http://guacamole:8080/guacamole")
GUACAMOLE_USER = os.environ.get("GUACAMOLE_USER", "guacadmin")
GUACAMOLE_PASSWORD = os.environ.get("GUACAMOLE_PASSWORD", "guacadmin")
```

- [ ] **Step 3: Write urls.py**

```python
# backend/examlab/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("exams/", include("exams.urls")),
]
```

- [ ] **Step 4: Write wsgi.py**

```python
# backend/examlab/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examlab.settings")
application = get_wsgi_application()
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: initialize Django project with settings"
```

---

## Phase 2: User Accounts

### Task 3: Student model and admin

**Files:**
- Create: `backend/accounts/__init__.py`
- Create: `backend/accounts/models.py`
- Create: `backend/accounts/admin.py`
- Create: `backend/accounts/urls.py` (placeholder)

- [ ] **Step 1: Write accounts/__init__.py** — leave empty

- [ ] **Step 2: Write models.py**

```python
# backend/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class Student(AbstractUser):
    """Custom user model for exam students."""

    name = models.CharField("姓名", max_length=100, blank=True)

    class Meta:
        verbose_name = "学员"
        verbose_name_plural = "学员"
        ordering = ["username"]

    def __str__(self):
        return f"{self.name or self.username} ({self.username})"
```

- [ ] **Step 3: Write admin.py**

```python
# backend/accounts/admin.py
import csv
import io

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path

from .models import Student


@admin.register(Student)
class StudentAdmin(UserAdmin):
    list_display = ["username", "name", "is_active", "date_joined"]
    list_filter = ["is_active"]
    search_fields = ["username", "name"]
    ordering = ["username"]
    actions = ["enable_students", "disable_students"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("个人信息", {"fields": ("name",)}),
        ("权限", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("日期", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "name", "password1", "password2"),
        }),
    )

    change_list_template = "admin/accounts/student_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-csv/", self.admin_site.admin_view(self.import_csv_view), name="student-import-csv"),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "请选择一个 CSV 文件", level=messages.ERROR)
                return redirect("..")

            decoded = csv_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            created = 0
            for row in reader:
                username = row.get("username", "").strip()
                name = row.get("name", "").strip()
                password = row.get("password", username + "@123")
                if username and not Student.objects.filter(username=username).exists():
                    Student.objects.create_user(
                        username=username,
                        name=name,
                        password=password,
                    )
                    created += 1

            self.message_user(request, f"成功导入 {created} 名学员", level=messages.SUCCESS)
            return redirect("..")

        return render(request, "admin/accounts/import_csv.html")

    @admin.action(description="启用所选学员")
    def enable_students(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="禁用所选学员")
    def disable_students(self, request, queryset):
        queryset.update(is_active=False)
```

- [ ] **Step 4: Write urls.py**

```python
# backend/accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
]
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add Student model with CSV import admin action"
```

---

### Task 4: Login/logout views and templates

**Files:**
- Create: `backend/accounts/views.py`
- Create: `backend/accounts/templates/accounts/login.html`
- Create: `backend/templates/base.html`
- Create: `backend/templates/admin/accounts/import_csv.html`
- Create: `backend/templates/admin/accounts/student_changelist.html`

- [ ] **Step 1: Write views.py**

```python
# backend/accounts/views.py
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.urls import reverse_lazy


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy("accounts:login")
```

- [ ] **Step 2: Write base.html**

```html
<!-- backend/templates/base.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}ExamLabPlatform{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; min-height: 100vh; }
    </style>
    {% block extra_head %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Write login.html**

```html
<!-- backend/accounts/templates/accounts/login.html -->
{% extends "base.html" %}
{% block title %}学员登录 - ExamLabPlatform{% endblock %}
{% block content %}
<div style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
    <div style="background:#fff;padding:40px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.1);width:100%;max-width:400px;">
        <h1 style="text-align:center;margin-bottom:24px;color:#1a1a2e;">ExamLabPlatform</h1>
        <h2 style="text-align:center;margin-bottom:24px;font-size:18px;color:#666;">学员登录</h2>
        {% if form.errors %}
        <div style="background:#fff2f0;border:1px solid #ffccc7;padding:12px;border-radius:4px;margin-bottom:16px;color:#cf1322;">
            用户名或密码错误，请重试。
        </div>
        {% endif %}
        <form method="post">
            {% csrf_token %}
            <div style="margin-bottom:16px;">
                <label style="display:block;margin-bottom:4px;font-weight:500;">用户名</label>
                <input type="text" name="username" required autofocus
                    style="width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;">
            </div>
            <div style="margin-bottom:24px;">
                <label style="display:block;margin-bottom:4px;font-weight:500;">密码</label>
                <input type="password" name="password" required
                    style="width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;">
            </div>
            <button type="submit" style="width:100%;padding:12px;background:#6C63FF;color:#fff;border:none;border-radius:4px;font-size:16px;cursor:pointer;">
                登录
            </button>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Write import_csv.html (admin template)**

```html
<!-- backend/templates/admin/accounts/import_csv.html -->
{% extends "admin/base_site.html" %}
{% block content %}
<h1>批量导入学员</h1>
<p style="margin-bottom:16px;">上传 CSV 文件，格式：<code>username,name,password</code>（密码列可选，默认为用户名+@123）</p>
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="file" name="csv_file" accept=".csv" required>
    <button type="submit" class="button" style="margin-top:12px;">上传并导入</button>
</form>
<div style="margin-top:24px;">
    <a href="../">← 返回学员列表</a>
</div>
{% endblock %}
```

- [ ] **Step 5: Write student_changelist.html**

```html
<!-- backend/templates/admin/accounts/student_changelist.html -->
{% extends "admin/change_list.html" %}
{% block object-tools-items %}
<li><a href="import-csv/" class="addlink">导入 CSV</a></li>
{{ block.super }}
{% endblock %}
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add login/logout views and templates"
```
---

## Phase 3: Exam & VM Models

### Task 5: Exam, VmGroup, VmInstance models

**Files:**
- Create: `backend/exams/__init__.py`
- Create: `backend/exams/models.py`
- Create: `backend/exams/admin.py`
- Create: `backend/exams/urls.py`

- [ ] **Step 1: Create empty `backend/exams/__init__.py`**

- [ ] **Step 2: Write models.py**

```python
# backend/exams/models.py
from django.conf import settings
from django.db import models


class Exam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"

    name = models.CharField(max_length=200)
    exam_time = models.DateTimeField()
    duration_minutes = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    vm_spec = models.JSONField(default=dict)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="VmGroup"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Exam"
        verbose_name_plural = "Exams"
        ordering = ["-exam_time"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class VmGroup(models.Model):
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="vm_groups"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vm_groups"
    )
    security_group_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "VM Group"
        verbose_name_plural = "VM Groups"
        unique_together = ["exam", "student"]

    def __str__(self):
        return f"{self.student.username} - {self.exam.name}"


class VmInstance(models.Model):
    class VmType(models.TextChoices):
        WINDOWS = "windows", "Windows"
        LINUX = "linux", "Linux"

    class Status(models.TextChoices):
        CREATING = "creating", "Creating"
        RUNNING = "running", "Running"
        STOPPED = "stopped", "Stopped"
        TERMINATED = "terminated", "Terminated"

    group = models.ForeignKey(
        VmGroup, on_delete=models.CASCADE, related_name="instances"
    )
    vm_type = models.CharField(max_length=20, choices=VmType.choices)
    role_label = models.CharField(max_length=100, blank=True)
    cpu = models.IntegerField(default=2)
    ram = models.IntegerField(default=4)
    disk = models.IntegerField(default=50)
    image_id = models.CharField(max_length=100, blank=True)
    cvm_instance_id = models.CharField(max_length=100, blank=True)
    private_ip = models.CharField(max_length=50, blank=True)
    admin_username = models.CharField(max_length=100, default="Administrator")
    admin_password = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CREATING
    )
    guacamole_connection_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "VM Instance"
        verbose_name_plural = "VM Instances"

    def __str__(self):
        return f"{self.get_vm_type_display()} - {self.group}"
```

- [ ] **Step 3: Write admin.py**

```python
# backend/exams/admin.py
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from .models import Exam, VmGroup, VmInstance


class VmInstanceInline(admin.TabularInline):
    model = VmInstance
    fields = ["vm_type", "role_label", "cpu", "ram", "disk", "status", "private_ip"]
    readonly_fields = ["status", "private_ip"]
    extra = 0


class VmGroupInline(admin.TabularInline):
    model = VmGroup
    fields = ["student"]
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["name", "exam_time", "duration_minutes", "status"]
    list_filter = ["status"]
    inlines = [VmGroupInline]
    actions = ["set_ready", "set_running", "set_finished"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:exam_id>/create-vms/",
                self.admin_site.admin_view(self.create_vms_view),
                name="exam-create-vms",
            ),
        ]
        return custom_urls + urls

    def create_vms_view(self, request, exam_id):
        from .services.tencent import create_vms_for_exam
        exam = Exam.objects.get(id=exam_id)
        result = create_vms_for_exam(exam)
        if result["error"] == 0:
            messages.success(request, f"Created VMs for {result['success']} students")
        else:
            messages.warning(
                request,
                f"Partial: {result['success']} OK, {result['error']} failed",
            )
        return redirect("admin:exams_exam_changelist")

    @admin.action(description="Mark as Ready")
    def set_ready(self, request, queryset):
        queryset.update(status=Exam.Status.READY)

    @admin.action(description="Mark as Running")
    def set_running(self, request, queryset):
        queryset.update(status=Exam.Status.RUNNING)

    @admin.action(description="Mark as Finished")
    def set_finished(self, request, queryset):
        queryset.update(status=Exam.Status.FINISHED)


@admin.register(VmGroup)
class VmGroupAdmin(admin.ModelAdmin):
    list_display = ["__str__", "exam", "student"]
    list_filter = ["exam"]
    inlines = [VmInstanceInline]


@admin.register(VmInstance)
class VmInstanceAdmin(admin.ModelAdmin):
    list_display = ["__str__", "private_ip", "status", "cvm_instance_id"]
    list_filter = ["vm_type", "status"]
```

- [ ] **Step 4: Write urls.py placeholder**

```python
# backend/exams/urls.py
from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("connect/<int:vm_id>/", views.ConnectView.as_view(), name="connect"),
]
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add Exam VmGroup VmInstance models and admin"
```
---

### Task 6: Initial migrations

- [ ] **Step 1: Build and run migrations**

```bash
docker compose build backend
docker compose run --rm backend python manage.py makemigrations accounts exams
docker compose run --rm backend python manage.py migrate
```

- [ ] **Step 2: Create superuser**

```bash
docker compose run --rm backend python manage.py createsuperuser
```
Enter: admin / admin@example.com / admin123

- [ ] **Step 3: Commit migration files**

```bash
git add -A && git commit -m "feat: add initial migrations"
```

---

## Phase 4: Tencent Cloud Integration

### Task 7: Tencent Cloud CVM service wrapper

**Files:**
- Create: `backend/exams/services/__init__.py` (empty)
- Create: `backend/exams/services/tencent.py`

- [ ] **Step 1: Create empty services/__init__.py**

- [ ] **Step 2: Write tencent.py**

```python
# backend/exams/services/tencent.py
import logging
import secrets
import string

from django.conf import settings
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models

from ..models import VmInstance

logger = logging.getLogger(__name__)


def _get_cvm_client():
    cred = credential.Credential(
        settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY
    )
    return cvm_client.CvmClient(cred, settings.TENCENT_REGION)


def _get_vpc_client():
    cred = credential.Credential(
        settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY
    )
    return vpc_client.VpcClient(cred, settings.TENCENT_REGION)


def create_security_group(name: str) -> str:
    """Create a security group for one student. Returns security group ID."""
    client = _get_vpc_client()
    req = vpc_models.CreateSecurityGroupRequest()
    req.GroupName = name
    req.GroupDescription = f"Exam security group - {name}"
    resp = client.CreateSecurityGroup(req)
    sg_id = resp.SecurityGroup.Id

    # Allow all traffic within the same security group
    policy_set = vpc_models.SecurityGroupPolicySet(
        Ingress=[
            vpc_models.SecurityGroupPolicy(
                Protocol="ALL",
                Port="ALL",
                SecurityGroupId=sg_id,
                Action="ACCEPT",
            )
        ],
        Egress=[
            vpc_models.SecurityGroupPolicy(
                Protocol="ALL",
                Port="ALL",
                SecurityGroupId=sg_id,
                Action="ACCEPT",
            )
        ],
    )
    policies_req = vpc_models.CreateSecurityGroupPoliciesRequest()
    policies_req.SecurityGroupId = sg_id
    policies_req.SecurityGroupPolicySet = policy_set
    client.CreateSecurityGroupPolicies(policies_req)

    logger.info("Created security group %s: %s", name, sg_id)
    return sg_id


def run_instances(
    image_id, instance_type, instance_count, vpc_id, subnet_id,
    security_group_ids, instance_name_prefix, password="", disk_size=50,
):
    """Create CVM instances. Returns list of instance IDs."""
    client = _get_cvm_client()
    req = cvm_models.RunInstancesRequest()
    req.ImageId = image_id
    req.InstanceType = instance_type
    req.InstanceCount = instance_count
    req.InstanceChargeType = "POSTPAID_BY_HOUR"
    req.VirtualPrivateCloud = cvm_models.VirtualPrivateCloud(
        VpcId=vpc_id,
        SubnetId=subnet_id,
    )
    req.SecurityGroupIds = security_group_ids
    req.InstanceName = instance_name_prefix
    req.SystemDisk = cvm_models.SystemDisk(
        DiskType="CLOUD_PREMIUM",
        DiskSize=disk_size,
    )
    if password:
        req.LoginSettings = cvm_models.LoginSettings(Password=password)

    try:
        resp = client.RunInstances(req)
        instance_ids = resp.InstanceIdSet
        logger.info("Launched instances: %s", instance_ids)
        return instance_ids
    except TencentCloudSDKException as e:
        logger.error("Failed to create instances: %s", e)
        raise


def describe_instances(instance_ids):
    """Get instance details including private IP."""
    client = _get_cvm_client()
    req = cvm_models.DescribeInstancesRequest()
    req.InstanceIds = instance_ids
    resp = client.DescribeInstances(req)
    results = []
    for item in resp.InstanceSet:
        results.append({
            "instance_id": item.InstanceId,
            "private_ip": (
                item.PrivateIpAddresses[0]
                if item.PrivateIpAddresses else ""
            ),
            "state": item.InstanceState,
        })
    return results


def terminate_instances(instance_ids):
    """Destroy CVM instances."""
    client = _get_cvm_client()
    req = cvm_models.TerminateInstancesRequest()
    req.InstanceIds = instance_ids
    client.TerminateInstances(req)


def get_instance_type(cpu, ram):
    """Map CPU/RAM to Tencent Cloud instance type."""
    mapping = {
        (1, 1): "S5.SMALL1",
        (1, 2): "S5.SMALL2",
        (2, 2): "S5.MEDIUM4",
        (2, 4): "S5.MEDIUM2",
        (4, 8): "S5.LARGE4",
        (4, 16): "S5.LARGE8",
    }
    return mapping.get((cpu, ram), "S5.MEDIUM2")


def generate_password(length=12):
    """Generate a random Windows admin password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add Tencent Cloud CVM service wrapper"
```

---

### Task 8: Batch VM creation orchestrator

**Files:**
- Modify: `backend/exams/services/tencent.py` (add create_vms_for_exam)

- [ ] **Step 1: Add create_vms_for_exam to tencent.py**

Append to the end of `backend/exams/services/tencent.py`:

```python
def create_vms_for_exam(exam) -> dict:
    """Create all VMs for an exam. Returns {success: N, error: N}."""
    from ..models import VmGroup, VmInstance

    vm_spec = exam.vm_spec
    windows_spec = vm_spec.get("windows", {"cpu": 2, "ram": 4, "disk": 50})
    linux_servers = vm_spec.get("linux_servers", [])

    groups = VmGroup.objects.filter(exam=exam).select_related("student")
    success_count = 0
    error_count = 0

    for group in groups:
        try:
            # Create security group for this student
            sg_name = f"exam-{exam.id}-student-{group.student_id}"
            sg_id = create_security_group(sg_name)
            group.security_group_id = sg_id
            group.save(update_fields=["security_group_id"])

            # Create Windows VM
            win_type = get_instance_type(windows_spec["cpu"], windows_spec["ram"])
            password = generate_password()
            win_ids = run_instances(
                image_id=windows_spec.get("image_id", ""),
                instance_type=win_type,
                instance_count=1,
                vpc_id=settings.TENCENT_VPC_ID,
                subnet_id=settings.TENCENT_SUBNET_ID_PRIVATE,
                security_group_ids=[sg_id],
                instance_name_prefix=f"exam-{exam.id}-win-{group.student.username}",
                password=password,
                disk_size=windows_spec.get("disk", 50),
            )

            if win_ids:
                VmInstance.objects.create(
                    group=group,
                    vm_type=VmInstance.VmType.WINDOWS,
                    role_label="Windows",
                    cpu=windows_spec["cpu"],
                    ram=windows_spec["ram"],
                    disk=windows_spec["disk"],
                    image_id=windows_spec.get("image_id", ""),
                    cvm_instance_id=win_ids[0],
                    admin_password=password,
                    status=VmInstance.Status.CREATING,
                )

            # Create Linux VMs
            for i, linux_spec in enumerate(linux_servers):
                linux_type = get_instance_type(
                    linux_spec["cpu"], linux_spec["ram"]
                )
                linux_ids = run_instances(
                    image_id=linux_spec.get("image_id", ""),
                    instance_type=linux_type,
                    instance_count=1,
                    vpc_id=settings.TENCENT_VPC_ID,
                    subnet_id=settings.TENCENT_SUBNET_ID_PRIVATE,
                    security_group_ids=[sg_id],
                    instance_name_prefix=(
                        f"exam-{exam.id}-linux{i+1}-{group.student.username}"
                    ),
                    disk_size=linux_spec.get("disk", 40),
                )

                if linux_ids:
                    VmInstance.objects.create(
                        group=group,
                        vm_type=VmInstance.VmType.LINUX,
                        role_label=linux_spec.get("role", f"Linux-{i+1}"),
                        cpu=linux_spec["cpu"],
                        ram=linux_spec["ram"],
                        disk=linux_spec["disk"],
                        image_id=linux_spec.get("image_id", ""),
                        cvm_instance_id=linux_ids[0],
                        status=VmInstance.Status.CREATING,
                    )

            success_count += 1
        except Exception:
            logger.exception("Failed to create VMs for group %s", group.id)
            error_count += 1

    if success_count > 0:
        exam.status = exam.Status.RUNNING
        exam.save(update_fields=["status"])

    return {"success": success_count, "error": error_count}
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add batch VM creation orchestrator"
```
---

## Phase 5: Guacamole Integration

### Task 9: Guacamole API service

**Files:**
- Create: `backend/exams/services/guacamole.py`

- [ ] **Step 1: Write guacamole.py**

```python
# backend/exams/services/guacamole.py
"""Apache Guacamole REST API client for managing RDP connections."""
import logging
import urllib.parse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GUAC_BASE = settings.GUACAMOLE_URL.rstrip("/")
GUAC_USER = settings.GUACAMOLE_USER
GUAC_PASS = settings.GUACAMOLE_PASSWORD


def _auth_token() -> str:
    """Get Guacamole auth token via POST /api/tokens."""
    url = f"{GUAC_BASE}/api/tokens"
    resp = requests.post(
        url,
        data={"username": GUAC_USER, "password": GUAC_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["authToken"]
    return token


def _headers():
    return {"Guacamole-Token": _auth_token()}


def create_rdp_connection(
    name, hostname, port, username, password, **kwargs
) -> str:
    """Create an RDP connection in Guacamole. Returns connection ID."""
    token = _auth_token()
    data_source = "postgresql"

    # Build connection parameters
    params = {
        "name": name,
        "protocol": "rdp",
        "parameters": {
            "hostname": hostname,
            "port": str(port),
            "username": username,
            "password": password,
            "ignore-cert": "true",
            "security": "any",
            "resize-method": "display-update",
            "enable-wallpaper": "true",
            "enable-font-smoothing": "true",
            "enable-drive": "false",
            "create-drive-path": "false",
            "enable-printing": "false",
        },
    }

    # Merge extra params
    params["parameters"].update(kwargs)

    url = f"{GUAC_BASE}/api/session/data/{data_source}/connections"
    params_qs = urllib.parse.quote(token)

    resp = requests.post(
        f"{url}?token={params_qs}",
        json=params,
        timeout=10,
    )
    resp.raise_for_status()
    connection_id = resp.json()["identifier"]
    logger.info("Created Guacamole connection %s for %s", connection_id, name)
    return str(connection_id)


def get_connection_token(connection_id: str) -> str:
    """Get a one-time connection token for a Guacamole connection."""
    token = _auth_token()
    data_source = "postgresql"

    url = (
        f"{GUAC_BASE}/api/session/data/{data_source}/connections/"
        f"{connection_id}/parameters"
    )
    params_qs = urllib.parse.quote(token)

    resp = requests.get(f"{url}?token={params_qs}", timeout=10)
    resp.raise_for_status()

    # Generate connection token
    connect_url = (
        f"{GUAC_BASE}/api/session/tunnels/{connection_id}/connection/rdp"
    )
    connect_resp = requests.post(
        f"{connect_url}?token={params_qs}",
        json={},
        timeout=10,
    )
    connect_resp.raise_for_status()
    return token


def delete_connection(connection_id: str):
    """Delete a Guacamole connection."""
    token = _auth_token()
    data_source = "postgresql"
    url = (
        f"{GUAC_BASE}/api/session/data/{data_source}/connections/"
        f"{connection_id}"
    )
    params_qs = urllib.parse.quote(token)
    resp = requests.delete(f"{url}?token={params_qs}", timeout=10)
    resp.raise_for_status()


def get_connection_url(vm_instance) -> str:
    """Get the direct Guacamole iframe URL for a VM instance.

    Creates a Guacamole connection if one doesn't exist yet.
    Returns a URL that can be embedded in an iframe.
    """
    if not vm_instance.guacamole_connection_id:
        conn_id = create_rdp_connection(
            name=f"{vm_instance.group.student.username}-{vm_instance.role_label}",
            hostname=vm_instance.private_ip,
            port=vm_instance.rdp_port,
            username=vm_instance.admin_username,
            password=vm_instance.admin_password,
        )
        vm_instance.guacamole_connection_id = conn_id
        vm_instance.save(update_fields=["guacamole_connection_id"])

    token = get_connection_token(vm_instance.guacamole_connection_id)
    return (
        f"/guacamole/#/client/{vm_instance.guacamole_connection_id}"
        f"?token={token}"
    )
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add Guacamole API service for RDP connections"
```

---

### Task 10: Sync VM IPs after creation (status check)

**Files:**
- Create: `backend/exams/management/commands/sync_vm_status.py`

- [ ] **Step 1: Write management command**

```python
# backend/exams/management/commands/sync_vm_status.py
"""Django management command to sync VM IPs and status from Tencent Cloud."""
from django.core.management.base import BaseCommand
from exams.models import VmInstance
from exams.services.tencent import describe_instances


class Command(BaseCommand):
    help = "Sync VM private IPs and status from Tencent Cloud"

    def handle(self, *args, **options):
        instances = VmInstance.objects.exclude(
            cvm_instance_id=""
        ).exclude(status=VmInstance.Status.TERMINATED)

        # Batch in groups of 100 (API limit)
        all_ids = list(instances.values_list("cvm_instance_id", flat=True))
        for i in range(0, len(all_ids), 100):
            batch = all_ids[i : i + 100]
            try:
                results = describe_instances(batch)
                result_map = {r["instance_id"]: r for r in results}
                for inst in instances.filter(cvm_instance_id__in=batch):
                    info = result_map.get(inst.cvm_instance_id)
                    if info:
                        inst.private_ip = info["private_ip"]
                        if info["state"] == "RUNNING":
                            inst.status = VmInstance.Status.RUNNING
                        elif info["state"] == "STOPPED":
                            inst.status = VmInstance.Status.STOPPED
                        inst.save(update_fields=["private_ip", "status"])
                self.stdout.write(
                    f"Synced {len(batch)} instances"
                )
            except Exception as e:
                self.stderr.write(f"Error syncing batch: {e}")
```

Make sure directory exists: `mkdir -p backend/exams/management/commands` and create `__init__.py` files:
- `backend/exams/management/__init__.py` (empty)
- `backend/exams/management/commands/__init__.py` (empty)

- [ ] **Step 2: Commit**

```bash
mkdir -p backend/exams/management/commands
touch backend/exams/management/__init__.py
touch backend/exams/management/commands/__init__.py
git add -A && git commit -m "feat: add sync_vm_status management command"
```
---

## Phase 6: Student Dashboard

### Task 11: Student dashboard view and template

**Files:**
- Modify: `backend/exams/views.py` (add DashboardView and ConnectView)
- Create: `backend/exams/templates/exams/dashboard.html`

- [ ] **Step 1: Write views.py**

```python
# backend/exams/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

from .models import Exam, VmGroup, VmInstance
from .services.guacamole import get_connection_url


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "exams/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = self.request.user

        # Find the active exam for this student
        now = timezone.now()
        vm_group = (
            VmGroup.objects.filter(
                student=student,
                exam__status__in=[Exam.Status.READY, Exam.Status.RUNNING],
            )
            .select_related("exam")
            .first()
        )

        if not vm_group:
            ctx["has_exam"] = False
            return ctx

        exam = vm_group.exam
        instances = vm_group.instances.all()

        # Calculate remaining time
        exam_end = exam.exam_time + timezone.timedelta(
            minutes=exam.duration_minutes
        )
        remaining_seconds = max(
            0, int((exam_end - now).total_seconds())
        )
        remaining_minutes = remaining_seconds // 60

        ctx.update({
            "has_exam": True,
            "exam": exam,
            "instances": instances,
            "remaining_minutes": remaining_minutes,
            "windows_vm": instances.filter(
                vm_type=VmInstance.VmType.WINDOWS
            ).first(),
            "linux_vms": instances.filter(
                vm_type=VmInstance.VmType.LINUX
            ),
            "vm_group": vm_group,
        })
        return ctx


class ConnectView(LoginRequiredMixin, View):
    """Redirect to Guacamole connection for a VM."""

    def get(self, request, vm_id):
        vm = get_object_or_404(
            VmInstance.objects.select_related("group"),
            id=vm_id,
            group__student=request.user,
        )

        # Ensure we have private IP (might need sync)
        if not vm.private_ip:
            from .services.tencent import describe_instances
            results = describe_instances([vm.cvm_instance_id])
            if results:
                vm.private_ip = results[0]["private_ip"]
                if results[0]["state"] == "RUNNING":
                    vm.status = VmInstance.Status.RUNNING
                vm.save(update_fields=["private_ip", "status"])

        # Get Guacamole connection URL
        guac_url = get_connection_url(vm)
        return redirect(guac_url)
```

- [ ] **Step 2: Write dashboard.html**

```html
<!-- backend/exams/templates/exams/dashboard.html -->
{% extends "base.html" %}
{% block title %}考试面板 - ExamLabPlatform{% endblock %}

{% block extra_head %}
<style>
  .dashboard { max-width: 960px; margin: 40px auto; padding: 0 20px; }
  .header { background: #fff; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }
  .header h1 { font-size: 22px; color: #1a1a2e; }
  .timer { font-size: 28px; font-weight: bold; color: #f44336; margin-top: 8px; }
  .timer.warning { color: #FF9800; }
  .cards { display: flex; gap: 16px; flex-wrap: wrap; }
  .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px; flex: 1; min-width: 200px; }
  .card.windows { border-top: 4px solid #0078D4; }
  .card.linux { border-top: 4px solid #f90; }
  .card h3 { font-size: 16px; margin-bottom: 8px; }
  .card .ip { color: #888; font-size: 13px; margin-bottom: 12px; }
  .card .specs { font-size: 12px; color: #aaa; margin-bottom: 16px; }
  .status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
  .status.running { background: #4CAF50; }
  .status.creating { background: #FF9800; }
  .status.stopped { background: #f44336; }
  .btn { display: inline-block; padding: 10px 20px; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 600; text-align: center; }
  .btn-primary { background: #6C63FF; }
  .btn:hover { opacity: 0.9; }
  .user-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .logout { color: #666; text-decoration: none; font-size: 14px; }
  .empty { text-align: center; padding: 60px 20px; color: #888; }
</style>
{% endblock %}

{% block content %}
<div class="dashboard">
  <div class="user-bar">
    <span>Welcome, <strong>{{ user.name|default:user.username }}</strong></span>
    <a href="{% url 'accounts:logout' %}" class="logout">Logout</a>
  </div>

  {% if not has_exam %}
  <div class="empty">
    <div style="font-size: 48px; margin-bottom: 16px;">No active exam</div>
    <p>No active exam or your VMs have not been assigned yet.</p>
    <p style="color: #aaa;">Please contact the administrator if you believe this is an error.</p>
  </div>
  {% else %}
  <div class="header">
    <h1>{{ exam.name }}</h1>
    <div class="timer {% if remaining_minutes < 15 %}warning{% endif %}">
      Remaining: {{ remaining_minutes }} minutes
    </div>
  </div>

  <div class="cards">
    {% if windows_vm %}
    <div class="card windows">
      <h3>Windows Management Machine</h3>
      <div class="ip">
        <span class="status {{ windows_vm.status }}"></span>
        {{ windows_vm.private_ip|default:"Waiting for IP..." }}
        &middot; {{ windows_vm.get_status_display }}
      </div>
      <div class="specs">
        {{ windows_vm.cpu }} CPU &middot; {{ windows_vm.ram }}GB RAM &middot; {{ windows_vm.disk }}GB Disk
      </div>
      {% if windows_vm.status == "running" %}
      <a href="{% url 'exams:connect' windows_vm.id %}" class="btn btn-primary" target="_blank">
        Connect
      </a>
      {% endif %}
    </div>
    {% endif %}

    {% for vm in linux_vms %}
    <div class="card linux">
      <h3>{{ vm.role_label|default:"Linux Server" }}</h3>
      <div class="ip">
        <span class="status {{ vm.status }}"></span>
        {{ vm.private_ip|default:"Waiting for IP..." }}
        &middot; {{ vm.get_status_display }}
      </div>
      <div class="specs">
        {{ vm.cpu }} CPU &middot; {{ vm.ram }}GB RAM &middot; {{ vm.disk }}GB Disk
      </div>
      <div style="font-size: 12px; color: #888;">
        SSH accessible from Windows machine at {{ vm.private_ip|default:"auto-assigned IP" }}
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Update exams/urls.py (already has dashboard and connect paths)**

Verify urls.py contains:
```python
# backend/exams/urls.py
from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("connect/<int:vm_id>/", views.ConnectView.as_view(), name="connect"),
]
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: add student dashboard with VM list and Guacamole connect"
```
---

## Phase 7: Final Assembly & Deployment

### Task 12: Docker verification and full-stack test

- [ ] **Step 1: Start all services**

```bash
docker compose up -d --build
```

Expected: All 5 containers (nginx, backend, db, guacamole, guacd) start without errors.

- [ ] **Step 2: Check each service**

```bash
docker compose ps                          # All should be "Up"
docker compose logs backend | grep -i error # No errors
docker compose logs guacamole | grep -i started
```

- [ ] **Step 3: Run Django checks**

```bash
docker compose exec backend python manage.py check --deploy
docker compose exec backend python manage.py migrate --plan  # No pending migrations
```

- [ ] **Step 4: Test admin login**

Open `http://localhost/admin/` — log in with superuser credentials. Verify:
- Students management page loads
- Exams management page loads
- CSV import link exists on student list page

- [ ] **Step 5: Create a test exam manually via Django Admin**

1. Create 2 test students via admin
2. Create an exam with vm_spec JSON:

```json
{
  "windows": {"cpu": 2, "ram": 4, "disk": 50, "image_id": "img-xxx"},
  "linux_servers": [
    {"role": "Web", "cpu": 2, "ram": 2, "disk": 40, "image_id": "img-yyy"}
  ]
}
```

3. Create VmGroup linking the students to the exam
4. Mark exam as "Ready"

- [ ] **Step 6: Test student login flow**

Open `http://localhost/accounts/login/` — log in as a test student. Verify:
- Dashboard shows (or "no active exam" message)
- No errors in logs

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: final assembly, full-stack verified"
```

---

### Task 13: Tencent Cloud environment setup guide

- [ ] **Step 1: Document one-time infrastructure setup**

Create `docs/infrastructure-setup.md`:

```markdown
# Tencent Cloud Infrastructure Setup

## One-time setup (performed once by admin via Tencent Cloud console)

### 1. Create VPC
- Name: examlab-vpc
- CIDR: 10.0.0.0/16

### 2. Create Subnets
- Public subnet: 10.0.1.0/24 (for management server)
- Private subnet: 10.0.2.0/23 (for exam VMs)

### 3. Create NAT Gateway
- Bind to public subnet
- Associate with private subnet's route table

### 4. Create Management Security Group (sg-mgmt)
- Ingress: SSH 22 from your IP, HTTPS 443 from 0.0.0.0/0
- Egress: All

### 5. Launch Management CVM
- 4核8G, 100GB SSD, CentOS 7.9 or Ubuntu 22.04
- Place in public subnet, bind management security group
- Allocate and bind an EIP

### 6. Create API Access Key
- CAM console -> API Keys -> Create
- Copy SecretId and SecretKey

### 7. Prepare VM Images
- Follow docs/superpowers/specs/... design doc Section 6

### 8. Deploy Application
- Git clone the repository on management server
- Copy .env.example to .env, fill in all values
- Run: docker compose up -d --build
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "docs: add Tencent Cloud infrastructure setup guide"
```

---

## Task Summary

| # | Task | Files |
|---|------|-------|
| 1 | Project scaffold | docker-compose.yml, Dockerfile, nginx.conf, .env.example |
| 2 | Django project init | manage.py, settings.py, urls.py, wsgi.py |
| 3 | Student model + admin | accounts/models.py, admin.py, urls.py |
| 4 | Login views + templates | accounts/views.py, login.html, base.html |
| 5 | Exam/VM models + admin | exams/models.py, admin.py, urls.py |
| 6 | Initial migrations | (auto-generated) |
| 7 | Tencent Cloud SDK wrapper | exams/services/tencent.py |
| 8 | Batch VM creation | exams/services/tencent.py (append) |
| 9 | Guacamole API service | exams/services/guacamole.py |
| 10 | VM status sync command | exams/management/commands/sync_vm_status.py |
| 11 | Student dashboard | exams/views.py, dashboard.html |
| 12 | Docker verification | (manual testing) |
| 13 | Infrastructure guide | docs/infrastructure-setup.md |

**Total: 13 tasks, ~60-90 minutes for an experienced developer.**
