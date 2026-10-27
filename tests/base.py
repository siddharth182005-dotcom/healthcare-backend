from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from doctors.models import Doctor
from patients.models import Patient

User = get_user_model()
STRONG_PASSWORD = "Str0ng-Pass!word42"


class BaseAPITestCase(APITestCase):
    """Creates two independent users, each with its own authenticated client."""

    def setUp(self):
        self.alice = User.objects.create_user("alice@example.com", STRONG_PASSWORD, name="Alice")
        self.bob = User.objects.create_user("bob@example.com", STRONG_PASSWORD, name="Bob")
        self.alice_client = self.client_for(self.alice)
        self.bob_client = self.client_for(self.bob)
        self.anon_client = APIClient()

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    # --- factories ---
    def make_patient(self, owner, **overrides):
        data = {"name": "Pat Patient", "age": 40, "gender": "F"}
        data.update(overrides)
        return Patient.objects.create(owner=owner, **data)

    def make_doctor(self, creator, **overrides):
        data = {"name": "Gregory House", "specialization": "Diagnostics",
                "email": "house@example.com"}
        data.update(overrides)
        return Doctor.objects.create(created_by=creator, **data)
