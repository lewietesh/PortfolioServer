# emails/types.py
from .base import BaseEmail

class VerifyEmail(BaseEmail):
    def __init__(self, recipient, code):
        subject = 'Verify Your Email - Portfolio API'
        message = f'Your email verification code is: {code}. This code expires in 10 minutes.'
        super().__init__(subject, message, recipient)

class RecoverPasswordEmail(BaseEmail):
    def __init__(self, recipient, code):
        subject = 'Password Reset Code - Portfolio API'
        message = f'Your password reset code is: {code}. This code expires in 10 minutes.'
        super().__init__(subject, message, recipient)
