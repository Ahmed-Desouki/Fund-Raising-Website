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


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reset@x.com', 'reset@x.com', 'OldPass#123', first_name='Reem')

    def test_login_page_links_to_reset(self):
        self.assertContains(self.client.get(reverse('auth_page')), reverse('password_reset'))

    def test_full_reset_flow(self):
        from django.core import mail
        response = self.client.post(reverse('password_reset'), {'email': 'RESET@x.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reset your Fundraiser password')
        self.assertIn('Hi Reem', mail.outbox[0].body)

        link = next(line for line in mail.outbox[0].body.splitlines() if '/password-reset/' in line)
        path = link.split('testserver', 1)[1]
        # Django swaps the token for a session value and redirects to a "set-password" URL
        response = self.client.get(path, follow=True)
        self.assertContains(response, 'Choose a new password')
        form_url = response.redirect_chain[-1][0]
        response = self.client.post(form_url, {'new_password1': 'BrandNew#456', 'new_password2': 'BrandNew#456'})
        self.assertRedirects(response, reverse('password_reset_complete'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew#456'))
        # The same link can't be used twice
        self.assertContains(self.client.get(path, follow=True), 'Link expired')

    def test_unknown_email_gives_same_answer_and_sends_nothing(self):
        from django.core import mail
        response = self.client.post(reverse('password_reset'), {'email': 'nobody@x.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_pages_render(self):
        for name in ['password_reset', 'password_reset_done', 'password_reset_complete']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('del@x.com', 'del@x.com', 'RightPass#1')
        Profile.objects.create(user=self.user, mobile_number='01012345678')
        self.client.force_login(self.user)

    def test_wrong_password_keeps_account_and_shows_error(self):
        response = self.client.post(reverse('delete_account'), {'password': 'wrong'})
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        page = self.client.get(reverse('profile'))
        self.assertContains(page, 'Incorrect password')
        # The error is shown once, not on every later visit
        self.assertNotContains(self.client.get(reverse('profile')), 'Incorrect password')

    def test_missing_password_keeps_account(self):
        self.client.post(reverse('delete_account'))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_correct_password_deletes_account_and_profile(self):
        response = self.client.post(reverse('delete_account'), {'password': 'RightPass#1'})
        self.assertRedirects(response, reverse('auth_page'))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Profile.objects.exists())
