from django.contrib.auth.models import AbstractUser
from django.db import models


class Student(AbstractUser):
    """Custom user model for exam students."""

    name = models.CharField("Name", max_length=100, blank=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ["username"]

    def __str__(self):
        return f"{self.name or self.username} ({self.username})"
