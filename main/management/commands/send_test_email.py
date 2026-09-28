"""
Check the email settings in .env by sending one real test email.

    python manage.py send_test_email someone@example.com
"""
import smtplib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from main.emails import send_link_email


class Command(BaseCommand):
    help = 'Send a test email to check the EMAIL_* settings in .env'

    def add_arguments(self, parser):
        parser.add_argument('to', help='Address to send the test email to')

    def handle(self, *args, **options):
        if not settings.EMAIL_BACKEND.endswith('smtp.EmailBackend'):
            raise CommandError(
                'EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are empty in .env, so emails are only printed in the '
                'terminal. Fill them in (see .env.example) and try again.')

        self.stdout.write(f'Sending from {settings.DEFAULT_FROM_EMAIL} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT} ...')
        try:
            send_link_email(
                to=options['to'], subject='Fundraiser test email', name=options['to'].split('@')[0],
                intro='If you can read this, the email settings work and new users will get their activation link.',
                button='Open Fundraiser', link='http://127.0.0.1:8000/', footer='This is a test from manage.py send_test_email.',
            )
        except smtplib.SMTPAuthenticationError:
            raise CommandError(
                'Login refused. EMAIL_HOST_PASSWORD must be an App Password (16 letters) created on the same '
                'Gmail account as EMAIL_HOST_USER: https://myaccount.google.com/apppasswords')
        except (smtplib.SMTPException, OSError) as e:
            raise CommandError(f'Could not send: {e}. Check EMAIL_HOST / EMAIL_PORT and your internet connection.')

        self.stdout.write(self.style.SUCCESS(
            f'Sent to {options["to"]}. If it is not in the inbox within a minute, check the Spam folder.'))
