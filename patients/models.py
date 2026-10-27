from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    # Ownership: every patient belongs to the user who created it.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patients"
    )
    name = models.CharField(max_length=150)
    age = models.PositiveSmallIntegerField(validators=[MaxValueValidator(150)])
    gender = models.CharField(max_length=1, choices=Gender.choices)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["owner", "name"], name="patient_owner_name_idx")]

    def __str__(self):
        return f"{self.name} (#{self.pk})"
