from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


@extend_schema(responses={201: UserSerializer}, request=RegisterSerializer, tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """Register a new user with name, email and password."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Auth"])
class LoginView(TokenObtainPairView):
    """Log in with email + password and receive JWT access and refresh tokens."""

    serializer_class = LoginSerializer


@extend_schema(tags=["Auth"])
class RefreshView(TokenRefreshView):
    """Exchange a valid refresh token for a new access token."""
