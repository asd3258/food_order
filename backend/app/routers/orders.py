import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _order_query(db: Session):
    return db.query(models.Order).options(joinedload(models.Order.items))


def _line_label(item: models.OrderItem, db: Session) -> str:
    mi = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
    name = mi.name if mi else "(已刪除品項)"
    opts = item.selected_options or []
    return f"{name}({'/'.join(opts)})" if opts else name


def _item_amount(item: models.OrderItem, db: Session) -> int:
    mi = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
    base = mi.price if mi else 0
    extra = 0
    if mi:
        for opt_name in (item.selected_options or []):
            match = next((o for o in mi.options if o.option_name == opt_name), None)
            if match:
                extra += match.extra_price
    return (base + extra) * item.quantity


@router.get("", response_model=list[schemas.OrderOut])
def list_orders(status: str = "open", db: Session = Depends(get_db)):
    return _order_query(db).filter(models.Order.status == status).all()


@router.post("", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderCreateIn, db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(models.Restaurant.id == payload.restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    order = models.Order(restaurant_id=payload.restaurant_id, initiator=payload.initiator,
                          deadline_at=payload.deadline_at,
                          source_vote_batch_id=payload.source_vote_batch_id)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = _order_query(db).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.get("/{order_id}/stats", response_model=list[schemas.StatRow])
def get_order_stats(order_id: int, db: Session = Depends(get_db)):
    """Everyone's current totals (SPEC 4.4) — one row per OrderItem, including
    soft-deleted rows (frontend renders those with strikethrough)."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    rows = []
    for item in order.items:
        rows.append(schemas.StatRow(
            label=_line_label(item, db), user=item.user, quantity=item.quantity,
            amount=_item_amount(item, db), item_id=item.id, is_deleted=item.is_deleted,
        ))
    return rows


@router.post("/{order_id}/items", response_model=schemas.OrderItemOut)
def add_item(order_id: int, payload: schemas.OrderItemCreateIn, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.status != "open":
        raise HTTPException(404, "Open order not found")
    item = models.OrderItem(order_id=order_id, user=payload.user, menu_item_id=payload.menu_item_id,
                             selected_options=payload.selected_options, quantity=payload.quantity,
                             note=payload.note)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{order_id}/items/{item_id}", response_model=schemas.OrderItemOut)
def update_own_item(order_id: int, item_id: int, payload: schemas.OrderItemCreateIn,
                     db: Session = Depends(get_db)):
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if item.user != payload.user:
        raise HTTPException(403, "只能修改自己加入的品項")
    item.quantity = payload.quantity
    item.selected_options = payload.selected_options
    item.note = payload.note
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{order_id}/items/{item_id}", status_code=204)
def remove_own_item(order_id: int, item_id: int, user: str, db: Session = Depends(get_db)):
    """Hard-remove an item you added yourself (the 'My Order' remove action)."""
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if item.user != user:
        raise HTTPException(403, "只能移除自己加入的品項")
    db.delete(item)
    db.commit()
    return None


@router.patch("/{order_id}/items/{item_id}/soft-delete", response_model=schemas.OrderItemOut)
def soft_delete_item(order_id: int, item_id: int, acting_user: str, db: Session = Depends(get_db)):
    """Initiator soft-deletes someone else's line (SPEC 4.4 / v0.4)."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.initiator != acting_user:
        raise HTTPException(403, "只有發起者可以刪除其他人的品項")
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.is_deleted = True
    item.deleted_by = acting_user
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{order_id}/deadline", response_model=schemas.OrderOut)
def update_deadline(order_id: int, payload: schemas.DeadlineIn, acting_user: str,
                     db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.initiator != acting_user:
        raise HTTPException(403, "只有發起者可以修改截止時間")
    order.deadline_at = payload.deadline_at
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/close", response_model=schemas.HistoryOut)
def close_order(order_id: int, acting_user: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.initiator != acting_user:
        raise HTTPException(403, "只有發起者可以結單")
    r = db.query(models.Restaurant).filter(models.Restaurant.id == order.restaurant_id).first()

    active_items = [it for it in order.items if not it.is_deleted]
    history = models.OrderHistory(
        order_id=order.id, restaurant_name=r.name if r else "未知餐廳", initiator=order.initiator,
        closed_date=dt.date.today().isoformat(), people_count=0, total_amount=0,
    )
    db.add(history)
    db.flush()

    by_user = {}
    for it in active_items:
        amount = _item_amount(it, db)
        line = models.OrderHistoryLine(order_history_id=history.id, item_label=_line_label(it, db),
                                        user=it.user, quantity=it.quantity, amount=amount)
        db.add(line)
        by_user[it.user] = by_user.get(it.user, 0) + amount

    history.total_amount = sum(by_user.values())
    history.people_count = len(by_user)
    for user, total in by_user.items():
        db.add(models.OrderHistoryPayment(order_history_id=history.id, user=user,
                                           total_amount=total, is_paid=False))

    order.status = "closed"
    order.closed_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(history)
    return history


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, acting_user: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.initiator != acting_user:
        raise HTTPException(403, "只有發起者可以刪除訂單")
    order.status = "deleted"
    db.commit()
    return None
