import json
from django import forms
from accounts.models import Student


class VmSpecWidget(forms.Widget):
    """Structured widget for vm_spec JSON field with dynamic Linux servers."""

    template_name = "exams/admin/vm_spec_widget.html"

    class Media:
        css = {"all": ("exams/admin/vm_spec_widget.css",)}
        js = ("exams/admin/vm_spec_widget.js",)

    def format_value(self, value):
        if isinstance(value, str):
            try:
                data = json.loads(value)
                data.setdefault("windows", None)
                data.setdefault("linux_servers", [])
                return data
            except (json.JSONDecodeError, TypeError):
                return self._default_spec()
        if not value:
            return self._default_spec()
        value.setdefault("windows", None)
        value.setdefault("linux_servers", [])
        return value

    def _default_spec(self):
        return {
            "windows": None,
            "linux_servers": [],
        }

    def value_from_datadict(self, data, files, name):
        try:
            linux_count = int(data.get(f"{name}_linux_count", 0))
            linux_servers = []
            for i in range(linux_count):
                role = data.get(f"{name}_linux_role_{i}", "").strip()
                if not role:
                    continue
                linux_servers.append({
                    "role": role,
                    "cpu": int(data.get(f"{name}_linux_cpu_{i}", 2)),
                    "ram": int(data.get(f"{name}_linux_ram_{i}", 2)),
                    "disk": int(data.get(f"{name}_linux_disk_{i}", 40)),
                    "image_id": data.get(f"{name}_linux_image_id_{i}", "").strip(),
                })

            # Windows is optional — null when unchecked
            win_enabled = data.get(f"{name}_win_enabled") == "1"
            windows = None
            if win_enabled:
                windows = {
                    "cpu": int(data.get(f"{name}_win_cpu", 2)),
                    "ram": int(data.get(f"{name}_win_ram", 4)),
                    "disk": int(data.get(f"{name}_win_disk", 50)),
                    "image_id": data.get(f"{name}_win_image_id", "").strip(),
                }

            spec = {
                "windows": windows,
                "linux_servers": linux_servers,
            }
            return json.dumps(spec, ensure_ascii=False)
        except (ValueError, TypeError):
            return json.dumps(self._default_spec(), ensure_ascii=False)


class VmSpecField(forms.fields.JSONField):
    """JSON field that uses VmSpecWidget for display."""

    widget = VmSpecWidget

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("initial", dict)
        super().__init__(**kwargs)


class ExamForm(forms.ModelForm):
    """Exam form with structured vm_spec and batch student selection."""

    vm_spec = VmSpecField()
    students_select = forms.ModelMultipleChoiceField(
        queryset=Student.objects.filter(is_active=True).order_by("username"),
        required=False,
        label="Assign Students",
        help_text="Select students to assign to this exam. "
                  "Already assigned students are pre-selected.",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        from .models import Exam

        model = Exam
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate with already assigned students
        if self.instance.pk:
            from .models import VmGroup
            assigned = VmGroup.objects.filter(exam=self.instance).values_list(
                "student_id", flat=True
            )
            self.fields["students_select"].initial = list(assigned)
