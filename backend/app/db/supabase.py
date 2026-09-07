"""
Supabase client initialization.
Provides both the admin client (service role) and user-scoped client.
"""
from functools import lru_cache
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from app.config import get_settings

# storage3 defaults to a 20-second timeout. That is fine for a PDF or a
# screenshot, but a lecture recording is tens of megabytes and regularly
# takes longer than that to transfer — which is why audio uploads failed
# while the smaller types went through.
STORAGE_TIMEOUT_SECONDS = 600


def _client_options() -> ClientOptions:
    return ClientOptions(storage_client_timeout=STORAGE_TIMEOUT_SECONDS)


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """
    Get Supabase client with service_role key.
    Used for server-side operations that bypass RLS.

    Cached: every call used to build a fresh client (and a fresh HTTP
    connection pool), which added a full TCP+TLS handshake to every request.
    """
    settings = get_settings()
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=_client_options(),
    )


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get Supabase client with anon key.
    Used with user JWT for RLS-protected operations.
    """
    settings = get_settings()
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        options=_client_options(),
    )
