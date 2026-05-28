from django.db import models

class ContactMessage(models.Model):
    name = models.CharField("Nom complet", max_length=150)
    email = models.EmailField("Adresse e-mail")
    subject = models.CharField("Sujet", max_length=200, blank=True)
    message = models.TextField("Message")
    created_at = models.DateTimeField("Reçu le", auto_now_add=True)
    is_read = models.BooleanField("Lu ?", default=False)

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message de {self.name} ({self.email}) - {self.subject or 'Sans sujet'}"
