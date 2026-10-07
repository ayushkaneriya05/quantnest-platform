import uuid
from rest_framework_simplejwt.tokens import RefreshToken

class CustomRefreshToken(RefreshToken):
    """Session identifiers are inherited by access tokens and survive rotation."""
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token["session_id"] = str(uuid.uuid4())
        return token
