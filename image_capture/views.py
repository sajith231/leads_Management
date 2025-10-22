import random
import base64
import logging
import re
import requests
from urllib.parse import quote
from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.files.base import ContentFile
from .models import ImageCapture

# ------------------------------------------------------------------
# ✅ OPTIMIZED: index view - NO MORE SLOW API CALLS
# ------------------------------------------------------------------
def index(request):
    # Get all verified image captures, ordered by most recent first
    verified_captures = ImageCapture.objects.filter(verified=True).order_by('-created_at')
    
    # Add pagination (20 customers per page)
    paginator = Paginator(verified_captures, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'index.html', {
        'verified_captures': page_obj,
        'page_obj': page_obj,
        'total_count': verified_captures.count()  # For stats
    })


# ------------------------------------------------------------------
# Helper: Reverse geocoding to get location name
# ------------------------------------------------------------------
def _get_location_name(latitude, longitude):
    """
    Convert coordinates to location name using OpenStreetMap Nominatim
    """
    try:
        if not latitude or not longitude:
            return "Location not available"
        
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 18,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'YourApp/1.0 (your@email.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Build location name from available address components
            location_parts = []
            
            if address.get('road'):
                location_parts.append(address['road'])
            if address.get('suburb'):
                location_parts.append(address['suburb'])
            if address.get('city') or address.get('town') or address.get('village'):
                location_parts.append(address.get('city') or address.get('town') or address.get('village'))
            if address.get('state'):
                location_parts.append(address['state'])
            if address.get('country'):
                location_parts.append(address['country'])
            
            if location_parts:
                return ', '.join(location_parts)
            else:
                return data.get('display_name', 'Location details not available')
        else:
            return f"{latitude}, {longitude}"
    
    except Exception as e:
        logging.error(f"Reverse geocoding error: {e}")
        return f"{latitude}, {longitude}"


# ------------------------------------------------------------------
# Helper: send OTP through DxIng WhatsApp gateway
# ------------------------------------------------------------------
import threading

def _send_otp_via_whatsapp(phone: str, otp: str) -> None:
    """
    Send OTP via DxIng WhatsApp in background thread (non-blocking)
    phone: E.164 without '+', e.g. 9198xxxxxxxxx
    """
    def send():
        url = (
            "https://app.dxing.in/api/send/whatsapp"
            "?secret=7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
            "&account=1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
            f"&recipient={phone}"
            "&type=text"
            f"&message=Your verification code is {otp}. Valid for 5 minutes."
            "&priority=0"  # ⚡️ Use highest priority for faster delivery
        )
        try:
            requests.get(url, timeout=5)
        except Exception as e:
            logging.error(f"WhatsApp send failed for {phone}: {e}")

    # Start async thread
    threading.Thread(target=send, daemon=True).start()



# ------------------------------------------------------------------
# 1. Agent-facing link-generator page
# ------------------------------------------------------------------
def image_capture_form(request):
    generated_link = None
    error = None
    customers = []
    customer_name = None
    phone_number = None

    # Fetch customer data from API
    try:
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            customers = response.json()
        else:
            logging.error(f"Failed to fetch clients: {response.status_code}")
    except Exception as e:
        logging.error(f"API fetch error: {e}")

    # Handle form submission
    if request.method == "POST":
        customer_name_dropdown = request.POST.get("customer_name", "").strip()
        customer_name_manual = request.POST.get("customer_name_manual", "").strip()
        
        # Use manual input if provided, otherwise use dropdown selection
        if customer_name_manual:
            customer_name = customer_name_manual
        else:
            customer_name = customer_name_dropdown
            
        phone_number = request.POST.get("phone_number", "").strip()

        if not customer_name:
            error = "Please enter or select a customer name"
        elif not re.fullmatch(r"\d{10}", phone_number):
            error = "Enter 10-digit mobile number only (no country code, no +, no 0)"
        else:
            obj = ImageCapture.objects.create(
                customer_name=customer_name,
                phone_number=phone_number,
            )
            generated_link = request.build_absolute_uri(
                reverse("capture_link", args=[obj.unique_id])
            )

    return render(
        request,
        "image_capture_form.html",
        {
            "generated_link": generated_link,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "error": error,
            "customers": customers,
        },
    )


