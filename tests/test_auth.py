from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from .base import STRONG_PASSWORD, BaseAPITestCase

User = get_user_model()
REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"


class RegistrationTests(BaseAPITestCase):
    def payload(self, **kw):
        data = {"name": "Carol", "email": "Carol@Example.com", "password": STRONG_PASSWORD}
        data.update(kw)
        return data

    def test_successful_registration(self):
        res = self.anon_client.post(REGISTER, self.payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"], "carol@example.com")  # normalised
        self.assertNotIn("password", res.data)
        self.assertTrue(User.objects.filter(email="carol@example.com").exists())

    def test_password_is_hashed(self):
        self.anon_client.post(REGISTER, self.payload(), format="json")
        user = User.objects.get(email="carol@example.com")
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_duplicate_email_rejected_case_insensitively(self):
        res = self.anon_client.post(REGISTER, self.payload(email="ALICE@example.com"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_missing_fields(self):
        res = self.anon_client.post(REGISTER, {}, format="json")
        self.assertEqual(res.status_code, 400)
        for field in ("name", "email", "password"):
            self.assertIn(field, res.data)

    def test_invalid_email(self):
        res = self.anon_client.post(REGISTER, self.payload(email="not-an-email"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_weak_passwords_rejected(self):
        for pwd in ("short1", "password", "12345678901"):
            res = self.anon_client.post(REGISTER, self.payload(password=pwd), format="json")
            self.assertEqual(res.status_code, 400, pwd)
            self.assertIn("password", res.data)

    def test_malformed_json_body(self):
        res = self.anon_client.post(REGISTER, "{bad json", content_type="application/json")
        self.assertEqual(res.status_code, 400)


class LoginTests(BaseAPITestCase):
    def test_successful_login_returns_jwt_pair(self):
        res = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["email"], "alice@example.com")

    def test_login_email_is_case_insensitive(self):
        res = self.anon_client.post(
            LOGIN, {"email": "ALICE@Example.com", "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_incorrect_password(self):
        res = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": "wrong-password"}, format="json"
        )
        self.assertEqual(res.status_code, 401)
        self.assertNotIn("access", res.data)

    def test_unknown_user(self):
        res = self.anon_client.post(
            LOGIN, {"email": "ghost@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 401)

    def test_missing_credentials(self):
        res = self.anon_client.post(LOGIN, {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_inactive_user_cannot_login(self):
        self.alice.is_active = False
        self.alice.save()
        res = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 401)


class JWTProtectionTests(BaseAPITestCase):
    PROTECTED = ["/api/patients/", "/api/doctors/", "/api/mappings/"]

    def test_protected_endpoints_require_token(self):
        for url in self.PROTECTED:
            self.assertEqual(self.anon_client.get(url).status_code, 401, url)
            self.assertEqual(self.anon_client.post(url, {}, format="json").status_code, 401, url)

    def test_invalid_token_rejected(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not.a.token")
        self.assertEqual(client.get("/api/patients/").status_code, 401)

    def test_real_jwt_flow_end_to_end(self):
        login = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        res = client.post(
            "/api/patients/", {"name": "Zed", "age": 30, "gender": "M"}, format="json"
        )
        self.assertEqual(res.status_code, 201)

    def test_refresh_token_cannot_be_used_as_access_token(self):
        login = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['refresh']}")
        self.assertEqual(client.get("/api/patients/").status_code, 401)

    def test_token_refresh(self):
        login = self.anon_client.post(
            LOGIN, {"email": "alice@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        res = self.anon_client.post(
            "/api/auth/token/refresh/", {"refresh": login.data["refresh"]}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_expired_token_rejected(self):
        from datetime import timedelta
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(self.alice)
        token.set_exp(lifetime=-timedelta(seconds=10))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get("/api/patients/").status_code, 401)
