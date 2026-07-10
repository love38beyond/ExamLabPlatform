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
