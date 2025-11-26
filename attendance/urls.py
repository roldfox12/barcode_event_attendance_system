from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Event management
    path('events/', views.event_list, name='event_list'),
    path('events_list/', views.events_list, name='events_list'),
    path('add_event/', views.add_event, name='add_event'),
    path('create_event/', views.create_event, name='create_event'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('remove_event/<int:event_id>/', views.remove_event, name='remove_event'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('archive_event/<int:event_id>/', views.archive_event, name='archive_event'),
    path('unarchive_event/<int:event_id>/', views.unarchive_event, name='unarchive_event'),

    # Attendance sheets / view/print
    path('view_attendance_sheet/', views.view_attendance_sheet, name='view_attendance_sheet'),
    path('view_attendance_sheet/<int:event_id>/', views.view_attendance_sheet_event, name='view_attendance_sheet_event'),
    path('print_attendance_sheet/<int:event_id>/', views.print_attendance_sheet, name='print_attendance_sheet'),
    path('attendance_sheet/<int:event_id>/', views.attendance_sheet, name='attendance_sheet'),

    # Manual sign / scan
    path('manual_sign/', views.manual_sign, name='manual_sign'),
    path('sign_in_manual/', views.sign_in_manual, name='sign_in_manual'),
    path('sign_out_manual/', views.sign_out_manual, name='sign_out_manual'),
    path('scan_barcode/', views.scan_barcode, name='scan_barcode'),
    path('barcode_scanner/', views.barcode_scanner, name='barcode_scanner'),

    # Students / SBO users
    path('students/', views.students_list, name='students_list'),
    path('sbo_users/', views.sbo_users_list, name='sbo_users_list'),
    path('add_sbo_user/', views.add_sbo_user, name='add_sbo_user'),
    path('edit_sbo_user/<int:user_id>/', views.edit_sbo_user, name='edit_sbo_user'),
    path('delete_sbo_user/<int:user_id>/', views.delete_sbo_user, name='delete_sbo_user'),

    # Attendance records
    path('attendance/edit/<int:attendance_id>/', views.edit_attendance, name='edit_attendance'),
    path('attendance/delete/<int:attendance_id>/', views.delete_attendance, name='delete_attendance'),

    # Colleges and misc
    path('add_college/', views.add_college, name='add_college'),
    path('add_student/', views.add_student, name='add_student'),
    path('edit_student/<int:student_id>/', views.edit_student, name='edit_student'),

    # Delete all records
    path('delete_all_sbo_users/', views.delete_all_sbo_users, name='delete_all_sbo_users'),
    path('delete_all_students/', views.delete_all_students, name='delete_all_students'),
    path('delete_all_events/', views.delete_all_events, name='delete_all_events'),

    # Delete student record
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),

    # Archived events
    path('archived_events/', views.archived_events_list, name='archived_events_list'),

    # Student attendance detail
    path('students/<int:student_id>/attendance/', views.student_attendance_detail, name='student_attendance_detail'),
    path('students/<int:student_id>/attendance/pdf/', views.print_student_attendance_pdf, name='print_student_attendance_pdf'),
]