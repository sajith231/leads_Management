from django.db import models
from django.core.exceptions import ValidationError


class DriveFolder(models.Model):
    """
    A folder can be a root (parent=None) or a subfolder (parent -> DriveFolder).
    Names are unique within the same parent.
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="subfolders",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"], name="uniq_folder_name_per_parent"
            )
        ]
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.path

    # ---- Safety net: disallow depth > 1 ----
    def clean(self):
        """
        Enforce max depth = 1:
        - Allowed: root folder (parent=None)
        - Allowed: first-level subfolder (parent exists, but parent.parent is None)
        - Blocked: any folder whose parent already has a parent
        """
        if self.parent and self.parent.parent:
            raise ValidationError("Nested subfolders beyond one level are not allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def ancestors(self):
        chain = []
        node = self
        while node:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))

    @property
    def path(self) -> str:
        return "/".join([f.name for f in self.ancestors])


class DriveFile(models.Model):
    folder = models.ForeignKey(
        DriveFolder,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="uploads/")
    file_name = models.CharField(max_length=255, blank=True)  # ✅ display name
    share_code = models.CharField(max_length=4, blank=True, null=True)
    share_expiry = models.DateTimeField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        indexes = [
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["folder"]),
        ]

    def save(self, *args, **kwargs):
        # Default display name if empty
        if not self.file_name and self.file:
            self.file_name = self.file.name.split("/")[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file_name or self.file.name} ({self.folder.path})"
