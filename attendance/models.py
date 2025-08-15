from django.db import models

# Create your models here.

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateTimeField()
    
    def __str__(self):
        return self.name
class Attendee(models.Model):
    barcode_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name
    
class Attendance(models.Model):
    attendee = models.ForeignKey(Attendee, on_delete=models.CASCADE)
    event= models.ForeignKey(Event, on_delete=models.CASCADE)
    sign_in_time = models.DateTimeField(null=True, blank=True)
    sign_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.attendee.name} - {self.event.name}"

