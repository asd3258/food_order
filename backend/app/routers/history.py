from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db

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
    if history.initiator != acting_user:
        raise HTTPException(403, "只有該筆訂單的發起者可以切換收款狀態")
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
