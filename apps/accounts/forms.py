from django import forms
from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('role', 'organization', 'phone', 'bio')
        widgets = {
            'role': forms.Select(attrs={'class': 'aq-form-control'}),
            'organization': forms.TextInput(attrs={'class': 'aq-form-control', 'placeholder': 'e.g. Government of Gujarat'}),
            'phone': forms.TextInput(attrs={'class': 'aq-form-control', 'placeholder': '+91 98765 43210'}),
            'bio': forms.Textarea(attrs={'class': 'aq-form-control', 'rows': 4, 'placeholder': 'Brief description...'}),
        }
