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


@router.patch("/{history_id}/payments/{user}", response_model=schemas.HistoryPaymentOut)
def toggle_payment(history_id: int, user: str, acting_user: str, db: Session = Depends(get_db)):
    """v0.5: only the original initiator of this history entry may toggle is_paid."""
    history = db.query(models.OrderHistory).filter(models.OrderHistory.id == history_id).first()
    if not history:
        raise HTTPException(404, "History entry not found")
    if not check_permission(db, acting_user, "歷史訂單", "update", history.initiator):
        raise HTTPException(403, "沒有權限修改")
    payment = db.query(models.OrderHistoryPayment).filter(
        models.OrderHistoryPayment.order_history_id == history_id,
        models.OrderHistoryPayment.user == user).first()
    if not payment:
        raise HTTPException(404, "Payment row not found")
    payment.is_paid = not payment.is_paid
    import datetime as dt
    payment.paid_at = dt.datetime.utcnow() if payment.is_paid else None
    db.commit()
    db.refresh(payment)
    return payment


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
