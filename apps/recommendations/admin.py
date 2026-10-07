from django.contrib import admin
from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'category', 'region', 'is_active', 'created_at')
    list_filter = ('priority', 'category', 'is_active')
    search_fields = ('title', 'description', 'region__name')
    readonly_fields = ('created_at',)
    list_editable = ('is_active',)
