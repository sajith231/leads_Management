# public_folder/models.py
import uuid
from django.db import models

def public_upload_path(instance, filename):
    # stored under MEDIA_ROOT/public_uploads/<uuid>_<cleanname>
    from django.utils.text import get_valid_filename
    safe = get_valid_filename(filename).replace(" ", "_")
    return f"public_uploads/{instance.id.hex}_{safe}"

class PublicUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=public_upload_path)
    provided_name = models.CharField(max_length=255, blank=True, help_text="Optional filename entered by uploader")
    original_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    client_name = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.provided_name or self.original_name or self.file.name
