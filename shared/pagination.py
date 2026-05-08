"""shared/pagination.py — T-3-004: cursor-based пагинация."""
from urllib.parse import urlparse, parse_qs

from rest_framework.pagination import CursorPagination as DRFCursorPagination
from rest_framework.response import Response


class CursorPagination(DRFCursorPagination):
    """
    Cursor-based пагинация по api-contract.md.

    Response: {results, next_cursor, prev_cursor, has_more}
    """
    page_size = 50
    page_size_query_param = "limit"
    max_page_size = 200
    cursor_query_param = "cursor"
    ordering = "-id"

    def get_paginated_response(self, data):
        return Response({
            "results": data,
            "next_cursor": self._extract_cursor(self.get_next_link()),
            "prev_cursor": self._extract_cursor(self.get_previous_link()),
            "has_more": self.has_next,
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "results": schema,
                "next_cursor": {"type": "string", "nullable": True},
                "prev_cursor": {"type": "string", "nullable": True},
                "has_more": {"type": "boolean"},
            },
        }

    @staticmethod
    def _extract_cursor(url):
        if not url:
            return None
        qs = parse_qs(urlparse(url).query)
        return qs.get("cursor", [None])[0]
