from django.shortcuts import render

# Create your views here.
def vehicle_details(request):
    return render(request, 'vehicle_details.html')
