# forms.py

from django import forms
from .models import Branch, Requirement,Lead


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

from .models import Branch, User
class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Password (leave empty to keep current password)',
        }),
        label="Password",
        required=False  # Make password optional
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
        
        # Make all fields required except password
        for field in self.fields:
            if field == 'password':
                self.fields[field].required = False
            else:
                self.fields[field].required = True
                
        # Update password placeholder in edit mode
        if self.edit_mode:
            self.fields['password'].widget.attrs['placeholder'] = 'Leave empty to keep current password'
    
    def clean_userid(self):
        userid = self.cleaned_data.get('userid')
        # Check if userid exists but exclude current instance in edit mode
        if self.instance and self.instance.pk:
            if User.objects.filter(userid=userid).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This User ID already exists. Please choose a different one.")
        else:
            if User.objects.filter(userid=userid).exists():
                raise forms.ValidationError("This User ID already exists. Please choose a different one.")
        return userid

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Only update password if it's provided in the form
        if self.cleaned_data.get('password'):
            user.password = self.cleaned_data['password'] 
        elif self.instance and self.instance.pk:
            # If this is an edit (instance exists) and no new password provided,
            # keep the existing password
            user.password = User.objects.get(pk=self.instance.pk).password
            
        if commit:
            user.save()
        return user
    




# forms.py - Update LeadForm
from django import forms
from .models import Lead, Requirement

from django import forms
from .models import Lead, Requirement

class LeadForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    
    software = forms.MultipleChoiceField(
        choices=Lead.SOFTWARE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    requirements = forms.ModelMultipleChoiceField(
        queryset=Requirement.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    follow_up_required = forms.ChoiceField(
        choices=((True, 'Yes'), (False, 'No')),
        widget=forms.RadioSelect,
        initial=False
    )

    quotation_required = forms.ChoiceField(
        choices=((True, 'Yes'), (False, 'No')),
        widget=forms.RadioSelect,
        initial=False
    )

    remarks = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Remarks',
            'rows': 3
        }),
        required=False
    )

    class Meta:
        model = Lead
        fields = [
            'firm_name', 'customer_name', 'contact_number',
            'location', 'business_nature', 'software', 'requirements',
            'follow_up_required', 'quotation_required', 'image', 'remarks'
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Firm Name'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Customer Name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Contact Number'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Location'}),
            'business_nature': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Business Nature'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance (editing mode), set initial software values
        if self.instance.pk:
            # Convert the comma-separated string back to a list
            initial_software = [s.strip() for s in self.instance.software.split(',') if s.strip()]
            self.initial['software'] = initial_software

    def clean_follow_up_required(self):
        return self.cleaned_data['follow_up_required'] == 'True'

    def clean_quotation_required(self):
        return self.cleaned_data['quotation_required'] == 'True'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert software list to a comma-separated string
        instance.software = ', '.join(self.cleaned_data.get('software', []))

        if self.cleaned_data.get('image'):
            instance.image = self.cleaned_data['image']
            
        if commit:
            instance.save()
            self.save_m2m()
        return instance
