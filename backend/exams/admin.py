from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html

from .forms import ExamForm
from .models import Exam, VmGroup, VmInstance


class VmInstanceInline(admin.TabularInline):
    model = VmInstance
    fields = ["vm_type", "role_label", "cpu", "ram", "disk", "status", "private_ip"]
    readonly_fields = ["status", "private_ip"]
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    form = ExamForm
    list_display = ["name", "exam_time", "duration_minutes", "student_count", "status", "vm_actions"]
    list_filter = ["status"]
    actions = ["set_ready", "set_running", "set_finished"]
    change_form_template = "exams/admin/exam_change_form.html"
    save_on_top = True

    fieldsets = (
        ("Exam Info", {
            "fields": ("name", "exam_time", "duration_minutes", "status"),
        }),
        ("VM Specification", {
            "fields": ("vm_spec",),
            "description": "Configure the Windows management machine and Linux target servers.",
        }),
        ("Student Assignment", {
            "fields": ("students_select",),
            "description": "Select active students to assign to this exam.",
        }),
    )

    def student_count(self, obj):
        return obj.vm_groups.count()
    student_count.short_description = "Students"
    student_count.admin_order_field = "vm_groups__count"

    def vm_actions(self, obj):
        if obj.status == Exam.Status.READY:
            url = f"{obj.id}/create-vms/"
            return format_html(
                '<a class="button" href="{}" '
                'onclick="return confirm(\'This will create real cloud VMs. Continue?\')">'
                'Create VMs</a>',
                url,
            )
        if obj.status == Exam.Status.RUNNING:
            return format_html(
                '<span style="color:#4CAF50;font-weight:bold;">VMs Running</span>'
            )
        return "-"
    vm_actions.short_description = "VM Actions"
    vm_actions.allow_tags = True

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

    def save_model(self, request, obj, form, change):
        """Save exam and sync VmGroup records for student assignment."""
        super().save_model(request, obj, form, change)

        selected_students = form.cleaned_data.get("students_select", [])
        selected_ids = {s.pk for s in selected_students}

        existing = set(
            VmGroup.objects.filter(exam=obj).values_list("student_id", flat=True)
        )

        # Remove students that were deselected
        to_remove = existing - selected_ids
        if to_remove:
            VmGroup.objects.filter(exam=obj, student_id__in=to_remove).delete()

        # Add newly selected students
        to_add = selected_ids - existing
        for student_id in to_add:
            VmGroup.objects.create(exam=obj, student_id=student_id)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj and obj.pk:
            extra_context["vm_status_summary"] = self._get_vm_summary(obj)
        return super().change_view(request, object_id, form_url, extra_context)

    def _get_vm_summary(self, exam):
        """Build a summary of VM status for this exam."""
        groups = exam.vm_groups.select_related("student").prefetch_related("instances")
        rows = []
        for g in groups:
            instances = list(g.instances.all())
            win = next((v for v in instances if v.vm_type == "windows"), None)
            linux = [v for v in instances if v.vm_type == "linux"]
            rows.append({
                "student": g.student,
                "sg_id": g.security_group_id,
                "windows": win,
                "linux": linux,
                "total": len(instances),
                "running": sum(1 for v in instances if v.status == "running"),
            })
        return rows

    def create_vms_view(self, request, exam_id):
        from .services.tencent import create_vms_for_exam

        exam = Exam.objects.get(id=exam_id)
        result = create_vms_for_exam(exam)
        if result["error"] == 0:
            messages.success(
                request, f"Created VMs for {result['success']} students"
            )
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
    list_display = ["student", "exam", "vm_summary", "security_group_id", "created_at"]
    list_filter = ["exam"]
    list_select_related = ["exam", "student"]
    search_fields = ["student__username", "student__name", "exam__name"]
    inlines = [VmInstanceInline]

    def vm_summary(self, obj):
        instances = obj.instances.all()
        total = instances.count()
        running = sum(1 for v in instances if v.status == "running")
        if total == 0:
            return "—"
        return format_html(
            '<span style="color:#4CAF50;">{}</span> / {} running',
            running,
            total,
        )
    vm_summary.short_description = "VMs"


@admin.register(VmInstance)
class VmInstanceAdmin(admin.ModelAdmin):
    list_display = [
        "student_name", "exam_name", "vm_type", "role_label",
        "cpu", "ram", "status_badge", "private_ip", "created_at",
    ]
    list_filter = ["vm_type", "status", "group__exam"]
    search_fields = [
        "cvm_instance_id", "private_ip",
        "group__student__username", "group__exam__name",
    ]
    list_select_related = ["group__student", "group__exam"]
    readonly_fields = ["cvm_instance_id", "private_ip", "status"]
    fieldsets = (
        (None, {
            "fields": ("group", "vm_type", "role_label", "status"),
        }),
        ("Specs", {
            "fields": ("cpu", "ram", "disk", "image_id"),
        }),
        ("Cloud Info", {
            "fields": ("cvm_instance_id", "private_ip"),
        }),
        ("Credentials", {
            "fields": ("admin_username", "admin_password"),
        }),
        ("Guacamole", {
            "fields": ("guacamole_connection_id",),
        }),
    )

    def student_name(self, obj):
        return obj.group.student.username
    student_name.short_description = "Student"
    student_name.admin_order_field = "group__student__username"

    def exam_name(self, obj):
        return obj.group.exam.name
    exam_name.short_description = "Exam"
    exam_name.admin_order_field = "group__exam__name"

    def status_badge(self, obj):
        colors = {
            "running": "#4CAF50",
            "creating": "#FF9800",
            "stopped": "#f44336",
            "terminated": "#999",
        }
        color = colors.get(obj.status, "#666")
        return format_html(
            '<span style="display:inline-block;width:8px;height:8px;'
            'border-radius:50%;background:{};margin-right:6px;"></span>{}',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def delete_queryset(self, request, queryset):
        """Terminate cloud instances before bulk-deleting DB records."""
        from .services.tencent import terminate_instances

        for instance in queryset:
            if instance.cvm_instance_id and instance.status != "terminated":
                try:
                    terminate_instances([instance.cvm_instance_id])
                except Exception:
                    pass
        super().delete_queryset(request, queryset)
