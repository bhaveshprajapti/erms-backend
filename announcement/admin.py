from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
