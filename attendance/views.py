from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
import attendance
from .models import Event, Attendee, Attendance, College, SBOProfile
from .forms import AddSBOUserForm
from .forms_event import AddEventForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Max, F, Value, DateTimeField
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.db import IntegrityError
from django.db.models.functions import Greatest
from django.contrib.auth.models import User
import datetime
from django.core.exceptions import FieldDoesNotExist
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_all_sbo_users(request):
    User = get_user_model()
    if request.method == 'POST':
        User.objects.filter(is_superuser=False, is_staff=False).delete()
        messages.success(request, "All SBO users have been deleted.")
    return redirect('sbo_users_list')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.username == 'sbo_admin')
def delete_all_students(request):
    if request.method == 'POST':
        Attendee.objects.all().delete()
        messages.success(request, "All students have been deleted.")
    return redirect('students_list')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.username == 'sbo_admin')
def delete_all_events(request):
    if request.method == 'POST':
        Event.objects.all().delete()
        messages.success(request, "All events have been deleted.")
    return redirect('events_list')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if username == 'sbo_admin':
                return redirect('dashboard')
            else:
                return redirect('index')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')


@login_required
def dashboard(request):
    events = Event.objects.all()
    students = Attendee.objects.all()
    colleges = College.objects.all()
    sbo_form = AddSBOUserForm()
    add_event_form = AddEventForm()
    return render(request, 'dashboard.html', {
        'events': events,
        'students': students,
        'colleges': colleges,
        'sbo_form': sbo_form,
        'add_event_form': add_event_form,
    })

def index(request):
    events = Event.objects.all()

    # Defaults for sticky form
    selected_event_id = ''
    selected_action = 'sign_in'
    barcode_id = ''

    # Get assigned college for SBO user
    assigned_college = None
    if request.user.is_authenticated and not (request.user.is_superuser or request.user.username == 'sbo_admin'):
        try:
            assigned_college = request.user.sboprofile.college.name
        except Exception:
            assigned_college = None

    # Handle manual sign-in/sign-out
    if request.method == 'POST':
        if 'barcode_id' in request.POST:
            selected_event_id = request.POST.get('event_id', '')
            barcode_id = request.POST.get('barcode_id', '')
            selected_action = request.POST.get('action', 'sign_in')

            event = get_object_or_404(Event, id=selected_event_id) if selected_event_id else None
            attendee = None
            if barcode_id:
                try:
                    attendee = Attendee.objects.get(barcode_id=barcode_id)
                except Attendee.DoesNotExist:
                    messages.error(request, "ID is not registered.")
                    attendee = None

            if event and attendee:
                attendance, created = Attendance.objects.get_or_create(
                    attendee=attendee,
                    event=event,
                )
                if selected_action == 'sign_in':
                    attendance.sign_in_time = timezone.now()
                    attendance.save()
                elif selected_action == 'sign_out':
                    attendance.sign_out_time = timezone.now()
                    attendance.save()
            # Clear barcode_id after processing so you can scan the next one
            barcode_id = ''

    # Update recent_attendance to use the new AM/PM fields
    from django.db.models.functions import Greatest
    recent_attendance = Attendance.objects.annotate(
        latest_time=Greatest(
            F('sign_in_am'),
            F('sign_out_am'),
            F('sign_in_pm'),
            F('sign_out_pm'),
            output_field=DateTimeField()
        )
    ).filter(
        Q(sign_in_am__isnull=False) | Q(sign_out_am__isnull=False) | Q(sign_in_pm__isnull=False) | Q(sign_out_pm__isnull=False)
    ).order_by('-latest_time')[:10]


    return render(
        request,
        'index.html',
        {
            'events': events,
            'recent_attendance': recent_attendance,
            'selected_event_id': selected_event_id,
            'selected_action': selected_action,
            'barcode_id': barcode_id,
            'assigned_college': assigned_college,
        }
    )


