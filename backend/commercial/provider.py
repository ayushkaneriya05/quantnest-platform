"""Bounded provider calls. Never retry an uncertain financial POST blindly."""
import httpx
from django.conf import settings


class ProviderUnavailable(Exception):
    pass


def request_razorpay(method, path, payload=None, *, headers=None):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ProviderUnavailable("razorpay_unconfigured")
    try:
        with httpx.Client(timeout=httpx.Timeout(12, connect=4), follow_redirects=False) as client:
            response = client.request(method, "https://api.razorpay.com/v1/" + path,
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET), json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ProviderUnavailable("provider_response_invalid")
            return data
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable(type(exc).__name__) from None
