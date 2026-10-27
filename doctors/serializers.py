from rest_framework import serializers

from patients.serializers import validate_phone_number

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=254)

    class Meta:
        model = Doctor
        fields = [
            "id", "name", "specialization", "email", "phone", "address",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_specialization(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_phone(self, value):
        return validate_phone_number(value)

    def validate_email(self, value):
        value = value.strip().lower()
        qs = Doctor.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A doctor with this email already exists.")
        return value