# ------------------------------------------------------------------
# 2. Customer landing page (asks phone number)
# ------------------------------------------------------------------
def capture_link_view(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)

    if request.method == "POST":
        entered_number = request.POST.get("phone_number", "").strip()

        # Normalize to 10 digits for comparison
        entered_ten = entered_number.lstrip("0")[-10:]
        stored_ten = data.phone_number[-10:]

        if entered_ten == stored_ten:
            otp = str(random.randint(1000, 9999))
            request.session["otp"] = otp
            request.session["unique_id"] = str(unique_id)

            # Send via WhatsApp (always 91-prefixed)
            ok = _send_otp_via_whatsapp(f"91{stored_ten}", otp)
            if not ok:
                logging.error("OTP WhatsApp failed for 91%s", stored_ten)

            return render(
                request, "otp_verification.html", {"data": data, "sent_otp": True}
            )
        else:
            return render(
                request,
                "capture_link.html",
                {"data": data, "error": "Invalid phone number"},
            )

    return render(request, "capture_link.html", {"data": data})


# ------------------------------------------------------------------
# 3. OTP verification page
# ------------------------------------------------------------------
def verify_otp(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get("otp")
        if entered_otp == session_otp:
            data.verified = True
            data.save()
            # Clear the OTP from session after successful verification
            if 'otp' in request.session:
                del request.session['otp']
            return render(request, "image_capture_page.html", {"data": data})
        else:
            return render(
                request,
                "otp_verification.html",
                {"data": data, "error": "Incorrect OTP"},
            )
    return redirect("capture_link", unique_id=unique_id)


# ------------------------------------------------------------------
# ✅ OPTIMIZED: 4. Image + location submit handler
# ------------------------------------------------------------------
def submit_image(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)
    
    if request.method == "POST":
        # Check if user is verified
        if not data.verified:
            return render(request, 'image_capture_page.html', {
                'data': data, 
                'error': 'Please complete OTP verification first'
            })
        
        image_data = request.POST.get("image_data")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")

        if image_data:
            try:
                # Extract base64 data
                if ';base64,' in image_data:
                    fmt, imgstr = image_data.split(';base64,')
                    # Get file extension
                    ext = fmt.split('/')[-1] if '/' in fmt else 'jpg'
                else:
                    # Handle case where format prefix is missing
                    imgstr = image_data
                    ext = 'jpg'
                
                image_file = ContentFile(
                    base64.b64decode(imgstr), 
                    name=f"{data.customer_name}_{unique_id}.{ext}"
                )
                data.image = image_file
                data.latitude = latitude
                data.longitude = longitude
                
                # ✅ Get location name ONCE and store in database
                if latitude and longitude:
                    data.location_name = _get_location_name(latitude, longitude)
                else:
                    data.location_name = "Location not available"
                
                data.save()
                
                return render(request, "success_page.html", {
                    "data": data,
                    "location_name": data.location_name
                })
                
            except Exception as e:
                logging.error(f"Error processing image: {e}")
                return render(request, 'image_capture_page.html', {
                    'data': data, 
                    'error': 'Error processing image. Please try again.'
                })
        else:
            return render(request, 'image_capture_page.html', {
                'data': data, 
                'error': 'No image data received'
            })
    
    return redirect("capture_link", unique_id=unique_id)


# ------------------------------------------------------------------
# 5. Delete customer
# ------------------------------------------------------------------
def delete_customer(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        try:
            customer = ImageCapture.objects.get(id=customer_id)
            customer_name = customer.customer_name
            customer.delete()
            messages.success(request, f'Customer "{customer_name}" deleted successfully.')
        except ImageCapture.DoesNotExist:
            messages.error(request, 'Customer not found.')
        except Exception as e:
            messages.error(request, f'Error deleting customer: {str(e)}')
    
    return redirect('index')