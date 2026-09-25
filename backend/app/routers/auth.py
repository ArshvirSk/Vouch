import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.config import get_settings
from app.auth import security, get_jwks_client

router = APIRouter(prefix="/auth", tags=["auth"])

class SyncRequest(BaseModel):
    handle: str
    email: str | None = None
    wallet_address: str | None = None

class SyncResponse(BaseModel):
    user_id: str
    handle: str

@router.post("/sync", response_model=SyncResponse)
async def sync_user(
    request: SyncRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Sync a Privy user to the local database."""
    settings = get_settings()
    token = credentials.credentials

    if not settings.privy_app_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PRIVY_APP_ID not configured in backend.",
        )

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=settings.privy_app_id,
            issuer="privy.io",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    privy_id = payload.get("sub")
    if not privy_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Check if user already exists by privy_id
    result = await db.execute(select(User).where(User.privy_id == privy_id))
    user = result.scalar_one_or_none()

    if user:
        return SyncResponse(user_id=str(user.id), handle=user.handle)

    # Legacy migration: check if user exists by email or wallet
    if request.email:
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
        
    if not user and request.wallet_address:
        result = await db.execute(select(User).where(User.wallet_address == request.wallet_address))
        user = result.scalar_one_or_none()
        
    if user:
        # Migrate the existing user to Privy
        user.privy_id = privy_id
        user.auth_provider = "privy"
        try:
            await db.commit()
            return SyncResponse(user_id=str(user.id), handle=user.handle)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Failed to migrate existing user")

    # Create new user
    # Check if handle is taken
    handle_check = await db.execute(select(User).where(User.handle == request.handle))
    if handle_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Handle already taken")

    email_to_use = request.email or f"{privy_id}@privy.vouch.app"
    
    user = User(
        handle=request.handle,
        email=email_to_use,
        wallet_address=request.wallet_address,
        privy_id=privy_id,
        auth_provider="privy",
    )
    db.add(user)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

    return SyncResponse(user_id=str(user.id), handle=user.handle)
