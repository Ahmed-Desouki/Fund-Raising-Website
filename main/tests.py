from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import ProfileEditForm, RegisterForm
from .models import Profile


class EgyptianMobileValidationTests(TestCase):
    VALID = ['01012345678', '01112345678', '01212345678', '01512345678']
    INVALID = ['01312345678', '0101234567', '010123456789', '1012345678', '+201012345678', '0101234567a']

    def register_data(self, mobile):
        return {
            'first_name': 'Test', 'last_name': 'User', 'email': 'test@x.com',
            'mobile_number': mobile, 'password1': 'StrongPass#1', 'password2': 'StrongPass#1',
        }

    def test_register_accepts_valid_numbers(self):
        for mobile in self.VALID:
            self.assertTrue(RegisterForm(self.register_data(mobile)).is_valid(), mobile)

    def test_register_rejects_invalid_numbers(self):
        for mobile in self.INVALID:
            form = RegisterForm(self.register_data(mobile))
            self.assertFalse(form.is_valid(), mobile)
            self.assertIn('mobile_number', form.errors)

    def test_api_register_returns_mobile_error(self):
        response = self.client.post(reverse('api_register'), self.register_data('01312345678'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('mobile_number', response.json()['errors'])
        self.assertFalse(User.objects.exists())

    def test_profile_edit_rejects_invalid_number(self):
        user = User.objects.create_user('p@x.com', 'p@x.com', 'StrongPass#1')
        Profile.objects.create(user=user, mobile_number='01012345678')
        self.client.force_login(user)
        self.client.post(reverse('profile'), {'first_name': 'A', 'last_name': 'B', 'mobile_number': '12345'})
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.mobile_number, '01012345678')

    def test_profile_edit_accepts_valid_number(self):
        form = ProfileEditForm({'first_name': 'A', 'last_name': 'B', 'mobile_number': '01112345678'})
        self.assertTrue(form.is_valid())
