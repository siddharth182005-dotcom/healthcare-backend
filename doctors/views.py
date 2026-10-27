from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.exceptions import APIException

from .models import Doctor
from .permissions import IsCreatorOrReadOnly
from .serializers import DoctorSerializer


class DoctorInUse(APIException):
    status_code = 409
    default_detail = "This doctor is assigned to one or more patients. Remove the mappings first."
    default_code = "doctor_in_use"


@extend_schema(tags=["Doctors"])
class DoctorListCreateView(generics.ListCreateAPIView):
    """GET: list all doctors (any authenticated user). POST: add a doctor."""

    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema(tags=["Doctors"])
class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Any authenticated user may read; only the creator may update or delete."""

    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrReadOnly]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise DoctorInUse()
