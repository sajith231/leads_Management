import os
from django.template.loader import render_to_string
from django.conf import settings
import pdfkit
from .wkhtml_config import config

class WKHTMLPDFGenerator:
    TEMPLATES = {
        'FORMAT_1': 'purchase_order/pdf_templates/format_1.html',
        'FORMAT_2': 'purchase_order/pdf_templates/format_2.html',
    }

    def __init__(self, po, pdf_format='FORMAT_1'):
        self.po = po
        self.pdf_format = pdf_format

    def _logo(self):
        if self.po.department.logo:
            return os.path.join(settings.MEDIA_ROOT, str(self.po.department.logo))
        return ""

    def _location(self):
        d = self.po.department
        parts = []
        if d.city: parts.append(d.city)
        if d.state: parts.append(d.state)
        if d.pincode: parts.append(f"- {d.pincode}")
        return ", ".join(parts)

    def generate(self):
        html = render_to_string(
            self.TEMPLATES[self.pdf_format],
            {
                'po': self.po,
                'department': self.po.department,
                'supplier': self.po.supplier,
                'items': self.po.po_items.all(),
                'location': self._location(),
                'logo_path': self._logo(),
            }
        )

        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'po_pdfs')
        os.makedirs(pdf_dir, exist_ok=True)

        file_path = os.path.join(
            pdf_dir,
            f"{self.po.po_number}_{self.po.supplier.name.replace(' ', '_')}.pdf"
        )

        pdfkit.from_string(
            html,
            file_path,
            configuration=config,
            options={
                'page-size': 'A4',
                'encoding': 'UTF-8',
                'enable-local-file-access': None
            }
        )

        return file_path
