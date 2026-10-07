from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'region', 'user', 'generated_at')
    list_filter = ('report_type', 'region')
    search_fields = ('title', 'summary', 'region__name')
    readonly_fields = ('generated_at',)
    date_hierarchy = 'generated_at'
    ordering = ('-generated_at',)
