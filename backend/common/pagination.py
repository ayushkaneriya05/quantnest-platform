"""One bounded, deterministic contract for user-facing record lists."""

from django.core.paginator import Paginator
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    page_sizes = (10, 25, 50, 100)
    max_page_size = 100

    @classmethod
    def defaults(cls):
        return {"page_size": cls.page_size, "page_sizes": cls.page_sizes}

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        raw_page = request.query_params.get(self.page_query_param, "1")
        raw_size = request.query_params.get(self.page_size_query_param, str(self.page_size))
        if len(raw_page) > 20 or not raw_page.isascii() or not raw_page.isdecimal() or int(raw_page) < 1:
            raise ValidationError({"page": "Enter a positive whole page number."})
        if len(raw_size) > 20 or not raw_size.isascii() or not raw_size.isdecimal() or int(raw_size) not in self.page_sizes:
            raise ValidationError({"page_size": f"Choose one of {', '.join(map(str, self.page_sizes))}."})
        self.size = int(raw_size)
        # Reuse Django's cached count; clamp deletions without a second COUNT.
        if hasattr(queryset, "ordered") and not queryset.ordered:
            queryset = queryset.order_by("-pk")
        paginator = Paginator(queryset, self.size)
        self.page = paginator.page(min(int(raw_page), paginator.num_pages))
        return list(self.page)

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.size,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
