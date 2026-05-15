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
    asset_id  = models.CharField(max_length=50, unique=True)   # e.g. AST-2025-001
    name      = models.CharField(max_length=200)
    category  = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # --- Department ---
    department = models.ForeignKey(
        'purchase_order.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        verbose_name='Department',
    )

    # --- Purchase info ---
    brand           = models.CharField(max_length=100, blank=True)
    model_number    = models.CharField(max_length=100, blank=True)
    serial_number   = models.CharField(max_length=100, blank=True)
    purchase_date   = models.DateField(null=True, blank=True)
    purchase_value  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    warranty_expiry = models.DateField(null=True, blank=True)

    # --- Technical specifications ---
    spec_cpu     = models.CharField(max_length=100, blank=True)
    spec_ram     = models.CharField(max_length=100, blank=True)
    spec_storage = models.CharField(max_length=100, blank=True)
    spec_display = models.CharField(max_length=100, blank=True)
    spec_os      = models.CharField(max_length=100, blank=True)
    spec_color   = models.CharField(max_length=100, blank=True)

    # --- Image ---
    image = models.ImageField(
        upload_to='assets/images/',
        blank=True,
        null=True,
        help_text='Optional photo of the asset (JPEG/PNG recommended).',
    )

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

    def get_image_url(self, request=None):
        if not self.image:
            return ''
        url = self.image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def to_dict(self, request=None):
        return {
            'id':       self.asset_id,
            'name':     self.name,
            'category': self.category,
            'departmentId':   self.department_id or '',
            'departmentName': self.department.name if self.department else '',
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
            'image':  self.get_image_url(request),
            'notes':  self.notes,
            'status': self.status,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Assignment
# ─────────────────────────────────────────────────────────────────────────────

class Assignment(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='assignments',
    )

    employee_id   = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    department    = models.CharField(max_length=200, blank=True)

    spec_details = models.CharField(max_length=500, blank=True)

    attachment = models.FileField(upload_to='assignments/attachments/', blank=True, null=True)

    assigned_date = models.DateField(auto_now_add=True)
    return_date   = models.DateField(null=True, blank=True)

    returned_by_id   = models.CharField(max_length=50, blank=True)
    returned_by_name = models.CharField(max_length=200, blank=True)

    # Primary return document (kept for backward-compat; new multi-image flow
    # saves to AssignmentReturnImage instead, but the first image is also stored
    # here so existing queries / to_dict() continue to work unchanged).
    return_document = models.FileField(upload_to='assignments/return_docs/', blank=True, null=True)

    return_condition = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def __str__(self):
        return f"{self.asset.asset_id} → {self.employee_name}"

    def to_dict(self, request=None):
        def file_url(field):
            """Return absolute URL for a file field, or ''."""
            if not field:
                return ''
            url = field.url
            return request.build_absolute_uri(url) if request else url

        return {
            'id':             self.pk,
            'emp':            self.employee_name,
            'emp_id':         self.employee_id,
            'dept':           self.department,
            'asset':          self.asset.name,
            'assetId':        self.asset.asset_id,
            'specs':          [s.strip() for s in self.spec_details.split(',') if s.strip()],
            'attachment':     file_url(self.attachment),
            'returnDate':     self.return_date.isoformat() if self.return_date else '',
            'returnedBy':     self.returned_by_name or '',
            'returnedById':   self.returned_by_id or '',
            'returnDocument': file_url(self.return_document),
            'returnCondition': self.return_condition,
            # All return images (new multi-upload)
            'returnImages': [
                file_url(img.image)
                for img in self.return_images.all()
                if img.image
            ],
            # Multiple images uploaded at assignment time
            'images': [
                file_url(img.image)
                for img in self.assignment_images.all()
                if img.image
            ],
            'image':       self.asset.get_image_url(request),
            'assetStatus': self.asset.status,
            'notes':       self.notes,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  AssignmentImage  — stores multiple photos uploaded at assignment time
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentImage(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='assignment_images',
    )
    image = models.ImageField(
        upload_to='assignments/attachments/',
        help_text='Photo uploaded at time of assignment.',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Assignment Image'
        verbose_name_plural = 'Assignment Images'

    def __str__(self):
        return f"Image for {self.assignment} — {self.pk}"


# ─────────────────────────────────────────────────────────────────────────────
#  AssignmentReturnImage  — stores multiple photos uploaded at return time
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentReturnImage(models.Model):
    """
    One row per image uploaded when an asset is returned.
    Related to Assignment via the 'return_images' reverse name.

    Usage in a view:
        for f in request.FILES.getlist('return_images'):
            AssignmentReturnImage.objects.create(assignment=assignment, image=f)
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='return_images',
    )
    image = models.ImageField(
        upload_to='assignments/return_images/',
        help_text='Photo taken at time of return (JPEG/PNG recommended).',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Assignment Return Image'
        verbose_name_plural = 'Assignment Return Images'

    def __str__(self):
        return f"Return image for {self.assignment} — {self.pk}"