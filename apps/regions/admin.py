from django.contrib import admin
from .models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'country', 'population', 'area_sq_km', 'is_active', 'created_at')
    list_filter = ('state', 'country', 'is_active')
    search_fields = ('name', 'state', 'country')
    readonly_fields = ('created_at',)
    list_editable = ('is_active',)
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'state', 'country', 'is_active')
        }),
        ('Geography', {
            'fields': ('latitude', 'longitude', 'area_sq_km')
        }),
        ('Demographics', {
            'fields': ('population',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
