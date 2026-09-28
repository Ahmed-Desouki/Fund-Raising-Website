from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    """
    Prints emails to the runserver terminal as plain, readable text.

    Django's console backend prints the raw encoded email: Arabic emails come out as base64
    and long lines are wrapped with '=', so the activation / reset link can't be read or copied.
    """

    def write_message(self, message):
        self.stream.write(
            f'\n===== Email (not sent: EMAIL_HOST_USER is not set in .env) =====\n'
            f'To: {", ".join(message.to)}\n'
            f'Subject: {message.subject}\n\n'
            f'{message.body}\n'
            f'{"=" * 66}\n'
        )
