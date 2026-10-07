from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Region


class RegionModelTest(TestCase):
    def setUp(self):
        self.region = Region.objects.create(
            name='Test City',
            state='Test State',
            country='India',
            latitude=12.97,
            longitude=77.59,
            population=500000,
            area_sq_km=200.0,
        )

    def test_region_creation(self):
        self.assertEqual(Region.objects.count(), 1)
        self.assertEqual(self.region.name, 'Test City')
        self.assertEqual(self.region.country, 'India')
        self.assertTrue(self.region.is_active)

    def test_region_str(self):
        self.assertEqual(str(self.region), 'Test City, Test State')

    def test_region_unique_name(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Region.objects.create(
                name='Test City',
                state='Other State',
                latitude=0.0,
                longitude=0.0,
            )


class RegionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.region = Region.objects.create(
            name='View Test Region',
            state='View State',
            latitude=12.0,
            longitude=77.0,
        )

    def test_region_list_requires_login(self):
        response = self.client.get(reverse('regions:list'))
        self.assertIn(response.status_code, [302, 301])
        self.assertIn('/login', response['Location'])

    def test_region_list_accessible(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('regions:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Test Region')

    def test_region_detail_accessible(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('regions:detail', kwargs={'pk': self.region.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Test Region')

    def test_region_detail_404(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('regions:detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_map_view_accessible(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('regions:map'))
        self.assertEqual(response.status_code, 200)
