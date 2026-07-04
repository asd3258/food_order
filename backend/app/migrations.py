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
from app.storage import MINIO_ACCESS_KEY, StorageError, upload_data_url, wait_for_minio


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


def _drop_column_if_exists(table: str, column: str) -> None:
    """Inverse of _add_column_if_missing -- also safe to call every startup;
    Postgres raises UndefinedColumn if it's already gone and this just
    swallows it."""
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
        print(f"[migrations] dropped {table}.{column}")
    except Exception:
        pass  # already gone


def _alter_column_type(table: str, column: str, coltype: str) -> None:
    """Alters a column's type. Safe to call if already altered."""
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {coltype}"))
    except Exception:
        pass


def _migrate_extra_price_to_float() -> None:
    _alter_column_type("menu_item_options", "extra_price", "FLOAT")
    print("[migrations] altered menu_item_options.extra_price to FLOAT")
def _migrate_photos_to_object_storage(db) -> None:
    """v0.11: move any already-stored `data:` base64 photos into MinIO,
    replacing the row's image_url with the new /media/... path -- see
    app/storage.py. Only touches rows that still start with "data:"; once
    migrated they no longer match, so re-running this on every startup is
    naturally idempotent and just a cheap no-op query once everything's
    already moved."""
    if not MINIO_ACCESS_KEY:
        return  # wait_for_minio() already printed why -- don't also spam per-photo errors below
    photos = db.query(models.RestaurantPhoto).filter(
        models.RestaurantPhoto.image_url.like("data:%")).all()
    if not photos:
        return
    migrated = 0
    for p in photos:
        try:
            p.image_url = upload_data_url(p.image_url, p.restaurant_id)
            migrated += 1
        except StorageError as exc:
            print(f"[migrations] skipped photo id={p.id}: {exc}")
    db.commit()
    if migrated:
        print(f"[migrations] moved {migrated} photo(s) from base64 to object storage")


def _fix_order_item_menu_fk() -> None:
    """v0.12: order_items.menu_item_id 原本是 NOT NULL,外鍵也沒設 ON DELETE 規則
    (預設 RESTRICT)。編輯餐廳存檔時,後端是整批刪除舊 MenuItem 再重建(見
    routers/restaurants.py update_restaurant)——只要這間餐廳曾經被下過訂單
    (不管訂單還開著還是已結單),這個外鍵就會擋住刪除,存檔時噴 500
    (ForeignKeyViolation)。改成 nullable + ON DELETE SET NULL:品項被刪除後,
    舊訂單品項的 menu_item_id 自動變成 NULL——顯示邏輯本來就有處理「找不到
    品項」的情況(_line_label/_item_amount 顯示「(已刪除品項)」、金額算 0),
    只是外鍵一直沒配合這個設計。歷史訂單(OrderHistory/OrderHistoryLine)是
    獨立的文字快照,不受影響。"""
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE order_items ALTER COLUMN menu_item_id DROP NOT NULL"))
            conn.execute(text("ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_menu_item_id_fkey"))
            conn.execute(text(
                "ALTER TABLE order_items ADD CONSTRAINT order_items_menu_item_id_fkey "
                "FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE SET NULL"
            ))
        print("[migrations] order_items.menu_item_id is now nullable, FK is ON DELETE SET NULL")
    except Exception as exc:
        print(f"[migrations] order_items FK migration skipped: {exc}")


