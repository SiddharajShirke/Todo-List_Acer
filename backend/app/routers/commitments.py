"""
routers/commitments.py — Commitment CRUD + AI Ingest
POST /api/commitments/ingest   → LLM extract from raw text, save, trigger scoring
GET  /api/commitments          → list (sorted by priority_score desc)
GET  /api/commitments/{id}     → detail with tasks + recovery_plan for high-risk
PATCH /api/commitments/{id}/done → mark done
DELETE /api/commitments/{id}   → soft-delete
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.commitment import Commitment
from app.models.task import Task
from app.schemas.commitment import CommitmentOut, CommitmentCreate, CommitmentIngest
from app.routers.deps import get_current_user
from app.services.llm_service import LLMService
from app.services.priority_engine import PriorityEngine
from app.services.risk_engine import RiskEngine
from app.services.graph_service import GraphService
from app.services.root_cause_engine import RootCauseEngine

router = APIRouter(prefix="/api/commitments", tags=["commitments"])

def _days_until(due_date) -> Optional[int]:
    try:
        delta = due_date - datetime.now().date()
        return delta.days
    except:
        return None

def _enrich(c: Commitment) -> CommitmentOut:
    out = CommitmentOut.model_validate(c)
    out.days_until_due = _days_until(c.due_date)
    return out

@router.post("/ingest", response_model=CommitmentOut, status_code=status.HTTP_201_CREATED)
async def ingest_commitment(payload: CommitmentIngest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """AI extracts structured commitment from raw text, saves + scores it."""
    llm = LLMService()
    extracted = await llm.extract_commitment(payload.raw_text)
    if not extracted:
        raise HTTPException(status_code=422, detail="LLM could not extract a commitment from this text")

    c = Commitment(
        user_id=user.id,
        type=extracted.get("type", "other"),
        title=extracted.get("title", "Untitled"),
        description=extracted.get("description"),
        due_date=extracted.get("due_date"),
        amount=extracted.get("amount"),
        source=payload.source,
        metadata_json={"raw_text": payload.raw_text[:500], "confidence": extracted.get("confidence", 0.8)},
    )
    db.add(c)
    db.flush()

    c.priority_score = PriorityEngine.score(c)
    c.risk_score = RiskEngine.score(c)
    rc = RootCauseEngine.predict(c)
    c.root_cause = rc["root_cause"]
    c.root_cause_score = rc["score"]

    tasks = GraphService.decompose(c)
    for i, t in enumerate(tasks):
        db.add(Task(commitment_id=c.id, user_id=user.id, order_index=i, **t))

    db.commit()
    db.refresh(c)
    return _enrich(c)

@router.post("/manual", response_model=CommitmentOut, status_code=status.HTTP_201_CREATED)
def create_manual(payload: CommitmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = Commitment(user_id=user.id, source="manual", **payload.model_dump())
    db.add(c)
    db.flush()
    c.priority_score = PriorityEngine.score(c)
    c.risk_score = RiskEngine.score(c)
    rc = RootCauseEngine.predict(c)
    c.root_cause, c.root_cause_score = rc["root_cause"], rc["score"]
    tasks = GraphService.decompose(c)
    for i, t in enumerate(tasks):
        db.add(Task(commitment_id=c.id, user_id=user.id, order_index=i, **t))
    db.commit()
    db.refresh(c)
    return _enrich(c)

@router.get("", response_model=List[CommitmentOut])
def list_commitments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Commitment).filter(Commitment.user_id == user.id, Commitment.is_done == False).order_by(Commitment.priority_score.desc()).all()
    return [_enrich(c) for c in items]

@router.get("/{commitment_id}", response_model=CommitmentOut)
def get_commitment(commitment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id, Commitment.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return _enrich(c)

@router.patch("/{commitment_id}/done")
def mark_done(commitment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id, Commitment.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    c.is_done = True
    db.commit()
    return {"message": "Marked as done"}

@router.delete("/{commitment_id}")
def delete_commitment(commitment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id, Commitment.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(c)
    db.commit()
    return {"message": "Deleted"}
