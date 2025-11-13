from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    create_employee_folder = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Check this to create a dedicated folder structure for this employee',
        label='Create Employee Folder'
    )
    is_on_probation = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Check if this employee is on probation',
        label='Is on Probation'
    )
    probation_months = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=24,
        help_text='Number of months for probation period (1-24)',
        label='Probation Months',
        widget=forms.NumberInput(attrs={'placeholder': 'Enter months (1-24)'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 
                 'organization', 'role', 'employee_type', 'joining_date', 'salary',
                 'is_on_probation', 'probation_months')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Handle folder creation
            if self.cleaned_data.get('create_employee_folder'):
                self._create_employee_folder(user)
        return user
    
    def _create_employee_folder(self, instance):
        """Create folder structure for employee"""
        import os
        from django.conf import settings
        
        folder_name = f"{instance.first_name}_{instance.last_name}_{instance.id}"
        folder_path = os.path.join('employee_folders', folder_name)
        full_folder_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        
        try:
            # Create main employee folder
            os.makedirs(full_folder_path, exist_ok=True)
            
            # Create subfolders for organization
            subfolders = ['documents', 'images', 'contracts', 'certificates']
            for subfolder in subfolders:
                subfolder_path = os.path.join(full_folder_path, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)
            
            instance.folder_path = folder_path
            instance.save(update_fields=['folder_path'])
            
        except Exception as e:
            print(f"Failed to create folder for employee {instance.username}: {e}")


class CustomUserChangeForm(UserChangeForm):
    create_employee_folder = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Check this to create a dedicated folder structure for this employee (only if not already created)',
        label='Create Employee Folder'
    )
    is_on_notice_period = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Check if this employee is on notice period',
        label='Is on Notice Period'
    )
    notice_period_end_date = forms.DateField(
        required=False,
        help_text='End date of notice period',
        label='Notice Period End Date',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable the checkbox if folder already exists
        if self.instance and self.instance.folder_path:
            self.fields['create_employee_folder'].disabled = True
            self.fields['create_employee_folder'].help_text = 'Folder already exists at: ' + str(self.instance.folder_path)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Handle folder creation for existing users
            if (self.cleaned_data.get('create_employee_folder') and 
                not user.folder_path):
                self._create_employee_folder(user)
        return user
    
    def _create_employee_folder(self, instance):
        """Create folder structure for employee"""
        import os
        from django.conf import settings
        
        folder_name = f"{instance.first_name}_{instance.last_name}_{instance.id}"
        folder_path = os.path.join('employee_folders', folder_name)
        full_folder_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        
        try:
            # Create main employee folder
            os.makedirs(full_folder_path, exist_ok=True)
            
            # Create subfolders for organization
            subfolders = ['documents', 'images', 'contracts', 'certificates']
            for subfolder in subfolders:
                subfolder_path = os.path.join(full_folder_path, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)
            
            instance.folder_path = folder_path
            instance.save(update_fields=['folder_path'])
            
        except Exception as e:
            print(f"Failed to create folder for employee {instance.username}: {e}")
