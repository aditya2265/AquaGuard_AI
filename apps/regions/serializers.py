from rest_framework import serializers
from .models import Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'


class RegionSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for use in nested contexts."""
    class Meta:
        model = Region
        fields = ('id', 'name', 'state', 'country')
