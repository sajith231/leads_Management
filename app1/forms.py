from django import forms
from .models import Branch, Requirement, Lead, User, SoftwareAmount
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

class CombinedSelectWidget(forms.Widget):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs = attrs or {}

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        
        # Convert value to list if it's a string
        if isinstance(value, str):
            value = [v.strip() for v in value.split(',') if v.strip()]
            
        # Get all requirements for choices
        requirement_choices = [(req.id, req.name) for req in Requirement.objects.all()]
        
        # Build the HTML structure
        html = f"""
        <div class="combined-select-container">
            <div class="selected-items mb-3" id="selected-items-{name}">
                {self._render_selected_items(value)}
            </div>
            
            <div class="input-group mb-3">
                <select class="form-select" id="software-select-{name}">
                    <option value="">Select Software</option>
                    {self._render_options(Lead.SOFTWARE_CHOICES)}
                </select>
                
                <select class="form-select" id="requirement-select-{name}">
                    <option value="">Select Requirement</option>
                    {self._render_options(requirement_choices)}
                </select>
                
                <button type="button" class="btn btn-primary" onclick="addSelectedItem('{name}')">
                    Add
                </button>
            </div>
            
            <input type="hidden" name="{name}" id="hidden-{name}" value="{','.join(value)}">
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Initialize the saved amounts map
            window.savedAmounts = new Map();
            
            // Load existing amounts from the page
            document.querySelectorAll('.software-amount').forEach(input => {{
                const softwareName = input.getAttribute('data-software');
                const value = input.value;
                if (softwareName && value) {{
                    window.savedAmounts.set(softwareName, value);
                }}
            }});

            // Add event listeners to all remove buttons
            document.querySelectorAll('.remove-item-btn').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const itemContainer = this.closest('.selected-item');
                    const itemText = itemContainer.querySelector('span').textContent.trim();
                    const name = '{name}';
                    removeItem(this, name, true);
                }});
            }});
        }});

        function addSelectedItem(name) {{
            const softwareSelect = document.getElementById(`software-select-${{name}}`);
            const requirementSelect = document.getElementById(`requirement-select-${{name}}`);
            const selectedItems = document.getElementById(`selected-items-${{name}}`);
            const hiddenInput = document.getElementById(`hidden-${{name}}`);
            
            let selectedValue = '';
            let selectedText = '';
            let isSoftware = false;
            
            if (softwareSelect.value) {{
                selectedValue = softwareSelect.value;
                selectedText = softwareSelect.options[softwareSelect.selectedIndex].text;
                isSoftware = true;
            }} else if (requirementSelect.value) {{
                selectedValue = requirementSelect.value;
                selectedText = requirementSelect.options[requirementSelect.selectedIndex].text;
            }}
            
            if (selectedText) {{
                const itemDiv = document.createElement('div');
                itemDiv.className = 'selected-item mb-2';
                
                let amountInputHtml = '';
                if (isSoftware) {{
                    const amountId = `amount_${{selectedText.replace(/\s+/g, '_')}}`;
                    const savedAmount = window.savedAmounts ? window.savedAmounts.get(selectedText) : '';
                    const amountValue = savedAmount || '';
                    
                    amountInputHtml = `
                        <div class="input-group mt-1">
                            <span class="input-group-text">₹</span>
                            <input type="number" 
                                   name="${{amountId}}"
                                   class="form-control form-control-sm software-amount"
                                   data-software="${{selectedText}}"
                                   placeholder="Enter amount"
                                   value="${{amountValue}}"
                                   step="0.01"
                                   min="0">
                        </div>`;
                }}
                
                itemDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <span>${{selectedText}}</span>
                        <button type="button" class="btn btn-sm btn-danger ms-2 remove-item-btn" 
                                onclick="removeItem(this, '${{name}}', true)">×</button>
                    </div>
                    ${{amountInputHtml}}
                `;
                
                selectedItems.appendChild(itemDiv);
                
                // Update hidden input
                const currentValues = hiddenInput.value ? hiddenInput.value.split(',') : [];
                if (!currentValues.includes(selectedText)) {{
                    currentValues.push(selectedText);
                    hiddenInput.value = currentValues.join(',');
                }}
                
                // Reset selects
                softwareSelect.value = '';
                requirementSelect.value = '';
            }}
        }}
        
        function removeItem(button, name, updateHidden = true) {{
            const itemDiv = button.closest('.selected-item');
            const hiddenInput = document.getElementById(`hidden-${{name}}`);
            const itemText = itemDiv.querySelector('span').textContent.trim();
            
            if (updateHidden) {{
                // Update hidden input
                const currentValues = hiddenInput.value.split(',').map(v => v.trim());
                const newValues = currentValues.filter(v => v !== itemText);
                hiddenInput.value = newValues.join(',');
            }}
            
            // Remove from saved amounts if it's a software item
            const amountInput = itemDiv.querySelector('.software-amount');
            if (amountInput && window.savedAmounts) {{
                window.savedAmounts.delete(itemText);
            }}
            
            // Remove the item div
            itemDiv.remove();
        }}
        </script>
        
        <style>
        .selected-item {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 8px;
        }}
        .software-amount {{
            width: 150px;
        }}
        </style>
        """
        return mark_safe(html)

    def _render_selected_items(self, value):
        items_html = []
        for item in value:
            is_software = any(item == choice[1] for choice in Lead.SOFTWARE_CHOICES)
            amount_input = ''
            if is_software:
                amount_id = f"amount_{item.replace(' ', '_')}"
                amount_input = f"""
                    <div class="input-group mt-1">
                        <span class="input-group-text">₹</span>
                        <input type="number" 
                               name="{amount_id}"
                               class="form-control form-control-sm software-amount"
                               data-software="{item}"
                               placeholder="Enter amount"
                               step="0.01"
                               min="0">
                    </div>
                """
            
            items_html.append(f"""
                <div class="selected-item mb-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <span>{item}</span>
                        <button type="button" class="btn btn-sm btn-danger ms-2 remove-item-btn" 
                                onclick="removeItem(this, '{self.attrs.get('name', '')}', true)">×</button>
                    </div>
                    {amount_input}
                </div>
            """)
        return '\n'.join(items_html)

    def _render_options(self, choices):
        options_html = []
        for value, label in choices:
            if value:  # Skip empty choice
                options_html.append(f'<option value="{value}">{label}</option>')
        return '\n'.join(options_html)

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
        ]
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
        
        items = [item.strip() for item in combined.split(',') if item.strip()]
        return items

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        combined_items = self.cleaned_data.get('combined_requirements', [])
        
        software_list = []
        requirement_names = []
        
        software_choices_dict = dict(Lead.SOFTWARE_CHOICES)
        
        for item in combined_items:
            if item in software_choices_dict.values():
                software_list.append(item)
            else:
                requirement_names.append(item)
        
        instance.software = ', '.join(software_list)
        
        if commit:
            instance.save()
            
            # Handle requirements
            instance.requirements.clear()
            requirement_objects = Requirement.objects.filter(name__in=requirement_names)
            instance.requirements.add(*requirement_objects)
            
            # Handle software amounts
            SoftwareAmount.objects.filter(lead=instance).delete()
            for software in software_list:
                amount_field = f"amount_{software.replace(' ', '_')}"
                amount = self.data.get(amount_field)
                if amount:
                    SoftwareAmount.objects.create(
                        lead=instance,
                        software_name=software,
                        amount=float(amount)
                    )
        
        return instance