"""
JWT authentication middleware.
Verifies Supabase JWT tokens from the Authorization header.
Supports both ES256 (via Supabase JWKS) and HS256 (via SUPABASE_JWT_SECRET).
"""
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import get_settings

security = HTTPBearer()

jwks_client_instance = None

def get_jwks_client(supabase_url: str) -> PyJWKClient:
    global jwks_client_instance
    if jwks_client_instance is None:
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        jwks_client_instance = PyJWKClient(jwks_url)
    return jwks_client_instance


async def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify the JWT token from the Authorization header.
    Returns the decoded payload containing user_id (sub).

    Raises:
        HTTPException 401: If token is missing, expired, or invalid.
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        # Determine the algorithm used to sign the token
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg == "ES256":
            # Verify against Supabase's JWKS endpoint
            jwks_client = get_jwks_client(settings.SUPABASE_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                options={"verify_iat": False},
            )
        else:
            # Fallback to local symmetric key (HS256)
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_iat": False},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_current_user_id(payload: dict = Depends(verify_jwt)) -> str:
    """Extract the user ID from the verified JWT payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return user_id
