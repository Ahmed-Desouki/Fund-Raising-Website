"""End-to-end tests for registration, activation, login, logout and the profile page."""
import re
import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Profile

TEMP_MEDIA = tempfile.mkdtemp()
PASSWORD = 'StrongPass#1'


def image_file(name='me.png', size=(10, 10)):
    buf = BytesIO()
    Image.new('RGB', size, 'purple').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


def register_data(**overrides):
    data = {
        'first_name': 'Salma', 'last_name': 'Ali', 'email': 'Salma@Example.com',
        'mobile_number': '01012345678', 'password1': PASSWORD, 'password2': PASSWORD,
    }
    data.update(overrides)
    return data


def activation_path(email_body):
    return re.search(r'https?://[^/\s]+(/activate/\S+/)', email_body).group(1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RegistrationFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def register(self, **overrides):
        return self.client.post(reverse('api_register'), register_data(**overrides))

    def test_register_creates_inactive_user_with_profile_and_sends_email(self):
        response = self.register(profile_picture=image_file())
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email='salma@example.com')  # stored lower-case
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.mobile_number, '01012345678')
        self.assertTrue(user.profile.profile_picture.name.startswith('profile_pics/'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/activate/', mail.outbox[0].body)

    def test_cannot_log_in_before_activation(self):
        self.register()
        response = self.client.post(reverse('api_login'), {'email': 'salma@example.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_activation_link_activates_logs_in_and_works_once(self):
        self.register()
        path = activation_path(mail.outbox[0].body)
        response = self.client.get(path)
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        self.assertTrue(User.objects.get(email='salma@example.com').is_active)
        self.assertIn('_auth_user_id', self.client.session)

        self.client.logout()
        # Logging in changed last_login, which invalidates the token: the link is single-use
        self.assertContains(self.client.get(path), 'Activation link is invalid or expired')

    def test_tampered_activation_links_are_rejected(self):
        self.register()
        uid = activation_path(mail.outbox[0].body).split('/')[2]
        for path in [f'/activate/{uid}/wrong-token/', '/activate/bm90LWFuLWlk/abc/', '/activate/!!!/abc/']:
            self.assertContains(self.client.get(path), 'Activation link is invalid or expired', msg_prefix=path)
        self.assertFalse(User.objects.get(email='salma@example.com').is_active)

    def test_register_again_after_link_expired_replaces_inactive_account(self):
        self.register()
        old_pk = User.objects.get(email='salma@example.com').pk
        response = self.register(first_name='Salma2')
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email='salma@example.com')
        self.assertNotEqual(user.pk, old_pk)
        self.assertEqual(user.first_name, 'Salma2')
        self.assertEqual(len(mail.outbox), 2)

    def test_cannot_register_over_an_active_account(self):
        User.objects.create_user('salma@example.com', 'salma@example.com', PASSWORD)
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_register_validation_errors(self):
        cases = {
            'password2': register_data(password2='Different#1'),
            'email': register_data(email='not-an-email'),
            'mobile_number': register_data(mobile_number='0101234'),
            'first_name': register_data(first_name=''),
        }
        for field, data in cases.items():
            response = self.client.post(reverse('api_register'), data)
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json()['errors'], field)
        self.assertFalse(User.objects.exists())

    def test_profile_picture_over_5mb_is_rejected(self):
        big = SimpleUploadedFile('big.png', image_file().read() + b'0' * (5 * 1024 * 1024), content_type='image/png')
        response = self.register(profile_picture=big)
        self.assertEqual(response.status_code, 400)
        self.assertIn('profile_picture', response.json()['errors'])

    def test_email_failure_does_not_leave_a_stuck_account(self):
        with mock.patch('main.emails.EmailMultiAlternatives.send', side_effect=OSError('SMTP down')):
            response = self.register()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.exists())
        self.assertEqual(self.register().status_code, 200)  # and trying again works

    def test_register_requires_post(self):
        self.assertEqual(self.client.get(reverse('api_register')).status_code, 405)
        self.assertEqual(self.client.get(reverse('api_login')).status_code, 405)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('omar@example.com', 'omar@example.com', PASSWORD, first_name='Omar')

    def login(self, email='omar@example.com', password=PASSWORD):
        return self.client.post(reverse('api_login'), {'email': email, 'password': password})

    def test_login_is_case_insensitive_and_redirects(self):
        response = self.login(email='OMAR@Example.COM')
        self.assertEqual(response.json(), {'success': True, 'redirect_url': '/dashboard/'})
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_wrong_password_and_unknown_email_get_the_same_answer(self):
        wrong = self.login(password='nope')
        unknown = self.login(email='nobody@example.com')
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json(), unknown.json())

    def test_missing_fields_do_not_crash(self):
        self.assertEqual(self.client.post(reverse('api_login'), {}).status_code, 401)

    def test_duplicate_emails_in_different_case_do_not_crash(self):
        User.objects.create_user('OMAR@example.com', 'OMAR@example.com', 'Other#Pass1', is_active=False)
        self.assertEqual(self.login().status_code, 200)

    def test_logout_then_login_again(self):
        self.login()
        self.assertRedirects(self.client.get(reverse('logout')), reverse('auth_page'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.login().status_code, 200)

    def test_login_page_redirects_logged_in_users_home(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('auth_page')), reverse('home'))

    def test_dashboard_redirects_to_home(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('home'))

    def test_email_backend(self):
        from django.contrib.auth import authenticate
        self.assertEqual(authenticate(username='Omar@example.com', password=PASSWORD), self.user)
        self.assertIsNone(authenticate(username='omar@example.com', password='bad'))
        self.assertIsNone(authenticate(username=None, password=PASSWORD))
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(username='omar@example.com', password=PASSWORD))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('nour@example.com', 'nour@example.com', PASSWORD, first_name='Nour')
        Profile.objects.create(user=self.user, mobile_number='01012345678')
        self.client.force_login(self.user)

    def test_edit_all_fields_except_email(self):
        response = self.client.post(reverse('profile'), {
            'first_name': 'Nora', 'last_name': 'Samy', 'mobile_number': '01298765432',
            'birthdate': '2000-05-17', 'facebook_profile': 'https://facebook.com/nora', 'country': 'Egypt',
            'email': 'hacker@example.com', 'profile_picture': image_file('new.png'),
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual((self.user.first_name, self.user.last_name), ('Nora', 'Samy'))
        self.assertEqual(self.user.email, 'nour@example.com')  # email can't be changed
        self.assertEqual(profile.mobile_number, '01298765432')
        self.assertEqual(str(profile.birthdate), '2000-05-17')
        self.assertEqual(profile.country, 'Egypt')
        self.assertTrue(profile.profile_picture)

    def test_invalid_facebook_url_is_rejected(self):
        self.client.post(reverse('profile'), {
            'first_name': 'Nora', 'last_name': 'Samy', 'mobile_number': '01298765432', 'facebook_profile': 'not a url',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Nour')

    def test_account_without_profile_does_not_crash(self):
        admin = User.objects.create_superuser('admin@example.com', 'admin@example.com', PASSWORD)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_profile_lists_own_projects_and_donations(self):
        from datetime import timedelta
        from django.utils import timezone
        from projects.models import Category, Donation, Project
        now = timezone.now()
        project = Project.objects.create(
            owner=self.user, title='Nour campaign', details='x', category=Category.objects.first(),
            total_target=100, start_time=now, end_time=now + timedelta(days=3),
        )
        Donation.objects.create(project=project, user=self.user, amount=25)
        page = self.client.get(reverse('profile'))
        self.assertContains(page, 'Nour campaign', count=2)


class ReadableConsoleEmailTests(TestCase):
    def test_arabic_and_english_links_are_printed_readably(self):
        from io import StringIO
        from django.core.mail import EmailMessage
        from .email import ReadableConsoleEmailBackend
        link = 'http://127.0.0.1:8000/activate/MTA/dfmklj-b824541676c5ce77a155d7e842641cf8/'
        for body in [f'أهلاً سلمى،\n\nاضغط على الرابط:\n\n{link}\n', f'Hi Salma,\n\nClick the link below to activate.\n\n{link}\n']:
            stream = StringIO()
            ReadableConsoleEmailBackend(stream=stream).send_messages([EmailMessage('Activate', body, None, ['s@x.com'])])
            output = stream.getvalue()
            self.assertIn(link, output)          # the whole link on one line, copyable
            self.assertIn(body.split('\n')[0], output)
            self.assertIn('To: s@x.com', output)

    def test_terminal_that_cannot_show_arabic_still_gets_the_link(self):
        import io
        from django.core.mail import EmailMessage
        from .email import ReadableConsoleEmailBackend
        link = 'http://127.0.0.1:8000/activate/MTA/abc-123/'
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding='cp1252')  # like a default Windows terminal
        sent = ReadableConsoleEmailBackend(stream=stream).send_messages(
            [EmailMessage('فعّل حسابك', f'أهلاً\n\n{link}\n', None, ['s@x.com'])])
        stream.flush()
        self.assertEqual(sent, 1)
        self.assertIn(link, raw.getvalue().decode('cp1252'))

    def test_arabic_signup_works_on_a_windows_terminal(self):
        import io
        from django.test import override_settings
        stream = io.TextIOWrapper(io.BytesIO(), encoding='cp1252')
        with override_settings(EMAIL_BACKEND='main.email.ReadableConsoleEmailBackend'), mock.patch('sys.stdout', stream):
            self.client.post(reverse('set_language'), {'language': 'ar', 'next': '/'})
            response = self.client.post(reverse('api_register'), register_data())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='salma@example.com').exists())
