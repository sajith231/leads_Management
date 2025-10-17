import random
import base64
import logging
import re
import requests
from urllib.parse import quote

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.files.base import ContentFile
from .models import ImageCapture


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
            'User-Agent': 'YourApp/1.0 (your@email.com)'  # Required by Nominatim
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
            return f"{latitude}, {longitude}"  # Fallback to coordinates
    
    except Exception as e:
        logging.error(f"Reverse geocoding error: {e}")
        return f"{latitude}, {longitude}"  # Fallback to coordinates


# ------------------------------------------------------------------
# Helper: send OTP through DxIng WhatsApp gateway
# ------------------------------------------------------------------
def _send_otp_via_whatsapp(phone: str, otp: str) -> bool:
    """
    phone : E.164 without '+',  e.g. 9198xxxxxxxxx
    otp   : 4-digit string
    """
    url = (
        "https://app.dxing.in/api/send/whatsapp"
        "?secret=7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
        "&account=1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
        f"&recipient={phone}"
        "&type=text"
        f"&message=Your verification code is {otp}. Valid for 5 minutes."
        "&priority=1"
    )
    try:
        r = requests.get(url, timeout=10)
        return r.status_code == 200 and r.json().get("status") == "success"
    except Exception as exc:
        logging.exception("WhatsApp gateway error: %s", exc)
        return False


# ------------------------------------------------------------------
# 1.  Agent-facing link-generator page
# ------------------------------------------------------------------
def image_capture_form(request):
    generated_link = None
    whatsapp_url = None
    error = None

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()

        # --- accept only 10 digits ---
        if not re.fullmatch(r"\d{10}", phone_number):
            error = "Enter 10-digit mobile number only (no country code, no +, no 0)"
        else:
            obj = ImageCapture.objects.create(
                customer_name=customer_name,
                phone_number=phone_number,
            )
            generated_link = request.build_absolute_uri(
                reverse("capture_link", args=[obj.unique_id])
            )
            # pre-build agent share-url
            msg = f"Hi {customer_name}, please verify your identity by clicking this link: {generated_link}"
            whatsapp_url = f"https://wa.me/91{phone_number}?text={quote(msg)}"

    return render(
        request,
        "image_capture_form.html",
        {"generated_link": generated_link, "whatsapp_url": whatsapp_url, "error": error},
    )


# ------------------------------------------------------------------
# 2.  Customer landing page (asks phone number)
# ------------------------------------------------------------------
def capture_link_view(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)

    if request.method == "POST":
        entered_number = request.POST.get("phone_number", "").strip()

        # --- normalise to 10 digits for comparison ---
        entered_ten = entered_number.lstrip("0")[-10:]  # drop any leading zero
        stored_ten = data.phone_number[-10:]

        if entered_ten == stored_ten:
            otp = str(random.randint(1000, 9999))
            request.session["otp"] = otp
            request.session["unique_id"] = str(unique_id)

            # send via WhatsApp (always 91-prefixed)
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
# 3.  OTP verification page
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
# 4.  Image + location submit handler
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
                data.save()
                
                # Get location name for display
                location_name = _get_location_name(latitude, longitude)
                
                return render(request, "success_page.html", {
                    "data": data,
                    "location_name": location_name
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