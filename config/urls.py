from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Admin site branding
admin.site.site_header = "AquaGuard AI Admin"
admin.site.site_title = "AquaGuard AI"
admin.site.index_title = "Water Crisis Management"

urlpatterns = [
    # Admin (only auth-protected area)
    path('admin/', admin.site.urls),

    # Landing page
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),

    # REST API
    path('api/', include('apps.api.urls')),

    # App URLs (all public)
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('regions/', include('apps.regions.urls')),
    path('alerts/', include('apps.alerts.urls')),
    path('reports/', include('apps.reports.urls')),
    path('recommendations/', include('apps.recommendations.urls')),
    path('water-data/', include('apps.water_data.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
