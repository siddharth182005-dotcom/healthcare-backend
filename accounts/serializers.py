from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    # Declared explicitly so we control normalisation and uniqueness ourselves
    # (case-insensitive).
    email = serializers.EmailField(max_length=254)
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["id", "name", "email", "password"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        # Run Django's password validators (length, common, numeric, similarity).
        candidate = User(name=attrs.get("name", ""), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
        )


class LoginSerializer(TokenObtainPairSerializer):
    """Email + password -> access/refresh JWT (plus basic user info)."""

    def validate(self, attrs):
        attrs[self.username_field] = str(attrs.get(self.username_field, "")).strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
