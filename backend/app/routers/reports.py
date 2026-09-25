from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.report import Report
from app.models.commitment import Commitment

router = APIRouter(prefix="/reports", tags=["reports"])

class ReportCreate(BaseModel):
    commitment_id: uuid.UUID
    reason: str

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    req: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a report for moderation (spam/abuse) on a public commitment."""
    commitment = await db.get(Commitment, req.commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
        
    report = Report(
        reporter_id=current_user.id,
        commitment_id=req.commitment_id,
        reason=req.reason
    )
    db.add(report)
    await db.commit()
    
    return {"status": "success", "message": "Report submitted"}
