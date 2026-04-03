from django.conf import settings as django_settings
from django.shortcuts import redirect
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import AllowList, User


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        frontend_url = django_settings.FRONTEND_URL
        return f"{frontend_url}/dashboard"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)

        if not sociallogin.is_existing:
            email = sociallogin.user.email
            if email:
                try:
                    existing_user = User.objects.get(email__iexact=email)
                    sociallogin.connect(request, existing_user)
                    sociallogin.user = existing_user
                    return
                except User.DoesNotExist:
                    pass

        if not sociallogin.is_existing and django_settings.ONLY_ALLOWLIST_CAN_SIGN_UP:
            email = sociallogin.user.email
            allowed = AllowList.objects.filter(email__iexact=email).exists()
            if not allowed:
                frontend_url = django_settings.FRONTEND_URL
                raise ImmediateHttpResponse(
                    redirect(f"{frontend_url}/login?error=allowlist")
                )
