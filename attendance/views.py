from asyncio import events
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse

import attendance
from .models import Event, Attendee, Attendance, College, SBOProfile
from .forms import AddSBOUserForm
from .forms_event import AddEventForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.db.models import Q, Max, F, Value, DateTimeField
from django.db.models.functions import Greatest
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
import datetime

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

    # >>>> MOVE THIS BLOCK AFTER POST <<<<
    recent_attendance = Attendance.objects.annotate(
        latest_time=Greatest(
            F('sign_in_time'),
            F('sign_out_time'),
            output_field=DateTimeField()
        )
    ).filter(
        Q(sign_in_time__isnull=False) | Q(sign_out_time__isnull=False)
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
            Event.objects.create(name=name, date=date, college=college)
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
        events = Event.objects.all()
    else:
        college_code = request.user.username.replace('sbo_', '').upper()
        user_college = College.objects.filter(name__iexact=college_code).first()
        events = Event.objects.filter(
            Q(college=user_college) | Q(college__isnull=True)
        )
    return render(request, 'event_list.html', {'events': events})

@login_required
def add_event(request):
    if request.method == 'POST':
        name = request.POST.get('event_name')
        date = request.POST.get('event_date')
        Event.objects.create(name=name, date=date)
        messages.success(request, "Event added successfully!")
    return redirect('dashboard')

@login_required
@user_passes_test(lambda u: u.username == 'sbo_admin')
def delete_event(request, event_id):
    Event.objects.filter(id=event_id).delete()
    messages.success(request, "Event deleted successfully!")
    return redirect('events_list')

@login_required
@user_passes_test(lambda u: u.username == 'sbo_admin')
def add_student(request):
    if request.method == 'POST':
        barcode_id = request.POST.get('barcode_id')
        name = request.POST.get('student_name')
        if Attendee.objects.filter(barcode_id=barcode_id, name=name):
            messages.error(request, "That student is already registered.")
        else:
            try:
                Attendee.objects.create(barcode_id=barcode_id, name=name)
                messages.success(request, "Student added successfully!")
            except IntegrityError:
                messages.error(request, "That student is already registered.")
    return redirect('dashboard')

@login_required
@user_passes_test(lambda u: u.username == 'sbo_admin')
def delete_student(request, student_id):
    Attendee.objects.filter(id=student_id).delete()
    messages.success(request, "Student deleted successfully!")
    return redirect('students_list')

@login_required
def sign_in_manual(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        name = request.POST.get('name')
        event = Event.objects.get(id=event_id)
        attendee, created = Attendee.objects.get_or_create(
            barcode_id=name,
            defaults={'name': name}
        )
        attendance, created = Attendance.objects.get_or_create(
            attendee=attendee,
            event=event,
            defaults={'sign_in_time': timezone.now()}
        )
        if not created and not attendance.sign_in_time:
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
        event = Event.objects.get(id=event_id)
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
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        barcode_id = request.POST.get('barcode_id')
        action = request.POST.get('action')
        event = Event.objects.get(id=event_id)
        try:
            attendee = Attendee.objects.get(barcode_id=barcode_id)
            attendance, created = Attendance.objects.get_or_create(
                attendee=attendee,
                event=event,
                defaults={'sign_in_time': timezone.now() if action == 'sign_in' else None}
            )
            if action == 'sign_in' and not attendance.sign_in_time:
                attendance.sign_in_time = timezone.now()
                attendance.save()
                messages.success(request, f"{attendee.name} signed in successfully!")
            elif action == 'sign_out' and not attendance.sign_out_time:
                attendance.sign_out_time = timezone.now()
                attendance.save()
                messages.success(request, f"{attendee.name} signed out successfully!")
            else:
                messages.error(request, f"{attendee.name} already processed for this action!")
        except Attendee.DoesNotExist:
            messages.error(request, "Attendee not found!")
        return redirect('index')
    return redirect('index')


@login_required
def students_list(request):
    query = request.GET.get('q', '')
    if query:
        students = Attendee.objects.filter(
            Q(barcode_id__icontains=query) | Q(name__icontains=query)
        )
    else:
        students = Attendee.objects.all()
    return render(request, 'students_list.html', {'students': students})

@login_required
def events_list(request):
    query = request.GET.get('q', '')
    if query:
        events = Event.objects.filter(name__icontains=query)
    else:
        events = Event.objects.all()
    return render(request, 'events_list.html', {'events': events})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def sbo_users_list(request):
    sbo_users = User.objects.filter(is_superuser=False, is_staff=False)
    return render(request, 'sbo_users_list.html', {'sbo_users': sbo_users})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_sbo_user(request):
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
    User = get_user_model()
    user = User.objects.get(id=user_id, is_superuser=False, is_staff=False)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and username != user.username:
            if User.objects.filter(username=username).exists():
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
    User = get_user_model()
    user = User.objects.get(id=user_id, is_superuser=False, is_staff=False)
    user.delete()
    messages.success(request, "SBO user deleted successfully.")
    return redirect('sbo_users_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_student(request, student_id):
    student = Attendee.objects.get(id=student_id)
    if request.method == 'POST':
        student.barcode_id = request.POST.get('barcode_id')
        student.name = request.POST.get('student_name')
        student.save()
        messages.success(request, "Student updated successfully.")
        return redirect('students_list')

    return render(request, 'edit_student.html', {'student': student})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_event(request, event_id):
    event = Event.objects.get(id=event_id)
    if request.method == 'POST':
        event.name = request.POST.get('name')
        event_date_str = request.POST.get('date')
        if event_date_str:
            event.date = datetime.datetime.strptime(event_date_str, "%Y-%m-%dT%H:%M")
        event.save()
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

    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        barcode_id = request.POST.get('barcode_id')
        action = request.POST.get('action')
        event = get_object_or_404(Event, id=event_id)
        attendee = get_object_or_404(Attendee, barcode_id=barcode_id)
        attendance, created = Attendance.objects.get_or_create(attendee=attendee, event=event)
        if action == 'sign_in':
            attendance.sign_in_time = timezone.now()
            success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed in to the event {event.name}"
        elif action == 'sign_out':
            attendance.sign_out_time = timezone.now()
            success_message = f"{attendee.barcode_id} {attendee.name} has successfully signed out of the event {event.name}"
        attendance.save()

    return render(request, 'barcode_scanner.html', {
        'events': events,
        'success_message': success_message
    })

def view_attendance_sheet(request):
    user = request.user
    events = []
    if user.is_superuser or user.username == 'sbo_admin':
        events = Event.objects.all().order_by('-date')
    else:
        try:
            college = user.sboprofile.college
            events = Event.objects.filter(
                Q(college=college) | Q(college__isnull=True)
            ).order_by('-date')
        except Exception:
            events = Event.objects.filter(college__isnull=True).order_by('-date')
    return render(request, 'view_attendance_sheet.html', {'events': events})

def view_attendance_sheet_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendances = Attendance.objects.filter(event=event)
    return render(request, 'attendance_sheet.html', {
        'event': event,
        'attendances': attendances,
        'is_sbo_admin': False,  # Colleges are not SBO admins
    })




