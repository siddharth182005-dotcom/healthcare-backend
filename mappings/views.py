from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from patients.models import Patient

from .models import PatientDoctorMapping
from .serializers import MappingSerializer


def mappings_for(user):
    """All mappings whose patient belongs to ``user``."""
    return PatientDoctorMapping.objects.filter(patient__owner=user).select_related("doctor", "patient")


@extend_schema(tags=["Mappings"])
class MappingListCreateView(generics.ListCreateAPIView):
    """GET: all mappings for my patients. POST: assign a doctor to one of my patients."""

    serializer_class = MappingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PatientDoctorMapping.objects.none()
        return mappings_for(self.request.user)


class MappingDetailView(APIView):
    """
    GET    /api/mappings/<patient_id>/ -> doctors assigned to that patient
    DELETE /api/mappings/<id>/         -> remove that mapping

    (The assignment uses the same URL shape for both; the number means a
    patient id for GET and a mapping id for DELETE.)
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Mappings"],
        operation_id="mappings_doctors_for_patient",
        summary="List doctors assigned to a patient (path id = patient id)",
        responses=MappingSerializer(many=True),
    )
    def get(self, request, pk):
        patient = get_object_or_404(Patient.objects.filter(owner=request.user), pk=pk)
        mappings = mappings_for(request.user).filter(patient=patient)
        return Response(MappingSerializer(mappings, many=True, context={"request": request}).data)

    @extend_schema(
        tags=["Mappings"],
        operation_id="mappings_remove",
        summary="Remove a doctor from a patient (path id = mapping id)",
        responses={204: None},
    )
    def delete(self, request, pk):
        mapping = get_object_or_404(mappings_for(request.user), pk=pk)
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
