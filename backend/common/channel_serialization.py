"""Convert event payloads to values supported by the Channels Redis serializer."""

from rest_framework.utils.encoders import JSONEncoder

_encoder = JSONEncoder()


def json_safe_channel_data(data):
    """Match REST JSON encoding before publishing data through a channel layer."""
    if isinstance(data, dict):
        return {str(key): json_safe_channel_data(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [json_safe_channel_data(value) for value in data]
    if data is None or isinstance(data, (str, int, float, bool)):
        return data
    return _encoder.default(data)
