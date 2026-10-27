from django.db import IntegrityError, transaction
from django.test import override_settings

from mappings.models import PatientDoctorMapping

from .base import BaseAPITestCase

LIST = "/api/mappings/"


def detail(pk):
    return f"/api/mappings/{pk}/"


class MappingTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.patient = self.make_patient(self.alice, name="Alice's patient")
        self.doctor = self.make_doctor(self.bob, email="d1@example.com")
        self.doctor2 = self.make_doctor(self.bob, email="d2@example.com", name="Second Doc")

    def assign(self, client=None, patient=None, doctor=None):
        client = client or self.alice_client
        return client.post(
            LIST,
            {"patient": (patient or self.patient).id, "doctor": (doctor or self.doctor).id},
            format="json",
        )

    # --- create ---
    def test_assign_doctor_to_own_patient(self):
        res = self.assign()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["doctor_detail"]["id"], self.doctor.id)
        self.assertTrue(
            PatientDoctorMapping.objects.filter(patient=self.patient, doctor=self.doctor).exists()
        )

    def test_response_does_not_leak_patient_details(self):
        res = self.assign()
        self.assertEqual(res.data["patient"], self.patient.id)
        self.assertNotIn("medical_history", str(res.data))
        self.assertNotIn(self.patient.name, str(res.data))

    def test_duplicate_assignment_rejected(self):
        self.assertEqual(self.assign().status_code, 201)
        res = self.assign()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(PatientDoctorMapping.objects.count(), 1)

    def test_database_constraint_prevents_duplicates(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)

    def test_same_doctor_for_multiple_patients_is_fine(self):
        other_patient = self.make_patient(self.alice, name="Second")
        self.assertEqual(self.assign().status_code, 201)
        self.assertEqual(self.assign(patient=other_patient).status_code, 201)

    def test_cannot_assign_to_another_users_patient(self):
        res = self.assign(client=self.bob_client)  # patient belongs to alice
        self.assertEqual(res.status_code, 400)
        self.assertIn("patient", res.data)
        self.assertEqual(PatientDoctorMapping.objects.count(), 0)

    def test_error_for_foreign_patient_matches_missing_patient(self):
        foreign = self.bob_client.post(LIST, {"patient": self.patient.id, "doctor": self.doctor.id}, format="json")
        missing = self.bob_client.post(LIST, {"patient": 999999, "doctor": self.doctor.id}, format="json")
        self.assertEqual(foreign.status_code, missing.status_code)
        self.assertEqual(str(foreign.data["patient"][0]).split('"')[0], str(missing.data["patient"][0]).split('"')[0])

    def test_invalid_foreign_keys(self):
        for payload in (
            {"patient": 999999, "doctor": self.doctor.id},
            {"patient": self.patient.id, "doctor": 999999},
            {"patient": "abc", "doctor": self.doctor.id},
            {"patient": self.patient.id},
            {},
        ):
            res = self.alice_client.post(LIST, payload, format="json")
            self.assertEqual(res.status_code, 400, payload)

    def test_unauthenticated_denied(self):
        res = self.anon_client.post(LIST, {"patient": self.patient.id, "doctor": self.doctor.id}, format="json")
        self.assertEqual(res.status_code, 401)

    # --- list ---
    def test_list_returns_only_authorized_mappings(self):
        mine = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        bobs_patient = self.make_patient(self.bob)
        PatientDoctorMapping.objects.create(patient=bobs_patient, doctor=self.doctor)
        res = self.alice_client.get(LIST)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([m["id"] for m in res.data], [mine.id])

    def test_list_empty_for_user_without_patients(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        res = self.bob_client.get(LIST)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    # --- doctors for a patient ---
    def test_list_doctors_for_patient(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor2)
        res = self.alice_client.get(detail(self.patient.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual({m["doctor_detail"]["id"] for m in res.data}, {self.doctor.id, self.doctor2.id})

    def test_list_doctors_for_patient_with_none_assigned(self):
        res = self.alice_client.get(detail(self.patient.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_cannot_list_doctors_of_other_users_patient(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        self.assertEqual(self.bob_client.get(detail(self.patient.id)).status_code, 404)

    def test_missing_patient_404(self):
        self.assertEqual(self.alice_client.get(detail(999999)).status_code, 404)

    # --- delete ---
    def test_remove_assignment(self):
        m = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        res = self.alice_client.delete(detail(m.id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=m.id).exists())
        self.assertTrue(type(self.doctor).objects.filter(pk=self.doctor.id).exists())

    def test_cannot_remove_other_users_mapping(self):
        m = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        res = self.bob_client.delete(detail(m.id))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(PatientDoctorMapping.objects.filter(pk=m.id).exists())

    def test_remove_missing_mapping_404(self):
        self.assertEqual(self.alice_client.delete(detail(999999)).status_code, 404)

    def test_deleting_patient_removes_its_mappings(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        self.alice_client.delete(f"/api/patients/{self.patient.id}/")
        self.assertEqual(PatientDoctorMapping.objects.count(), 0)

    def test_non_numeric_id_returns_json_404(self):
        res = self.alice_client.get("/api/mappings/abc/")
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=False)
    def test_unknown_url_returns_json_not_html(self):
        res = self.alice_client.get("/api/does-not-exist/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res["Content-Type"], "application/json")
