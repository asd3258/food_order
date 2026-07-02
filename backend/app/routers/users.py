from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


def _order_counts(db: Session) -> dict:
    """How many OrderHistoryLine rows mention each name -- used to sort the
    快速登入 (quick login) list so the most frequent orderers show up first."""
    rows = db.query(
        models.OrderHistoryLine.user, func.count(models.OrderHistoryLine.id)
    ).group_by(models.OrderHistoryLine.user).all()
    return {name: count for name, count in rows}


def _to_out(u: models.User, counts: dict) -> schemas.UserOut:
    return schemas.UserOut(id=u.id, name=u.name, order_count=counts.get(u.name, 0))


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    counts = _order_counts(db)
    users = db.query(models.User).all()
    out = [_to_out(u, counts) for u in users]
    out.sort(key=lambda u: (-u.order_count, u.name))
    return out


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    return _to_out(u, _order_counts(db))


@router.post("", response_model=schemas.UserOut)
def login_or_create(payload: schemas.UserCreateIn, db: Session = Depends(get_db)):
    """Powers both the "登入&自動建立" free-text field and the 快速登入 list
    (which just re-submits an existing name) -- idempotent: matching an
    existing name (case-insensitive) logs in as that person instead of
    creating a duplicate roster entry."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "請輸入使用者名稱")
    existing = db.query(models.User).filter(func.lower(models.User.name) == name.lower()).first()
    if existing:
        return _to_out(existing, _order_counts(db))
    u = models.User(name=name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return _to_out(u, _order_counts(db))


@router.patch("/{user_id}", response_model=schemas.UserOut)
def rename_user(user_id: int, payload: schemas.UserRenameIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    new_name = payload.name.strip()
    if not new_name:
        raise HTTPException(400, "請輸入使用者名稱")
    u.name = new_name
    db.commit()
    db.refresh(u)
    return _to_out(u, _order_counts(db))


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Removes this person from the roster/quick-login list only -- does NOT
    touch any orders/votes/history they're mentioned in (those store the name
    as a plain string snapshot, see the note in models.py)."""
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    db.delete(u)
    db.commit()
    return None
