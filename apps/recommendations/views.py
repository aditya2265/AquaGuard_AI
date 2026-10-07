from django.shortcuts import render, get_object_or_404
from django.views import View
from rest_framework import generics, permissions
from .models import Recommendation
from .serializers import RecommendationSerializer


class RecommendationListView(View):
    template_name = 'recommendations/recommendation_list.html'

    def get(self, request):
        region_id = request.GET.get('region')
        priority  = request.GET.get('priority')
        category  = request.GET.get('category')

        qs = Recommendation.objects.filter(is_active=True).select_related('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        if priority:
            qs = qs.filter(priority=priority)
        if category:
            qs = qs.filter(category=category)

        # Sort CRITICAL → HIGH → MEDIUM → LOW
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        recommendations = sorted(qs, key=lambda r: priority_order.get(r.priority, 4))

        return render(request, self.template_name, {
            'recommendations': recommendations,
        })


class RecommendationDetailView(View):
    template_name = 'recommendations/detail.html'

    def get(self, request, pk):
        rec = get_object_or_404(Recommendation, pk=pk)
        return render(request, self.template_name, {'recommendation': rec})


# DRF API
class RecommendationAPIListView(generics.ListAPIView):
    serializer_class = RecommendationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Recommendation.objects.filter(is_active=True).select_related('region')
        region_id = self.request.query_params.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs
