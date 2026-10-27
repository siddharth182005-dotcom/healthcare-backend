from django.db import IntegrityError, transaction

from doctors.models import Doctor

from .base import BaseAPITestCase

LIST = "/api/doctors/"


def detail(pk):
    return f"/api/doctors/{pk}/"


VALID = {"name": "Meredith Grey", "specialization": "Surgery", "email": "Grey@Example.com",
         "phone": "+1 555 000 1111", "address": "Seattle Grace"}


class DoctorCrudTests(BaseAPITestCase):
    def test_create_doctor(self):
        res = self.alice_client.post(LIST, VALID, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"], "grey@example.com")
        self.assertEqual(Doctor.objects.get(pk=res.data["id"]).created_by, self.alice)

    def test_list_shows_all_doctors_to_any_authenticated_user(self):
        self.make_doctor(self.alice, email="a@example.com")
        self.make_doctor(self.bob, email="b@example.com")
        res = self.alice_client.get(LIST)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_doctor_created_by_someone_else(self):
        d = self.make_doctor(self.bob)
        self.assertEqual(self.alice_client.get(detail(d.id)).status_code, 200)

    def test_update_own_doctor(self):
        d = self.make_doctor(self.alice)
        res = self.alice_client.put(detail(d.id), dict(VALID, name="New Name"), format="json")
        self.assertEqual(res.status_code, 200)
        d.refresh_from_db()
        self.assertEqual(d.name, "New Name")

    def test_update_keeping_same_email_is_allowed(self):
        d = self.make_doctor(self.alice, email="grey@example.com")
        res = self.alice_client.put(detail(d.id), VALID, format="json")
        self.assertEqual(res.status_code, 200)

    def test_delete_own_doctor(self):
        d = self.make_doctor(self.alice)
        self.assertEqual(self.alice_client.delete(detail(d.id)).status_code, 204)
        self.assertFalse(Doctor.objects.filter(pk=d.id).exists())

    def test_missing_doctor_404(self):
        self.assertEqual(self.alice_client.get(detail(424242)).status_code, 404)

    def test_validation(self):
        for bad in ({}, dict(VALID, email="nope"), dict(VALID, name=""),
                    dict(VALID, specialization=" "), dict(VALID, phone="x")):
            self.assertEqual(self.alice_client.post(LIST, bad, format="json").status_code, 400, bad)

    def test_duplicate_email_rejected(self):
        self.make_doctor(self.alice, email="grey@example.com")
        res = self.bob_client.post(LIST, VALID, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_db_enforces_case_insensitive_email_uniqueness(self):
        self.make_doctor(self.alice, email="dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Doctor.objects.create(name="X", specialization="Y", email="DUP@example.com")

    def test_unauthenticated_denied(self):
        self.assertEqual(self.anon_client.get(LIST).status_code, 401)
        self.assertEqual(self.anon_client.post(LIST, VALID, format="json").status_code, 401)


class DoctorOwnershipTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.doc = self.make_doctor(self.bob)

    def test_other_user_cannot_update(self):
        res = self.alice_client.put(detail(self.doc.id), VALID, format="json")
        self.assertEqual(res.status_code, 403)
        self.doc.refresh_from_db()
        self.assertNotEqual(self.doc.name, VALID["name"])

    def test_other_user_cannot_partially_update(self):
        res = self.alice_client.patch(detail(self.doc.id), {"name": "Hacked"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_other_user_cannot_delete(self):
        res = self.alice_client.delete(detail(self.doc.id))
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Doctor.objects.filter(pk=self.doc.id).exists())

    def test_doctor_with_no_creator_is_read_only(self):
        orphan = self.make_doctor(None, email="orphan@example.com")
        self.assertEqual(self.alice_client.get(detail(orphan.id)).status_code, 200)
        self.assertEqual(self.alice_client.delete(detail(orphan.id)).status_code, 403)

    def test_deleting_creator_keeps_doctor(self):
        self.bob.delete()
        self.doc.refresh_from_db()
        self.assertIsNone(self.doc.created_by)

    def test_cannot_delete_doctor_assigned_to_patients(self):
        from mappings.models import PatientDoctorMapping

        patient = self.make_patient(self.alice)
        PatientDoctorMapping.objects.create(patient=patient, doctor=self.doc)
        res = self.bob_client.delete(detail(self.doc.id))
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Doctor.objects.filter(pk=self.doc.id).exists())
