# forms.py

from django import forms
from .models import Branch, Requirement

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
            'placeholder': 'Enter Password',
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
        self.edit_mode = kwargs.pop('edit_mode', False)  # Add edit_mode parameter
        super(UserForm, self).__init__(*args, **kwargs)
        # Make all fields required except password in edit mode
        for field in self.fields:
            if field == 'password' and self.edit_mode:
                self.fields[field].required = False
            else:
                self.fields[field].required = True
    
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
        # Only update password if it's provided
        if self.cleaned_data.get('password'):
            user.password = self.cleaned_data['password']
        if commit:
            user.save()
        return user