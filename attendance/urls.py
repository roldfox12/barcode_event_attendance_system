from django.urls import path
from . import views

urlpatterns = [
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('add_event/', views.add_event, name='add_event'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('sign_in_manual/', views.sign_in_manual, name='sign_in_manual'),
    path('sign_out_manual/', views.sign_out_manual, name='sign_out_manual'),
    path('scan_barcode/', views.scan_barcode, name='scan_barcode'),   
    path('attendance_sheet/<int:event_id>/', views.attendance_sheet, name='attendance_sheet'),
    path('events/', views.events_list, name='events_list'),
    # SBO Officers management
    path('sbo_users/', views.sbo_users_list, name='sbo_users_list'),
    path('add_sbo_user/', views.add_sbo_user, name='add_sbo_user'),
    path('edit_sbo_user/<int:user_id>/', views.edit_sbo_user, name='edit_sbo_user'),
    path('delete_sbo_user/<int:user_id>/', views.delete_sbo_user, name='delete_sbo_user'),
    # Student management
    path('edit_student/<int:student_id>/', views.edit_student, name='edit_student'),
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    path('add_student/', views.add_student, name='add_student'),
    path('students/', views.students_list, name='students_list'),
    path('', views.attendance_sheet, name='attendance_sheet'),
    path('manual_sign/', views.manual_sign, name='manual_sign')
]