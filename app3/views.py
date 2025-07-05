# app/views.py

from django.shortcuts import get_object_or_404, render, redirect
from app1.models import Employee
from .models import SalaryCertificate
from django.http import JsonResponse,HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

# views.py
from django.shortcuts import render
from .models import SalaryCertificate

from django.core.paginator import Paginator
from django.shortcuts import render
from .models import SalaryCertificate

from django.shortcuts import render
from .models import SalaryCertificate

from django.core.paginator import Paginator
from django.shortcuts import render
from .models import SalaryCertificate

def make_salary_certificate(request):
    # Get the search query from the request
    search_query = request.GET.get('search', '').strip()

    # Fetch all certificates with related data
    certificates = SalaryCertificate.objects.select_related('employee', 'added_by', 'approved_by').order_by('-id')

    # Filter certificates based on the search query
    if search_query:
        certificates = certificates.filter(employee__name__icontains=search_query)

    # Set up pagination
    paginator = Paginator(certificates, 10)  # Show 10 rows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate the starting SI NO for the current page
    start_index = (page_obj.number - 1) * paginator.per_page + 1

    # Add pagination info to page_obj
    page_obj.start_index = start_index
    page_obj.end_index = min(start_index + paginator.per_page - 1, paginator.count)

    return render(request, 'make_salary_certificate.html', {
        'employees': page_obj,
        'search_query': search_query,
        'start_index': start_index,
        'is_first_page': page_obj.number == 1
    })
# views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from app1.models import Employee

