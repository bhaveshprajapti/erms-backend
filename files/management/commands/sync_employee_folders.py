from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from files.models import Folder
import os
import re

User = get_user_model()

class Command(BaseCommand):
    help = 'Sync employee folders from file system to database'

    def handle(self, *args, **options):
        employee_folders_path = os.path.join(settings.MEDIA_ROOT, 'employee_folders')
        
        if not os.path.exists(employee_folders_path):
            self.stdout.write(
                self.style.WARNING(f'Employee folders directory "{employee_folders_path}" does not exist')
            )
            return

        synced_count = 0
        
        # Get all directories in employee_folders
        for folder_name in os.listdir(employee_folders_path):
            folder_path = os.path.join(employee_folders_path, folder_name)
            
            if os.path.isdir(folder_path):
                # Try to extract employee info from folder name (format: firstname_lastname_id)
                employee = None
                match = re.match(r'(.+)_(.+)_(\d+)$', folder_name)
                if match:
                    first_name, last_name, employee_id = match.groups()
                    try:
                        employee = User.objects.get(id=employee_id)
                    except User.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Employee with ID {employee_id} not found for folder {folder_name}')
                        )
                
                # Check if main folder already exists in database
                existing_folder = Folder.objects.filter(
                    employee=employee,
                    is_employee_folder=True,
                    parent=None
                ).first()
                
                if not existing_folder:
                    # Create main employee folder in database
                    display_name = f"Employee_{folder_name}" if not employee else f"Employee_{employee.first_name}_{employee.last_name}"
                    main_folder = Folder.objects.create(
                        name=display_name,
                        employee=employee,
                        description=f'Employee folder for {folder_name}',
                        is_employee_folder=True,
                        is_system_folder=True,
                        color='yellow',
                        created_by=employee
                    )
                    synced_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created main folder: {display_name}')
                    )
                    
                    # Create subfolders if they exist physically
                    subfolders = ['documents', 'images', 'contracts', 'certificates']
                    for subfolder_name in subfolders:
                        subfolder_path = os.path.join(folder_path, subfolder_name)
                        if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                            Folder.objects.create(
                                name=subfolder_name.title(),
                                parent=main_folder,
                                employee=employee,
                                created_by=employee,
                                is_employee_folder=True,
                                is_system_folder=True,
                                color='blue',
                                description=f"{subfolder_name.title()} folder for {folder_name}"
                            )
                            self.stdout.write(f'  Created subfolder: {subfolder_name.title()}')
                else:
                    self.stdout.write(f'Folder already exists: {folder_name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully synced {synced_count} employee folders')
        )