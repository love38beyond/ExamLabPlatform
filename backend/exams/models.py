import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


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

    def delete(self, *args, **kwargs):
        """Delete DB record AND terminate the actual CVM on Tencent Cloud."""
        if self.cvm_instance_id and self.status != self.Status.TERMINATED:
            try:
                from .services.tencent import terminate_instances

                terminate_instances([self.cvm_instance_id])
                logger.info(
                    "Terminated CVM %s before deleting VmInstance %s",
                    self.cvm_instance_id,
                    self.id,
                )
            except Exception as e:
                logger.error(
                    "Failed to terminate CVM %s: %s",
                    self.cvm_instance_id,
                    e,
                )
        super().delete(*args, **kwargs)
