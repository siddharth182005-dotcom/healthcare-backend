import re

from rest_framework import serializers

from .models import Patient

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,18}$")


def validate_phone_number(value):
    value = value.strip()
    if value and not PHONE_RE.match(value):
        raise serializers.ValidationError("Enter a valid phone number (7-20 digits, may start with +).")
    return value


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id", "name", "age", "gender", "phone", "address",
            "medical_history", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_phone(self, value):
        return validate_phone_number(value)
