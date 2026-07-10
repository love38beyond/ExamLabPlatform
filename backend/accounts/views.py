from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.urls import reverse_lazy


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy("accounts:login")
