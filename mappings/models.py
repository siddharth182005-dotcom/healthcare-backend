from django.db import models


class PatientDoctorMapping(models.Model):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="doctor_mappings"
    )
    # PROTECT: a doctor who is assigned to patients cannot be deleted by accident.
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="patient_mappings"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["patient", "doctor"], name="unique_patient_doctor"),
        ]

    def __str__(self):
        return f"Patient {self.patient_id} -> Doctor {self.doctor_id}"
