from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("connect/<int:vm_id>/", views.ConnectView.as_view(), name="connect"),
]
