from django.urls import path
from . import views

urlpatterns = [
    path('add_event/', views.add_event, name='add_event'),
    path('add_student/', views.add_student, name='add_student'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('sign_in_manual/', views.sign_in_manual, name='sign_in_manual'),
    path('sign_out_manual/', views.sign_out_manual, name='sign_out_manual'),
    path('scan_barcode/', views.scan_barcode, name='scan_barcode'),   
    path('attendance_sheet/<int:event_id>/', views.attendance_sheet, name='attendance_sheet'),
    path('students/', views.students_list, name='students_list'),
    path('events/', views.events_list, name='events_list'),
]