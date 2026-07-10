# backend/exams/views.py
# Placeholder views - will be fully implemented in Task 11

from django.views.generic import TemplateView, View


class DashboardView(TemplateView):
    template_name = "exams/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["has_exam"] = False
        return ctx


class ConnectView(View):
    def get(self, request, vm_id):
        from django.http import HttpResponse
        return HttpResponse("Connect view placeholder")
