"""
Supabase client initialization.
Provides both the admin client (service role) and user-scoped client.
"""
from supabase import create_client, Client
from app.config import get_settings


def get_supabase_admin() -> Client:
    """
    Get Supabase client with service_role key.
    Used for server-side operations that bypass RLS.
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_client() -> Client:
    """
    Get Supabase client with anon key.
    Used with user JWT for RLS-protected operations.
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
