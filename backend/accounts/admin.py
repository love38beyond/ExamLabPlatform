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
        ("Personal Info", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
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
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="student-import-csv",
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "Please select a CSV file", level=messages.ERROR)
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

            self.message_user(
                request, f"Successfully imported {created} students", level=messages.SUCCESS
            )
            return redirect("..")

        return render(request, "admin/accounts/import_csv.html")

    @admin.action(description="Enable selected students")
    def enable_students(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Disable selected students")
    def disable_students(self, request, queryset):
        queryset.update(is_active=False)
