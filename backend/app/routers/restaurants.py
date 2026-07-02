from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
<<<<<<< Updated upstream
=======
from app.ai_menu import parse_menu_photo, classify_menu_categories, MenuParseError
from app.places import fetch_place_info, PlacesError
>>>>>>> Stashed changes

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


@router.get("/types", response_model=list[str])
def list_restaurant_types(db: Session = Depends(get_db)):
    """v0.7: 餐廳類型 is no longer a fixed whitelist -- this returns the 4
    baseline types plus any custom type someone has typed in on a restaurant,
    so the filter chips on 餐廳清單/開單與投票 stay in sync automatically."""
    used = {row[0] for row in db.query(models.Restaurant.type).distinct().all() if row[0]}
    extra = sorted(t for t in used if t not in schemas.RESTAURANT_TYPES)
    return list(schemas.RESTAURANT_TYPES) + extra


@router.get("/{restaurant_id}/menu", response_model=schemas.RestaurantDetailOut)
def get_restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    r = _restaurant_query(db).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return r


@router.post("", response_model=schemas.RestaurantDetailOut)
def create_restaurant(payload: schemas.RestaurantIn, db: Session = Depends(get_db)):
    if not payload.type or not payload.type.strip():
        raise HTTPException(400, "請輸入餐廳類型")
    r = models.Restaurant(name=payload.name, phone=payload.phone, address=payload.address,
                           map_url=payload.map_url, hours=payload.hours, type=payload.type.strip(),
                           created_by=payload.created_by)
    db.add(r)
    db.flush()
    for item in payload.menu_items:
        mi = models.MenuItem(restaurant_id=r.id, name=item.name, price=item.price, category=item.category)
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
    if payload.map_url is not None:
        r.map_url = payload.map_url
    if payload.hours is not None:
        r.hours = payload.hours
    if payload.type is not None:
        if not payload.type.strip():
            raise HTTPException(400, "請輸入餐廳類型")
        r.type = payload.type.strip()
    if payload.menu_items is not None:
        db.query(models.MenuItem).filter(models.MenuItem.restaurant_id == r.id).delete()
        db.flush()
        for item in payload.menu_items:
            mi = models.MenuItem(restaurant_id=r.id, name=item.name, price=item.price, category=item.category)
            db.add(mi)
            db.flush()
            for opt in item.options:
                db.add(models.MenuItemOption(menu_item_id=mi.id, option_group=opt.option_group,
                                              option_type=opt.option_type,
                                              option_name=opt.option_name,
                                              extra_price=opt.extra_price))
    db.commit()
    return _restaurant_query(db).filter(models.Restaurant.id == r.id).first()


@router.delete("/{restaurant_id}", status_code=204)
def delete_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """v0.7: 編輯餐廳資料 gets a delete button. Open to any logged-in user
    (same as editing a restaurant), not admin-gated.

    Blocked while there's a currently-open order or vote pointing at this
    restaurant (ask the user to close/delete those first). Any leftover
    closed/deleted Order rows referencing it are cleaned up here too --
    their data already lives in OrderHistory as a plain-text snapshot, so
    the Order row itself is disposable once the restaurant is gone."""
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")

    open_order = db.query(models.Order).filter(
        models.Order.restaurant_id == restaurant_id, models.Order.status == "open").first()
    if open_order:
        raise HTTPException(400, "此餐廳目前有進行中的訂單,請先結單或刪除該訂單才能刪除餐廳")

    open_vote = db.query(models.VoteBatchCandidate).join(
        models.VoteBatch, models.VoteBatchCandidate.vote_batch_id == models.VoteBatch.id
    ).filter(models.VoteBatchCandidate.restaurant_id == restaurant_id,
             models.VoteBatch.status == "open").first()
    if open_vote:
        raise HTTPException(400, "此餐廳目前在進行中的投票裡,請先完成或刪除該投票才能刪除餐廳")

    for stale_order in db.query(models.Order).filter(models.Order.restaurant_id == restaurant_id).all():
        db.delete(stale_order)
    db.query(models.VoteBatchCandidate).filter(
        models.VoteBatchCandidate.restaurant_id == restaurant_id).delete()

    db.delete(r)  # cascades to RestaurantPhoto + MenuItem (+ MenuItemOption)
    db.commit()
    return None


<<<<<<< Updated upstream
=======
@router.post("/parse-menu", response_model=list[schemas.MenuItemIn])
def parse_menu(payload: schemas.MenuParseIn):
    """v0.9: AI-assisted 品項 extraction from a photo of a menu -- see
    app/ai_menu.py for the Gemini-first/OpenAI-fallback logic. Returns
    unsaved draft items (no restaurant_id involved yet) for the frontend to
    drop into the editable 品項清單 for a human to review/fix before the
    restaurant is actually created or saved."""
    try:
        return parse_menu_photo(payload.image_url)
    except MenuParseError as exc:
        raise HTTPException(400, str(exc))


@router.post("/fetch-place-info", response_model=schemas.PlaceInfoOut)
def fetch_place_info_endpoint(payload: schemas.PlaceInfoIn):
    """v0.10: reads phone/address/營業時間 off a Google Maps listing via the
    Places API (New) -- see app/places.py. Does NOT touch menu photos (see
    that module's docstring for why)."""
    try:
        return fetch_place_info(payload.map_url)
    except PlacesError as exc:
        raise HTTPException(400, str(exc))


@router.post("/classify-categories", response_model=list[schemas.CategorySuggestionOut])
def classify_categories(payload: schemas.ClassifyCategoriesIn, db: Session = Depends(get_db)):
    """v0.10: "AI自動分類品項類型" on EditRestaurantView -- suggests a 分類 for
    each of the currently-edited item names, using every other
    already-categorized (name, category) pair in the DB as reference so
    category naming stays consistent across restaurants. Returns
    suggestions only; nothing is written here -- the frontend applies them
    to its in-memory draft, and the real write happens on the existing
    儲存變更 save."""
    reference = db.query(models.MenuItem.name, models.MenuItem.category).filter(
        models.MenuItem.category.isnot(None), models.MenuItem.category != "").distinct().limit(500).all()
    try:
        return classify_menu_categories(payload.item_names, [(n, c) for n, c in reference])
    except MenuParseError as exc:
        raise HTTPException(400, str(exc))


>>>>>>> Stashed changes
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
