"""
Supabase client initialization.
Provides both the admin client (service role) and user-scoped client.
"""
from functools import lru_cache

import httpx
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from app.config import get_settings

# storage3 defaults to a 20-second timeout. That is fine for a PDF or a
# screenshot, but a lecture recording is tens of megabytes and regularly
# takes longer than that to transfer — which is why audio uploads failed
# while the smaller types went through.
STORAGE_TIMEOUT_SECONDS = 600

# Supabase's edge closes idle connections without warning. Keeping our own
# idle sockets shorter-lived than theirs means we open a fresh one instead of
# writing into a half-closed pipe.
KEEPALIVE_EXPIRY_SECONDS = 15

# How many times a request is replayed after a dead pooled connection.
CONNECTION_RETRIES = 2

_RETRYABLE = (
    httpx.RemoteProtocolError,  # "Server disconnected" on a reused connection
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
)


class _RetryTransport(httpx.BaseTransport):
    """
    Retries a request when the *connection* dies, not when the server answers.

    The clients below are cached for the process lifetime, so their httpx
    connection pools hand out sockets that have been sitting idle. Supabase
    (and the proxy in front of it) drops those, and httpx surfaces the reuse
    of a dead socket as RemoteProtocolError("Server disconnected") — which
    reached the routers as a 500 on perfectly valid queries. The failed
    connection is evicted from the pool, so simply asking again gets a new
    one. HTTP statuses are never retried: a 4xx/5xx from PostgREST is a real
    answer and belongs to the caller.
    """

    def __init__(self, inner: httpx.BaseTransport, retries: int = CONNECTION_RETRIES):
        self._inner = inner
        self._retries = retries

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            # Buffer the body so the request can be sent a second time; a
            # streaming upload cannot be rewound, so it is left alone.
            request.read()
            replayable = True
        except Exception:
            replayable = False

        attempts = self._retries + 1 if replayable else 1
        for attempt in range(attempts):
            try:
                return self._inner.handle_request(request)
            except _RETRYABLE:
                if attempt == attempts - 1:
                    raise
        raise AssertionError("unreachable")

    def close(self) -> None:
        self._inner.close()


def _harden_session(session: httpx.Client) -> None:
    """Give one httpx client a short keepalive and connection retries."""
    inner = httpx.HTTPTransport(
        # HTTP/1.1 only. PostgREST gains nothing from multiplexing here, and
        # the h2 GOAWAY path is where the stale-connection errors came from.
        http2=False,
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=KEEPALIVE_EXPIRY_SECONDS,
        ),
    )
    session._transport = _RetryTransport(inner)
    session._mounts = {}


def _harden(client: Client) -> Client:
    """
    Apply the transport above to every sub-client that talks over HTTP.

    `postgrest` and `storage` are lazy properties — touching them here builds
    them once, at startup, instead of on the first request that needs them.
    """
    for session in (
        client.postgrest.session,
        client.storage.session,
        getattr(client.auth, "_http_client", None),
    ):
        if isinstance(session, httpx.Client):
            _harden_session(session)
    return client


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
    return _harden(
        create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            options=_client_options(),
        )
    )


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get Supabase client with anon key.
    Used with user JWT for RLS-protected operations.
    """
    settings = get_settings()
    return _harden(
        create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
            options=_client_options(),
        )
    )
