# app/views.py

from django.shortcuts import get_object_or_404, render, redirect
from app1.models import Employee
from .models import SalaryCertificate
# from .forms import SalaryCertificateForm
from django.http import JsonResponse,HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test

# views.py
from django.shortcuts import render
from .models import SalaryCertificate

def make_salary_certificate(request):
    certificates = SalaryCertificate.objects.select_related('employee')
    return render(request, 'make_salary_certificate.html', {'employees': certificates})

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
                salary=salary
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
                salary=salary
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
    certificate.save()
    return redirect('make_salary_certificate')
