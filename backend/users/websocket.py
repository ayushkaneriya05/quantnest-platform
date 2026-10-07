"""Session revocation and token expiry apply to every authenticated stream."""
import asyncio
import json
import time
from channels.db import database_sync_to_async
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from .authentication import SafeJWTAuthentication


class AuthSessionConsumerMixin:
    async def __call__(self, *args, **kwargs):
        self.auth_group = None
        self.auth_expiry_task = None
        try:
            return await super().__call__(*args, **kwargs)
        finally:
            if self.auth_expiry_task:
                self.auth_expiry_task.cancel()
            if self.auth_group:
                await self.channel_layer.group_discard(self.auth_group, self.channel_name)

    async def accept(self, *args, **kwargs):
        session_id = self.scope.get("auth_session_id")
        if not session_id:
            await self.close(code=4401)
            return
        self.auth_group = f"auth_session_{session_id}"
        await self.channel_layer.group_add(self.auth_group, self.channel_name)
        # Cover a revocation between middleware validation and joining the group.
        if not await self._session_is_valid():
            await self.close(code=4401)
            return
        await super().accept(*args, **kwargs)
        self.auth_expiry_task = asyncio.create_task(self._close_on_expiry())

    @database_sync_to_async
    def _session_is_valid(self):
        try:
            self.scope["auth_token"].check_exp()
            SafeJWTAuthentication().get_user(self.scope["auth_token"])
            return True
        except (AuthenticationFailed, TokenError):
            return False

    async def _close_on_expiry(self):
        await asyncio.sleep(max(0, self.scope["auth_expires_at"] - time.time()))
        await self.close(code=4001)

    async def auth_session_revoked(self, event):
        await self.send(text_data=json.dumps({"type": "auth.revoked", "session_id": self.scope["auth_session_id"]}))
        await self.close(code=4401)

    async def auth_credentials_changed(self, event):
        await self.close(code=4001)