def _seed_default_permissions(db) -> None:
    if db.query(models.PermissionRule).first():
        return
        
    rules = [
        # 歷史訂單
        ("歷史訂單", "admin", "-", "V", "V", "V"),
        ("歷史訂單", "owner", "-", "V", "V", "X"),
        ("歷史訂單", "other", "-", "V", "X", "X"),
        # 建立餐廳
        ("建立餐廳", "admin", "V", "V", "-", "-"),
        ("建立餐廳", "MikeZY Zhang", "V", "V", "-", "-"),
        ("建立餐廳", "other", "X", "V", "-", "-"),
        # 權限維護
        ("權限維護", "admin", "V", "V", "V", "V"),
        ("權限維護", "MikeZY Zhang", "V", "V", "V", "V"),
        ("權限維護", "other", "X", "V", "X", "X"),
        # 編輯餐廳資料
        ("編輯餐廳資料", "admin", "-", "V", "V", "V"),
        ("編輯餐廳資料", "owner", "-", "V", "V", "V"),
        ("編輯餐廳資料", "other", "-", "V", "X", "X"),
        # 開單與投票
        ("開單與投票", "admin", "V", "V", "-", "-"),
        ("開單與投票", "owner", "V", "V", "-", "-"),
        ("開單與投票", "other", "V", "V", "-", "-"),
        # 訂單
        ("訂單", "admin", "-", "V", "V", "V"),
        ("訂單", "owner", "-", "V", "V", "V"),
        ("訂單", "other", "-", "V", "V", "X"),
        # 投票
        ("投票", "admin", "-", "V", "V", "V"),
        ("投票", "owner", "-", "V", "V", "V"),
        ("投票", "other", "-", "V", "V", "X"),
    ]
    for r in rules:
        db.add(models.PermissionRule(
            module=r[0], role=r[1], can_create=r[2],
            can_read=r[3], can_update=r[4], can_delete=r[5]
        ))
    db.commit()
    print("[migrations] seeded default permission rules")


def _seed_restaurant_types(db) -> None:
    """v0.15: Migrate distinct restaurant types to RestaurantType table."""
    # First get existing predefined from schemas
    from app.schemas import RESTAURANT_TYPES
    all_types = set(RESTAURANT_TYPES)
    
    # Also get all existing distinct types that might have been typed in manually, separated by comma or not
    existing_types = db.query(models.Restaurant.type).distinct().all()
    for row in existing_types:
        if row[0]:
            parts = [p.strip() for p in row[0].split(",") if p.strip()]
            for p in parts:
                all_types.add(p)
    
    # Now insert missing ones
    for t in all_types:
        exists = db.query(models.RestaurantType).filter(models.RestaurantType.name == t).first()
        if not exists:
            db.add(models.RestaurantType(name=t))
    db.commit()
    print("[migrations] seeded restaurant types")


def run_light_migrations() -> None:
    # v0.10: 營業時間 on restaurants, 分類 on menu_items.
    _add_column_if_missing("restaurants", "hours", "TEXT")
    _add_column_if_missing("menu_items", "category", "VARCHAR")
    # v0.11: 餐廳清單改成固定排序按鈕(建立時間/名稱),手動排序欄位移除。
    _drop_column_if_exists("restaurants", "sort_order")
    # v0.11: 大字模式偏好跟著使用者帳號走。
    _add_column_if_missing("users", "ui_mode", "VARCHAR", default_sql="'normal'")
    # v0.12: 修正編輯餐廳存檔時,曾下過訂單的餐廳會被 order_items 外鍵擋住刪除的問題。
    _fix_order_item_menu_fk()
    # v0.13: 新增訂單鎖定功能。
    _add_column_if_missing("orders", "is_locked", "BOOLEAN", default_sql="FALSE")

    # v0.14: 訂單 deadline_at 允許為空
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE orders ALTER COLUMN deadline_at DROP NOT NULL"))
        print("[migrations] orders.deadline_at is now nullable")
    except Exception as e:
        print(f"[migrations] failed to make orders.deadline_at nullable: {e}")

    _migrate_extra_price_to_float()

    # v0.11: make sure the MinIO bucket exists/is public-read before the
    # photo backfill below tries to use it.
    wait_for_minio()
    with SessionLocal() as db:
        try:
            _rename_admin_mike_to_mike_admin(db)
            _fix_null_prices(db)
            _seed_permission_rules(db)
            _seed_restaurant_types(db)
            _migrate_photos_to_object_storage(db)
        finally:
            db.close()
