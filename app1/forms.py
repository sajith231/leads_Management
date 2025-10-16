from django import forms
from .models import Branch, Requirement, Lead, User,LeadRequirementAmount,District,Area,Location,Hardware,LeadHardwarePrice,Complaint
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User as DjangoUser

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

class DistrictForm(forms.ModelForm):
    class Meta:
        model = District  # You'll need to create this model first
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter District Name', 'class': 'form-control'}),
        }


from django import forms
from .models import User, Branch, CV  # Add CV to imports
from django.contrib.auth.models import User as DjangoUser

class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Password',
        }),
        label="Password",
        required=True
    )
    
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        empty_label="Select Branch",
        label="Branch",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    # Add new field for CV names
    cv_name = forms.ModelChoiceField(
        queryset=CV.objects.all(),
        required=False,
        label="Add name from CV",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'cv-name-select'
        })
    )
    phone_number = forms.CharField(
        required=False,
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Phone Number'
        })
    )


    class Meta:
        model = User
        fields = ['name', 'userid', 'password', 'branch', 'user_level', 'image','phone_number', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Full Name',
                'id': 'name-input'
            }),
            'userid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter User ID',
            }),
            'user_level': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, **kwargs):
        self.edit_mode = kwargs.pop('edit_mode', False)
        super(UserForm, self).__init__(*args, **kwargs)

        # Adjust 'required' based on edit_mode
        for field in self.fields:
            if field == 'password':
                self.fields[field].required = not self.edit_mode
            elif field == 'image':
                self.fields[field].required = not self.edit_mode
            elif field == 'cv_name':  # Never required
                self.fields[field].required = False
            else:
                self.fields[field].required = True

        if self.edit_mode:
            self.fields['password'].widget.attrs['placeholder'] = 'Leave empty to keep current password'
            self.fields['image'].help_text = "Leave empty to keep current image"

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
        
        # Handle password update if it's provided
        password = self.cleaned_data.get('password')
        if password:
            user.password = password
        elif self.instance and self.instance.pk:
            user.password = User.objects.get(pk=self.instance.pk).password

        if commit:
            user.save()

        # Create or update corresponding Django user
        django_user, created = DjangoUser.objects.get_or_create(
            username=user.userid,
            defaults={
                'is_staff': user.user_level == 'admin_level',
                'is_superuser': user.user_level == 'admin_level',
                'password': 'dummy_password'
            }
        )

        if created:
            django_user.set_password(password if password else 'dummy_password')
            django_user.save()
        else:
            # Update existing Django user attributes
            django_user.is_staff = user.user_level == 'admin_level'
            django_user.is_superuser = user.user_level == 'admin_level'
            django_user.save()

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
    hardware = forms.ModelMultipleChoiceField(
        queryset=Hardware.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'style': 'display:none;'})
    )
    

    class Meta:
        model = Lead
        fields = [
            'firm_name', 'customer_name', 'contact_number', 'landmark', 
            'location', 'district', 'area', 'business_nature', 'requirements',
            # 'hardware',  # Added hardware field
            'follow_up_required', 'quotation_required', 'image','document', 'remarks', 'voice_note','hardwares'
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Firm Name'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Customer Name'}),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Contact Number',
                'type': 'tel'  # Specify the input type as 'tel'
            }),

            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Landmark'}),
            
            'business_nature': forms.Select(attrs={'class': 'form-select'}),
            'requirements': DropdownCheckboxWidget(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'document': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.txt'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': False}),
            'voice_note': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'district': forms.Select(attrs={'class': 'form-select', 'id': 'id_district'}),
            'location': forms.Select(attrs={'class': 'form-select', 'id': 'id_location','readonly': True}),
            'district': forms.Select(attrs={'class': 'form-select', 'id': 'id_district'}),
            'area': forms.Select(attrs={'class': 'form-select', 'id': 'id_area'}),
            

            # 'district': forms.TextInput(attrs={'class': 'form-select', 'id': 'id_district','readonly': True}),
            # 'area': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_area', 'readonly': True}),


            
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
    






class AreaForm(forms.ModelForm):
    district = forms.ModelChoiceField(
        queryset=District.objects.all(),
        empty_label="Select District",
        label="District",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Area
        fields = ['name', 'district']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Area Name'
            })
        }





class LocationForm(forms.ModelForm):
    area = forms.ModelChoiceField(
        queryset=Area.objects.select_related('district').all(),
        empty_label="Select Area",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_area'})  # Add id for JS
    )

    class Meta:
        model = Location
        fields = ['name', 'area']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Location Name',
            }),
        }

    def save(self, commit=True):
        # Automatically assign district based on the selected area
        instance = super().save(commit=False)
        instance.district = instance.area.district
        if commit:
            instance.save()
        return instance
    







class HardwareForm(forms.ModelForm):
    class Meta:
        model = Hardware
        fields = ['name', 'specification', 'price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Hardware Name'
            }),
            'specification': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Hardware Specification',
                'rows': 3
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Price',
                'step': '0.01'
            })
        }









from django import forms
from .models import Complaint
from software_master.models import Software

class ComplaintForm(forms.ModelForm):
    software = forms.ModelChoiceField(
        queryset=Software.objects.all(),
        required=False,  # default to False; we'll override it in __init__
        empty_label="-- Select Software --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Complaint
        fields = ['description', 'complaint_type', 'software']
        widgets = {
            'description': forms.TextInput(attrs={'rows': 3, 'class': 'form-control'}),
            'complaint_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If creating a new complaint (no instance yet), make software required
        if not self.instance or not self.instance.pk:
            self.fields['software'].required = True
        else:
            # When editing, software can be optional
            self.fields['software'].required = False




# forms.py
from django import forms
from .models import CV

class CVSelectionForm(forms.Form):
    cv_id = forms.IntegerField(widget=forms.HiddenInput())
    selected = forms.BooleanField(required=False, widget=forms.HiddenInput())