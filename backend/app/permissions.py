"""Shared admin-check helper (v0.7).

Identity is still just a display-name string passed by the frontend as
`acting_user` (see the note in models.py/api.ts) -- this checks whether that
name currently belongs to a roster entry with is_admin=True. It's re-checked
server-side on every admin-gated endpoint, but there's no password behind
it: whoever is logged in as "admin_mike" (or any other roster entry someone
later flags as admin directly in the DB) passes this check.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def require_admin(db: Session, acting_user: str) -> models.User:
    name = (acting_user or "").strip()
    u = db.query(models.User).filter(models.User.name == name).first() if name else None
    if not u or not u.is_admin:
        raise HTTPException(403, "只有管理者帳號可以執行此操作")
    return u
