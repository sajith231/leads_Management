from django.shortcuts import render

# Create your views here.
"""
lead_form_api/views.py

REST API endpoints for the Lead form.

Endpoints
---------
POST   /api/leads/           → create a new lead
GET    /api/leads/           → list all leads  (with optional ?status=Active&priority=High&search=)
GET    /api/leads/<id>/      → retrieve a single lead
PUT    /api/leads/<id>/      → full update
PATCH  /api/leads/<id>/      → partial update
DELETE /api/leads/<id>/      → delete

All endpoints return JSON.  Authentication is kept intentionally simple:
the mobile app can send a session cookie (same as the web) OR a custom
`X-User-Id` header that maps to app1.User.id.
"""

import logging
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from app5.models import Lead
from .serializers import LeadReadSerializer, LeadWriteSerializer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_current_user(request):
    """
    Try to resolve the logged-in app1.User from:
      1. session  (custom_user_id)
      2. X-User-Id request header
      3. Django's request.user (if authenticated)
    Returns a User instance or None.
    """
    try:
        from app1.models import User as AppUser
    except Exception:
        return None

    # 1. Session
    uid = request.session.get("custom_user_id")
    if uid:
        return AppUser.objects.filter(id=uid).first()

    # 2. Custom header
    header_uid = request.headers.get("X-User-Id")
    if header_uid and str(header_uid).isdigit():
        return AppUser.objects.filter(id=int(header_uid)).first()

    # 3. Django auth
    if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
        try:
            return AppUser.objects.filter(email__iexact=request.user.email).first()
        except Exception:
            pass

    return None


def _apply_user_filter(qs, user):
    """
    Mirror the web app's get_user_filtered_leads logic:
    super-admins / admins see everything; others see only their own leads.
    If no user is resolved (e.g. unauthenticated API call), return all leads.
    """
    if user is None:
        return qs  # ← FIXED: was qs.none(), now returns all leads when no user session

    is_admin = (
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "role", "").lower() in ("admin", "superadmin", "super_admin")
        or getattr(user, "user_type", "").lower() in ("admin", "superadmin")
        or getattr(user, "designation", "").lower() in ("admin", "manager")
    )

    if is_admin:
        return qs

    # Non-admin: own leads only
    user_name = (
        getattr(user, "name", None)
        or getattr(user, "username", None)
        or str(user)
    )
    return qs.filter(
        Q(created_by=user)
        | Q(marketedBy__iexact=user_name)
        | Q(assigned_to_name__iexact=user_name)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pagination
# ─────────────────────────────────────────────────────────────────────────────

class LeadPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ─────────────────────────────────────────────────────────────────────────────
# List + Create
# ─────────────────────────────────────────────────────────────────────────────

class LeadListCreateAPIView(APIView):
    """
    GET  /api/leads/
    POST /api/leads/

    GET query params:
      status=Active          → filter by status  (case-insensitive)
      priority=High          → filter by priority
      customer_type=Business → filter by customerType
      search=<text>          → fuzzy search on ownerName, name, phoneNo, ticket_number
      page=1                 → pagination
      page_size=20
    """

    def get(self, request, *args, **kwargs):
        current_user = _get_current_user(request)

        qs = Lead.objects.prefetch_related("requirements").order_by("-created_at")
        qs = _apply_user_filter(qs, current_user)

        # ── Filters ──────────────────────────────────────────────────────────
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__iexact=status_param)

        priority_param = request.query_params.get("priority")
        if priority_param:
            qs = qs.filter(priority__iexact=priority_param)

        customer_type = request.query_params.get("customer_type")
        if customer_type:
            qs = qs.filter(customerType__iexact=customer_type)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(ownerName__icontains=search)
                | Q(name__icontains=search)
                | Q(phoneNo__icontains=search)
                | Q(ticket_number__icontains=search)
                | Q(email__icontains=search)
            )

        # ── Paginate ──────────────────────────────────────────────────────────
        paginator = LeadPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = LeadReadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = LeadWriteSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            lead = serializer.save()
            # Return the full read representation after creation
            read_serializer = LeadReadSerializer(lead)
            return Response(
                {
                    "success": True,
                    "message": f"Lead created successfully. Ticket: {lead.ticket_number}",
                    "data": read_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Retrieve + Update + Delete
# ─────────────────────────────────────────────────────────────────────────────

class LeadDetailAPIView(APIView):
    """
    GET    /api/leads/<id>/
    PUT    /api/leads/<id>/
    PATCH  /api/leads/<id>/
    DELETE /api/leads/<id>/
    """

    def _get_lead(self, pk, user):
        qs = Lead.objects.prefetch_related("requirements")
        qs = _apply_user_filter(qs, user)
        try:
            return qs.get(pk=pk)
        except Lead.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        user = _get_current_user(request)
        lead = self._get_lead(pk, user)
        if lead is None:
            return Response(
                {"success": False, "message": "Lead not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "data": LeadReadSerializer(lead).data})

    def put(self, request, pk, *args, **kwargs):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk, *args, **kwargs):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        user = _get_current_user(request)
        lead = self._get_lead(pk, user)
        if lead is None:
            return Response(
                {"success": False, "message": "Lead not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LeadWriteSerializer(
            lead, data=request.data, partial=partial, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            lead.refresh_from_db()
            return Response(
                {
                    "success": True,
                    "message": "Lead updated successfully.",
                    "data": LeadReadSerializer(lead).data,
                }
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk, *args, **kwargs):
        user = _get_current_user(request)
        lead = self._get_lead(pk, user)
        if lead is None:
            return Response(
                {"success": False, "message": "Lead not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ticket = lead.ticket_number
        lead.delete()
        return Response(
            {"success": True, "message": f"Lead {ticket} deleted successfully."},
            status=status.HTTP_200_OK,
        )