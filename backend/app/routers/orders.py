import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, selectinload

from app import models, schemas
from app.database import get_db
from app.permissions import check_permission
from app.ws_manager import manager
from app.scheduler import schedule_order_deadline, cancel_order_deadline

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _order_query(db: Session):
    # sold_outs 用 selectinload,避免跟 items 兩個 collection 一起 joinedload 時
    # 產生列的笛卡兒積。
    return db.query(models.Order).options(joinedload(models.Order.items),
                                           selectinload(models.Order.sold_outs))


def _reject_if_sold_out(db: Session, order_id: int, menu_item_id: int | None,
                        selected_options: list[str]) -> None:
    """v0.19: 售完的品項/選項連後端都不收 -- 前端會反灰擋住點選,但別人可能停在
    標記售完之前載入的舊畫面(或直接打 API),所以下單/改單時再驗一次。"""
    if menu_item_id is None:
        return
    marks = db.query(models.OrderSoldOut).filter(
        models.OrderSoldOut.order_id == order_id,
        models.OrderSoldOut.menu_item_id == menu_item_id).all()
    if any(m.option_name is None for m in marks):
        raise HTTPException(409, "此品項已售完,無法點選")
    chosen = set(selected_options or [])
    hit = next((m for m in marks if m.option_name in chosen), None)
    if hit:
        raise HTTPException(409, f"選項「{hit.option_name}」已售完,請改選其他選項")


import math

def _line_label(item: models.OrderItem, db: Session) -> str:
    mi = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
    name = mi.name if mi else "(已刪除品項)"
    opts = item.selected_options or []
    
    formatted_opts = []
    if mi:
        for opt_name in opts:
            match = next((o for o in mi.options if o.option_name == opt_name), None)
            if match and match.extra_price:
                ep = match.extra_price
                sign = "+" if ep > 0 else "-"
                val = abs(ep)
                val_str = f"{val:g}"
                formatted_opts.append(f"{opt_name}({sign}${val_str})")
            else:
                formatted_opts.append(opt_name)
    else:
        formatted_opts = opts
        
    return f"{name}({'/'.join(formatted_opts)})" if formatted_opts else name


def _validate_integer_amount(db: Session, menu_item_id: int | None,
                             selected_options: list[str], quantity: int) -> None:
    mi = db.query(models.MenuItem).filter(models.MenuItem.id == menu_item_id).first()
    if mi is None:
        return
    unit_price = Decimal(str(mi.price))
    for opt_name in selected_options:
        match = next((o for o in mi.options if o.option_name == opt_name), None)
        if match:
            unit_price += Decimal(str(match.extra_price or 0))
    amount = unit_price * quantity
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise HTTPException(422, f"品項總價不能有小數點（目前為 {amount:g} 元），請調整數量或選項，使總價為整數。")


def _item_amount(item: models.OrderItem, db: Session) -> int:
    mi = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
    base = mi.price if mi else 0
    extra = 0.0
    if mi:
        for opt_name in (item.selected_options or []):
            match = next((o for o in mi.options if o.option_name == opt_name), None)
            if match:
                extra += float(match.extra_price)
    return math.ceil((base + extra) * item.quantity)


@router.get("", response_model=list[schemas.OrderOut])
def list_orders(status: str = "open", db: Session = Depends(get_db)):
    return _order_query(db).filter(models.Order.status == status).all()


