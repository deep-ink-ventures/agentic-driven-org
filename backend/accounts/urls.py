from django.urls import path, include
from accounts import views

urlpatterns = [
    path("session/", views.SessionView.as_view(), name="auth-session"),
    path("signup/", views.SignupView.as_view(), name="auth-signup"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("ws-ticket/", views.WsTicketView.as_view(), name="ws-ticket"),
    path("", include("allauth.socialaccount.providers.google.urls")),
]
