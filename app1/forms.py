from django import forms
from .models import Branch, Requirement, Lead, User,LeadRequirementAmount
from django.utils.html import format_html
from django.utils.safestring import mark_safe

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter Branch Name'}),
        }

class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter Requirement Name'}),
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Password (leave empty to keep current password)',
        }),
        label="Password",
        required=False
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        empty_label="Select Branch",
        label="Branch",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    class Meta:
        model = User
        fields = ['name', 'userid', 'password', 'branch']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Full Name',
            }),
            'userid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter User ID',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.edit_mode = kwargs.pop('edit_mode', False)
        super(UserForm, self).__init__(*args, **kwargs)
        
        for field in self.fields:
            if field == 'password':
                self.fields[field].required = False
            else:
                self.fields[field].required = True
                
        if self.edit_mode:
            self.fields['password'].widget.attrs['placeholder'] = 'Leave empty to keep current password'

    def clean_userid(self):
        userid = self.cleaned_data.get('userid')
        if self.instance and self.instance.pk:
            if User.objects.filter(userid=userid).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This User ID already exists. Please choose a different one.")
        else:
            if User.objects.filter(userid=userid).exists():
                raise forms.ValidationError("This User ID already exists. Please choose a different one.")
        return userid

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if self.cleaned_data.get('password'):
            user.password = self.cleaned_data['password']
        elif self.instance and self.instance.pk:
            user.password = User.objects.get(pk=self.instance.pk).password
            
        if commit:
            user.save()
        return user

from django import forms
from .models import Lead, Requirement, LeadRequirementAmount
from django.utils.safestring import mark_safe
import json

class DropdownCheckboxWidget(forms.SelectMultiple):
    """
    Custom widget to render a dropdown with checkboxes.
    """
    template_name = "widgets/dropdown_checkbox.html"

    def render(self, name, value, attrs=None, renderer=None):
        value = value or []
        final_attrs = self.build_attrs(attrs, name=name)
        final_attrs['id'] = final_attrs.get('id', 'id_' + name)
        options = self.get_context(name, value, attrs)['widget']['optgroups']
        rendered = []

        for group_name, options, index in options:
            for option in options:
                rendered.append(
                    f"<input type='checkbox' name='{name}' value='{option['value']}' "
                    f"{'checked' if option['selected'] else ''} id='{final_attrs['id']}_{index}' />"
                    f"<label for='{final_attrs['id']}_{index}'>{option['label']}</label>"
                )

        dropdown = f"<select class='form-select' id='{final_attrs['id']}' style='display: none;'>" + \
                   "".join(rendered) + "</select>"

        return mark_safe(dropdown)


from django import forms
from .models import Lead, LeadRequirementAmount
import json

class LeadForm(forms.ModelForm):
    requirement_amounts_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    # requirement_remarks = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Lead
        fields = [
            'firm_name', 'customer_name', 'contact_number',
            'location', 'district', 'business_nature', 'requirements',
            'follow_up_required', 'quotation_required', 'image', 'remarks'
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Firm Name'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Customer Name'}),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Contact Number',
                'type': 'tel'  # Specify the input type as 'tel'
            }),

            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Location'}),
            'district': forms.Select(attrs={'class': 'form-select'}),
            'business_nature': forms.Select(attrs={'class': 'form-select'}),
            'requirements': DropdownCheckboxWidget(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': False}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            self.save_m2m()

            # Handle the requirement amounts data
            requirement_amounts = self.cleaned_data.get('requirement_amounts_data', '')
            if requirement_amounts:
                try:
                    amounts_data = json.loads(requirement_amounts)
                except json.JSONDecodeError:
                    amounts_data = {}

                # Delete existing LeadRequirementAmount entries for this lead
                LeadRequirementAmount.objects.filter(lead=instance).delete()

                # Create new LeadRequirementAmount entries
                for req_id, amount in amounts_data.items():
                    try:
                        req_id = int(req_id)
                        amount = float(amount) if amount else 0.0
                        
                        LeadRequirementAmount.objects.create(
                            lead=instance,
                            requirement_id=req_id,
                            amount=amount
                        )
                    except (ValueError, TypeError):
                        continue

        return instance 