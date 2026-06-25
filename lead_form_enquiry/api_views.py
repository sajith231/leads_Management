from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Enquiry
from .serializers import EnquirySerializer
from common.cloudflare_storage import upload_to_cloudflare


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


def _handle_cloudflare_uploads(request, data):
    """
    Upload image/audio to Cloudflare R2 and save URLs.
    Supports:
    1. multipart/form-data (recommended)
    2. file fields from mobile apps
    """

    print("=" * 50)
    print("REQUEST CONTENT TYPE:", request.content_type)
    print("REQUEST DATA KEYS:", list(request.data.keys()))
    print("REQUEST FILES KEYS:", list(request.FILES.keys()))
    print("=" * 50)

    image = request.FILES.get('image')
    audio = request.FILES.get('audio')

    # Debugging
    print("IMAGE FILE:", image)
    print("AUDIO FILE:", audio)

    # Upload Image
    if image:
        try:
            result = upload_to_cloudflare(
                image,
                folder_name='enquiry_files/images'
            )

            print("IMAGE UPLOAD RESULT:", result)

            if result.get('success'):
                data['cloudflare_image_url'] = result.get('r2_url')
                data['cloudflare_image_key'] = result.get('file_key')
                data.pop('image', None)

                print("IMAGE UPLOADED SUCCESSFULLY")
                print("IMAGE URL:", result.get('r2_url'))
            else:
                print("IMAGE UPLOAD FAILED:", result)

        except Exception as e:
            print("IMAGE UPLOAD EXCEPTION:", str(e))

    # Upload Audio
    if audio:
        try:
            result = upload_to_cloudflare(
                audio,
                folder_name='enquiry_files/audio'
            )

            print("AUDIO UPLOAD RESULT:", result)

            if result.get('success'):
                data['cloudflare_audio_url'] = result.get('r2_url')
                data['cloudflare_audio_key'] = result.get('file_key')
                data.pop('audio', None)

                print("AUDIO UPLOADED SUCCESSFULLY")
                print("AUDIO URL:", result.get('r2_url'))
            else:
                print("AUDIO UPLOAD FAILED:", result)

        except Exception as e:
            print("AUDIO UPLOAD EXCEPTION:", str(e))

    print("FINAL DATA:", data)
    print("=" * 50)

    return data


def _resolve_creator(request):
    # 1. Explicit creator string in request body (highest priority for mobile)
    creator = str(request.data.get('creator', '')).strip()
    if creator and creator.lower() != 'anonymous':
        return creator

    try:
        from app1.models import User as AppUser
    except Exception:
        return creator or None

    # 2. Resolve from userid + password (mobile app auth pattern)
    userid   = str(request.data.get('userid', '')).strip()
    password = str(request.data.get('password', '')).strip()
    if userid and password:
        user = AppUser.objects.filter(userid=userid, password=password).first()
        if user:
            return user.name

    user = None

    # 3. Session custom_user_id (web session)
    uid = request.session.get("custom_user_id")
    if uid:
        user = AppUser.objects.filter(id=uid).first()

    # 4. X-User-Id header
    if not user:
        header_uid = request.headers.get("X-User-Id")
        if header_uid and str(header_uid).isdigit():
            user = AppUser.objects.filter(id=int(header_uid)).first()

    # 5. Django request.user
    if not user and request.user and request.user.is_authenticated:
        user = AppUser.objects.filter(id=request.user.id).first()

    if user:
        return user.name

    return None


@method_decorator(csrf_exempt, name='dispatch')
class EnquiryListCreateAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes     = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        request._login_exempt = True
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        enquiries  = Enquiry.objects.all().order_by('-date')
        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()

        creator = _resolve_creator(request)
        if not creator:
            return Response(
                {"error": "creator field is required. Send 'creator' in the request body or include the X-User-Id header."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data['creator'] = creator
        data = _handle_cloudflare_uploads(request, data)

        serializer = EnquirySerializer(data=data)

        if serializer.is_valid():
            enquiry = serializer.save(
                cloudflare_image_url=data.get('cloudflare_image_url'),
                cloudflare_image_key=data.get('cloudflare_image_key'),
                cloudflare_audio_url=data.get('cloudflare_audio_url'),
                cloudflare_audio_key=data.get('cloudflare_audio_key'),
            )

            return Response(
                {
                    "message": "Enquiry submitted successfully.",
                    "data": EnquirySerializer(enquiry).data
                },
                status=status.HTTP_201_CREATED
            )

        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class EnquiryDetailAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes     = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        request._login_exempt = True
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, pk):
        return get_object_or_404(Enquiry, pk=pk)

    def get(self, request, pk):
        serializer = EnquirySerializer(self.get_object(pk))
        return Response(serializer.data)

    def put(self, request, pk):
        instance = self.get_object(pk)
        data = request.data.copy()
        data = _handle_cloudflare_uploads(request, data)

        extra = {}

        if 'cloudflare_image_url' in data:
            extra['cloudflare_image_url'] = data.get('cloudflare_image_url')

        if 'cloudflare_image_key' in data:
            extra['cloudflare_image_key'] = data.get('cloudflare_image_key')

        if 'cloudflare_audio_url' in data:
            extra['cloudflare_audio_url'] = data.get('cloudflare_audio_url')

        if 'cloudflare_audio_key' in data:
            extra['cloudflare_audio_key'] = data.get('cloudflare_audio_key')

        serializer = EnquirySerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            updated = serializer.save(**extra)
            return Response(EnquirySerializer(updated).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)