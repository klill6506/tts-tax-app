from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me, name="me"),
    path("auth/login/", views.auth_login, name="auth-login"),
    path("auth/logout/", views.auth_logout, name="auth-logout"),
]
