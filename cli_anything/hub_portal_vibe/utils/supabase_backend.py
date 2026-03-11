"""Supabase backend wrapper for Hub Portal Vibe CLI.

Uses the same Supabase project as the web app.
Requires SUPABASE_URL and SUPABASE_KEY environment variables,
or falls back to the project's public anon key.
"""
import os
from functools import lru_cache

SUPABASE_URL = "https://amylxrskjhqwrlarqfcz.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFteWx4cnNramhxd3JsYXJxZmN6Iiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NDk1NTU5NTcsImV4cCI6MjA2NTEzMTk1N30."
    "Gzgy4GywX-5VYbEcqqBKoorr3jswjUx23TZXVslbK0Y"
)


@lru_cache(maxsize=1)
def get_client():
    """Get or create a Supabase client."""
    try:
        from supabase import create_client
    except ImportError:
        raise RuntimeError(
            "supabase-py is not installed. Install with:\n"
            "  pip install supabase"
        )

    url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
    key = os.environ.get("SUPABASE_KEY", SUPABASE_ANON_KEY)
    return create_client(url, key)


def query_table(table: str, select: str = "*", filters: dict = None,
                order: str = None, limit: int = None):
    """Query a Supabase table with optional filters.

    Args:
        table: Table name.
        select: Columns to select (default "*").
        filters: Dict of {column: value} equality filters.
        order: Column to order by (prefix with - for descending).
        limit: Max rows to return.

    Returns:
        List of row dicts.
    """
    client = get_client()
    q = client.table(table).select(select)

    if filters:
        for col, val in filters.items():
            q = q.eq(col, val)

    if order:
        if order.startswith("-"):
            q = q.order(order[1:], desc=True)
        else:
            q = q.order(order)

    if limit:
        q = q.limit(limit)

    result = q.execute()
    return result.data


def insert_row(table: str, data: dict):
    """Insert a row into a Supabase table."""
    client = get_client()
    result = client.table(table).insert(data).execute()
    return result.data


def update_row(table: str, row_id: str, data: dict):
    """Update a row by ID."""
    client = get_client()
    result = client.table(table).update(data).eq("id", row_id).execute()
    return result.data


def count_rows(table: str, filters: dict = None) -> int:
    """Count rows in a table with optional filters."""
    client = get_client()
    q = client.table(table).select("id", count="exact")
    if filters:
        for col, val in filters.items():
            q = q.eq(col, val)
    result = q.execute()
    return result.count or 0
