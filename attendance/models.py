from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateTimeField()
    college = models.ForeignKey(
        'College',
        on_delete=models.CASCADE,
        null=True,      # Null means general event
        blank=True
    )

    def __str__(self):
        return self.name
    
class Attendee(models.Model):
    barcode_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    college = models.ForeignKey('College', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
class Attendance(models.Model):
    attendee = models.ForeignKey(Attendee, on_delete=models.CASCADE)
    event= models.ForeignKey(Event, on_delete=models.CASCADE)
    sign_in_am = models.DateTimeField(null=True, blank=True)
    sign_out_am = models.DateTimeField(null=True, blank=True)
    sign_in_pm = models.DateTimeField(null=True, blank=True)
    sign_out_pm = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.attendee.name} - {self.event.name}"

class College(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class SBOProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.college.name}"
