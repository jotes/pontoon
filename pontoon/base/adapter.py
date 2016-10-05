import base64
import hashlib

from allauth.account.adapter import get_adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.utils.encoding import smart_bytes


class PontoonSocialAdapter(DefaultSocialAccountAdapter):
    """
    It's required to merge old accounts created via django-browserid
    with accounts created by django-allauth.
    """

    def save_user(self, request, sociallogin, form=None):
        """
        Generates an unique username in the same way as it was done in django-browserid.
        This is required to avoid collisions and the backward compatibility.
        """
        user = super(PontoonSocialAdapter, self).save_user(request, sociallogin, form)
        user.username = base64.urlsafe_b64encode(
            hashlib.sha1(smart_bytes(user.email)).digest()
        ).rstrip(b'=')
        user.save()
        return user

    def pre_social_login(self, request, sociallogin):
        """connect existing accounts with existing accounts."""
        email = sociallogin.account.extra_data.get('email')

        if not email:
            return


        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if sociallogin.state['process'] == 'connect' and request.user.is_authenticated() and user:
            oldest_account, newer_account = (request.user, user) if request.user.pk < user.pk else (user, request.user)
            newer_account.is_active = False
            newer_account.socialaccount_set.update(user=oldest_account)
            newer_account.save()
            user = oldest_account
            newer_account.save()

            message = 'Your Persona account and Firefox Account have been connected.'
            messages.success(request, message)

            sociallogin.user = oldest_account
            sociallogin.account.user = oldest_account
            adapter = get_adapter(request)
            adapter.login(request, oldest_account)


        # Without this adapter, django-allauth can't connect accounts from the old auth
        # system (django-browserid) and requires manual intervention from the user.
        # Because all of our providers use verified emails, we can safely merge
        # accounts if they have the same primary email.

    def get_connect_redirect_url(self, request, sociallogin):
        """
        Redirect to the main page if accounts were connected.
        """
        assert request.user.is_authenticated()
        return '/'

    def is_open_for_signup(self, request, sociallogin):
        """
        Disable signups with Persona.
        """
        if sociallogin.account.provider == 'persona':
            return False

        return True
