from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from rest_framework import generics, permissions
from apps.regions.models import Region
from .models import Alert
from .serializers import AlertSerializer


class AlertListView(View):
    template_name = 'alerts/alert_list.html'

    def get(self, request):
        severity = request.GET.get('severity', '')
        region_id = request.GET.get('region', '')
        read_filter = request.GET.get('read', '')

        qs = Alert.objects.filter(is_active=True).select_related('region').order_by('-created_at')

        if severity:
            qs = qs.filter(severity=severity)
        if region_id:
            qs = qs.filter(region_id=region_id)
        if read_filter == 'unread':
            qs = qs.filter(is_read=False)
        elif read_filter == 'read':
            qs = qs.filter(is_read=True)

        # Counts for the severity filter buttons
        all_alerts = Alert.objects.filter(is_active=True)
        total_count    = all_alerts.count()
        critical_count = all_alerts.filter(severity='CRITICAL').count()
        high_count     = all_alerts.filter(severity='HIGH').count()
        warning_count  = all_alerts.filter(severity='WARNING').count()
        info_count     = all_alerts.filter(severity='INFO').count()
        unread_count   = all_alerts.filter(is_read=False).count()

        return render(request, self.template_name, {
            'alerts': qs,
            'all_regions': Region.objects.filter(is_active=True).order_by('name'),
            'unread_count': unread_count,
            'total_count': total_count,
            'critical_count': critical_count,
            'high_count': high_count,
            'warning_count': warning_count,
            'info_count': info_count,
        })


class AlertMarkReadView(View):
    """Mark one or all alerts as read via POST."""

    def post(self, request, pk=None):
        if pk:
            alert = get_object_or_404(Alert, pk=pk)
            alert.is_read = True
            alert.save(update_fields=['is_read'])
            return JsonResponse({'status': 'ok', 'pk': pk})
        else:
            Alert.objects.filter(is_active=True, is_read=False).update(is_read=True)
            return JsonResponse({'status': 'ok', 'marked': 'all'})


# DRF API
class AlertAPIListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Alert.objects.filter(is_active=True).select_related('region')
        region_id = self.request.query_params.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        unread = self.request.query_params.get('unread')
        if unread:
            qs = qs.filter(is_read=False)
        return qs