def add_salary_certificate(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_name')
        address = request.POST.get('address')
        joining_date = request.POST.get('joining_date')
        job_title = request.POST.get('job_title')
        salary = request.POST.get('salary')

        if not employee_id or not salary:
            return JsonResponse({'success': False, 'message': 'Employee and salary are required'})

        try:
            employee = get_object_or_404(Employee, id=employee_id)
            salary_certificate = SalaryCertificate(
                employee=employee,
                address=address,
                joining_date=joining_date,
                job_title=job_title,
                salary=salary,
                added_by=request.user  # Set the user who added the certificate
            )
            salary_certificate.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    else:
        employees = Employee.objects.all()
        return render(request, 'add_salary_certificate.html', {'employees': employees})
    
# views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from app1.models import Employee
from .models import SalaryCertificate

def save_salary_certificate(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_name')
        address = request.POST.get('address')
        joining_date = request.POST.get('joining_date')
        job_title = request.POST.get('job_title')
        salary = request.POST.get('salary')

        if not employee_id or not salary:
            return JsonResponse({'success': False, 'message': 'Employee and salary are required'})

        try:
            employee = get_object_or_404(Employee, id=employee_id)
            salary_certificate = SalaryCertificate(
                employee=employee,
                address=address,
                joining_date=joining_date,
                job_title=job_title,
                salary=salary,
                added_by=request.user  # Set the user who added the certificate
            )
            salary_certificate.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def get_employee_details(request):
    emp_id = request.GET.get('id')
    employee = get_object_or_404(Employee, id=emp_id)
    data = {
        'address': employee.address,
        'joining_date': employee.joining_date.strftime('%Y-%m-%d'),
        'job_title': employee.job_title,
    }
    return JsonResponse(data)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import SalaryCertificate

def delete_salary_certificate(request, salary_certificate_id):
    if request.method == 'POST':
        try:
            salary_certificate = get_object_or_404(SalaryCertificate, id=salary_certificate_id)
            salary_certificate.delete()
            messages.success(request, 'Salary certificate deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting certificate: {e}')
    else:
        messages.error(request, 'Invalid request method.')

    return redirect('make_salary_certificate')  # Change to your actual list page name


# app3/views.py

# app3/views.py

from django.shortcuts import get_object_or_404, render, redirect
from .models import SalaryCertificate
from app1.models import Employee  # Import Employee model from app1

def edit_salary_certificate(request, salary_certificate_id):
    salary_certificate = get_object_or_404(SalaryCertificate, id=salary_certificate_id)
    employees = Employee.objects.all()  # Fetch all employees for the dropdown

    if request.method == 'POST':
        employee_id = request.POST.get('employee_name')
        salary = request.POST.get('salary')

        if employee_id and salary:
            try:
                employee = get_object_or_404(Employee, id=employee_id)
                salary_certificate.employee = employee
                salary_certificate.salary = salary
                salary_certificate.save()
                return redirect('make_salary_certificate')
            except Exception as e:
                return render(request, 'edit_salary_certificate.html', {
                    'salary_certificate': salary_certificate,
                    'employees': employees,
                    'error': str(e)
                })
        else:
            return render(request, 'edit_salary_certificate.html', {
                'salary_certificate': salary_certificate,
                'employees': employees,
                'error': 'Employee and salary are required'
            })
    else:
        return render(request, 'edit_salary_certificate.html', {
            'salary_certificate': salary_certificate,
            'employees': employees
        })


# app3/views.py
from django.shortcuts import render, get_object_or_404
from app1.models import Employee
from .models import SalaryCertificate
from num2words import num2words
from datetime import date
from django.shortcuts import render, get_object_or_404
from app1.models import Employee
from .models import SalaryCertificate
from num2words import num2words
from datetime import date

def view_salary_certificate(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    salary_certificates = SalaryCertificate.objects.filter(employee=employee)

    if not salary_certificates.exists():
        return render(request, 'view_salary_certificate.html', {
            'error': 'No salary certificate found for this employee.'
        })

    # If multiple certificates exist, choose the most recent one
    salary_details = salary_certificates.latest('id')

    # Convert salary to words
    salary_number = int(salary_details.salary)
    salary_words = num2words(salary_number, lang='en_IN').capitalize()
    salary_words += " Rupees"

    # Get date from URL or default to today's date
    certificate_date = request.GET.get('date') or date.today().strftime('%d-%m-%Y')

    context = {
        'employee': employee,
        'salary_details': salary_details,
        'salary_words': salary_words,
        'certificate_date': certificate_date,
    }
    return render(request, 'view_salary_certificate.html', context)

from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def approve_salary_certificate(request, certificate_id):
    certificate = get_object_or_404(SalaryCertificate, id=certificate_id)
    certificate.is_approved = True
    certificate.approved_by = request.user  # Set the user who approved the certificate
    certificate.approved_on = timezone.now()  # Set the approval timestamp
    certificate.save()
    return redirect('make_salary_certificate')





from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator



from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Interview  # Adjust if needed

@login_required
def interview_management(request):
    search_query = request.GET.get('q', '').strip()

    if search_query:
        interviews = Interview.objects.filter(name__icontains=search_query)
    else:
        interviews = Interview.objects.all()

    interviews = interviews.order_by('-created_date')  # or '-id'

    paginator = Paginator(interviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'interview_management.html', {
        'interviews': page_obj,
        'search_query': search_query
    })


from django.shortcuts import render, redirect
from app1.models import CV
from app1.models import Employee  # Assuming name is stored in Employee model
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from app1.models import CV
from .models import Interview

@login_required
def add_interview(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        cv = CV.objects.get(id=employee_id)
        
        # Create a new Interview instance
        interview = Interview.objects.create(
            name=cv.name,
            job_title=cv.job_title.title,
            cv_attachment=cv.cv_attachment,
            place=cv.place,
            created_user=request.user,
            gender=cv.gender,
            address=cv.address,
            district=cv.district,
            phone_number=cv.phone_number,
            education=cv.education,
            experience=cv.experience,
            dob=cv.dob,
            remarks=cv.remarks,
            cv_source=cv.agent.name if cv.agent else 'DIRECT'
        )
        
        return redirect('interview_management')  # Redirect to the interview management page

    employees = CV.objects.all().order_by('name')  # ensure alphabetical order
    return render(request, 'add_interview_management.html', {'employees': employees})


from django.shortcuts import get_object_or_404, redirect
from .models import Interview  # adjust model name if different

def delete_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if request.method == 'POST':
        interview.delete()
        return redirect('interview_management')  # change this to your list view name

from app1.models import CV  # instead of Employee

def edit_interview_management(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    candidates = CV.objects.all()

    if request.method == 'POST':
        candidate_id = request.POST.get('employee_id')
        if candidate_id:
            cv = get_object_or_404(CV, id=candidate_id)

            interview.name = cv.name
            interview.job_title = cv.job_title.title
            interview.cv_attachment = cv.cv_attachment
            interview.place = cv.place
            interview.gender = cv.gender
            interview.address = cv.address
            interview.district = cv.district
            interview.phone_number = cv.phone_number
            interview.education = cv.education
            interview.experience = cv.experience
            interview.dob = cv.dob
            interview.remarks = cv.remarks
            interview.cv_source = cv.agent.name if cv.agent else 'DIRECT'

        interview.save()
        return redirect('interview_management')

    return render(request, 'edit_interview_management.html', {
        'interview': interview,
        'candidates': candidates
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import Interview, Rating

from django.shortcuts import get_object_or_404, render, redirect
from .models import Interview, Rating

def add_rating(request, interview_id):
    interview = get_object_or_404(Interview, pk=interview_id)
    fields = ['appearance', 'knowledge', 'confidence', 'attitude', 'communication']
    languages = ['English', 'Malayalam', 'Tamil', 'Hindi']

    # Check if a rating already exists
    existing_rating = Rating.objects.filter(interview=interview).last()

    if request.method == 'POST':
        voice_file = request.FILES.get('voice_note')

        if existing_rating:
            # Update only the fields that are submitted (partial update)
            for field in fields:
                val = request.POST.get(field)
                if val:
                    setattr(existing_rating, field, val)

            selected_languages = request.POST.getlist('languages')
            if selected_languages:
                existing_rating.languages = ','.join(selected_languages)

            if request.POST.get('expected_salary'):
                existing_rating.expected_salary = request.POST.get('expected_salary')
            if request.POST.get('experience'):
                existing_rating.experience = request.POST.get('experience')
            if request.POST.get('remark'):
                existing_rating.remark = request.POST.get('remark')
            if voice_file:
                existing_rating.voice_note = voice_file

            existing_rating.save()

        else:
            # New rating submission
            Rating.objects.create(
                interview=interview,
                appearance=request.POST.get('appearance'),
                knowledge=request.POST.get('knowledge'),
                confidence=request.POST.get('confidence'),
                attitude=request.POST.get('attitude'),
                communication=request.POST.get('communication'),
                languages=','.join(request.POST.getlist('languages')),
                expected_salary=request.POST.get('expected_salary'),
                experience=request.POST.get('experience'),
                remark=request.POST.get('remark'),
                voice_note=voice_file
            )

        return redirect('interview_management')

    return render(request, 'add_rating.html', {
        'interview': interview,
        'fields': fields,
        'languages': languages,
        'existing_rating': existing_rating  # Pass existing data to prefill the form
    })

from django.views.decorators.csrf import csrf_exempt
from .models import Interview, Rating

@csrf_exempt
def update_status(request, interview_id):
    if request.method == "POST":
        status = request.POST.get("status")
        interview = get_object_or_404(Interview, id=interview_id)

        # Get or create a Rating instance (now with proper defaults in model)
        rating, created = Rating.objects.get_or_create(interview=interview)

        if status in ['selected', 'rejected']:
            rating.status = status
            rating.save()

    return redirect('interview_management')



from django.shortcuts import render, get_object_or_404
from .models import Interview, Rating  # adjust import paths as needed

def view_rating(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    rating = Rating.objects.filter(interview_id=pk).order_by('-id').first()  # latest rating

    return render(request, 'view_rating.html', {
        'interview': interview,
        'rating': rating,
    })






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from app3.models import Interview

from django.core.paginator import Paginator

@login_required
def make_offer_letter(request):
    # Get the search query from the request
    search_query = request.GET.get('q', '').strip()

    # Fetch all interviews that have an associated OfferLetter
    interviews_with_offer_letters = Interview.objects.filter(offer_letter__isnull=False)

    # Apply search filter if provided
    if search_query:
        interviews_with_offer_letters = interviews_with_offer_letters.filter(name__icontains=search_query)

    # Order by creation date (most recent first)
    interviews_with_offer_letters = interviews_with_offer_letters.order_by('-created_date')

    # Set up pagination
    paginator = Paginator(interviews_with_offer_letters, 10)  # Show 10 interviews per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Calculate the starting index for the serial number
    start_index = (page_obj.number - 1) * paginator.per_page + 1

    return render(request, 'make_offer_letter.html', {
        'interviews': page_obj, 
        'start_index': start_index,
        'selected_count': interviews_with_offer_letters.count()
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Interview, OfferLetter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Interview, OfferLetter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Interview, OfferLetter
from datetime import datetime
from django.contrib.auth.decorators import login_required

@login_required
def add_offer_letter(request):
    selected_candidates = Interview.objects.filter(
        Q(offer_letter__isnull=True) | Q(offer_letter__is_generated=False)
    ).filter(rating__status='selected').order_by('name')

    if request.method == 'POST':
        interview_id = request.POST.get('employee_id')
        position = request.POST.get('position', '').strip()
        department = request.POST.get('department', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        salary = request.POST.get('salary', '').strip()
        notice_period = request.POST.get('notice_period', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        end_time = request.POST.get('end_time', '').strip()

        # Validate interview ID
        if not interview_id:
            messages.error(request, "Interview ID is required")
            return redirect('add_offer_letter')

        try:
            interview = get_object_or_404(Interview, id=interview_id)
        except Interview.DoesNotExist:
            messages.error(request, "Invalid Interview ID")
            return redirect('add_offer_letter')

        # Validate required fields
        errors = []
        if not position:
            errors.append("Position is required")
        if not department:
            errors.append("Department is required")
        if not start_date:
            errors.append("Start Date is required")
        if not salary:
            errors.append("Salary is required")
        if not notice_period:
            errors.append("Notice Period is required")
        if not start_time or not end_time:
            errors.append("Start time and end time are required")

        if errors:
            messages.error(request, "; ".join(errors))
            return redirect('add_offer_letter')

        # Validate numeric fields
        try:
            salary_decimal = float(salary)
            if salary_decimal <= 0:
                messages.error(request, "Salary must be greater than 0")
                return redirect('add_offer_letter')
        except ValueError:
            messages.error(request, "Invalid salary amount")
            return redirect('add_offer_letter')

        try:
            notice_period_int = int(notice_period)
            if notice_period_int < 0:
                messages.error(request, "Notice period cannot be negative")
                return redirect('add_offer_letter')
        except ValueError:
            messages.error(request, "Invalid notice period")
            return redirect('add_offer_letter')

        # Validate date & time formats
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            messages.error(request, "Invalid date or time format")
            return redirect('add_offer_letter')

        try:
            offer_letter, created = OfferLetter.objects.get_or_create(
                interview=interview,
                defaults={
                    'position': position,
                    'department': department,
                    'start_date': start_date_obj,
                    'salary': salary_decimal,
                    'notice_period': notice_period_int,
                    'start_time': start_time_obj,
                    'end_time': end_time_obj,
                    'is_generated': False
                }
            )

            if not created:
                offer_letter.position = position
                offer_letter.department = department
                offer_letter.start_date = start_date_obj
                offer_letter.salary = salary_decimal
                offer_letter.notice_period = notice_period_int
                offer_letter.start_time = start_time_obj
                offer_letter.end_time = end_time_obj
                offer_letter.is_generated = False
                offer_letter.save()
                messages.success(request, "Offer letter updated successfully.")
            else:
                messages.success(request, "Offer letter created successfully.")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('add_offer_letter')

        return redirect('make_offer_letter')

    return render(request, 'add_offer_letter.html', {'employees': selected_candidates})







@login_required
def remove_offer_letter_candidate(request, interview_id):
    """Remove a candidate from the offer letter list"""
    if request.method == 'POST':
        try:
            offer_letter = OfferLetter.objects.get(interview_id=interview_id)
            offer_letter.delete()
            messages.success(request, "Candidate removed from offer letter list.")
        except OfferLetter.DoesNotExist:
            messages.error(request, "Candidate not found in the list.")
    
    return redirect('make_offer_letter')

@login_required
def clear_offer_letter_list(request):
    """Clear all selected candidates from offer letter list"""
    if request.method == 'POST':
        OfferLetter.objects.all().delete()
        messages.success(request, "All candidates cleared from offer letter list.")
    
    return redirect('make_offer_letter')

from django.shortcuts import render, get_object_or_404, redirect
from .models import Interview



from django.shortcuts import render, get_object_or_404
from app3.models import OfferLetter
# Adjust this based on where your Interview model is
from django.shortcuts import render, get_object_or_404
from app3.models import OfferLetter
from django.utils import timezone

def generate_offer_letter(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    offer_letter = get_object_or_404(OfferLetter, interview=interview)

    if not offer_letter.is_generated:
        offer_letter.is_generated = True
        offer_letter.generated_by = request.user  # Set the user who generated the offer letter
        offer_letter.generated_date = timezone.now()
        offer_letter.save()

    context = {
        "today_date": timezone.now().date(),
        "candidate_name": interview.name,
        "candidate_address": interview.address,
        "candidate_phone": interview.phone_number,
        "offer_letter_details": offer_letter,
    }

    return render(request, 'offer_letter.html', context)


from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from .models import Interview, OfferLetter  # ✅ Import your models
from datetime import date

from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect
from django.http import HttpResponseBadRequest
from app3.models import OfferLetter
 # adjust app name if Interview is in another app

from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.contrib import messages
from .models import OfferLetter, Interview
@csrf_protect
def save_offer_letter(request):
    if request.method == 'POST':
        interview_id = request.POST.get('interview_id')
        position = request.POST.get('position', '').strip()
        department = request.POST.get('department', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        salary = request.POST.get('salary', '').strip()
        notice_period = request.POST.get('notice_period', '').strip()

        # Validate interview ID
        if not interview_id:
            messages.error(request, "Interview ID is required")
            return redirect('make_offer_letter')

        try:
            interview = Interview.objects.get(id=interview_id)
        except Interview.DoesNotExist:
            messages.error(request, "Invalid Interview ID")
            return redirect('make_offer_letter')

        # Validate required fields
        errors = []
        if not position:
            errors.append("Position is required")
        if not department:
            errors.append("Department is required")
        if not start_date:
            errors.append("Start Date is required")
        if not salary:
            errors.append("Salary is required")
        if not notice_period:
            errors.append("Notice Period is required")

        if errors:
            messages.error(request, "; ".join(errors))
            return redirect('make_offer_letter')

        # Validate salary is a valid number
        try:
            salary_decimal = float(salary)
            if salary_decimal <= 0:
                messages.error(request, "Salary must be greater than 0")
                return redirect('make_offer_letter')
        except (ValueError, TypeError):
            messages.error(request, "Invalid salary amount")
            return redirect('make_offer_letter')

        # Validate notice period is a valid integer
        try:
            notice_period_int = int(notice_period)
            if notice_period_int < 0:
                messages.error(request, "Notice period cannot be negative")
                return redirect('make_offer_letter')
        except (ValueError, TypeError):
            messages.error(request, "Invalid notice period")
            return redirect('make_offer_letter')

        # Validate start_date format
        try:
            from datetime import datetime
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            messages.error(request, "Invalid start date format. Please use YYYY-MM-DD format")
            return redirect('make_offer_letter')

        try:
            # Check if an offer letter already exists for this interview
            offer_letter, created = OfferLetter.objects.get_or_create(
                interview=interview,
                defaults={
                    'position': position,
                    'department': department,
                    'start_date': start_date,
                    'salary': salary_decimal,
                    'notice_period': notice_period_int,
                    'is_generated': False  # Always start as False
                }
            )
            
            if not created:
                # Update existing offer letter and reset is_generated to False
                offer_letter.position = position
                offer_letter.department = department
                offer_letter.start_date = start_date
                offer_letter.salary = salary_decimal
                offer_letter.notice_period = notice_period_int
                offer_letter.is_generated = False  # Reset to False when details are updated
                offer_letter.save()
                messages.success(request, "Offer letter details updated successfully.")
            else:
                messages.success(request, "Offer letter details saved successfully.")

        except Exception as e:
            messages.error(request, f"Error saving offer letter: {str(e)}")
            return redirect('make_offer_letter')

        return redirect('make_offer_letter')

    messages.error(request, "Only POST method allowed")
    return redirect('make_offer_letter')

import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
# ... other imports
@csrf_exempt
@login_required
def update_candidate_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            interview_id = data.get('interview_id')
            status = data.get('status')
            remarks = data.get('remarks', '')

            if not interview_id or not status:
                return JsonResponse({
                    'success': False, 
                    'message': 'Interview ID and status are required'
                })

            if status not in ['willing', 'not_willing']:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid status value'
                })

            # Get the offer letter
            try:
                offer_letter = OfferLetter.objects.get(interview_id=interview_id)
            except OfferLetter.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'message': 'Offer letter not found'
                })

            # Update the status
            offer_letter.candidate_status = status
            offer_letter.status_remarks = remarks if status == 'not_willing' else ''
            offer_letter.status_updated_by = request.user
            offer_letter.status_updated_date = timezone.now()
            offer_letter.save()

            return JsonResponse({
                'success': True, 
                'message': 'Status updated successfully'
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid JSON data'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Error: {str(e)}'
            })

    return JsonResponse({
        'success': False, 
        'message': 'Only POST method allowed'
    })




from django.shortcuts import render, get_object_or_404, redirect
from app1.models import Employee  # Adjust the import based on your app structure

from django.shortcuts import render, get_object_or_404, redirect





from django.shortcuts import render
from app1.models import Employee  # Adjust the import based on your app structure

# app3/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from app1.models import Employee

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from app1.models import Employee
from .models import ExperienceCertificate

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from app1.models import Employee
from .models import ExperienceCertificate

def add_experience_certificate(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        if employee_id and start_date and end_date:
            try:
                employee = Employee.objects.get(id=employee_id)
                
                # Check if experience certificate already exists
                experience_cert, created = ExperienceCertificate.objects.get_or_create(
                    employee=employee,
                    defaults={
                        'added_by': request.user if request.user.is_authenticated else None,
                        'start_date': start_date,
                        'end_date': end_date,
                    }
                )
                
                if created:
                    return JsonResponse({
                        'success': True, 
                        'employee_id': employee.id,
                        'message': 'Experience certificate created successfully'
                    })
                else:
                    return JsonResponse({
                        'success': True, 
                        'employee_id': employee.id,
                        'message': 'Experience certificate already exists'
                    })
                    
            except Employee.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'message': 'Employee not found'
                })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Employee ID, start date, and end date are required'
            })
    
    # GET request - display the form
    employees = Employee.objects.all().order_by('name')
    return render(request, 'add_experience_certificate.html', {'employees': employees})

def make_experience_certificate(request, employee_id=None):
    search_query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset - employees that have experience certificates
    employees_queryset = Employee.objects.filter(
        experience_certificate__isnull=False
    ).select_related('experience_certificate').distinct()
    
    # Apply search filter ACROSS ALL PAGES if query exists
    if search_query:
        employees_queryset = employees_queryset.filter(
            name__icontains=search_query
        ).order_by('name')
    else:
        employees_queryset = employees_queryset.order_by('-id')

    # Pagination AFTER filtering
    paginator = Paginator(employees_queryset, 10)  # Show 10 employees per page
    
    try:
        employees = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        employees = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        employees = paginator.page(paginator.num_pages)

    context = {
        'employees': employees,
        'search_query': search_query,
        'highlighted_employee_id': int(employee_id) if employee_id else None,
        'total_results': employees_queryset.count(),  # Total filtered results
    }

    return render(request, 'make_experience_certificate.html', context)

def approve_experience_certificate(request, employee_id):
    if request.method == 'POST':
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            experience_cert = get_object_or_404(ExperienceCertificate, employee=employee)
            
            experience_cert.is_approved = True
            experience_cert.approved_by = request.user if request.user.is_authenticated else None
            experience_cert.approved_on = timezone.now()
            experience_cert.save()
            
            messages.success(request, f'Experience certificate for {employee.name} has been approved.')
        except Exception as e:
            messages.error(request, f'Error approving certificate: {str(e)}')
    
    return redirect('make_experience_certificate')

def delete_experience_certificate(request, employee_id):
    if request.method == 'POST':
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            experience_cert = get_object_or_404(ExperienceCertificate, employee=employee)
            experience_cert.delete()
            
            messages.success(request, f'Experience certificate for {employee.name} has been deleted.')
        except Exception as e:
            messages.error(request, f'Error deleting certificate: {str(e)}')
    
    return redirect('make_experience_certificate')

def view_experience_certificate(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    try:
        experience_cert = ExperienceCertificate.objects.get(employee=employee)
    except ExperienceCertificate.DoesNotExist:
        return render(request, 'experience_certificate.html', {
            'error': 'No experience certificate found.'
        })

    certificate_date = request.GET.get('date', timezone.now().strftime('%d-%m-%Y'))

    return render(request, 'experience_certificate.html', {
        'employee': employee,
        'experience_certificate': experience_cert,
        'certificate_date': certificate_date,
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from app1.models import Employee
from .models import ExperienceCertificate

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from app1.models import Employee
from .models import ExperienceCertificate

def edit_experience_certificate(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    experience_cert = get_object_or_404(ExperienceCertificate, employee=employee)

    if request.method == 'POST':
        # Check if this is an AJAX request (JSON expected)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')

                # Validate the input dates
                if not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Start date and end date are required.'
                    })

                # Additional validation: ensure end_date is after start_date
                from datetime import datetime
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    if end_date_obj <= start_date_obj:
                        return JsonResponse({
                            'success': False,
                            'message': 'End date must be after start date.'
                        })
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid date format.'
                    })

                # Update the experience certificate
                experience_cert.start_date = start_date
                experience_cert.end_date = end_date
                experience_cert.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Experience certificate updated successfully.'
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Failed to update experience certificate: {str(e)}'
                })
        
        # Handle regular form submission (non-AJAX)
        else:
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # Validate the input dates
            if not start_date or not end_date:
                messages.error(request, 'Start date and end date are required.')
                return render(request, 'edit_experience_certificate.html', {
                    'employee': employee,
                    'experience_cert': experience_cert,
                    'initial_data': {
                        'start_date': start_date,
                        'end_date': end_date,
                    }
                })

            try:
                # Update the experience certificate
                experience_cert.start_date = start_date
                experience_cert.end_date = end_date
                experience_cert.save()
                messages.success(request, 'Experience certificate updated successfully.')
                return redirect('make_experience_certificate')
            except Exception as e:
                messages.error(request, f'Failed to update experience certificate: {str(e)}')
                return render(request, 'edit_experience_certificate.html', {
                    'employee': employee,
                    'experience_cert': experience_cert,
                    'initial_data': {
                        'start_date': start_date,
                        'end_date': end_date,
                    }
                })
    
    # GET request - show the form
    else:
        # Pre-fill the form with existing data
        initial_data = {
            'start_date': experience_cert.start_date.strftime('%Y-%m-%d') if experience_cert.start_date else '',
            'end_date': experience_cert.end_date.strftime('%Y-%m-%d') if experience_cert.end_date else '',
        }

        return render(request, 'edit_experience_certificate.html', {
            'employee': employee,
            'experience_cert': experience_cert,
            'initial_data': initial_data,
        })





from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import requests
from django.shortcuts import render

def debtors1_list(request):
    api_url = "https://rrcpython.imcbs.com/api/master/all   "
    data = []
    error_message = None

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get('data', [])
        for item in data:
            item['name'] = item.get('name', '').strip()
        print(f"Successfully fetched {len(data)} records")

    except requests.exceptions.Timeout:
        error_message = "API request timed out"
    except requests.exceptions.ConnectionError:
        error_message = "Could not connect to API"
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error: {e}"
    except Exception as e:
        error_message = f"Error fetching data: {str(e)}"

    # Search logic
    query = request.GET.get('q', '').strip()
    original_count = len(data)

    if query:
        search_terms = query.lower().split()
        filtered_data = []

        for item in data:
            searchable_fields = [
                str(item.get('code', '')),
                str(item.get('name', '')),
                str(item.get('super_code', '')),
                str(item.get('opening_balance', '')),
                str(item.get('debit', '')),
                str(item.get('credit', '')),
                str(item.get('place', '')),
                str(item.get('phone2', '')),
                str(item.get('openingdepartment', '')),
            ]
            combined_text = ' '.join(searchable_fields).lower()

            # AND logic: all terms must match somewhere
            if all(term in combined_text for term in search_terms):
                filtered_data.append(item)

        data = filtered_data
        print(f"Search '{query}' matched {len(data)} out of {original_count} records")

    # Pagination
    paginator = Paginator(data, 15)
    page = request.GET.get('page')

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'debtors1_list.html', {
        'page_obj': page_obj,
        'error_message': error_message,
        'total_records': original_count,
        'filtered_count': len(data),
        'query': query,
        'search_terms': query.lower().split() if query else []
    })
