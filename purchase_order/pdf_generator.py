from io import BytesIO
import os
from django.template.loader import render_to_string
from django.conf import settings
from xhtml2pdf import pisa


# -------------------------
# INTERNAL HELPERS
# -------------------------

def _logo_path(po):
    """Return absolute filesystem path to the logo."""
    try:
        if po.department and getattr(po.department, 'logo', None):
            return os.path.join(settings.MEDIA_ROOT, str(po.department.logo))
    except Exception:
        return ""
    return ""


def _location(po):
    """Return 'City, State - Pincode'."""
    d = po.department
    parts = []
    if not d:
        return ""

    if getattr(d, 'city', None):
        parts.append(d.city)
    if getattr(d, 'state', None):
        parts.append(d.state)
    if getattr(d, 'pincode', None):
        parts.append(f"- {d.pincode}")

    return ", ".join(parts)


def get_po_context(po):
    """Common context passed to PDF templates."""
    return {
        'po': po,
        'department': getattr(po, 'department', None),
        'supplier': getattr(po, 'supplier', None),
        'items': po.po_items.all(),
        'location': _location(po),
        'logo_path': _logo_path(po),
    }


# -------------------------
# MAIN PDF GENERATOR
# -------------------------

def generate_pdf_from_template(po, template_name='purchase_order/pdf_templates/format_1.html'):
    """
    Renders the template + context and writes a PDF to MEDIA_ROOT/po_pdfs.
    Returns file path.
    """
    context = get_po_context(po)
    html = render_to_string(template_name, context)

    # Ensure output directory exists
    pdf_dir = os.path.join(settings.MEDIA_ROOT, "po_pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    # Create safe filename
    supplier_name = (po.supplier.name if po.supplier else "SUPPLIER").replace(" ", "_")
    filename = f"{supplier_name}_{po.po_number}.pdf"
    file_path = os.path.join(pdf_dir, filename)

    # Create PDF
    with open(file_path, "wb") as output:
        pisa_status = pisa.CreatePDF(
            html,
            dest=output,
            link_callback=_link_callback
        )

    if pisa_status.err:
        # delete corrupt file if any
        try:
            os.remove(file_path)
        except:
            pass
        raise Exception("xhtml2pdf failed to generate PDF")

    return file_path


def render_pdf_bytes(po, template_name='purchase_order/pdf_templates/format_1.html'):
    """
    Render PDF into memory (bytes). Used for WhatsApp/email sending.
    """
    context = get_po_context(po)
    html = render_to_string(template_name, context)

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result, link_callback=_link_callback)

    if pisa_status.err:
        raise Exception("xhtml2pdf failed to render PDF bytes")

    result.seek(0)
    return result.getvalue()


# -------------------------
# Resolve STATIC/MEDIA paths for xhtml2pdf
# -------------------------

def _link_callback(uri, rel):
    """
    Convert URIs used in HTML (STATIC_URL, MEDIA_URL, file:///) 
    into absolute local file paths for xhtml2pdf.
    """

    # Handle file:///C:/.. paths
    if uri.startswith("file:///"):
        return uri.replace("file:///", "")

    # If it's an absolute path and exists
    if os.path.isabs(uri) and os.path.exists(uri):
        return uri

    media_url = settings.MEDIA_URL
    static_url = settings.STATIC_URL

    # MEDIA file
    if uri.startswith(media_url):
        path = uri.replace(media_url, "")
        return os.path.join(settings.MEDIA_ROOT, path)

    # STATIC file
    if uri.startswith(static_url):
        path = uri.replace(static_url, "")
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            return os.path.join(static_root, path)

    # Fallback: BASE_DIR + uri
    base_dir = settings.BASE_DIR
    fallback_path = os.path.join(base_dir, uri.lstrip("/"))
    if os.path.exists(fallback_path):
        return fallback_path

    return uri