from django import forms

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Votre nom"}),
            "email": forms.EmailInput(attrs={"placeholder": "Votre email"}),
            "subject": forms.TextInput(attrs={"placeholder": "Sujet (optionnel)"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Votre message"}),
        }
