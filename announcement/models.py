from django.db import models

# Create your models here.
class Announcement(models.Model):
  title = models.CharField(max_length=255)
  description = models.TextField()
  image = models.ImageField(upload_to='announcemets/',null=True,blank=True)
  start_date = models.DateField()
  end_date = models.DateField()

  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['end_date']

  def __str__(self):
    return self.title