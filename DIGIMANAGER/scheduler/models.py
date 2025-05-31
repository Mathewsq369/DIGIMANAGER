from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

class Platform(models.Model):
    name = models.CharField(max_length=50)
    access_token = models.TextField()

    def __str__(self):
        return self.name

class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('approved', 'Approved'),
        ('published', 'Published'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.platform.name} - {self.status}"

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('creator', 'Content Creator'),
        ('manager', 'Manager'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)