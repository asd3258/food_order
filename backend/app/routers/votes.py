import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.permissions import is_admin_user

router = APIRouter(prefix="/api/votes", tags=["votes"])


def _serialize_batch(batch: models.VoteBatch, db: Session, user: str | None = None) -> schemas.VoteBatchOut:
    candidates = []
    for c in batch.candidates:
        r = db.query(models.Restaurant).filter(models.Restaurant.id == c.restaurant_id).first()
        count = db.query(models.Vote).filter(
            models.Vote.vote_batch_id == batch.id,
            models.Vote.restaurant_id == c.restaurant_id,
            models.Vote.status == "locked",
        ).count()
        candidates.append(schemas.VoteCandidateOut(
            restaurant_id=c.restaurant_id, restaurant_name=r.name if r else "未知餐廳", count=count))

    my_selection, my_locked = None, False
    if user:
        my_vote = db.query(models.Vote).filter(models.Vote.vote_batch_id == batch.id,
                                                 models.Vote.user == user).first()
        if my_vote:
            my_selection = my_vote.restaurant_id
            my_locked = my_vote.status == "locked"

    return schemas.VoteBatchOut(id=batch.id, initiator=batch.initiator, deadline_at=batch.deadline_at,
                                 status=batch.status, candidates=candidates,
                                 my_selection=my_selection, my_locked=my_locked)


@router.get("", response_model=list[schemas.VoteBatchOut])
def list_votes(status: str = "open", db: Session = Depends(get_db)):
    batches = db.query(models.VoteBatch).options(
        joinedload(models.VoteBatch.candidates)).filter(models.VoteBatch.status == status).all()
    return [_serialize_batch(b, db) for b in batches]


@router.post("", response_model=schemas.VoteBatchOut)
def create_vote(payload: schemas.VoteBatchCreateIn, db: Session = Depends(get_db)):
    if len(payload.restaurant_ids) < 2:
        raise HTTPException(400, "投票需要至少 2 家候選餐廳")
    batch = models.VoteBatch(initiator=payload.initiator, deadline_at=payload.deadline_at)
    db.add(batch)
    db.flush()
    for rid in payload.restaurant_ids:
        db.add(models.VoteBatchCandidate(vote_batch_id=batch.id, restaurant_id=rid))
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch, db)


@router.get("/{batch_id}", response_model=schemas.VoteBatchOut)
def get_vote(batch_id: int, user: str | None = None, db: Session = Depends(get_db)):
    batch = db.query(models.VoteBatch).options(
        joinedload(models.VoteBatch.candidates)).filter(models.VoteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Vote batch not found")
    return _serialize_batch(batch, db, user)


@router.put("/{batch_id}/my-choice")
def save_my_choice(batch_id: int, payload: schemas.VoteChoiceIn, db: Session = Depends(get_db)):
    """Corresponds to pressing Save: locks in the user's choice for this batch."""
    batch = db.query(models.VoteBatch).filter(models.VoteBatch.id == batch_id).first()
    if not batch or batch.status != "open":
        raise HTTPException(404, "Open vote batch not found")
    vote = db.query(models.Vote).filter(models.Vote.vote_batch_id == batch_id,
                                         models.Vote.user == payload.user).first()
    if not vote:
        vote = models.Vote(vote_batch_id=batch_id, user=payload.user)
        db.add(vote)
    vote.restaurant_id = payload.restaurant_id
    vote.status = "locked"
    vote.locked_at = dt.datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/{batch_id}/my-choice")
def clear_my_choice(batch_id: int, user: str, db: Session = Depends(get_db)):
    """Corresponds to pressing Edit (v0.5 behavior change): immediately
    removes the user's locked vote so it stops counting toward the tally
    right away, rather than keeping the old pick counted until Save is
    pressed again. The user has to pick and Save again to be counted."""
    batch = db.query(models.VoteBatch).filter(models.VoteBatch.id == batch_id).first()
    if not batch or batch.status != "open":
        raise HTTPException(404, "Open vote batch not found")
    vote = db.query(models.Vote).filter(models.Vote.vote_batch_id == batch_id,
                                         models.Vote.user == user).first()
    if vote:
        db.delete(vote)
        db.commit()
    return {"ok": True}


@router.patch("/{batch_id}/deadline", response_model=schemas.VoteBatchOut)
def update_deadline(batch_id: int, payload: schemas.DeadlineIn, acting_user: str,
                     db: Session = Depends(get_db)):
    batch = db.query(models.VoteBatch).options(
        joinedload(models.VoteBatch.candidates)).filter(models.VoteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Vote batch not found")
    if batch.initiator != acting_user and not is_admin_user(db, acting_user):
        raise HTTPException(403, "只有發起者可以修改截止時間")
    batch.deadline_at = payload.deadline_at
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch, db)


@router.post("/{batch_id}/decide", response_model=schemas.OrderOut)
def decide_vote(batch_id: int, acting_user: str, db: Session = Depends(get_db)):
    """Tally: highest locked-vote candidate wins; ties -> first in candidate order."""
    batch = db.query(models.VoteBatch).options(
        joinedload(models.VoteBatch.candidates)).filter(models.VoteBatch.id == batch_id).first()
    if not batch or batch.status != "open":
        raise HTTPException(404, "Open vote batch not found")
    if batch.initiator != acting_user and not is_admin_user(db, acting_user):
        raise HTTPException(403, "只有發起者可以開票")

    winner_id, best_count = None, -1
    for c in batch.candidates:
        count = db.query(models.Vote).filter(
            models.Vote.vote_batch_id == batch.id,
            models.Vote.restaurant_id == c.restaurant_id,
            models.Vote.status == "locked",
        ).count()
        if count > best_count:
            best_count, winner_id = count, c.restaurant_id

    order = models.Order(restaurant_id=winner_id, initiator=acting_user,
                          deadline_at=batch.deadline_at, source_vote_batch_id=batch.id)
    db.add(order)
    batch.status = "decided"
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{batch_id}", status_code=204)
def delete_vote(batch_id: int, acting_user: str, db: Session = Depends(get_db)):
    batch = db.query(models.VoteBatch).filter(models.VoteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Vote batch not found")
    if batch.initiator != acting_user and not is_admin_user(db, acting_user):
        raise HTTPException(403, "只有發起者可以刪除投票")
    batch.status = "deleted"
    db.commit()
    return None
