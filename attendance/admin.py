from django.contrib import admin
from .models import Event, Attendee, Attendance
from .models import College



admin.site.register(Event)
admin.site.register(Attendee)
admin.site.register(Attendance)
admin.site.register(College) 
# Register your models here.


