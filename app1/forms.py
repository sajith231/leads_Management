from django import forms
from .models import Branch, Requirement, Lead, User
from django.template.loader import render_to_string

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

class CombinedSelectWidget(forms.Widget):
    template_name = 'widgets/combined_select.html'
    
    def __init__(self, choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices or []

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        
        # Convert value to list if it's a string (for software)
        if isinstance(value, str):
            value = [v.strip() for v in value.split(',') if v.strip()]
            
        # Get all requirements for choices
        requirement_choices = [(req.id, req.name) for req in Requirement.objects.all()]
            
        context = {
            'widget': {
                'name': name,
                'value': value,
                'attrs': attrs or {},
                'choices': requirement_choices,
                'software_choices': Lead.SOFTWARE_CHOICES,
            }
        }
        return render_to_string(self.template_name, context)

class LeadForm(forms.ModelForm):
    combined_requirements = forms.CharField(
        widget=CombinedSelectWidget(),
        required=False
    )

    class Meta:
        model = Lead
        fields = [
            'firm_name', 'customer_name', 'contact_number',
            'location', 'business_nature', 'software',
            'follow_up_required', 'quotation_required', 
            'image', 'remarks'
        ]  # Removed 'requirements' from fields
        widgets = {
            'firm_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Firm Name'
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Customer Name'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Contact Number'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Location'
            }),
            'business_nature': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Business Nature'
            }),
            'software': forms.SelectMultiple(attrs={
                'class': 'form-select'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate combined_requirements if editing an existing instance
        if self.instance.pk:
            software_list = [s.strip() for s in self.instance.software.split(',') if s.strip()]
            requirement_list = list(self.instance.requirements.values_list('id', flat=True))
            combined_values = []

            combined_values.extend(software_list)
            requirement_names = Requirement.objects.filter(id__in=requirement_list).values_list('name', flat=True)
            combined_values.extend(requirement_names)

            self.initial['combined_requirements'] = ', '.join(combined_values)

    def clean_follow_up_required(self):
        return bool(self.cleaned_data['follow_up_required'])

    def clean_quotation_required(self):
        return bool(self.cleaned_data['quotation_required'])

    def clean_combined_requirements(self):
        combined = self.cleaned_data.get('combined_requirements', '')
        if not combined:
            raise forms.ValidationError("At least one requirement or software must be selected")
        
        # Split the comma-separated string into a list
        items = [item.strip() for item in combined.split(',') if item.strip()]
        return items

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Get the combined requirements from cleaned data
        combined_items = self.cleaned_data.get('combined_requirements', [])
        
        # Separate software and requirements
        software_list = []
        requirement_names = []
        
        software_choices_dict = dict(Lead.SOFTWARE_CHOICES)
        
        for item in combined_items:
            # Check if the item is in SOFTWARE_CHOICES
            if item in software_choices_dict.values():
                software_list.append(item)
            else:
                requirement_names.append(item)
        
        # Save software as comma-separated string
        instance.software = ', '.join(software_list)
        
        if commit:
            instance.save()
            
            # Clear existing requirements and add new ones
            instance.requirements.clear()
            requirement_objects = Requirement.objects.filter(name__in=requirement_names)
            instance.requirements.add(*requirement_objects)
        
        return instance