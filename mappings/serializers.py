from rest_framework import serializers

from doctors.models import Doctor
from doctors.serializers import DoctorSerializer
from patients.models import Patient

from .models import PatientDoctorMapping


class MappingSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.none())
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all())
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = ["id", "patient", "doctor", "doctor_detail", "created_at"]
        read_only_fields = ["id", "created_at"]
        validators = []  # duplicate check is done explicitly in validate()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        # Only patients owned by the caller are valid targets. A patient owned by
        # someone else produces the same "does not exist" error as a missing one,
        # so existence of other users' patients is never revealed.
        if user is not None and user.is_authenticated:
            self.fields["patient"].queryset = Patient.objects.filter(owner=user)

    def validate(self, attrs):
        if PatientDoctorMapping.objects.filter(
            patient=attrs["patient"], doctor=attrs["doctor"]
        ).exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["This doctor is already assigned to this patient."]}
            )
        return attrs
