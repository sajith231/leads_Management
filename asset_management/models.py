from django.db import models


class Asset(models.Model):

    CATEGORY_CHOICES = [
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
        ('Mobile / Tablet', 'Mobile / Tablet'),
        ('Monitor', 'Monitor'),
        ('Printer / Scanner', 'Printer / Scanner'),
        ('Networking Equipment', 'Networking Equipment'),
        ('Vehicle', 'Vehicle'),
        ('Furniture', 'Furniture'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
    ]

    # --- Core identification ---
    asset_id       = models.CharField(max_length=50, unique=True)          # e.g. AST-2025-001
    name           = models.CharField(max_length=200)
    category       = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # --- Purchase info ---
    brand          = models.CharField(max_length=100, blank=True)
    model_number   = models.CharField(max_length=100, blank=True)
    serial_number  = models.CharField(max_length=100, blank=True)
    purchase_date  = models.DateField(null=True, blank=True)
    purchase_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    warranty_expiry = models.DateField(null=True, blank=True)

    # --- Technical specifications ---
    spec_cpu     = models.CharField(max_length=100, blank=True)
    spec_ram     = models.CharField(max_length=100, blank=True)
    spec_storage = models.CharField(max_length=100, blank=True)
    spec_display = models.CharField(max_length=100, blank=True)
    spec_os      = models.CharField(max_length=100, blank=True)
    spec_color   = models.CharField(max_length=100, blank=True)

    # --- Image ---
    image = models.ImageField(upload_to='assets/images/', blank=True, null=True)

    # --- Status & notes ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    notes  = models.TextField(blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'

    def __str__(self):
        return f"{self.asset_id} – {self.name}"

    def to_dict(self):
        """Serialize to the JS-compatible dict the frontend expects."""
        return {
            'id':           self.asset_id,
            'name':         self.name,
            'category':     self.category,
            'brand':        self.brand,
            'model':        self.model_number,
            'serial':       self.serial_number,
            'purchaseDate': self.purchase_date.isoformat() if self.purchase_date else '',
            'value':        float(self.purchase_value),
            'warranty':     self.warranty_expiry.isoformat() if self.warranty_expiry else '',
            'specs': {
                'cpu':     self.spec_cpu,
                'ram':     self.spec_ram,
                'storage': self.spec_storage,
                'display': self.spec_display,
                'os':      self.spec_os,
                'color':   self.spec_color,
            },
            'image':  self.image.url if self.image else '',
            'notes':  self.notes,
            'status': self.status,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Assignment  — links an employee (User) to an Asset for a period of time
# ──────────────────────────────────────────────────────────────────────────────

class Assignment(models.Model):
    """
    Records an asset being assigned to an employee, including any
    spec notes captured at the time of assignment and the expected
    (or actual) return date.
    """

    # The asset being assigned
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='assignments',
    )

    # Employee who received the asset.
    # Stored as a CharField so the app is not hard-coupled to a specific User model.
    # Store the user's PK as a string; resolve in views via your own User model.
    employee_id   = models.CharField(max_length=50)       # PK of the user
    employee_name = models.CharField(max_length=200)      # cached for fast display
    department    = models.CharField(max_length=200, blank=True)

    # Free-form spec/condition notes captured at assignment time.
    # Stored as comma-separated tags, e.g. "32GB RAM,M3 Pro,1TB SSD"
    spec_details = models.CharField(max_length=500, blank=True)

    # Attachment uploaded at time of assignment (e.g. handover document / photo)
    attachment = models.FileField(upload_to='assignments/attachments/', blank=True, null=True)

    # Dates
    assigned_date = models.DateField(auto_now_add=True)
    return_date   = models.DateField(null=True, blank=True)

    # Who physically returned the asset (optional)
    returned_by_id   = models.CharField(max_length=50, blank=True)
    returned_by_name = models.CharField(max_length=200, blank=True)

    # Document uploaded at time of return (e.g. return receipt / inspection photo)
    return_document = models.FileField(upload_to='assignments/return_docs/', blank=True, null=True)

    # Extra notes
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def __str__(self):
        return f"{self.asset.asset_id} → {self.employee_name}"

    def to_dict(self):
        """Serialize to the JS-compatible dict the frontend (asset_list.html) expects."""
        return {
            'id':             self.pk,
            'emp':            self.employee_name,
            'emp_id':         self.employee_id,
            'dept':           self.department,
            'asset':          self.asset.name,
            'assetId':        self.asset.asset_id,
            # specs stored as comma-separated string → list for the JS frontend
            'specs':          [s.strip() for s in self.spec_details.split(',') if s.strip()],
            'attachment':     self.attachment.url if self.attachment else '',
            'returnDate':     self.return_date.isoformat() if self.return_date else '',
            'returnedBy':     self.returned_by_name or '',
            'returnedById':   self.returned_by_id or '',
            'returnDocument': self.return_document.url if self.return_document else '',
            'image':          self.asset.image.url if self.asset.image else '',
            'assetStatus':    self.asset.status,
            'notes':          self.notes,
        }