@login_required
def create_event(request):
    if request.method == 'POST':
        form = AddEventForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['event_name']
            date = form.cleaned_data['event_date']
            if request.user.is_superuser or request.user.username == 'sbo_admin':
                college = form.cleaned_data['college']
            else:
                try:
                    college = request.user.sboprofile.college
                except Exception:
                    college = None

            # Safely include description only if the form or POST provides it and the model has the field
            description = form.cleaned_data.get('description') if isinstance(form.cleaned_data, dict) else None
            if not description:
                description = request.POST.get('description', '').strip() or None

            create_kwargs = {'name': name, 'date': date, 'college': college}
            try:
                # Check if Event model has a 'description' field
                Event._meta.get_field('description')
                if description:
                    create_kwargs['description'] = description
            except FieldDoesNotExist:
                # Event model has no description field, ignore it
                pass

            event = Event.objects.create(**create_kwargs)
            # ensure description is persisted even if it wasn't included in create_kwargs
            if description:
                try:
                    Event._meta.get_field('description')
                    event.description = description
                    event.save(update_fields=['description'])
                except FieldDoesNotExist:
                    pass
            messages.success(request, "Event created successfully!")
            # Redirect after successful creation
            if request.user.is_superuser or request.user.username == 'sbo_admin':
                return redirect('dashboard')
            else:
                return redirect('index')
        else:
            messages.error(request, "Please provide all required fields.")
    else:
        # GET request: render the form
        if request.user.is_superuser or request.user.username == 'sbo_admin':
            form = AddEventForm()
        else:
            # For SBO, hide college field (handled in form or template)
            form = AddEventForm()
        return render(request, 'add_event.html', {'form': form})
        print(f"DEBUG: add_event called. User authenticated: {request.user.is_authenticated}, Username: {request.user.username}, Superuser: {request.user.is_superuser}")
        if request.method == 'POST':
            print("DEBUG: POST request received.")
            form = AddEventForm(request.POST)
            if form.is_valid():
                print("DEBUG: Form is valid.")
                name = form.cleaned_data['event_name']
                date = form.cleaned_data['event_date']
                if request.user.is_superuser or request.user.username == 'sbo_admin':
                    print("DEBUG: User is admin. Using college from form.")
                    college = form.cleaned_data['college']
                else:
                    print("DEBUG: User is SBO. Getting assigned college.")
                    try:
                        college = request.user.sboprofile.college
                        print(f"DEBUG: SBO assigned college: {college}")
                    except Exception as e:
                        print(f"DEBUG: Error getting SBO college: {e}")
                        college = None
                Event.objects.create(name=name, date=date, college=college)
                messages.success(request, "Event created successfully!")
            else:
                print("DEBUG: Form is invalid.")
                messages.error(request, "Please provide all required fields.")
        # Redirect to dashboard for admin, or index for SBO
        if request.user.is_superuser or request.user.username == 'sbo_admin':
            print("DEBUG: Redirecting to dashboard.")
            return redirect('dashboard')
        else:
            print("DEBUG: Redirecting to index.")
            return redirect('index')

@login_required
def remove_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event removed successfully!")
        return redirect('event_list')
    return render(request, 'remove_event_confirm.html', {'event': event})

@login_required
def event_list(request):
    if request.user.is_superuser or request.user.username == 'sbo_admin':
        events = Event.objects.filter(archived=False)
        events_archived = Event.objects.filter(archived=True)
    else:
        college_code = request.user.username.replace('sbo_', '').upper()
        user_college = College.objects.filter(name__iexact=college_code).first()
        events = Event.objects.filter(
            Q(college=user_college) | Q(college__isnull=True),
            archived=False
        )
        events_archived = []
    return render(request, 'event_list.html', {
        'events': events,
        'events_archived': events_archived,
    })

