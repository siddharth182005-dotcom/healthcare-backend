from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions

from .models import Patient
from .permissions import IsOwner
from .serializers import PatientSerializer


class OwnedPatientQuerysetMixin:
    """Restrict every query to patients owned by the authenticated user."""

    serializer_class = PatientSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Patient.objects.none()
        return Patient.objects.filter(owner=self.request.user)


@extend_schema(tags=["Patients"])
class PatientListCreateView(OwnedPatientQuerysetMixin, generics.ListCreateAPIView):
    """GET: list my patients. POST: create a patient owned by me."""

    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema(tags=["Patients"])
class PatientDetailView(OwnedPatientQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update (PUT) or delete one of my patients.

    Other users' patients are not in the queryset, so they return 404.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwner]
