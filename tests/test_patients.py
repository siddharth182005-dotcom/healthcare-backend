from patients.models import Patient

from .base import BaseAPITestCase

LIST = "/api/patients/"


def detail(pk):
    return f"/api/patients/{pk}/"


class PatientCrudTests(BaseAPITestCase):
    VALID = {"name": "John Doe", "age": 35, "gender": "M", "phone": "+1 555 123 4567",
             "address": "1 Main St", "medical_history": "Asthma"}

    def test_create_patient_sets_owner(self):
        res = self.alice_client.post(LIST, self.VALID, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("owner", res.data)
        self.assertEqual(Patient.objects.get(pk=res.data["id"]).owner, self.alice)

    def test_owner_cannot_be_set_by_client(self):
        data = dict(self.VALID, owner=self.bob.id)
        res = self.alice_client.post(LIST, data, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Patient.objects.get(pk=res.data["id"]).owner, self.alice)

    def test_list_returns_only_own_patients(self):
        mine = self.make_patient(self.alice, name="Mine")
        self.make_patient(self.bob, name="Theirs")
        res = self.alice_client.get(LIST)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([p["id"] for p in res.data], [mine.id])

    def test_retrieve_own_patient(self):
        p = self.make_patient(self.alice)
        res = self.alice_client.get(detail(p.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["name"], p.name)

    def test_update_patient_put(self):
        p = self.make_patient(self.alice)
        res = self.alice_client.put(detail(p.id), dict(self.VALID, name="Renamed"), format="json")
        self.assertEqual(res.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.name, "Renamed")

    def test_delete_patient(self):
        p = self.make_patient(self.alice)
        res = self.alice_client.delete(detail(p.id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Patient.objects.filter(pk=p.id).exists())

    def test_missing_patient_is_404(self):
        self.assertEqual(self.alice_client.get(detail(999999)).status_code, 404)
        self.assertEqual(self.alice_client.delete(detail(999999)).status_code, 404)

    def test_validation_errors(self):
        for bad in (
            {},  # missing everything
            dict(self.VALID, name="   "),
            dict(self.VALID, age=-1),
            dict(self.VALID, age=500),
            dict(self.VALID, gender="X"),
            dict(self.VALID, phone="abc"),
        ):
            res = self.alice_client.post(LIST, bad, format="json")
            self.assertEqual(res.status_code, 400, bad)

    def test_put_requires_full_payload(self):
        p = self.make_patient(self.alice)
        res = self.alice_client.put(detail(p.id), {"name": "Only name"}, format="json")
        self.assertEqual(res.status_code, 400)


class PatientIsolationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.bobs_patient = self.make_patient(self.bob, name="Bob's patient")

    def test_cannot_retrieve_other_users_patient(self):
        res = self.alice_client.get(detail(self.bobs_patient.id))
        self.assertEqual(res.status_code, 404)

    def test_cannot_update_other_users_patient(self):
        res = self.alice_client.put(
            detail(self.bobs_patient.id), {"name": "Hacked", "age": 1, "gender": "M"}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        self.bobs_patient.refresh_from_db()
        self.assertEqual(self.bobs_patient.name, "Bob's patient")

    def test_cannot_delete_other_users_patient(self):
        res = self.alice_client.delete(detail(self.bobs_patient.id))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Patient.objects.filter(pk=self.bobs_patient.id).exists())

    def test_unauthenticated_access_denied(self):
        self.assertEqual(self.anon_client.get(detail(self.bobs_patient.id)).status_code, 401)
