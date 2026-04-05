import logging

from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AllowList, User
from accounts.serializers import LoginSerializer, SignupSerializer, UserSerializer

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response({"user": UserSerializer(request.user).data})
        return Response({"user": None})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if django_settings.ONLY_ALLOWLIST_CAN_SIGN_UP:
            email = data["email"]
            allowed = AllowList.objects.filter(email__iexact=email).exists()
            if not allowed:
                return Response(
                    {"error": "This email is not on the allow list."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        user = User.objects.create_user(email=data["email"], password=data["password"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            logger.warning("Failed login attempt for email: %s", serializer.validated_data["email"].lower())
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out"})


class WsTicketView(APIView):
    def post(self, request):
        from config.ws_auth import create_ws_ticket

        ticket = create_ws_ticket(request.user.id)
        return Response({"ticket": ticket})
