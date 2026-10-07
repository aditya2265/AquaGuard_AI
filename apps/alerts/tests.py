from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.regions.models import Region
from .models import Alert


def make_region(name='Alert Region'):
    return Region.objects.create(
        name=name, state='Test State', latitude=12.0, longitude=77.0
    )


class AlertModelTest(TestCase):
    def setUp(self):
        self.region = make_region()

    def test_alert_creation(self):
        alert = Alert.objects.create(
            region=self.region,
            severity='WARNING',
            alert_type='reservoir',
            title='Low Reservoir Level',
            message='Reservoir is below 30% capacity.',
        )
        self.assertEqual(alert.severity, 'WARNING')
        self.assertFalse(alert.is_read)
        self.assertTrue(alert.is_active)

    def test_alert_str(self):
        alert = Alert.objects.create(
            region=self.region,
            severity='CRITICAL',
            alert_type='rainfall',
            title='No Rainfall',
            message='No rainfall recorded for 30 days.',
        )
        s = str(alert)
        self.assertIn('CRITICAL', s)
        self.assertIn('Alert Region', s)

    def test_mark_read(self):
        alert = Alert.objects.create(
            region=self.region,
            severity='INFO',
            title='Test',
            message='Test message',
        )
        self.assertFalse(alert.is_read)
        alert.is_read = True
        alert.save(update_fields=['is_read'])
        alert.refresh_from_db()
        self.assertTrue(alert.is_read)

    def test_severity_color_property(self):
        self.assertEqual(Alert(severity='INFO').severity_color, 'info')
        self.assertEqual(Alert(severity='WARNING').severity_color, 'warning')
        self.assertEqual(Alert(severity='HIGH').severity_color, 'danger')
        self.assertEqual(Alert(severity='CRITICAL').severity_color, 'dark')


class AlertViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='alertuser', password='pass123')
        self.region = make_region('Alert View Region')
        Alert.objects.create(
            region=self.region,
            severity='HIGH',
            title='High Risk Alert',
            message='High risk detected.',
        )

    def test_alert_list_requires_login(self):
        response = self.client.get(reverse('alerts:list'))
        self.assertEqual(response.status_code, 302)

    def test_alert_list_accessible(self):
        self.client.login(username='alertuser', password='pass123')
        response = self.client.get(reverse('alerts:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'High Risk Alert')


class AlertAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apialertuser', password='pass123')
        self.region = make_region('API Alert Region')
        Alert.objects.create(
            region=self.region,
            severity='WARNING',
            title='API Test Alert',
            message='Testing the API.',
            is_read=False,
        )

    def test_alert_list_api_requires_auth(self):
        response = self.client.get(reverse('alerts:api_list'))
        self.assertIn(response.status_code, [401, 403])

    def test_mark_read_api(self):
        self.client.login(username='apialertuser', password='pass123')
        alert = Alert.objects.first()
        response = self.client.post(
            reverse('alerts:mark_read', kwargs={'pk': alert.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        alert.refresh_from_db()
        self.assertTrue(alert.is_read)

    def test_mark_all_read_api(self):
        self.client.login(username='apialertuser', password='pass123')
        response = self.client.post(
            reverse('alerts:mark_all_read'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
