"""
Every email the site sends goes through here, so they all look the same and are sent the same way:
a plain-text version plus an HTML version (a single plain-text email is much more likely to be
flagged as spam), from DEFAULT_FROM_EMAIL, to the person who registered.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import get_language, get_language_bidi
from django.utils.translation import gettext as _

from .tokens import account_activation_token


def send_link_email(to, subject, name, intro, button, link, footer):
    text = '\n\n'.join([_('Hi %(name)s,') % {'name': name}, intro, link, footer]) + '\n'
    html = render_to_string('main/emails/base.html', {
        'subject': subject, 'name': name, 'intro': intro, 'button': button, 'link': link, 'footer': footer,
        'LANGUAGE_CODE': get_language(), 'LANGUAGE_BIDI': get_language_bidi(),
    })
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    message.attach_alternative(html, 'text/html')
    message.send()


def activation_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    return request.build_absolute_uri(reverse('activate', args=[uid, token]))


def send_activation_email(request, user):
    send_link_email(
        to=user.email,
        subject=_('Activate your account'),
        name=user.first_name,
        intro=_('Thanks for signing up. Click the button below to activate your account. This link expires in 24 hours.'),
        button=_('Activate my account'),
        link=activation_link(request, user),
        footer=_("If you didn't create this account, you can ignore this email."),
    )
