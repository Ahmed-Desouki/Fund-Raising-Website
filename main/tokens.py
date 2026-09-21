from django.contrib.auth.tokens import PasswordResetTokenGenerator

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Subclassing (rather than reusing default_token_generator directly) gives this
    a different internal salt, so activation tokens and password-reset tokens
    can never be swapped/reused for the other purpose.
    """
    pass

account_activation_token = AccountActivationTokenGenerator()