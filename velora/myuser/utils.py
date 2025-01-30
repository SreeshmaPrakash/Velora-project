from django.core.mail import send_mail
from django.conf import settings
import random

def generate_otp():
    return random.randint(1000,9999)

def send_otp(email,otp):
    subject = 'Your OTP code'
    message = f'Your OTP for signup is {otp}.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject,message,email_from,recipient_list)