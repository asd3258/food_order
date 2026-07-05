from typing import Optional
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.permissions import check_permission

from app import models, schemas
from app.database import get_db
from app.ai_menu import parse_menu_photo, classify_menu_categories, MenuParseError
from app.places import fetch_place_info, PlacesError
from app.storage import upload_data_url, delete_object, StorageError
from app.limiter import limiter

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


def _restaurant_query(db: Session):
    return db.query(models.Restaurant).options(
        joinedload(models.Restaurant.photos),
        joinedload(models.Restaurant.menu_items).joinedload(models.MenuItem.options),
        joinedload(models.Restaurant.periods),
    )


@router.get("", response_model=list[schemas.RestaurantSummaryOut])
def list_restaurants(q: Optional[str] = None, type: Optional[str] = None, sort: str = "created_desc",
                      user: Optional[str] = None, days: Optional[str] = None, db: Session = Depends(get_db)):
    """v0.5: `q` matches restaurant name OR any menu item name; `type` filters
    by restaurant type. Both combine with AND, matching SPEC.md section 3.
    v0.11: `sort` replaces the old manual drag-to-reorder feature with fixed
    presets -- "created_desc" (預設,建立時間新到舊), "name" (名稱排序), or
    (v0.12) "star" (★常用優先,再依名稱).
    v0.12: `user` -- 用來算每筆餐廳目前是否已被這個使用者加入★常用
    (is_favorite),也是 sort="star" 時用來排序的依據。沒帶 user 的話
    is_favorite 全部是 False,star 排序就退化成純名稱排序。
    v0.17: `days` -- 逗號分隔的整數(0=週日, 1=週一...), 篩選這些天數有營業的餐廳 (OR 邏輯)。"""
    query = db.query(models.Restaurant)
    if type:
        query = query.filter(
            (models.Restaurant.type == type) |
            models.Restaurant.type.like(f"{type},%") |
            models.Restaurant.type.like(f"%,{type}") |
            models.Restaurant.type.like(f"%,{type},%")
        )
    
    if days:
        day_list = [int(d) for d in days.split(",") if d.strip().isdigit()]
        if day_list:
            query = query.filter(models.Restaurant.periods.any(models.RestaurantPeriod.day.in_(day_list)))

    restaurants = query.all()

    fav_ids: set[int] = set()
    if user:
        fav_ids = {row[0] for row in db.query(models.RestaurantFavorite.restaurant_id).filter(
            models.RestaurantFavorite.user == user).all()}

    if sort == "name":
        restaurants.sort(key=lambda r: r.name)
    elif sort == "star":
        restaurants.sort(key=lambda r: (r.id not in fav_ids, r.name))
    else:
        restaurants.sort(key=lambda r: (r.created_at, r.id), reverse=True)

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

    for r in restaurants:
        r.is_favorite = r.id in fav_ids
    return restaurants


@router.post("/{restaurant_id}/favorite", response_model=schemas.FavoriteOut)
def add_favorite(restaurant_id: int, user: str, db: Session = Depends(get_db)):
    """v0.12: 餐廳清單的★常用 -- by user 記錄,不是全域的。重複呼叫是安全的
    (已經加過就不會重複新增)。"""
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    name = (user or "").strip()
    if not name:
        raise HTTPException(400, "請先登入")
    existing = db.query(models.RestaurantFavorite).filter(
        models.RestaurantFavorite.user == name,
        models.RestaurantFavorite.restaurant_id == restaurant_id).first()
    if not existing:
        db.add(models.RestaurantFavorite(user=name, restaurant_id=restaurant_id))
        db.commit()
    return schemas.FavoriteOut(is_favorite=True)


@router.delete("/{restaurant_id}/favorite", response_model=schemas.FavoriteOut)
def remove_favorite(restaurant_id: int, user: str, db: Session = Depends(get_db)):
    name = (user or "").strip()
    fav = db.query(models.RestaurantFavorite).filter(
        models.RestaurantFavorite.user == name,
        models.RestaurantFavorite.restaurant_id == restaurant_id).first()
    if fav:
        db.delete(fav)
        db.commit()
    return schemas.FavoriteOut(is_favorite=False)



@router.get("/{restaurant_id}/menu", response_model=schemas.RestaurantDetailOut)
def get_restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    r = _restaurant_query(db).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return r


