import re

from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

LINK = re.compile(r'https?://\S+')


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    """
    Prints emails to the runserver terminal as plain, readable text.

    Django's console backend prints the raw encoded email: Arabic emails come out as base64
    and long lines are wrapped with '=', so the activation / reset link can't be read or copied.
    """

    def write_message(self, message):
        links = '\n'.join(LINK.findall(message.body))
        text = (
            f'\n===== Email (not sent: EMAIL_HOST_USER is not set in .env) =====\n'
            f'To: {", ".join(message.to)}\n'
            f'Subject: {message.subject}\n'
            f'Links:\n{links}\n\n'
            f'{message.body}\n'
            f'{"=" * 66}\n'
        )
        try:
            self.stream.write(text)
        except UnicodeEncodeError:
            # Windows terminals often can't show Arabic; keep the (ASCII) links intact
            # and replace only the characters the terminal can't display
            encoding = getattr(self.stream, 'encoding', None) or 'ascii'
            self.stream.write(text.encode(encoding, errors='replace').decode(encoding))
