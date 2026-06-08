"""
lead_form_api/serializers.py

Serializers for Lead and RequirementItem models.
"""

import datetime
from rest_framework import serializers
from app5.models import Lead, RequirementItem


class FlexibleDateField(serializers.Field):
    """
    Accepts both date and datetime values from the DB and always
    returns a plain YYYY-MM-DD string — avoids DRF's strict
    'Expected date, got datetime' assertion error.
    """
    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date().isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    def to_internal_value(self, data):
        if isinstance(data, datetime.datetime):
            return data.date()
        if isinstance(data, datetime.date):
            return data
        try:
            return datetime.date.fromisoformat(str(data))
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid date format. Use YYYY-MM-DD.")


# ─────────────────────────────────────────────────────────────────────────────
# Requirement Item
# ─────────────────────────────────────────────────────────────────────────────

class RequirementItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementItem
        fields = [
            "id",
            "item_id",
            "item_name",
            "section",
            "unit",
            "price",
            "quantity",
            "total",
        ]
        read_only_fields = ["id", "total"]


# ─────────────────────────────────────────────────────────────────────────────
# Lead – write (create / update)
# ─────────────────────────────────────────────────────────────────────────────

class LeadWriteSerializer(serializers.ModelSerializer):
    """
    Accepts the same fields the web form posts, plus an optional
    `requirements` list so requirement items can be created together
    with the lead in one call.
    """

    requirements = RequirementItemSerializer(many=True, required=False, write_only=True)
    date = FlexibleDateField(required=False)

    class Meta:
        model = Lead
        fields = [
            # Common
            "customerType",
            "ownerName",
            "phoneNo",
            "email",
            # Business
            "name",
            "address",
            "place",
            "District",
            "State",
            "pinCode",
            # Individual
            "firstName",
            "lastName",
            "individualAddress",
            "individualPlace",
            "individualDistrict",
            "individualState",
            "individualPinCode",
            # Lead info
            "status",
            "priority",
            "refFrom",
            "business",
            "campaign",
            "marketedBy",
            "Consultant",
            "requirement",
            "details",
            "date",
            # Assignment
            "assignment_type",
            "assigned_to_name",
            "assigned_by_name",
            "assigned_date",
            "assigned_time",
            # Nested
            "requirements",
        ]
        extra_kwargs = {
            "ownerName": {"required": True},
            "phoneNo": {"required": True},
            "status": {"default": "Active"},
            "priority": {"default": "High"},
            "customerType": {"default": "Business"},
            "assignment_type": {"default": "unassigned"},
        }

    def create(self, validated_data):
        from decimal import Decimal
        from django.utils import timezone

        requirements_data = validated_data.pop("requirements", [])
        request = self.context.get("request")

        # Resolve created_by from session or token
        created_by = None
        if request:
            try:
                from app1.models import User as AppUser
                user_id = request.session.get("custom_user_id") or getattr(
                    getattr(request, "user", None), "id", None
                )
                if user_id:
                    created_by = AppUser.objects.filter(id=user_id).first()
            except Exception:
                pass

        lead = Lead.objects.create(**validated_data)

        if created_by:
            lead.created_by = created_by
            lead.save(update_fields=["created_by"])

        # Bulk-create requirement items
        for req in requirements_data:
            item_id = req.get("item_id")
            RequirementItem.objects.create(
                lead=lead,
                item_id=item_id,
                item_name=req.get("item_name", ""),
                ticket_number=lead.ticket_number,
                owner_name=lead.ownerName,
                phone_no=lead.phoneNo,
                email=lead.email or "",
                section=req.get("section", ""),
                unit=req.get("unit", "pcs"),
                price=Decimal(str(req.get("price", 0))),
                quantity=int(req.get("quantity", 1)),
            )

        return lead


# ─────────────────────────────────────────────────────────────────────────────
# Lead – read (list / detail)
# ─────────────────────────────────────────────────────────────────────────────

class LeadReadSerializer(serializers.ModelSerializer):
    requirements = RequirementItemSerializer(many=True, read_only=True)
    requirements_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()
    date = FlexibleDateField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "ticket_number",
            "customerType",
            "ownerName",
            "phoneNo",
            "email",
            # Business
            "name",
            "address",
            "place",
            "District",
            "State",
            "pinCode",
            # Individual
            "firstName",
            "lastName",
            "individualAddress",
            "individualPlace",
            "individualDistrict",
            "individualState",
            "individualPinCode",
            # Lead info
            "status",
            "priority",
            "refFrom",
            "business",
            "campaign",
            "marketedBy",
            "Consultant",
            "requirement",
            "details",
            "date",
            # Assignment
            "assignment_type",
            "assigned_to_name",
            "assigned_by_name",
            "assigned_date",
            "assigned_time",
            # Computed
            "display_name",
            "requirements_count",
            "time_elapsed",
            "created_at",
            "updated_at",
            # Nested
            "requirements",
        ]
        read_only_fields = fields

    def get_requirements_count(self, obj):
        try:
            return obj.requirements.count()
        except Exception:
            return 0

    def get_display_name(self, obj):
        if obj.customerType == "Business":
            return obj.name or obj.ownerName
        fullname = f"{obj.firstName or ''} {obj.lastName or ''}".strip()
        return fullname or obj.ownerName

    def get_time_elapsed(self, obj):
        from django.utils import timezone
        if not obj.created_at:
            return ""
        delta = timezone.now() - obj.created_at
        if delta.days > 365:
            y = delta.days // 365
            return f"{y} year{'s' if y > 1 else ''} ago"
        if delta.days > 30:
            m = delta.days // 30
            return f"{m} month{'s' if m > 1 else ''} ago"
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        if delta.seconds > 3600:
            h = delta.seconds // 3600
            return f"{h} hour{'s' if h > 1 else ''} ago"
        if delta.seconds > 60:
            mins = delta.seconds // 60
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        return "Just now"