from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Platform, Post, CustomUser

# Register your models here.
admin.site.register(Platform)
admin.site.register(Post)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff']

admin.site.register(CustomUser, CustomUserAdmin)