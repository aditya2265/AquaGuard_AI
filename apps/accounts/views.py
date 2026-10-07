from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from .forms import UserProfileForm
from .models import UserProfile
from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement
from apps.predictions.models import WaterPrediction


class ProfileView(View):
    """Public settings/profile page — no login required."""
    template_name = 'accounts/profile.html'

    def get(self, request):
        # Anonymous visitors see a blank profile form; admins see their own
        profile = None
        profile_form = UserProfileForm()
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=request.user)
            profile_form = UserProfileForm(instance=profile)
        return render(request, self.template_name, {
            'profile': profile,
            'profile_form': profile_form,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:profile')
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        profile_form = UserProfileForm(request.POST, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        return render(request, self.template_name, {
            'profile': profile,
            'profile_form': profile_form,
        })
