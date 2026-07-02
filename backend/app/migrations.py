"""Tiny, idempotent one-off fixups for already-deployed databases.

There's no Alembic wired up (see the note in models.py), so schema/data
changes that need to reach an already-running deployment without wiping the
Postgres volume (`docker compose down -v`, which would also erase real
orders/history/roster data) go here instead. Each function must be safe to
run on every startup, forever.
"""
from sqlalchemy import func, text

from app import models
from app.database import SessionLocal, engine


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


def _add_column_if_missing(table: str, column: str, coltype: str, default_sql: str = "''") -> None:
    """`Base.metadata.create_all()` only creates missing *tables*, never adds
    missing *columns* to a table that already exists -- so a brand-new
    column on an existing model (like the two below) needs an explicit
    ALTER TABLE here. Safe to call every startup: if the column is already
    there (fresh install, or already migrated), Postgres raises
    DuplicateColumn and this just swallows it and moves on."""
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype} DEFAULT {default_sql}"))
        print(f"[migrations] added {table}.{column}")
    except Exception:
        pass  # already exists


def run_light_migrations() -> None:
    # v0.10: 營業時間 on restaurants, 分類 on menu_items.
    _add_column_if_missing("restaurants", "hours", "TEXT")
    _add_column_if_missing("menu_items", "category", "VARCHAR")

    db = SessionLocal()
    try:
        _rename_admin_mike_to_mike_admin(db)
    finally:
        db.close()
