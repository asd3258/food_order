from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.permissions import check_permission

router = APIRouter(prefix="/api/orders/history", tags=["history"])


@router.get("", response_model=list[schemas.HistoryOut])
def list_history(db: Session = Depends(get_db)):
    return db.query(models.OrderHistory).options(
        joinedload(models.OrderHistory.lines),
        joinedload(models.OrderHistory.payments),
    ).order_by(models.OrderHistory.id.desc()).all()


@router.patch("/{history_id}/lines/{line_id}/payment", response_model=schemas.HistoryLineOut)
def toggle_payment(history_id: int, line_id: int, acting_user: str, db: Session = Depends(get_db)):
    """v0.18: Toggle is_paid on a specific order history line."""
    history = db.query(models.OrderHistory).filter(models.OrderHistory.id == history_id).first()
    if not history:
        raise HTTPException(404, "History entry not found")
    if not check_permission(db, acting_user, "歷史訂單", "update", history.initiator):
        raise HTTPException(403, "沒有權限修改")
    
    line = db.query(models.OrderHistoryLine).filter(
        models.OrderHistoryLine.order_history_id == history_id,
        models.OrderHistoryLine.id == line_id
    ).first()
    if not line:
        raise HTTPException(404, "History line not found")
        
    line.is_paid = not line.is_paid
    db.commit()
    db.refresh(line)
    return line


@router.delete("/{history_id}", status_code=204)
def delete_history(history_id: int, acting_user: str, db: Session = Depends(get_db)):
    """v0.7: deleting a history entry is admin-only."""
    if not check_permission(db, acting_user, "歷史訂單", "delete"):
        raise HTTPException(403, "沒有權限刪除歷史訂單")
    history = db.query(models.OrderHistory).filter(models.OrderHistory.id == history_id).first()
    if not history:
        raise HTTPException(404, "History entry not found")
    db.delete(history)  # cascades to OrderHistoryLine/OrderHistoryPayment
    db.commit()
    return None
