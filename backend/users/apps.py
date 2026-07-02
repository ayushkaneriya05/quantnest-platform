from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Universal Fix for Session Revocation:
        # Patch RefreshToken globally so any library generating tokens (dj-rest-auth, OTP, Social)
        # automatically includes the 'sid' (Session ID) claim in its access tokens.
        import rest_framework_simplejwt.tokens
        from .tokens import CustomRefreshToken
        rest_framework_simplejwt.tokens.RefreshToken = CustomRefreshToken
