from django.db import models


# app2/models.py

from django.db import models
from app1.models import Branch
from app1.models import User
  
class License(models.Model):
    name             = models.CharField(max_length=255)
    branch           = models.ForeignKey(Branch, on_delete=models.CASCADE)
    service_pack     = models.CharField(max_length=255, blank=True, null=True)
    place            = models.CharField(max_length=255, blank=True, null=True)
    type             = models.CharField(max_length=255, blank=True, null=True)
    number_of_system = models.CharField(max_length=50, blank=True, null=True)
    module           = models.CharField(max_length=255, blank=True, null=True)
    notes            = models.TextField(blank=True, null=True)

    license_key = models.TextField()
    file_name   = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        display = self.file_name or self.name
        return f"{display} ({self.branch.name})"



class Printer(models.Model):
    name = models.CharField(max_length=100)




class KeyRequest(models.Model):
    KEY_TYPES = [
        ("Seat Upgradation Request", "Seat Upgradation Request"),
        ("More Module Request", "More Module Request"),
        ("Trade Name And Address Change Request", "Trade Name And Address Change Request"),
        ("Key type Change Request", "Key type Change Request"),
        ("Key Extension Request", "Key Extension Request"),
        ("Hosted Key Request", "Hosted Key Request"),
        ("Feeder Cancellation Request", "Feeder Cancellation Request"),
        ("Demo Key Request", "Demo Key Request"),
        ("Software Amount Change Request", "Software Amount Change Request"),
        ("Maturity Upgradation Request", "Maturity Upgradation Request"),
        ("Enterprises Key Request", "Enterprises Key Request"),
        ("Image Request", "Image Request"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("On Process", "On Process"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    ]

    REQUESTED_STATUS_CHOICES = [
        ("Requested", "Requested"),
        ("Pending", "Pending"),
        ("Delayed", "Delayed"),
        ("Rejected", "Rejected"),
        ("Working on it", "Working on it"),
        ("Work completed/No payment", "Work completed/No payment"),
        ("Work completed/Payment pending", "Work completed/Payment pending"),
        ("Work done & Payment collected", "Work done & Payment collected"),
    ]

    clientName = models.CharField(max_length=255)
    requested_by = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    keyType = models.CharField(max_length=255, choices=KEY_TYPES)
    requestDate = models.DateField(null=True, blank=True)
    gps_location = models.CharField(max_length=100, blank=True, null=True)
    gps_address = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending"
    )
    requested_status = models.CharField(
        max_length=50,
        choices=REQUESTED_STATUS_CHOICES,
        default="Requested"
    )

    requestImage = models.ImageField(
        upload_to="key_request_images/", blank=True, null=True
    )
    
    # Changed from foreign key to simple text field
    branch_name = models.CharField(max_length=200, blank=True, null=True)
    
    amount = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.clientName} - {self.keyType} ({self.requestDate})"






class Collection(models.Model):
    """Payment-collection record with verification status."""

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_VERIFIED, "Verified"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Collection verification status",
    )

    # ------------------------------------------------------------------
    # Collection Type (NEW)
    # ------------------------------------------------------------------
    TYPE_CASH    = "cash"
    TYPE_ONLINE  = "online"
    TYPE_CHEQUE  = "cheque"

    COLLECTION_TYPE_CHOICES = [
        (TYPE_CASH,   "By Cash"),
        (TYPE_ONLINE, "Online Payment"),
        (TYPE_CHEQUE, "Cheque"),
    ]

    collection_type = models.CharField(
        max_length=10,
        choices=COLLECTION_TYPE_CHOICES,
        default=TYPE_CASH,
        help_text="Payment mode used by the client",
    )

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    client_name = models.CharField(max_length=255, help_text="Name of the client")
    branch = models.CharField(max_length=255, help_text="Branch name")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Amount collected"
    )
    paid_for = models.CharField(max_length=255, help_text="What the payment was for")
    payment_screenshot = models.ImageField(
        upload_to="payment_screenshots/", help_text="Screenshot of the payment"
    )
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    created_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="User who created this collection",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def __str__(self):
        return f"{self.client_name} - ₹{self.amount} ({self.get_status_display()})"

    @property
    def is_pending(self) -> bool:
        return self.status == self.STATUS_PENDING

    @property
    def is_verified(self) -> bool:
        return self.status == self.STATUS_VERIFIED

    def get_amount_display(self) -> str:
        return f"₹{self.amount:,.2f}"

    def get_short_notes(self) -> str:
        if not self.notes:
            return ""
        return (
            self.notes[:50] + "…" if len(self.notes) > 50 else self.notes
        )

    def get_status_badge_class(self) -> str:
        """Bootstrap-5 class for the status badge."""
        return (
            "bg-success" if self.is_verified else "bg-warning text-dark"
        )

    # ---------------------------------------------------------
    # NEW: tiny helper for templates / admin
    # ---------------------------------------------------------
    def requires_proof(self) -> bool:
        """Returns True when the payment mode demands an upload."""
        return self.collection_type in {self.TYPE_ONLINE, self.TYPE_CHEQUE}