@login_required
def add_event(request):
    # Accept description and college from POST and create event safely
    if request.method == 'POST':
        name = request.POST.get('event_name')
        date = request.POST.get('event_date')
        description = request.POST.get('description', '').strip() or None

        # Determine college if provided (handles both admin form and SBO hidden input)
        college = None
        college_id = request.POST.get('college')
        if college_id:
            try:
                college = College.objects.get(id=college_id)
            except (College.DoesNotExist, ValueError, TypeError):
                college = None

        create_kwargs = {'name': name, 'date': date}

        # Attach college if Event model supports it
        try:
            Event._meta.get_field('college')
            create_kwargs['college'] = college
        except FieldDoesNotExist:
            pass

        # Attach description if Event model supports it and a description was provided
        try:
            Event._meta.get_field('description')
            if description:
                create_kwargs['description'] = description
        except FieldDoesNotExist:
            pass

        event = Event.objects.create(**create_kwargs)
        # ensure description persisted
        if description:
            try:
                Event._meta.get_field('description')
                event.description = description
                event.save(update_fields=['description'])
            except FieldDoesNotExist:
                pass
        messages.success(request, "Event added successfully!")
    return redirect('dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_event(request, event_id):
    event = Event.objects.get(id=event_id)
    if request.method == 'POST':
        event.name = request.POST.get('name')
        event_date_str = request.POST.get('date')
        if event_date_str:
            event.date = datetime.datetime.strptime(event_date_str, "%Y-%m-%dT%H:%M")
        # Only update description if the field exists, and do NOT use update_fields if not present
        try:
            Event._meta.get_field('description')
            event.description = request.POST.get('description', '')
            event.save()  # Don't use update_fields, let Django handle fields
        except FieldDoesNotExist:
            event.save(update_fields=['name', 'date'])
        messages.success(request, "Event updated successfully.")
        return redirect('events_list')
    return render(request, 'edit_event.html', {'event': event})

def manual_sign(request):
    events = Event.objects.all()
    selected_event_id = None
    selected_action = 'sign_in'
    barcode_id = ''

    if request.method == 'POST':
        selected_event_id = request.POST.get('event_id')
        barcode_id = request.POST.get('barcode_id')
        selected_action = request.POST.get('action')

        event = get_object_or_404(Event, id=selected_event_id) if selected_event_id else None
        attendee = None
        if barcode_id:
            try:
                attendee = Attendee.objects.get(barcode_id=barcode_id)
            except Attendee.DoesNotExist:
                messages.error(request, "ID is not registered.")
                attendee = None

        if event and attendee:
            attendance, created = Attendance.objects.get_or_create(
                attendee=attendee,
                event=event,
            )
            if selected_action == 'sign_in':
                if not attendance.sign_in_time:
                    attendance.sign_in_time = timezone.now()
                    attendance.save()
            elif selected_action == 'sign_out':
                if not attendance.sign_out_time:
                    attendance.sign_out_time = timezone.now()
                    attendance.save()
        # Clear barcode_id after processing so you can scan the next one
        barcode_id = ''

    return render(request, 'manual_sign.html', {
        'events': events,
        'selected_event_id': selected_event_id,
        'selected_action': selected_action,
        'barcode_id': barcode_id,
    })
    
def attendance_sheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendances = Attendance.objects.filter(event=event)
    is_sbo_admin = (
    request.user.is_superuser or
    request.user.groups.filter(name__in=['sbo_admin', 'sbo_ccs']).exists()
    )
    return render(request, 'attendance_sheet.html', {
        'event': event,
        'attendances': attendances,
        'is_sbo_admin': is_sbo_admin,
    })

def is_sbo_admin(user):
    return (
        user.is_superuser or
        user.groups.filter(name__in=['sbo_admin', 'sbo_ccs']).exists()
    )

@user_passes_test(is_sbo_admin)
def edit_attendance(request, attendance_id):
    # Implement the function body or add a pass statement to avoid syntax errors
    pass


def delete_attendance(request, attendance_id):
    attendance = get_object_or_404(Attendance, id=attendance_id)
    event_id = attendance.event.id
    if request.method == 'POST':
        attendance.delete()
        return redirect('attendance_sheet', event_id=event_id)
    # Always return a response for GET
    return render(request, 'confirm_delete_attendance.html', {'attendance': attendance})

@user_passes_test(is_sbo_admin)
def edit_attendance(request, attendance_id):
    attendance = get_object_or_404(Attendance, id=attendance_id)
    if request.method == 'POST':
        sign_in_time = request.POST.get('sign_in_time')
        sign_out_time = request.POST.get('sign_out_time')
        if sign_in_time:
            attendance.sign_in_time = sign_in_time
        if sign_out_time:
            attendance.sign_out_time = sign_out_time
        attendance.save()
        return redirect('attendance_sheet', event_id=attendance.event.id)
    # Always return a response for GET or any non-POST
    return render(request, 'edit_attendance.html', {'attendance': attendance})

def add_college(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            College.objects.create(name=name)
            return redirect('dashboard')  # or wherever you want to go after adding
    return render(request, 'add_college.html')

def barcode_scanner(request):
    if request.user.is_superuser or request.user.username == 'sbo_admin':
        events = Event.objects.all()
    else:
        try:
            user_college = request.user.sboprofile.college
            events = Event.objects.filter(
                Q(college=user_college) | Q(college__isnull=True)
            )
        except Exception:
            events = Event.objects.filter(college__isnull=True)
    success_message = None
    error_message = None
    selected_event_id = None
    barcode_id = ''
    action = 'sign_in'

    if request.method == 'POST':
        selected_event_id = request.POST.get('event_id')
        barcode_id = request.POST.get('barcode_id', '')
        action = request.POST.get('action', 'sign_in_am')
        event = get_object_or_404(Event, id=selected_event_id) if selected_event_id else None
        try:
            attendee = Attendee.objects.get(barcode_id=barcode_id)
            # Restrict SBO users to only scan students from their own college
            if not (request.user.is_superuser or request.user.username == 'sbo_admin'):
                try:
                    user_college = request.user.sboprofile.college
                except Exception:
                    user_college = None
                if attendee.college != user_college:
                    error_message = "You can only scan students from your assigned college."
                    barcode_id = ''
                    return render(request, 'barcode_scanner.html', {
                        'events': events,
                        'success_message': success_message,
                        'error_message': error_message,
                        'selected_event_id': selected_event_id,
                        'barcode_id': barcode_id,
                        'action': action
                    })
            # Check if event has a college restriction
            if event and event.college and attendee.college != event.college:
                error_message = "Student doesn't belong to this college."
            else:
                attendance, created = Attendance.objects.get_or_create(attendee=attendee, event=event)
                now = timezone.now()
                if action == 'sign_in_am':
                    if attendance.sign_in_am:
                        error_message = "ID has already been signed in (AM)."
                    else:
                        attendance.sign_in_am = now
                        success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed in (AM) to the event {event.name}"
                        attendance.save()
                elif action == 'sign_out_am':
                    if attendance.sign_out_am:
                        error_message = "ID has already been signed out (AM)."
                    else:
                        attendance.sign_out_am = now
                        success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed out (AM) of the event {event.name}"
                        attendance.save()
                elif action == 'sign_in_pm':
                    if attendance.sign_in_pm:
                        error_message = "ID has already been signed in (PM)."
                    else:
                        attendance.sign_in_pm = now
                        success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed in (PM) to the event {event.name}"
                        attendance.save()
                elif action == 'sign_out_pm':
                    if attendance.sign_out_pm:
                        error_message = "ID has already been signed out (PM)."
                    else:
                        attendance.sign_out_pm = now
                        success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed out (PM) of the event {event.name}"
                        attendance.save()
        except Attendee.DoesNotExist:
            error_message = "ID is not registered."
        barcode_id = ''

    # After processing POST, build a flat list of attendance actions
    from django.db.models.functions import Greatest
    attendance_qs = Attendance.objects.select_related('attendee', 'event').filter(
        Q(sign_in_am__isnull=False) | Q(sign_out_am__isnull=False) | Q(sign_in_pm__isnull=False) | Q(sign_out_pm__isnull=False)
    )

    recent_logs = []
    for att in attendance_qs:
        if att.sign_in_am:
            recent_logs.append({
                'attendee': att.attendee,
                'event': att.event,
                'action': 'In AM',
                'timestamp': att.sign_in_am,
            })
        if att.sign_out_am:
            recent_logs.append({
                'attendee': att.attendee,
                'event': att.event,
                'action': 'Out AM',
                'timestamp': att.sign_out_am,
            })
        if att.sign_in_pm:
            recent_logs.append({
                'attendee': att.attendee,
                'event': att.event,
                'action': 'In PM',
                'timestamp': att.sign_in_pm,
            })
        if att.sign_out_pm:
            recent_logs.append({
                'attendee': att.attendee,
                'event': att.event,
                'action': 'Out PM',
                'timestamp': att.sign_out_pm,
            })

    # Sort all logs by timestamp descending and take the top 10
    recent_logs = sorted(recent_logs, key=lambda x: x['timestamp'], reverse=True)[:10]

    return render(request, 'barcode_scanner.html', {
        'events': events,
        'success_message': success_message,
        'error_message': error_message,
        'selected_event_id': selected_event_id,
        'barcode_id': barcode_id,
        'action': action,
        'recent_attendance': recent_logs,
    })

def view_attendance_sheet(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'event')

    # base events queryset (preserve existing college restrictions)
    if user.is_superuser or user.username == 'sbo_admin':
        events = Event.objects.all().order_by('-date')
    else:
        try:
            college = user.sboprofile.college
            events = Event.objects.filter(
                Q(college=college) | Q(college__isnull=True),
                archived=False  # <-- Only show non-archived events
            ).order_by('-date')
        except Exception:
            events = Event.objects.filter(college__isnull=True, archived=False).order_by('-date')

    # apply search/filter if query present
    if query:
        if search_type == 'event':
            events = events.filter(name__icontains=query)
        elif search_type == 'student':
            # find event ids that have matching attendees, then restrict to user's allowed events
            event_ids = Attendance.objects.filter(
                Q(attendee__barcode_id__icontains=query) | Q(attendee__name__icontains=query)
            ).values_list('event_id', flat=True)
            events = events.filter(id__in=event_ids)

    return render(request, 'view_attendance_sheet.html', {
        'events': events,
        'query': query,
        'search_type': search_type,
    })

def print_attendance_sheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendances = Attendance.objects.filter(event=event)
    # Render a minimal template for printing
    return render(request, 'print_attendance_sheet.html', {
        'event': event,
        'attendances': attendances,
    })

def view_attendance_sheet_event(request, event_id):
    """
    Restore function expected by attendance/urls.py.
    Renders the attendance_sheet for a specific event.
    """
    event = get_object_or_404(Event, id=event_id)
    attendances = Attendance.objects.filter(event=event)
    return render(request, 'attendance_sheet.html', {
        'event': event,
        'attendances': attendances,
        'is_sbo_admin': False,  # Colleges are not SBO admins
    })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.username == 'sbo_admin')
def delete_event(request, event_id):
    """
    Remove event endpoint expected by attendance/urls.py.
    Only accessible to superusers or the 'sbo_admin' account.
    """
    Event.objects.filter(id=event_id).delete()
    messages.success(request, "Event deleted successfully!")
    return redirect('events_list')

@login_required
def sign_in_manual(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        name = request.POST.get('name')
        event = get_object_or_404(Event, id=event_id)
        attendee, created = Attendee.objects.get_or_create(
            barcode_id=name,
            defaults={'name': name}
        )
        attendance, created = Attendance.objects.get_or_create(
            attendee=attendee,
            event=event,
            defaults={'sign_in_time': timezone.now()}
        )
        if not attendance.sign_in_time:
            attendance.sign_in_time = timezone.now()
            attendance.save()
        messages.success(request, f"{attendee.name} signed in successfully!")
        return redirect('index')
    return redirect('index')

@login_required
def sign_out_manual(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        name = request.POST.get('name')
        event = get_object_or_404(Event, id=event_id)
        try:
            attendee = Attendee.objects.get(name=name)
            attendance = Attendance.objects.get(attendee=attendee, event=event)
            if not attendance.sign_out_time:
                attendance.sign_out_time = timezone.now()
                attendance.save()
                messages.success(request, f"{attendee.name} signed out successfully!")
            else:
                messages.error(request, f"{attendee.name} already signed out!")
        except (Attendee.DoesNotExist, Attendance.DoesNotExist):
            messages.error(request, "Attendee or attendance record not found!")
        return redirect('index')
    return redirect('index')

@login_required
def scan_barcode(request):
    """
    Handles barcode scanning for events.
    """
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        barcode_id = request.POST.get('barcode_id', '').strip()
        action = request.POST.get('action', 'sign_in')

        # Validate event
        try:
            event = Event.objects.get(id=event_id)
        except (Event.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Event not found.")
            return redirect('index')

        # Validate barcode
        if not barcode_id:
            messages.error(request, "No barcode provided.")
            return redirect('index')

        # Find attendee
        try:
            attendee = Attendee.objects.get(barcode_id=barcode_id)
        except Attendee.DoesNotExist:
            messages.error(request, "Attendee not found!")
            return redirect('index')

        # Handle attendance
        attendance, created = Attendance.objects.get_or_create(
            attendee=attendee,
            event=event,
            defaults={'sign_in_time': timezone.now() if action == 'sign_in' else None}
        )

        now = timezone.now()
        if action == 'sign_in':
            if attendance.sign_in_time:
                messages.error(request, f"{attendee.name} already signed in.")
            else:
                attendance.sign_in_time = now
                attendance.save()
                messages.success(request, f"{attendee.name} signed in successfully!")
        elif action == 'sign_out':
            if attendance.sign_out_time:
                messages.error(request, f"{attendee.name} already signed out.")
            else:
                attendance.sign_out_time = now
                attendance.save()
                messages.success(request, f"{attendee.name} signed out successfully!")
        else:
            messages.error(request, "Unknown action.")
        return redirect('index')

    # For non-POST requests, redirect to index
    return redirect('index')

@login_required
def students_list(request):
    """
    View to list all students with optional filtering by query or college.
    """
    query = request.GET.get('q', '').strip()
    selected_college = request.GET.get('college', '')
    colleges = College.objects.all()
    students = Attendee.objects.all()

    # Filter by college if selected
    if selected_college:
        students = students.filter(college__id=selected_college)

    # Filter by query (search by barcode or name)
    if query:
        students = students.filter(
            Q(barcode_id__icontains=query) | Q(name__icontains=query)
        )

    return render(request, 'students_list.html', {
        'students': students,
        'colleges': colleges,
        'selected_college': selected_college,
    })

@login_required
def events_list(request):
    """
    View to list all events with optional filtering by query or college.
    """
    query = request.GET.get('q', '')
    selected_college = request.GET.get('college', '')
    colleges = College.objects.all()
    events = Event.objects.filter(archived=False)  # <-- Only show non-archived events

    # Filter by college if selected
    if selected_college:
        events = events.filter(college__id=selected_college)

    # Filter by query (search by event name)
    if query:
        events = events.filter(name__icontains=query)

    return render(request, 'events_list.html', {
        'events': events,
        'colleges': colleges,
        'selected_college': selected_college,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def sbo_users_list(request):
    """
    View to list all SBO users (non-superuser, non-staff).
    """
    UserModel = get_user_model()
    sbo_users = UserModel.objects.filter(is_superuser=False, is_staff=False)
    return render(request, 'sbo_users_list.html', {'sbo_users': sbo_users})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_sbo_user(request):
    """
    View to add a new SBO user and assign to a college.
    """
    if request.method == 'POST':
        form = AddSBOUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            college = form.cleaned_data['college']
            UserModel = get_user_model()
            if UserModel.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            else:
                user = UserModel.objects.create_user(username=username, password=password)
                user.is_staff = False
                user.is_superuser = False
                user.save()
                SBOProfile.objects.create(user=user, college=college)
                messages.success(request, "SBO user added and assigned to college successfully.")
        else:
            messages.error(request, "Invalid form submission.")
    return redirect('dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_sbo_user(request, user_id):
    """
    View to edit an existing SBO user's username and password.
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(id=user_id, is_superuser=False, is_staff=False)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and username != user.username:
            if UserModel.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect('edit_sbo_user', user_id=user.id)
            user.username = username
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, "SBO user updated successfully.")
        return redirect('sbo_users_list')
    return render(request, 'edit_sbo_user.html', {'edit_user': user})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_sbo_user(request, user_id):
    """
    View to delete an SBO user (non-superuser, non-staff).
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(id=user_id, is_superuser=False, is_staff=False)
    user.delete()
    messages.success(request, "SBO user deleted successfully.")
    return redirect('sbo_users_list')

@login_required
@user_passes_test(lambda u: u.username == 'sbo_admin')
def add_student(request):
    if request.method == 'POST':
        barcode_id = request.POST.get('barcode_id')
        name = request.POST.get('student_name')
        college_id = request.POST.get('college')
        college = College.objects.get(id=college_id) if college_id else None
        if Attendee.objects.filter(barcode_id=barcode_id, name=name):
            messages.error(request, "That student is already registered.")
        else:
            try:
                Attendee.objects.create(barcode_id=barcode_id, name=name, college=college)
                messages.success(request, "Student added successfully!")
            except IntegrityError:
                messages.error(request, "That student is already registered.")
    return redirect('dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_student(request, student_id):
    student = Attendee.objects.get(id=student_id)
    colleges = College.objects.all()
    if request.method == 'POST':
        barcode_id = request.POST.get('barcode_id')
        student_name = request.POST.get('student_name')
        college_id = request.POST.get('college')
        if barcode_id and student_name and college_id:
            student.barcode_id = barcode_id
            student.name = student_name
            student.college_id = college_id
            student.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('students_list')
    return render(request, 'edit_student.html', {'student': student, 'colleges': colleges})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_student(request, student_id):
    student = get_object_or_404(Attendee, id=student_id)
    student.delete()
    messages.success(request, "Student deleted successfully.")
    return redirect('students_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def archive_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.archived = True
    event.save(update_fields=['archived'])
    messages.success(request, "Event archived successfully.")
    return redirect('events_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def unarchive_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.archived = False
    event.save(update_fields=['archived'])
    messages.success(request, "Event unarchived successfully.")
    # Stay on archived events page if coming from there
    referer = request.META.get('HTTP_REFERER', '')
    if 'archived_events' in referer:
        return redirect('archived_events_list')
    return redirect('events_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def archived_events_list(request):
    query = request.GET.get('q', '')
    selected_college = request.GET.get('college', '')
    colleges = College.objects.all()
    events_archived = Event.objects.filter(archived=True)

    if selected_college:
        events_archived = events_archived.filter(college__id=selected_college)
    if query:
        events_archived = events_archived.filter(name__icontains=query)

    return render(request, 'archived_events_list.html', {
        'events_archived': events_archived,
        'colleges': colleges,
        'selected_college': selected_college,
    })

@login_required
def student_attendance_detail(request, student_id):
    """
    View to show all attendance records for a specific student.
    """
    student = get_object_or_404(Attendee, id=student_id)
    attendances = Attendance.objects.filter(attendee=student).select_related('event').order_by('-event__date')
    return render(request, 'student_attendance_detail.html', {
        'student': student,
        'attendances': attendances,
    })

@login_required
def print_student_attendance_pdf(request, student_id):
    """
    Generate a PDF of all attendance records for a specific student.
    """
    student = get_object_or_404(Attendee, id=student_id)
    attendances = Attendance.objects.filter(attendee=student).select_related('event').order_by('-event__date')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Attendance Report for {student.name} ({student.barcode_id})")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 70, f"College: {student.college.name if student.college else '-'}")

    # Table headers
    y = height - 100
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Event")
    p.drawString(200, y, "Date")
    p.drawString(300, y, "In AM")
    p.drawString(360, y, "Out AM")
    p.drawString(430, y, "In PM")
    p.drawString(490, y, "Out PM")
    y -= 18
    p.setFont("Helvetica", 10)

    for att in attendances:
        if y < 60:
            p.showPage()
            y = height - 50
        p.drawString(50, y, att.event.name)
        p.drawString(200, y, att.event.date.strftime("%Y-%m-%d %H:%M") if att.event.date else "-")
        p.drawString(300, y, att.sign_in_am.strftime("%H:%M") if att.sign_in_am else "-")
        p.drawString(360, y, att.sign_out_am.strftime("%H:%M") if att.sign_out_am else "-")
        p.drawString(430, y, att.sign_in_pm.strftime("%H:%M") if att.sign_in_pm else "-")
        p.drawString(490, y, att.sign_out_pm.strftime("%H:%M") if att.sign_out_pm else "-")
        y -= 16

    p.showPage()
    p.save()
    buffer.seek(0)
    filename = f"{student.name}_attendance.pdf".replace(" ", "_")
    # Open in browser, not as download
    return FileResponse(buffer, as_attachment=False, filename=filename)




