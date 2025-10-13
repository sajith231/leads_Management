from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from django.views.decorators.http import require_http_methods
from .models import DriveFolder, DriveFile
import mimetypes
import os


# ---------- Helpers ----------
def _breadcrumbs(folder):
    trail = []
    node = folder
    while node:
        trail.append(node)
        node = node.parent
    return list(reversed(trail))


# ---------- Folder Views ----------
def drive_list(request):
    folders = DriveFolder.objects.filter(parent__isnull=True)
    return render(request, "drive_list.html", {"folders": folders})


def drive_add(request):
    if request.method == "POST":
        folder_name = (request.POST.get("folderName") or "").strip()
        if folder_name:
            DriveFolder.objects.create(name=folder_name)
            return redirect("drive_list")
    return render(request, "drive_add.html")


def drive_delete(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)
    parent = folder.parent
    folder.delete()
    if parent:
        return redirect("drive_detail", pk=parent.pk)
    return redirect("drive_list")


@require_http_methods(["GET", "POST"])
def drive_detail(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)

    # Handle file upload (with optional custom name)
    if request.method == "POST" and request.FILES.get("fileUpload"):
        uploaded_file = request.FILES["fileUpload"]
        custom_name = (request.POST.get("file_name") or "").strip()

        DriveFile.objects.create(
            folder=folder,
            file=uploaded_file,
            file_name=custom_name if custom_name else None
        )
        return redirect("drive_detail", pk=folder.pk)

    subfolders = folder.subfolders.all()
    files = folder.files.all()
    crumbs = _breadcrumbs(folder)

    template_name = "subfolder_detail.html" if folder.parent else "drive_detail.html"

    return render(
        request,
        template_name,
        {
            "folder": folder,
            "subfolders": subfolders,
            "files": files,
            "breadcrumbs": crumbs,
        },
    )


def subfolder_add(request, parent_pk):
    parent = get_object_or_404(DriveFolder, pk=parent_pk)

    if parent.parent is not None:
        return redirect("drive_detail", pk=parent.pk)

    if request.method == "POST":
        name = (request.POST.get("folderName") or "").strip()
        if name:
            DriveFolder.objects.create(name=name, parent=parent)
            return redirect("drive_detail", pk=parent.pk)

    return redirect("drive_detail", pk=parent.pk)


def subfolder_delete(request, pk):
    """Delete a subfolder and redirect back to its parent folder."""
    subfolder = get_object_or_404(DriveFolder, pk=pk)
    parent = subfolder.parent
    if request.method == "POST":
        subfolder.delete()
    if parent:
        return redirect("drive_detail", pk=parent.pk)
    return redirect("drive_list")


# ---------- File Views ----------
def file_delete(request, pk):
    f = get_object_or_404(DriveFile, pk=pk)
    folder_id = f.folder.id
    f.delete()
    return redirect("drive_detail", pk=folder_id)


def file_edit(request, pk):
    """Rename file (from popup modal)."""
    f = get_object_or_404(DriveFile, pk=pk)
    if request.method == "POST":
        new_name = (request.POST.get("file_name") or "").strip()
        if new_name:
            f.file_name = new_name
            f.save()
    return redirect("drive_detail", pk=f.folder.id)


def file_preview(request, pk):
    f = get_object_or_404(DriveFile, pk=pk)
    file_path = f.file.path
    file_handle = open(file_path, "rb")
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    response = FileResponse(file_handle, content_type=content_type)

    # Use custom name if available, otherwise fallback
    filename = f.file_name if f.file_name else os.path.basename(f.file.name)
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def drive_edit(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)

    if request.method == "POST":
        new_name = (request.POST.get("folderName") or "").strip()
        if new_name:
            folder.name = new_name
            folder.save()
            return redirect("drive_list")

    return render(request, "drive_add.html", {"folder": folder, "mode": "edit"})
