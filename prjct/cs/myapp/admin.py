from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    list_display = ('registration_number', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('is_active', 'role')
    fieldsets = (
        (None, {'fields': ('registration_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('registration_number', 'password1', 'password2', 'role'),
        }),
    )
    search_fields = ('registration_number', 'first_name', 'last_name')
    ordering = ('registration_number',)

admin.site.register(User, UserAdmin)