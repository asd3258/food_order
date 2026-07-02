"""Tiny, idempotent one-off fixups for already-deployed databases.

There's no Alembic wired up (see the note in models.py), so schema/data
changes that need to reach an already-running deployment without wiping the
Postgres volume (`docker compose down -v`, which would also erase real
orders/history/roster data) go here instead. Each function must be safe to
run on every startup, forever.
"""
from sqlalchemy import func

from app import models
from app.database import SessionLocal


def _rename_admin_mike_to_mike_admin(db) -> None:
    """v0.8: the admin account was renamed from admin_mike to mike_admin so
    it no longer starts with the newly-reserved "admin" prefix (regular
    users are now blocked from picking admin*/root*/... names on
    create/rename -- the admin account itself shouldn't collide with its
    own rule, or look like a guessable "admin_*" convention)."""
    old = db.query(models.User).filter(func.lower(models.User.name) == "admin_mike").first()
    if not old:
        return
    already_new = db.query(models.User).filter(func.lower(models.User.name) == "mike_admin").first()
    if already_new:
        return
    old.name = "mike_admin"
    old.is_admin = True
    db.commit()
    print("[migrations] renamed admin_mike -> mike_admin")


def run_light_migrations() -> None:
    db = SessionLocal()
    try:
        _rename_admin_mike_to_mike_admin(db)
    finally:
        db.close()
