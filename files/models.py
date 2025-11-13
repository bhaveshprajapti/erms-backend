from django.db import models
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Folder(models.Model):
    FOLDER_COLORS = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink'),
        ('gray', 'Gray'),
    ]
    
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='folders')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, null=True, blank=True, related_name='folders')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_folders')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_folders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)
    is_project_folder = models.BooleanField(default=False)
    is_employee_folder = models.BooleanField(default=False)
    is_client_folder = models.BooleanField(default=False)
    color = models.CharField(max_length=10, choices=FOLDER_COLORS, default='blue')
    is_system_folder = models.BooleanField(default=False)  # Cannot be deleted by users
    folder_link = models.CharField(max_length=500, blank=True)  # Shareable link
    
    class Meta:
        unique_together = ['name', 'parent']
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """Get the full path of the folder"""
        if self.parent:
            return f"{self.parent.full_path}/{self.name}"
        return self.name
    
    @property
    def files_count(self):
        """Count of files in this folder"""
        return self.files.count()
    
    @property
    def subfolders_count(self):
        """Count of subfolders in this folder"""
        return self.subfolders.count()
    
    @property
    def total_size(self):
        """Total size of all files in this folder and subfolders"""
        total = sum(file.size for file in self.files.all())
        for subfolder in self.subfolders.all():
            total += subfolder.total_size
        return total
    
    def generate_folder_link(self):
        """Generate shareable folder link"""
        import uuid
        if not self.folder_link:
            self.folder_link = str(uuid.uuid4())
        return self.folder_link
    
    def save(self, *args, **kwargs):
        if not self.folder_link:
            self.generate_folder_link()
        super().save(*args, **kwargs)


class File(models.Model):
    FILE_TYPE_CHOICES = [
        ('document', 'Document'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('archive', 'Archive'),
        ('spreadsheet', 'Spreadsheet'),
        ('presentation', 'Presentation'),
        ('pdf', 'PDF'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='files/%Y/%m/%d/')
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='files', null=True, blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    size = models.BigIntegerField(default=0)  # Size in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    file_link = models.CharField(max_length=500, blank=True)  # Shareable link
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_name)[1].lower()
    
    @property
    def formatted_size(self):
        """Get human readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.original_name
            
        # Set file size if not already set and file_path exists
        if self.file_path and not self.size:
            try:
                self.size = self.file_path.size
            except:
                self.size = 0
        
        # Determine file type based on extension
        if not self.file_type or self.file_type == 'other':
            ext = self.extension
            if ext == '.pdf':
                self.file_type = 'pdf'
            elif ext in ['.doc', '.docx', '.txt', '.rtf', '.odt']:
                self.file_type = 'document'
            elif ext in ['.xls', '.xlsx', '.csv', '.ods']:
                self.file_type = 'spreadsheet'
            elif ext in ['.ppt', '.pptx', '.odp']:
                self.file_type = 'presentation'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                self.file_type = 'image'
            elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                self.file_type = 'video'
            elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
                self.file_type = 'audio'
            elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                self.file_type = 'archive'
        
        # Generate file link if not exists
        if not self.file_link:
            import uuid
            self.file_link = str(uuid.uuid4())
        
        super().save(*args, **kwargs)


class FileShare(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_files')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files_shared')
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['file', 'shared_with']
    
    def __str__(self):
        return f"{self.file.name} shared with {self.shared_with.username}"