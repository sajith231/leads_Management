from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from django.views.decorators.http import require_http_methods
from .models import DriveFolder, DriveFile
import mimetypes
import os
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# ---------- Helpers ----------

def _breadcrumbs(folder):
    """Build breadcrumb trail for a folder."""
    trail = []
    node = folder
    while node:
        trail.append(node)
        node = node.parent
    return list(reversed(trail))


def _response_filename(f: DriveFile) -> str:
    """
    Returns the correct filename (ensures the file has its extension).
    Example: if user renamed 'Report' for a PDF, returns 'Report.pdf'
    """
    display_name = f.file_name.strip() if f.file_name else os.path.basename(f.file.name)
    display_ext = os.path.splitext(display_name)[1]
    real_ext = os.path.splitext(f.file.name)[1]
    if not display_ext and real_ext:
        display_name = f"{display_name}{real_ext}"
    return display_name


# ---------- Folder Views ----------
def drive_list(request):
    query = request.GET.get("q", "").strip()
    page_num = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", "10")

    try:
        per_page = int(per_page)
        if per_page not in [10, 15, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    folders_qs = DriveFolder.objects.filter(parent__isnull=True).order_by('name')
    if query:
        folders_qs = folders_qs.filter(name__icontains=query)

    paginator = Paginator(folders_qs, per_page)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        "drive_list.html",
        {
            "folders": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "query": query,
            "per_page": per_page,
        },
    )



def drive_add(request):
    if request.method == "POST":
        folder_name = (request.POST.get("folderName") or "").strip()

        if folder_name:
            if DriveFolder.objects.filter(name__iexact=folder_name, parent__isnull=True).exists():
                messages.error(request, f'A folder named "{folder_name}" already exists.')
                return render(request, "drive_add.html", {"folder_name": folder_name})

            DriveFolder.objects.create(name=folder_name)
            messages.success(request, f'Folder "{folder_name}" created successfully!')
            return redirect("drive_list")
        else:
            messages.error(request, "Folder name cannot be empty.")

    return render(request, "drive_add.html")


def drive_delete(request, pk):
    """Prevent deletion if subfolders exist."""
    folder = get_object_or_404(DriveFolder, pk=pk)
    parent = folder.parent

    if folder.subfolders.exists():
        messages.error(request, "Cannot delete folder that contains subfolders.")
        if parent:
            return redirect("drive_detail", pk=parent.pk)
        return redirect("drive_list")

    folder.delete()
    return redirect("drive_detail", pk=parent.pk) if parent else redirect("drive_list")


from django.db.models import Count, Q


@require_http_methods(["GET", "POST"])
def drive_detail(request, pk):
    folder = get_object_or_404(DriveFolder, pk=pk)

    # Handle file upload (unchanged)
    if request.method == "POST" and request.FILES.get("fileUpload"):
        uploaded_file = request.FILES["fileUpload"]
        custom_name = (request.POST.get("file_name") or "").strip()

        DriveFile.objects.create(
            folder=folder,
            file=uploaded_file,
            file_name=custom_name if custom_name else None
        )
        return redirect("drive_detail", pk=folder.pk)

    subfolders = folder.subfolders.annotate(file_count=Count("files"))

    # NEW: search across ALL files in this folder
    query = (request.GET.get("q") or "").strip()

    files_qs = folder.files.all().order_by("-uploaded_at")
    if query:
        files_qs = files_qs.filter(
            Q(file_name__icontains=query) |
            Q(file__icontains=query)  # matches original filename within the stored path
        )

    # per_page (same logic you already had)
    per_page = request.GET.get("per_page", "10")
    try:
        per_page = int(per_page)
        if per_page not in [10, 15, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    paginator = Paginator(files_qs, per_page)
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
            "files": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "breadcrumbs": crumbs,
            "query": query,          # <-- pass it through
            "per_page": per_page,    # <-- handy for drive_detail template
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
    """Delete a subfolder and redirect back to its parent."""
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
    """Rename file (popup modal)."""
    f = get_object_or_404(DriveFile, pk=pk)
    if request.method == "POST":
        new_name = (request.POST.get("file_name") or "").strip()
        if new_name:
            f.file_name = new_name
            f.save()
    return redirect("drive_detail", pk=f.folder.id)


def file_edit_page(request, pk):
    """Standalone page for renaming a file."""
    f = get_object_or_404(DriveFile, pk=pk)

    if request.method == "POST":
        new_name = (request.POST.get("file_name") or "").strip()
        if new_name:
            f.file_name = new_name
            f.save()
            return redirect("drive_detail", pk=f.folder.id)

    return render(request, "edit_thename.html", {"file": f})


def file_preview(request, pk):
    """Serve a file inline with proper extension in filename."""
    f = get_object_or_404(DriveFile, pk=pk)
    file_path = f.file.path
    file_handle = open(file_path, "rb")
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    response = FileResponse(file_handle, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{_response_filename(f)}"'
    return response


def file_download(request, pk):
    f = get_object_or_404(DriveFile, pk=pk)
    file_path = f.file.path

    filename = _response_filename(f)   # ✅ Ensures extension always added

    response = FileResponse(open(file_path, "rb"))
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def drive_edit(request, pk):
    """Edit folder name."""
    folder = get_object_or_404(DriveFolder, pk=pk)

    if request.method == "POST":
        new_name = (request.POST.get("folderName") or "").strip()
        if new_name:
            folder.name = new_name
            folder.save()
            return redirect("drive_list")

    return render(request, "drive_add.html", {"folder": folder, "mode": "edit"})




from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.cache import cache
import random

from .models import DriveFile
from django.utils import timezone
import random

def generate_share_code(request, pk):
    file = get_object_or_404(DriveFile, pk=pk)

    code = str(random.randint(1000, 9999))
    expiry = timezone.now() + timezone.timedelta(minutes=1)

    file.share_code = code
    file.share_expiry = expiry
    file.save()

    share_link = request.build_absolute_uri(
        f"/my_drive/drives/share/{file.id}/"
    )

    return JsonResponse({
        "code": code,
        "expires_in": "1 minute",
        "link": share_link
    })



from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect

def verify_share_code(request, pk):
    file = get_object_or_404(DriveFile, pk=pk)

    # ❗ If direct open without code => show code input page
    if request.method == "GET":
        return render(request, "enter_code.html")

    # POST --> Check code
    entered = request.POST.get("code", "").strip()

    # If expired
    if not file.share_expiry or timezone.now() > file.share_expiry:
        return render(request, "enter_code.html", {
            "error": "Code expired! Generate a new one."
        })

    # Wrong code
    if entered != file.share_code:
        return render(request, "enter_code.html", {
            "error": "Invalid code! Try again."
        })

    # ✅ Correct → download
    filename = _response_filename(file)
    response = FileResponse(open(file.file.path, "rb"))
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
