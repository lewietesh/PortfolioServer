# emails/base.py
from django.core.mail import send_mail
from django.conf import settings

class BaseEmail:
    def __init__(self, subject, message, recipient, from_email=None):
        self.subject = subject
        self.message = message
        self.recipient = recipient
        self.from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portfolio.com')

    def send(self):
        return send_mail(
            self.subject,
            self.message,
            self.from_email,
            [self.recipient],
            fail_silently=False
        )
