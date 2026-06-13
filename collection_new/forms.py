from django import forms
from .models import Collection

PROOF_REQUIRED_TYPES = ('cheque', 'upi', 'bank_transfer')

COMPANY_CHOICES = [
    ('', 'Select Company'),
    ('Sysmac Computers', 'Sysmac Computers'),
    ('Sysmac Info',      'Sysmac Info'),
    ('IMCB LLP',         'IMCB LLP'),
]


class CollectionForm(forms.ModelForm):
    company = forms.ChoiceField(choices=COMPANY_CHOICES)

    class Meta:
        model  = Collection
        fields = [
            'company', 'department', 'client_name',
            'collection_type', 'amount', 'paid_for',
            'payment_proof', 'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        ctype = cleaned.get('collection_type')
        proof = cleaned.get('payment_proof')
        existing_proof = getattr(self.instance, 'payment_proof', None)

        if ctype in PROOF_REQUIRED_TYPES and not proof and not existing_proof:
            self.add_error('payment_proof',
                           f'Payment proof is required for {ctype.replace("_", " ").title()}.')
        return cleaned