from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/parameters", tags=["parameters"])


class RestaurantTypeCreate(BaseModel):
    name: str

class RestaurantTypeOut(BaseModel):
    id: int
    name: str


@router.get("/restaurant-types", response_model=list[RestaurantTypeOut])
def list_restaurant_types(db: Session = Depends(get_db)):
    # Sort by id or name? Sort by id (insertion order)
    return db.query(models.RestaurantType).order_by(models.RestaurantType.id).all()


@router.post("/restaurant-types", response_model=RestaurantTypeOut)
def create_restaurant_type(payload: RestaurantTypeCreate, db: Session = Depends(get_db)):
    if not payload.name or not payload.name.strip():
        raise HTTPException(400, "Name is required")
    name = payload.name.strip()
    
    existing = db.query(models.RestaurantType).filter(models.RestaurantType.name == name).first()
    if existing:
        raise HTTPException(400, "Restaurant type already exists")
        
    t = models.RestaurantType(name=name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/restaurant-types/{type_id}", response_model=RestaurantTypeOut)
def update_restaurant_type(type_id: int, payload: RestaurantTypeCreate, db: Session = Depends(get_db)):
    if not payload.name or not payload.name.strip():
        raise HTTPException(400, "Name is required")
    name = payload.name.strip()
    
    t = db.query(models.RestaurantType).filter(models.RestaurantType.id == type_id).first()
    if not t:
        raise HTTPException(404, "Restaurant type not found")
        
    existing = db.query(models.RestaurantType).filter(models.RestaurantType.name == name, models.RestaurantType.id != type_id).first()
    if existing:
        raise HTTPException(400, "Another restaurant type with this name already exists")
        
    # We should update restaurants that are using this type to keep consistency?
    # No, comma separated strings don't automatically update in SQLAlchemy. We must manually update them.
    # Since this is a bit complex (comma separated values like '便當,飲料'), let's rename the type in all restaurants
    # It requires fetching all restaurants that have the old name, replacing it.
    old_name = t.name
    
    t.name = name
    
    # Update restaurants
    # Search for old_name in type
    # Since it's a comma separated string, we can do this in python to be safe.
    restaurants = db.query(models.Restaurant).all()
    for r in restaurants:
        if r.type:
            parts = [p.strip() for p in r.type.split(",") if p.strip()]
            if old_name in parts:
                parts = [name if p == old_name else p for p in parts]
                # deduplicate
                parts = list(dict.fromkeys(parts))
                r.type = ",".join(parts)
    
    db.commit()
    db.refresh(t)
    return t


@router.delete("/restaurant-types/{type_id}", status_code=204)
def delete_restaurant_type(type_id: int, db: Session = Depends(get_db)):
    t = db.query(models.RestaurantType).filter(models.RestaurantType.id == type_id).first()
    if not t:
        raise HTTPException(404, "Restaurant type not found")
        
    # Check if any restaurant uses it
    name = t.name
    restaurants = db.query(models.Restaurant).all()
    used = False
    for r in restaurants:
        if r.type:
            parts = [p.strip() for p in r.type.split(",") if p.strip()]
            if name in parts:
                used = True
                break
                
    if used:
        raise HTTPException(400, "此類型仍有餐廳使用中，無法刪除")
        
    db.delete(t)
    db.commit()
    return None
