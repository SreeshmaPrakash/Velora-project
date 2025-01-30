
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib import messages


User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return

        # Get email
        email = user_email(user)
        if not email:
            return

        # Check if given email exists
        try:
            existing_user = User.objects.get(email=email)
            # Connect social account to existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

