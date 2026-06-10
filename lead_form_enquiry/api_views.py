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


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Skip CSRF check


@method_decorator(csrf_exempt, name='dispatch')
class EnquiryListCreateAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes     = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        # Mark request as login-exempt so LoginRequiredMiddleware skips it
        request._login_exempt = True
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        enquiries  = Enquiry.objects.all().order_by('-date')
        serializer = EnquirySerializer(enquiries, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = EnquirySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                creator=request.user.username if request.user.is_authenticated else 'anonymous'
            )
            return Response(
                {
                    "message": "Enquiry submitted successfully.",
                    "data": serializer.data
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
        serializer = EnquirySerializer(self.get_object(pk), data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)