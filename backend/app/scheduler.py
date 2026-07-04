import datetime as dt
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.orm import joinedload

from app.database import engine, SessionLocal
from app import models
from app.routers.ws import manager


jobstores = {
    'default': SQLAlchemyJobStore(engine=engine)
}
# 前端傳送的是本地時間 (沒有時區)，我們這裡統一使用台北時區來解讀
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=ZoneInfo("Asia/Taipei"))


async def auto_lock_order_job(order_id: int):
    """Fired automatically when an order's deadline is reached."""
    db = SessionLocal()
    try:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if order and order.status == "open" and not order.is_locked:
            order.is_locked = True
            db.commit()
            print(f"[scheduler] Auto-locked order {order_id} (deadline reached)")
            await manager.broadcast_order_update(order_id)
            await manager.broadcast_home_update()
    except Exception as e:
        print(f"[scheduler] Failed to auto-lock order {order_id}: {e}")
    finally:
        db.close()


async def auto_decide_vote_job(batch_id: int):
    """Fired automatically when a vote batch's deadline is reached."""
    db = SessionLocal()
    try:
        batch = db.query(models.VoteBatch).options(
            joinedload(models.VoteBatch.candidates)).filter(models.VoteBatch.id == batch_id).first()
        
        if batch and batch.status == "open":
            counts = []
            for c in batch.candidates:
                count = db.query(models.Vote).filter(
                    models.Vote.vote_batch_id == batch.id,
                    models.Vote.restaurant_id == c.restaurant_id,
                    models.Vote.status == "locked",
                ).count()
                counts.append((count, c.restaurant_id))
            
            if not counts:
                batch.status = "failed"
                db.commit()
                print(f"[scheduler] Auto-decided vote batch {batch_id}: failed (no candidates)")
            else:
                best_count = max([c[0] for c in counts])
                winners = [c[1] for c in counts if c[0] == best_count]
                
                if len(winners) > 1:
                    batch.status = "failed"
                    db.commit()
                    print(f"[scheduler] Auto-decided vote batch {batch_id}: failed (tie, {len(winners)} winners with {best_count} votes)")
                else:
                    winner_id = winners[0]
                    order = models.Order(restaurant_id=winner_id, initiator=batch.initiator,
                                          deadline_at=None, source_vote_batch_id=batch.id)
                    db.add(order)
                    batch.status = "decided"
                    db.commit()
                    db.refresh(order)
                    print(f"[scheduler] Auto-decided vote batch {batch_id}, generated order {order.id} with empty deadline")
            
            await manager.broadcast_vote_update(batch_id)
            await manager.broadcast_home_update()
    except Exception as e:
        print(f"[scheduler] Failed to auto-decide vote batch {batch_id}: {e}")
    finally:
        db.close()


def schedule_order_deadline(order: models.Order):
    """Add or update an APScheduler job for the order deadline."""
    job_id = f"order_{order.id}"
    
    if order.deadline_at is None:
        print(f"[scheduler] Order {order.id} has no deadline_at, skip scheduling")
        cancel_order_deadline(order.id)
        return

    # ensure it runs in Taipei time, models.Order.deadline_at is naive local time
    run_date = order.deadline_at.replace(tzinfo=ZoneInfo("Asia/Taipei"))
    
    # Check if the deadline is in the past
    now_taipei = dt.datetime.now(ZoneInfo("Asia/Taipei")).replace(tzinfo=None)
    if order.deadline_at <= now_taipei:
        print(f"[scheduler] Order {order.id} deadline {order.deadline_at} is in the past, skip scheduling")
        cancel_order_deadline(order.id)
        return
    scheduler.add_job(
        auto_lock_order_job,
        trigger='date',
        run_date=run_date,
        args=[order.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace time in case the server was down
    )
    print(f"[scheduler] Scheduled job {job_id} for {run_date}")


def cancel_order_deadline(order_id: int):
    """Cancel an APScheduler job if the order is closed/deleted early."""
    job_id = f"order_{order_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[scheduler] Removed job {job_id}")


def schedule_vote_deadline(batch: models.VoteBatch):
    """Add or update an APScheduler job for the vote batch deadline."""
    job_id = f"vote_{batch.id}"
    
    run_date = batch.deadline_at.replace(tzinfo=ZoneInfo("Asia/Taipei"))
    scheduler.add_job(
        auto_decide_vote_job,
        trigger='date',
        run_date=run_date,
        args=[batch.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600
    )
    print(f"[scheduler] Scheduled job {job_id} for {run_date}")


def cancel_vote_deadline(batch_id: int):
    """Cancel an APScheduler job if the vote is decided/deleted early."""
    job_id = f"vote_{batch_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[scheduler] Removed job {job_id}")
