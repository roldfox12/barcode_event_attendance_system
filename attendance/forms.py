from django import forms
from django.contrib.auth.models import User
from .models import College

class AddSBOUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    college = forms.ModelChoiceField(queryset=College.objects.all())
