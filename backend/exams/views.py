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

        if not vm.private_ip:
            from .services.tencent import describe_instances
            results = describe_instances([vm.cvm_instance_id])
            if results:
                vm.private_ip = results[0]["private_ip"]
                if results[0]["state"] == "RUNNING":
                    vm.status = VmInstance.Status.RUNNING
                vm.save(update_fields=["private_ip", "status"])

        guac_url = get_connection_url(vm)
        return redirect(guac_url)
