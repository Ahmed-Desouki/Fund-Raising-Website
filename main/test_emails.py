"""The emails the site sends: who gets them, what they look like, resending, and the check command."""
from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

PASSWORD = 'StrongPass#1'


def register(client, email='new.person@example.com'):
    return client.post(reverse('api_register'), {
        'first_name': 'Mohamed', 'last_name': 'Ali', 'email': email, 'mobile_number': '01012345678',
        'password1': PASSWORD, 'password2': PASSWORD,
    })


@override_settings(DEFAULT_FROM_EMAIL='Fundraiser <sender@gmail.com>')
class ActivationEmailTests(TestCase):
    def test_goes_to_the_person_who_registered_from_the_site_address(self):
        response = register(self.client, 'mohamed@example.com')
        self.assertIn('mohamed@example.com', response.json()['message'])
        email = mail.outbox[0]
        self.assertEqual(email.to, ['mohamed@example.com'])
        self.assertEqual(email.from_email, 'Fundraiser <sender@gmail.com>')

    def test_has_plain_text_and_html_versions_with_the_link(self):
        register(self.client)
        email = mail.outbox[0]
        html, mimetype = email.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        link = next(line for line in email.body.splitlines() if '/activate/' in line)
        self.assertTrue(link.startswith('http://testserver/activate/'))
        self.assertIn(f'href="{link}"', html)
        self.assertIn('Hi Mohamed,', email.body)

    def test_email_is_in_arabic_for_arabic_visitors(self):
        self.client.post(reverse('set_language'), {'language': 'ar', 'next': '/'})
        register(self.client)
        email = mail.outbox[0]
        self.assertEqual(email.subject, 'فعّل حسابك')
        self.assertIn('dir="rtl"', email.alternatives[0][0])
        self.assertIn('فعّل حسابي', email.alternatives[0][0])

    def test_password_reset_email_has_html_version(self):
        User.objects.create_user('p@example.com', 'p@example.com', PASSWORD, first_name='Pat')
        self.client.post(reverse('password_reset'), {'email': 'p@example.com'})
        email = mail.outbox[0]
        self.assertEqual(email.to, ['p@example.com'])
        html = email.alternatives[0][0]
        self.assertIn('Hi Pat,', html)
        self.assertIn('/password-reset/', html)


class ResendActivationTests(TestCase):
    def resend(self, email='new.person@example.com'):
        return self.client.post(reverse('api_resend_activation'), {'email': email})

    def test_login_to_inactive_account_offers_resend(self):
        register(self.client)
        response = self.client.post(reverse('api_login'), {'email': 'new.person@example.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json()['inactive'])
        self.assertContains(self.client.get(reverse('auth_page')), 'id="resendButton"')

    def test_resend_sends_a_new_working_link(self):
        register(self.client)
        self.assertEqual(self.resend().status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        link = next(line for line in mail.outbox[1].body.splitlines() if '/activate/' in line)
        self.client.get(link.replace('http://testserver', ''))
        self.assertTrue(User.objects.get(email='new.person@example.com').is_active)

    def test_same_answer_for_unknown_and_active_accounts_and_nothing_sent(self):
        User.objects.create_user('active@example.com', 'active@example.com', PASSWORD)
        expected = self.resend('nobody@example.com').json()
        self.assertEqual(self.resend('active@example.com').json(), expected)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_is_rate_limited(self):
        register(self.client)
        for _ in range(3):
            self.assertEqual(self.resend().status_code, 200)
        self.assertEqual(self.resend().status_code, 429)
        self.assertEqual(len(mail.outbox), 1 + 3)


class SendTestEmailCommandTests(TestCase):
    @override_settings(EMAIL_BACKEND='main.email.ReadableConsoleEmailBackend')
    def test_refuses_when_email_is_not_configured(self):
        with self.assertRaisesMessage(CommandError, 'EMAIL_HOST_USER'):
            call_command('send_test_email', 'x@example.com', stdout=StringIO())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_sends_when_configured(self):
        from unittest import mock
        with mock.patch('main.emails.EmailMultiAlternatives.send') as send:
            out = StringIO()
            call_command('send_test_email', 'x@example.com', stdout=out)
        send.assert_called_once()
        self.assertIn('Sent to x@example.com', out.getvalue())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_explains_a_wrong_app_password(self):
        import smtplib
        from unittest import mock
        with mock.patch('main.emails.EmailMultiAlternatives.send', side_effect=smtplib.SMTPAuthenticationError(535, b'bad')):
            with self.assertRaisesMessage(CommandError, 'App Password'):
                call_command('send_test_email', 'x@example.com', stdout=StringIO())
