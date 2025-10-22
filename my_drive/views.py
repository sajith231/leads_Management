from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from django.views.decorators.http import require_http_methods
from .models import DriveFolder, DriveFile
import mimetypes
import os
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Count  
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


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
    query = request.GET.get("q", "").strip()
    page_num = request.GET.get("page", 1)

    folders_qs = DriveFolder.objects.filter(parent__isnull=True)
    if query:
        folders_qs = folders_qs.filter(name__icontains=query)

    # paginate: change 10 to however many rows per page you want
    paginator = Paginator(folders_qs, 10)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, "drive_list.html", {
        "folders": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": query,
    })


  # (you already have this import)

def drive_add(request):
    if request.method == "POST":
        folder_name = (request.POST.get("folderName") or "").strip()

        if folder_name:
            # ✅ Check if a folder with this name already exists (case-insensitive)
            if DriveFolder.objects.filter(name__iexact=folder_name, parent__isnull=True).exists():
                messages.error(request, f'A folder named "{folder_name}" already exists. Please choose another name.')
                # Return to same page with the folder_name preserved
                return render(request, "drive_add.html", {"folder_name": folder_name})

            # ✅ Create folder if unique
            DriveFolder.objects.create(name=folder_name)
            messages.success(request, f'Folder "{folder_name}" created successfully!')
            return redirect("drive_list")

        else:
            # Optional — handle empty name submission (just in case)
            messages.error(request, "Folder name cannot be empty.")

    return render(request, "drive_add.html")



def drive_delete(request, pk):
    """
    Prevent deletion of a folder if it contains any subfolders.
    If no subfolders exist, delete and redirect to parent or drive_list.
    """
    folder = get_object_or_404(DriveFolder, pk=pk)
    parent = folder.parent

    # Server-side protection: don't allow delete if subfolders exist
    if folder.subfolders.exists():
        # Add a message so the user knows why it failed (if your templates show messages)
        messages.error(request, "Cannot delete folder because it contains subfolders. Remove subfolders first.")
        if parent:
            return redirect("drive_detail", pk=parent.pk)
        return redirect("drive_list")

    # Safe to delete
    folder.delete()
    return redirect("drive_detail", pk=parent.pk) if parent else redirect("drive_list")


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

    # ✅ Annotate subfolders with file count
    subfolders = folder.subfolders.annotate(file_count=Count("files"))

    # ✅ Add pagination for files
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    files_qs = folder.files.all().order_by('-uploaded_at')  # most recent first

    paginator = Paginator(files_qs, 10)  # Show 10 files per page
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    crumbs = _breadcrumbs(folder)

    template_name = "subfolder_detail.html" if folder.parent else "drive_detail.html"

    return render(
        request,
        template_name,
        {
            "folder": folder,
            "subfolders": subfolders,
            "files": page_obj.object_list,  # Only files for current page
            "page_obj": page_obj,
            "paginator": paginator,
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

def file_edit_page(request, pk):
    """Standalone page for renaming a file (edit_thename.html)."""
    f = get_object_or_404(DriveFile, pk=pk)

    if request.method == "POST":
        new_name = (request.POST.get("file_name") or "").strip()
        if new_name:
            f.file_name = new_name
            f.save()
            return redirect("drive_detail", pk=f.folder.id)

    return render(request, "edit_thename.html", {"file": f})

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


def file_download(request, pk):
    f = get_object_or_404(DriveFile, pk=pk)
    file_path = f.file.path
    file_handle = open(file_path, "rb")
    response = FileResponse(file_handle, as_attachment=True)
    filename = f.file_name if f.file_name else os.path.basename(f.file.name)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
