from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_me(client_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.client_id == client_id).first()
    if not user:
        # First visit: seed a default name so the frontend always has something to show.
        user = models.User(client_id=client_id, display_name="訪客")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.put("/me", response_model=schemas.UserOut)
def upsert_me(payload: schemas.UserUpsert, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.client_id == payload.client_id).first()
    if not user:
        user = models.User(client_id=payload.client_id, display_name=payload.display_name,
                            teams_name_raw=payload.teams_name_raw)
        db.add(user)
    else:
        user.display_name = payload.display_name
        if payload.teams_name_raw:
            user.teams_name_raw = payload.teams_name_raw
    db.commit()
    db.refresh(user)
    return user
