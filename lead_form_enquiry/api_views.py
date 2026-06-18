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
    Pulls 'image' / 'audio' out of request.FILES (if present), uploads them to
    Cloudflare R2, and patches `data` so the serializer writes the R2 url/key
    instead of saving the file locally. If the R2 upload fails, the original
    file is left in `data` so DRF falls back to local FileField/ImageField
    storage (matching the behaviour of the HTML views).
    """
    image = request.FILES.get('image')
    audio = request.FILES.get('audio')

    if image:
        result = upload_to_cloudflare(image, folder_name='enquiry_files/images')
        if result['success']:
            data['cloudflare_image_url'] = result['r2_url']
            data['cloudflare_image_key'] = result['file_key']
            data.pop('image', None)  # don't also save locally
        # else: leave 'image' in data so it saves locally as a fallback

    if audio:
        result = upload_to_cloudflare(audio, folder_name='enquiry_files/audio')
        if result['success']:
            data['cloudflare_audio_url'] = result['r2_url']
            data['cloudflare_audio_key'] = result['file_key']
            data.pop('audio', None)
        # else: leave 'audio' in data so it saves locally as a fallback

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
                cloudflare_image_key=data.get('cloudflare_image_key'),
                cloudflare_audio_key=data.get('cloudflare_audio_key'),
            )
            return Response(
                {
                    "message": "Enquiry submitted successfully.",
                    "data": EnquirySerializer(enquiry).data
                },
                status=status.HTTP_201_CREATED
            )
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
        if 'cloudflare_image_key' in data:
            extra['cloudflare_image_key'] = data.get('cloudflare_image_key')
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