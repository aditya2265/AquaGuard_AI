from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileModelTest(TestCase):
    def test_profile_auto_created_via_signal(self):
        user = User.objects.create_user(username='struser', password='pass')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_profile_str(self):
        user = User.objects.create_user(username='struser2', password='pass')
        profile = user.profile
        profile.role = 'admin'
        profile.save()
        self.assertIn('struser2', str(profile))
        self.assertIn('Administrator', str(profile))

    def test_is_admin(self):
        user = User.objects.create_user(username='adminuser', password='pass')
        profile = user.profile
        profile.role = 'admin'
        profile.save()
        self.assertTrue(profile.is_admin())
        self.assertFalse(profile.is_analyst())

    def test_is_analyst(self):
        user = User.objects.create_user(username='analystuser', password='pass')
        profile = user.profile
        profile.role = 'analyst'
        profile.save()
        self.assertTrue(profile.is_analyst())
        self.assertFalse(profile.is_admin())

    def test_profile_page_public(self):
        """Profile page must be accessible without login."""
        from django.test import Client
        c = Client()
        response = c.get('/accounts/profile/')
        self.assertEqual(response.status_code, 200)
