from collections.abc import Mapping
from rest_framework.exceptions import ParseError
from rest_framework.views import APIView


class ObjectRequestMixin:
    allow_list_payload = False
    skip_object_validation = False
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not self.skip_object_validation and request.method in {"POST", "PATCH", "PUT", "DELETE"} and not isinstance(request.data, Mapping):
            if not (self.allow_list_payload and isinstance(request.data, list)):
                raise ParseError("Provide a JSON object for this request.")


class ObjectAPIView(ObjectRequestMixin, APIView):
    pass
