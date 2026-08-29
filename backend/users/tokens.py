import uuid
from rest_framework_simplejwt.tokens import RefreshToken

class CustomRefreshToken(RefreshToken):
    """
    Globally patched RefreshToken that ensures all generated tokens
    contain a persistent 'session_id' claim across rotations.
    """
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        # Generate a unique session ID for this new login
        token["session_id"] = str(uuid.uuid4())
        return token

    @property
    def access_token(self):
        access = super().access_token
        # Ensure the access token inherits the session_id
        if "session_id" in self.payload:
            access["session_id"] = self.payload["session_id"]
        return access
