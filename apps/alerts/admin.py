from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'alert_type', 'region', 'is_read', 'is_active', 'created_at')
    list_filter = ('severity', 'alert_type', 'is_read', 'is_active', 'region')
    search_fields = ('title', 'message', 'region__name')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_read', 'is_active')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
