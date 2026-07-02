from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


def _restaurant_query(db: Session):
    return db.query(models.Restaurant).options(
        joinedload(models.Restaurant.photos),
        joinedload(models.Restaurant.menu_items).joinedload(models.MenuItem.options),
    )


@router.get("", response_model=list[schemas.RestaurantSummaryOut])
def list_restaurants(q: Optional[str] = None, type: Optional[str] = None,
                      db: Session = Depends(get_db)):
    """v0.5: `q` matches restaurant name OR any menu item name; `type` filters
    by restaurant type. Both combine with AND, matching SPEC.md section 3."""
    query = db.query(models.Restaurant)
    if type:
        query = query.filter(models.Restaurant.type == type)
    restaurants = query.all()
    if q:
        needle = q.strip().lower()
        if needle:
            filtered = []
            for r in restaurants:
                if needle in r.name.lower():
                    filtered.append(r)
                    continue
                item_names = db.query(models.MenuItem.name).filter(
                    models.MenuItem.restaurant_id == r.id).all()
                if any(needle in (n[0] or "").lower() for n in item_names):
                    filtered.append(r)
            restaurants = filtered
    return restaurants


@router.get("/{restaurant_id}/menu", response_model=schemas.RestaurantDetailOut)
def get_restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    r = _restaurant_query(db).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return r


@router.post("", response_model=schemas.RestaurantDetailOut)
def create_restaurant(payload: schemas.RestaurantIn, db: Session = Depends(get_db)):
    if payload.type not in schemas.RESTAURANT_TYPES:
        raise HTTPException(400, f"type must be one of {schemas.RESTAURANT_TYPES}")
    r = models.Restaurant(name=payload.name, phone=payload.phone, address=payload.address,
                           type=payload.type, created_by=payload.created_by)
    db.add(r)
    db.flush()
    for item in payload.menu_items:
        mi = models.MenuItem(restaurant_id=r.id, name=item.name, price=item.price)
        db.add(mi)
        db.flush()
        for opt in item.options:
            db.add(models.MenuItemOption(menu_item_id=mi.id, option_group=opt.option_group,
                                          option_type=opt.option_type, option_name=opt.option_name,
                                          extra_price=opt.extra_price))
    db.commit()
    return _restaurant_query(db).filter(models.Restaurant.id == r.id).first()


@router.put("/{restaurant_id}", response_model=schemas.RestaurantDetailOut)
def update_restaurant(restaurant_id: int, payload: schemas.RestaurantUpdate,
                       db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    if payload.name is not None:
        r.name = payload.name
    if payload.phone is not None:
        r.phone = payload.phone
    if payload.address is not None:
        r.address = payload.address
    if payload.type is not None:
        if payload.type not in schemas.RESTAURANT_TYPES:
            raise HTTPException(400, f"type must be one of {schemas.RESTAURANT_TYPES}")
        r.type = payload.type
    if payload.menu_items is not None:
        db.query(models.MenuItem).filter(models.MenuItem.restaurant_id == r.id).delete()
        db.flush()
        for item in payload.menu_items:
            mi = models.MenuItem(restaurant_id=r.id, name=item.name, price=item.price)
            db.add(mi)
            db.flush()
            for opt in item.options:
                db.add(models.MenuItemOption(menu_item_id=mi.id, option_group=opt.option_group,
                                              option_type=opt.option_type,
                                              option_name=opt.option_name,
                                              extra_price=opt.extra_price))
    db.commit()
    return _restaurant_query(db).filter(models.Restaurant.id == r.id).first()


@router.post("/{restaurant_id}/photos", response_model=schemas.PhotoOut)
def upload_photo(restaurant_id: int, payload: schemas.PhotoUploadIn, db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    max_order = db.query(models.RestaurantPhoto).filter(
        models.RestaurantPhoto.restaurant_id == restaurant_id).count()
    photo = models.RestaurantPhoto(restaurant_id=restaurant_id, image_url=payload.image_url,
                                    caption=payload.caption, sort_order=max_order)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/{restaurant_id}/photos/{photo_id}", status_code=204)
def delete_photo(restaurant_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(models.RestaurantPhoto).filter(
        models.RestaurantPhoto.id == photo_id,
        models.RestaurantPhoto.restaurant_id == restaurant_id).first()
    if not photo:
        raise HTTPException(404, "Photo not found")
    db.delete(photo)
    db.commit()
    return None
