from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

class CustomRefreshToken(RefreshToken):
    """
    Globally patched RefreshToken that ensures all generated access tokens
    contain the 'sid' (Session ID) claim linked to this refresh token's JTI.
    """
    @property
    def access_token(self):
        access = super().access_token
        # Link the access token to this refresh token's JTI (Session ID)
        access["sid"] = self.payload.get("jti")
        return access
