from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Doctor(models.Model):
    # Who added the doctor. Only this user may edit/delete the record.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="doctors_created",
    )
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            # Case-insensitive uniqueness of the doctor's email.
            models.UniqueConstraint(Lower("email"), name="doctor_email_ci_unique"),
        ]
        indexes = [models.Index(fields=["specialization"], name="doctor_specialization_idx")]

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"