@router.post("", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderCreateIn, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(models.Restaurant.id == payload.restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    if not check_permission(db, payload.initiator, "開單與投票", "create"):
        raise HTTPException(403, "沒有權限發起訂單")
    order = models.Order(restaurant_id=payload.restaurant_id, initiator=payload.initiator,
                          deadline_at=payload.deadline_at,
                          source_vote_batch_id=payload.source_vote_batch_id)
    db.add(order)
    db.commit()
    db.refresh(order)
    
    schedule_order_deadline(order)
    
    bg_tasks.add_task(manager.broadcast_home_update)
    return order


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, user: str | None = None, db: Session = Depends(get_db)):
    order = _order_query(db).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.get("/{order_id}/stats", response_model=list[schemas.StatRow])
def get_order_stats(order_id: int, user: str | None = None, db: Session = Depends(get_db)):
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
def add_item(order_id: int, payload: schemas.OrderItemCreateIn, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.status != "open":
        raise HTTPException(404, "Open order not found")
    if not check_permission(db, payload.user, "訂單", "update", order.initiator):
        raise HTTPException(403, "沒有權限新增品項")
    if order.is_locked and not check_permission(db, payload.user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "此訂單已鎖單，無法新增品項")
    _reject_if_sold_out(db, order_id, payload.menu_item_id, payload.selected_options)
    _validate_integer_amount(db, payload.menu_item_id, payload.selected_options, payload.quantity)
    item = models.OrderItem(order_id=order_id, user=payload.user, menu_item_id=payload.menu_item_id,
                             selected_options=payload.selected_options, quantity=payload.quantity,
                             note=payload.note)
    db.add(item)
    db.commit()
    db.refresh(item)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    return item


@router.patch("/{order_id}/items/{item_id}", response_model=schemas.OrderItemOut)
def update_own_item(order_id: int, item_id: int, payload: schemas.OrderItemCreateIn, bg_tasks: BackgroundTasks,
                     db: Session = Depends(get_db)):
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order and not check_permission(db, payload.user, "訂單", "update", order.initiator):
        raise HTTPException(403, "沒有權限修改品項")
    if order and order.is_locked and not check_permission(db, payload.user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "此訂單已鎖單，無法修改品項")
    if item.user != payload.user:
        raise HTTPException(403, "只能修改自己加入的品項")
    _reject_if_sold_out(db, order_id, item.menu_item_id, payload.selected_options)
    _validate_integer_amount(db, item.menu_item_id, payload.selected_options, payload.quantity)
    item.quantity = payload.quantity
    item.selected_options = payload.selected_options
    item.note = payload.note
    db.commit()
    db.refresh(item)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    return item


@router.delete("/{order_id}/items/{item_id}", status_code=204)
def remove_own_item(order_id: int, item_id: int, user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Hard-remove an item you added yourself (the 'My Order' remove action)."""
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order and not check_permission(db, user, "訂單", "update", order.initiator):
        raise HTTPException(403, "沒有權限移除品項")
    if order and order.is_locked and not check_permission(db, user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "此訂單已鎖單，無法移除品項")
    if item.user != user:
        raise HTTPException(403, "只能移除自己加入的品項")
    db.delete(item)
    db.commit()
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    return None


@router.patch("/{order_id}/items/{item_id}/soft-delete", response_model=schemas.OrderItemOut)
def soft_delete_item(order_id: int, item_id: int, acting_user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Initiator soft-deletes someone else's line (SPEC 4.4 / v0.4)."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有發起者可以刪除其他人的品項")
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id,
                                               models.OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.is_deleted = True
    item.deleted_by = acting_user
    db.commit()
    db.refresh(item)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    return item


@router.get("/{order_id}/sold-out", response_model=list[schemas.SoldOutOut])
def list_sold_out(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order.sold_outs


@router.post("/{order_id}/sold-out", response_model=list[schemas.SoldOutOut])
def toggle_sold_out(order_id: int, payload: schemas.SoldOutToggleIn, acting_user: str,
                     bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """v0.19: 訂單開啟期間把某個品項(或某個客製選項)標記/取消「已售完」。

    權限跟鎖單/結單同一組(訂單建立者 & admin),已結單或已刪除的訂單不能再改。
    回傳這張訂單目前完整的售完清單,前端直接覆蓋不用再多打一次 GET。"""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != "open":
        raise HTTPException(409, "訂單已結束，無法標記售完")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有訂單建立者或管理者可以標記售完")

    mi = db.query(models.MenuItem).filter(models.MenuItem.id == payload.menu_item_id).first()
    if not mi or mi.restaurant_id != order.restaurant_id:
        raise HTTPException(404, "此品項不屬於這張訂單的餐廳")
    group = (payload.option_group or "").strip() or None
    name = (payload.option_name or "").strip() or None
    if bool(group) != bool(name):
        raise HTTPException(400, "選項群組與選項名稱必須一起提供")
    if name and not any(o.option_group == group and o.option_name == name for o in mi.options):
        raise HTTPException(404, "此品項沒有這個客製選項")

    existing = db.query(models.OrderSoldOut).filter(
        models.OrderSoldOut.order_id == order_id,
        models.OrderSoldOut.menu_item_id == payload.menu_item_id,
        models.OrderSoldOut.option_group.is_(None) if group is None else models.OrderSoldOut.option_group == group,
        models.OrderSoldOut.option_name.is_(None) if name is None else models.OrderSoldOut.option_name == name,
    ).first()

    if payload.sold_out and not existing:
        db.add(models.OrderSoldOut(order_id=order_id, menu_item_id=payload.menu_item_id,
                                    option_group=group, option_name=name, created_by=acting_user))
    elif not payload.sold_out and existing:
        db.delete(existing)
    db.commit()
    db.refresh(order)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    return order.sold_outs


@router.patch("/{order_id}/deadline", response_model=schemas.OrderOut)
def update_deadline(order_id: int, payload: schemas.DeadlineIn, acting_user: str, bg_tasks: BackgroundTasks,
                     db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有發起者可以修改截止時間")
    order.deadline_at = payload.deadline_at
    db.commit()
    db.refresh(order)
    
    schedule_order_deadline(order)
    
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    bg_tasks.add_task(manager.broadcast_home_update)
    return order


@router.post("/{order_id}/close", response_model=schemas.HistoryOut)
def close_order(order_id: int, acting_user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
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
                                        user=it.user, quantity=it.quantity, amount=amount, is_paid=False)
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
    
    cancel_order_deadline(order.id)
    
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    bg_tasks.add_task(manager.broadcast_home_update)
    return history


@router.patch("/{order_id}/lock", response_model=schemas.OrderOut)
def lock_order(order_id: int, acting_user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有發起者可以鎖定訂單")
    order.is_locked = True
    db.commit()
    db.refresh(order)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    bg_tasks.add_task(manager.broadcast_home_update)
    return order


@router.patch("/{order_id}/unlock", response_model=schemas.OrderOut)
def unlock_order(order_id: int, acting_user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有發起者可以解除鎖單")
    order.is_locked = False
    db.commit()
    db.refresh(order)
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    bg_tasks.add_task(manager.broadcast_home_update)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, acting_user: str, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not check_permission(db, acting_user, "訂單", "delete", order.initiator):
        raise HTTPException(403, "只有發起者可以刪除訂單")
    order.status = "deleted"
    db.commit()
    
    cancel_order_deadline(order.id)
    
    bg_tasks.add_task(manager.broadcast_order_update, order_id)
    bg_tasks.add_task(manager.broadcast_home_update)
    return None
