"""Privy JWT authentication utilities.

Validates JWT tokens issued by Privy using their JWKS public keys.
"""

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer()

# We will lazily instantiate the JWKS client to ensure settings are loaded
_jwks_client = None

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"https://auth.privy.io/api/v1/apps/{settings.privy_app_id}/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from Privy JWT."""
    settings = get_settings()
    token = credentials.credentials

    if not settings.privy_app_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PRIVY_APP_ID not configured in backend.",
        )

    try:
        # Get the signing key from the JWKS
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        
        # Verify the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=settings.privy_app_id,
            issuer="privy.io",
        )
        
    except jwt.PyJWKClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to fetch JWKS: {str(e)}",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    # The subject claim 'sub' contains the Privy DID (did:privy:...)
    privy_id = payload.get("sub")
    if not privy_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Find the user by privy_id
    result = await db.execute(select(User).where(User.privy_id == privy_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found in local database (needs sync)",
        )
        
    return user
