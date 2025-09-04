from django import forms
from .models import College

class AddEventForm(forms.Form):
    event_name = forms.CharField(max_length=200)
    event_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    college = forms.ModelChoiceField(queryset=College.objects.all(), required=False, empty_label="General (All Colleges)")
