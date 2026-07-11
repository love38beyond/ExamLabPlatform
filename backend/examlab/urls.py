from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/"), name="root"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("exams/", include("exams.urls")),
]