@router.post("", response_model=schemas.RestaurantDetailOut)
def create_restaurant(payload: schemas.RestaurantIn, db: Session = Depends(get_db)):
    if not check_permission(db, payload.created_by, "建立餐廳", "create"):
        raise HTTPException(403, "沒有權限建立餐廳")
    if not payload.type or not payload.type.strip():
        raise HTTPException(400, "請輸入餐廳類型")
    r = models.Restaurant(name=payload.name, phone=payload.phone, address=payload.address,
                           map_url=payload.map_url, hours=payload.hours, type=payload.type.strip(),
                           created_by=payload.created_by)
    db.add(r)
    db.flush()
    for p in payload.periods:
        db.add(models.RestaurantPeriod(restaurant_id=r.id, day=p.day, open_time=p.open_time, close_time=p.close_time))
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
                       acting_user: str, db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    if not check_permission(db, acting_user, "編輯餐廳資料", "update", r.created_by):
        raise HTTPException(403, "沒有權限編輯此餐廳")
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
        
    if payload.periods is not None:
        db.query(models.RestaurantPeriod).filter(models.RestaurantPeriod.restaurant_id == r.id).delete(synchronize_session=False)
        db.flush()
        for p in payload.periods:
            db.add(models.RestaurantPeriod(restaurant_id=r.id, day=p.day, open_time=p.open_time, close_time=p.close_time))

    if payload.menu_items is not None:
        # Query.delete() is a *bulk* DELETE -- it bypasses SQLAlchemy's ORM
        # cascade rules entirely (those only fire on session.delete()/unit-
        # of-work operations), so deleting MenuItem rows this way leaves
        # their MenuItemOption children behind and the DB rejects it with a
        # foreign key violation. Delete the options first, explicitly.
        old_item_ids = [row[0] for row in db.query(models.MenuItem.id).filter(
            models.MenuItem.restaurant_id == r.id).all()]
        if old_item_ids:
            db.query(models.MenuItemOption).filter(
                models.MenuItemOption.menu_item_id.in_(old_item_ids)).delete(synchronize_session=False)
        db.query(models.MenuItem).filter(models.MenuItem.restaurant_id == r.id).delete(synchronize_session=False)
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
def delete_restaurant(restaurant_id: int, acting_user: str, db: Session = Depends(get_db)):
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
    if not check_permission(db, acting_user, "編輯餐廳資料", "delete", r.created_by):
        raise HTTPException(403, "沒有權限刪除此餐廳")

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
    db.query(models.Vote).filter(
        models.Vote.restaurant_id == restaurant_id).delete()

    db.delete(r)  # cascades to RestaurantPhoto + MenuItem (+ MenuItemOption) + RestaurantPeriod
    db.commit()
    return None


@router.post("/parse-menu", response_model=list[schemas.MenuItemIn])
@limiter.limit("2/minute")
def parse_menu(payload: schemas.MenuParseIn, request: Request, db: Session = Depends(get_db)):
    """v0.9: AI-assisted 品項 extraction from a photo of a menu -- see
    app/ai_menu.py for the Gemini-first/OpenAI-fallback logic. Returns
    unsaved draft items (no restaurant_id involved yet) for the frontend to
    drop into the editable 品項清單 for a human to review/fix before the
    restaurant is actually created or saved.

    v0.11: also asks for a 分類 suggestion per item in this SAME AI call
    (using every other already-categorized (name, category) pair in the DB
    as reference, same idea as /classify-categories) instead of a separate
    round trip right after uploading -- one AI call instead of two every
    time someone uploads a menu photo."""
    reference = db.query(models.MenuItem.name, models.MenuItem.category).filter(
        models.MenuItem.category.isnot(None), models.MenuItem.category != "").distinct().limit(500).all()
    try:
        return parse_menu_photo(payload.image_url, [(n, c) for n, c in reference])
    except MenuParseError as exc:
        raise HTTPException(400, str(exc))


@router.post("/fetch-place-info", response_model=schemas.PlaceInfoOut)
@limiter.limit("2/minute")
def fetch_place_info_endpoint(payload: schemas.PlaceInfoIn, request: Request, db: Session = Depends(get_db)):
    """v0.10: reads phone/address/營業時間 off a Google Maps listing via the
    Places API (New) -- see app/places.py. Does NOT touch menu photos (see
    that module's docstring for why).
    v0.13: Added caching and rate limiting."""
    today = dt.date.today().isoformat()
    map_url = (payload.map_url or "").strip()
    
    if map_url:
        cached = db.query(models.PlaceCache).filter(models.PlaceCache.map_url == map_url).first()
        if cached and cached.updated_date == today:
            return schemas.PlaceInfoOut(
                name=cached.name,
                phone=cached.phone,
                address=cached.address,
                hours=cached.hours,
                periods=cached.periods,
                is_cached=True
            )

    try:
        data = fetch_place_info(map_url)
        
        if map_url:
            cached = db.query(models.PlaceCache).filter(models.PlaceCache.map_url == map_url).first()
            if not cached:
                cached = models.PlaceCache(map_url=map_url)
                db.add(cached)
            cached.name = data.get("name", "")
            cached.phone = data.get("phone", "")
            cached.address = data.get("address", "")
            cached.hours = data.get("hours", "")
            cached.periods = data.get("periods", [])
            cached.updated_date = today
            db.commit()
            
        data["is_cached"] = False
        return data
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


@router.post("/{restaurant_id}/photos", response_model=schemas.PhotoOut)
def upload_photo(restaurant_id: int, payload: schemas.PhotoUploadIn, db: Session = Depends(get_db)):
    """v0.11: the uploaded `data:` base64 photo is decoded and pushed to
    MinIO here (see app/storage.py) -- only the resulting short /media/...
    path gets stored in the DB, not the whole image."""
    r = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    max_order = db.query(models.RestaurantPhoto).filter(
        models.RestaurantPhoto.restaurant_id == restaurant_id).count()
    try:
        stored_url = upload_data_url(payload.image_url, restaurant_id)
    except StorageError as exc:
        raise HTTPException(400, str(exc))
    photo = models.RestaurantPhoto(restaurant_id=restaurant_id, image_url=stored_url,
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
    delete_object(photo.image_url)  # no-op for placeholder:/legacy data: rows -- see storage.py
    db.delete(photo)
    db.commit()
    return None
