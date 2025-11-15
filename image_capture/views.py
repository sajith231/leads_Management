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
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io
import piexif
from app1.models import Branch
# ------------------------------------------------------------------
# Helper: Convert decimal coordinates to GPS EXIF format
# ------------------------------------------------------------------
def decimal_to_dms(decimal):
    """
    Convert decimal GPS coordinate to degrees, minutes, seconds format
    Returns: ((degrees, 1), (minutes, 1), (seconds, 100))
    """
    decimal = float(decimal)
    is_positive = decimal >= 0
    decimal = abs(decimal)
    
    degrees = int(decimal)
    minutes_decimal = (decimal - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60
    
    # Convert to rational numbers (numerator, denominator)
    return (
        (degrees, 1),
        (minutes, 1),
        (int(seconds * 100), 100)
    )

# ------------------------------------------------------------------
# Helper: Embed GPS data into image EXIF
# ------------------------------------------------------------------
def embed_gps_to_image(image_bytes, latitude, longitude):
    """
    Embed GPS coordinates into image EXIF data
    Returns: modified image bytes with GPS data
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Prepare GPS data
        lat_deg = decimal_to_dms(abs(latitude))
        lon_deg = decimal_to_dms(abs(longitude))
        
        lat_ref = 'N' if latitude >= 0 else 'S'
        lon_ref = 'E' if longitude >= 0 else 'W'
        
        # Create GPS IFD
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: lat_deg,
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLongitude: lon_deg,
        }
        
        # Get existing EXIF data or create new
        try:
            exif_dict = piexif.load(image.info.get('exif', b''))
        except:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
        # Update GPS data
        exif_dict['GPS'] = gps_ifd
        
        # Convert to bytes
        exif_bytes = piexif.dump(exif_dict)
        
        # Save image with new EXIF data
        output = io.BytesIO()
        image.save(output, format=image.format or 'JPEG', exif=exif_bytes, quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        logging.error(f"Error embedding GPS into image: {e}")
        return image_bytes  # Return original if embedding fails

# ------------------------------------------------------------------
# Extract GPS from EXIF data (server-side)
# ------------------------------------------------------------------
def extract_gps_from_image(image_data):
    """
    Extract GPS coordinates from image EXIF data
    Returns: (latitude, longitude) or (None, None)
    """
    try:
        # Decode base64 image
        if ';base64,' in image_data:
            imgstr = image_data.split(';base64,')[1]
        else:
            imgstr = image_data
        
        image_bytes = base64.b64decode(imgstr)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Get EXIF data
        exif_data = image._getexif()
        
        if not exif_data:
            logging.warning("No EXIF data found in image")
            return None, None
        
        # EXIF tags for GPS
        GPS_INFO = 34853
        
        if GPS_INFO not in exif_data:
            logging.warning("No GPS info in EXIF data")
            return None, None
        
        gps_info = exif_data[GPS_INFO]
        
        # GPS tag IDs
        GPS_LATITUDE = 2
        GPS_LATITUDE_REF = 1
        GPS_LONGITUDE = 4
        GPS_LONGITUDE_REF = 3
        
        if GPS_LATITUDE not in gps_info or GPS_LONGITUDE not in gps_info:
            logging.warning("GPS coordinates not found in EXIF")
            return None, None
        
        # Convert GPS coordinates
        lat = gps_info[GPS_LATITUDE]
        lat_ref = gps_info.get(GPS_LATITUDE_REF, 'N')
        lon = gps_info[GPS_LONGITUDE]
        lon_ref = gps_info.get(GPS_LONGITUDE_REF, 'E')
        
        # Convert DMS to decimal
        def dms_to_decimal(dms, ref):
            degrees = float(dms[0])
            minutes = float(dms[1])
            seconds = float(dms[2])
            
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            if ref in ['S', 'W']:
                decimal = -decimal
            
            return decimal
        
        latitude = dms_to_decimal(lat, lat_ref)
        longitude = dms_to_decimal(lon, lon_ref)
        
        logging.info(f"GPS extracted: {latitude}, {longitude}")
        return latitude, longitude
        
    except Exception as e:
        logging.error(f"Error extracting GPS from image: {e}")
        return None, None

# ------------------------------------------------------------------
# OPTIMIZED: index view
# ------------------------------------------------------------------
def index(request):
    verified_captures = ImageCapture.objects.filter(verified=True).order_by('-created_at')
    
    paginator = Paginator(verified_captures, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'index.html', {
        'verified_captures': page_obj,
        'page_obj': page_obj,
        'total_count': verified_captures.count()
    })

# ------------------------------------------------------------------
# Helper: Reverse geocoding
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
# Helper: send OTP via WhatsApp
# ------------------------------------------------------------------
import threading

def _send_otp_via_whatsapp(phone: str, otp: str) -> None:
    """
    Send OTP via DxIng WhatsApp in background thread (non-blocking)
    """
    def send():
        message = f"Your verification code is {otp}. Valid for 5 minutes."
        url = (
            "https://app.dxing.in/api/send/whatsapp"
            "?secret=7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
            "&account=1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"
            f"&recipient={phone}"
            "&type=text"
            f"&message={message}"
            "&priority=1"
        )
        try:
            requests.get(url, timeout=5)
        except Exception as e:
            logging.error(f"WhatsApp send failed for {phone}: {e}")
    
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

    # Get user's branch if logged in
    user_branch = None
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        user_branch = request.user.userprofile.branch.name
    elif request.user.is_authenticated and hasattr(request.user, 'branch'):
        user_branch = request.user.branch.name

    try:
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            customers = response.json()
            
            # Filter customers by user's branch if user has a specific branch
            if user_branch:
                customers = [c for c in customers if c.get('branch') == user_branch]
            
            customers.sort(key=lambda x: x.get("name", "").lower())
        else:
            logging.error(f"Failed to fetch clients: {response.status_code}")
    except Exception as e:
        logging.error(f"API fetch error: {e}")

    # Get all branches
    branches = Branch.objects.all().order_by('name')

    if request.method == "POST":
        customer_name_dropdown = request.POST.get("customer_name", "").strip()
        customer_name_manual = request.POST.get("customer_name_manual", "").strip()
        
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
            "branches": branches,
            "user_branch": user_branch,  # Pass user's branch to template
        },
    )

def manual_capture_form(request):
    """
    Page to manually select or enter customer and directly upload image
    """
    customers = []
    error = None

    # Get user's branch if logged in
    user_branch = None
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        user_branch = request.user.userprofile.branch.name
    elif request.user.is_authenticated and hasattr(request.user, 'branch'):
        user_branch = request.user.branch.name

    # Fetch customer list
    try:
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            customers = response.json()
            
            # Filter customers by user's branch if user has a specific branch
            if user_branch:
                customers = [c for c in customers if c.get('branch') == user_branch]
            
            customers.sort(key=lambda x: x.get("name", "").lower())
    except Exception as e:
        logging.error(f"Error fetching customer list: {e}")

    # Get all branches
    branches = Branch.objects.all().order_by('name')

    if request.method == "POST":
        customer_name_dropdown = request.POST.get("customer_name", "").strip()
        customer_name_manual = request.POST.get("customer_name_manual", "").strip()

        if customer_name_manual:
            customer_name = customer_name_manual
        else:
            customer_name = customer_name_dropdown

        if not customer_name:
            error = "Please enter or select a customer name"
        else:
            # Create object directly as verified (no OTP)
            obj = ImageCapture.objects.create(
                customer_name=customer_name,
                verified=True
            )
            return redirect("manual_image_upload", unique_id=obj.unique_id)

    return render(request, "manual_capture_form.html", {
        "customers": customers,
        "error": error,
        "branches": branches,
        "user_branch": user_branch,  # Pass user's branch to template
    })

def manual_image_upload(request, unique_id):
    """
    Handle image upload and location detection for manual capture
    """
    data = get_object_or_404(ImageCapture, unique_id=unique_id)

    if request.method == "POST":
        image_data = request.POST.get("image_data")
        client_lat = request.POST.get("latitude", "").strip()
        client_lon = request.POST.get("longitude", "").strip()
        source = request.POST.get("location_source", "unknown")

        if image_data:
            latitude, longitude = extract_gps_from_image(image_data)

            if not latitude or not longitude:
                latitude = client_lat or None
                longitude = client_lon or None

            # Reverse geocode
            location_name = _get_location_name(latitude, longitude) if latitude and longitude else None

            imgstr = image_data.split(';base64,')[1]
            image_bytes = base64.b64decode(imgstr)

            # Save image
            data.image.save(f"{data.customer_name}_capture.jpg", ContentFile(image_bytes))
            data.latitude = latitude
            data.longitude = longitude
            data.location_name = location_name
            data.location_source = source
            data.verified = True
            data.save()

            return render(request, "success_page.html", {"data": data})

    return render(request, "manual_image_upload.html", {"data": data})

# ------------------------------------------------------------------
# 2. Customer landing page
# ------------------------------------------------------------------
def capture_link_view(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)

    if request.method == "POST":
        entered_number = request.POST.get("phone_number", "").strip()

        entered_ten = entered_number.lstrip("0")[-10:]
        stored_ten = data.phone_number[-10:]

        if entered_ten == stored_ten:
            otp = str(random.randint(1000, 9999))
            request.session["otp"] = otp
            request.session["unique_id"] = str(unique_id)

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
# 4. ENHANCED: Image + location submit with GPS embedding
# ------------------------------------------------------------------
def submit_image(request, unique_id):
    data = get_object_or_404(ImageCapture, unique_id=unique_id)
    
    if request.method == "POST":
        if not data.verified:
            return render(request, 'image_capture_page.html', {
                'data': data, 
                'error': 'Please complete OTP verification first'
            })
        
        image_data = request.POST.get("image_data")
        client_latitude = request.POST.get("latitude", "").strip()
        client_longitude = request.POST.get("longitude", "").strip()
        location_source = request.POST.get("location_source", "unknown")

        if image_data:
            try:
                # STEP 1: Try to extract GPS from EXIF
                latitude, longitude = extract_gps_from_image(image_data)
                
                # STEP 2: Use client coordinates if EXIF fails
                if not latitude or not longitude:
                    logging.warning("EXIF extraction failed, using client-side coordinates")
                    
                    # Validate and convert client coordinates
                    try:
                        if client_latitude and client_longitude and \
                           client_latitude.lower() != 'nan' and client_longitude.lower() != 'nan':
                            latitude = float(client_latitude)
                            longitude = float(client_longitude)
                            
                            # Validate coordinate ranges
                            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                                logging.error(f"Invalid coordinate ranges: {latitude}, {longitude}")
                                latitude = None
                                longitude = None
                        else:
                            latitude = None
                            longitude = None
                    except (ValueError, TypeError) as e:
                        logging.error(f"Error converting coordinates: {e}")
                        latitude = None
                        longitude = None
                
                # Extract base64 data
                if ';base64,' in image_data:
                    fmt, imgstr = image_data.split(';base64,')
                    ext = fmt.split('/')[-1] if '/' in fmt else 'jpg'
                else:
                    imgstr = image_data
                    ext = 'jpg'
                
                image_bytes = base64.b64decode(imgstr)
                
                # STEP 3: Embed GPS into image if we have coordinates and source is "live"
                if latitude and longitude and location_source == "live":
                    logging.info(f"Embedding live GPS into image: {latitude}, {longitude}")
                    image_bytes = embed_gps_to_image(
                        image_bytes,
                        float(latitude),
                        float(longitude)
                    )
                
                # Save the image with embedded GPS
                image_file = ContentFile(
                    image_bytes,
                    name=f"{data.customer_name}_{unique_id}.{ext}"
                )
                
                data.image = image_file
                data.latitude = latitude
                data.longitude = longitude
                
                # Get location name
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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import ImageCapture

def update_status(request, pk):
    """Update the manual status of a customer"""
    if request.method == "POST":
        try:
            obj = get_object_or_404(ImageCapture, id=pk)
            new_status = request.POST.get("status")
            
            if new_status in ["Pending", "Verified"]:
                obj.status = new_status
                obj.save()
                return JsonResponse({"success": True, "status": new_status})
            else:
                return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
                
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid method"}, status=405)