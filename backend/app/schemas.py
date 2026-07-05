import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

RESTAURANT_TYPES = ["便當", "飲料", "牛排", "義大利麵"]


# ---------- User (v0.6: shared roster / "login as" picker) ----------
class UserCreateIn(BaseModel):
    name: str


class UserRenameIn(BaseModel):
    name: str


class UserOut(BaseModel):
    id: int
    name: str
    order_count: int = 0  # how many OrderHistoryLine rows mention this name -- powers 快速登入 ordering
    is_admin: bool = False
    ui_mode: str = "normal"  # v0.11: "normal" | "large" -- 大字模式偏好

# ---------- Auth / Account Management ----------
class LoginIn(BaseModel):
    name: str
    password: Optional[str] = None

class ForgotPasswordIn(BaseModel):
    name: str
    email: str

class UpdateEmailIn(BaseModel):
    name: str
    email: str

class UpdatePasswordIn(BaseModel):
    name: str
    current_password: str
    new_password: str


class UiModeIn(BaseModel):
    ui_mode: str  # "normal" | "large"


# ---------- Menu item options ----------
class OptionChoiceIn(BaseModel):
    option_group: str
    option_type: str  # radio | checkbox
    option_name: str
    extra_price: float = 0.0


class OptionChoiceOut(OptionChoiceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Menu items ----------
class MenuItemIn(BaseModel):
    name: str
    price: int
    category: str = ""  # v0.10: brought back -- see 分類 grouping on the menu view
    options: List[OptionChoiceIn] = []


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: int
    category: str = ""
    options: List[OptionChoiceOut] = []


# ---------- Photos ----------
class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_url: str
    caption: str
    sort_order: int


# ---------- Restaurant Periods ----------
class RestaurantPeriodIn(BaseModel):
    day: int
    open_time: str = "0000"
    close_time: str = "2359"


class RestaurantPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day: int
    open_time: str
    close_time: str


# ---------- Restaurant ----------
class RestaurantIn(BaseModel):
    name: str
    phone: str = ""
    address: str = ""
    map_url: str = ""
    hours: str = ""  # v0.10: 營業時間 (textarea, free text)
    type: str
    created_by: str = ""
    menu_items: List[MenuItemIn] = []
    periods: List[RestaurantPeriodIn] = []


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    map_url: Optional[str] = None
    hours: Optional[str] = None
    type: Optional[str] = None
    menu_items: Optional[List[MenuItemIn]] = None
    periods: Optional[List[RestaurantPeriodIn]] = None


class RestaurantSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: str
    phone: str
    address: str
    created_at: dt.datetime
    created_by: str = ""
    is_favorite: bool = False  # v0.12: 這個 user 是否已把這間餐廳加入★常用


class FavoriteOut(BaseModel):
    is_favorite: bool


class RestaurantDetailOut(RestaurantSummaryOut):
    map_url: str
    hours: str = ""
    menu_items: List[MenuItemOut] = []
    photos: List[PhotoOut] = []
    periods: List[RestaurantPeriodOut] = []


class PhotoUploadIn(BaseModel):
    image_url: str  # data URL from the client (FileReader)
    caption: str = ""


class MenuParseIn(BaseModel):
    image_url: str  # data URL of a menu photo, same shape as PhotoUploadIn


# ---------- v0.10: Google Places lookup ----------
class PlaceInfoIn(BaseModel):
    map_url: str


class PlaceInfoOut(BaseModel):
    name: str = ""
    phone: str = ""
    address: str = ""
    hours: str = ""
    periods: List[RestaurantPeriodIn] = []
    is_cached: bool = False


# ---------- v0.10: AI 品項分類 ----------
class ClassifyCategoriesIn(BaseModel):
    item_names: List[str]


class CategorySuggestionOut(BaseModel):
    name: str
    category: str


# ---------- Deadline helper ----------
class DeadlineIn(BaseModel):
    deadline_at: Optional[dt.datetime] = None


# ---------- Orders ----------
class OrderCreateIn(BaseModel):
    restaurant_id: int
    initiator: str
    deadline_at: Optional[dt.datetime] = None
    source_vote_batch_id: Optional[int] = None


class OrderItemCreateIn(BaseModel):
    user: str
    menu_item_id: int
    selected_options: List[str] = []
    quantity: int = 1
    note: str = ""


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user: str
    # v0.12: nullable now -- see models.py OrderItem.menu_item_id (ON DELETE
    # SET NULL when the referenced menu item is deleted by an Edit
    # Restaurant save).
    menu_item_id: Optional[int] = None
    selected_options: List[str] = []
    quantity: int
    note: str
    is_deleted: bool


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    restaurant_id: int
    initiator: str
    deadline_at: Optional[dt.datetime] = None
    status: str
    is_locked: bool = False
    items: List[OrderItemOut] = []


class StatRow(BaseModel):
    label: str
    user: str
    quantity: int
    amount: int
    item_id: int
    is_deleted: bool = False


# ---------- Votes ----------
class VoteBatchCreateIn(BaseModel):
    restaurant_ids: List[int]
    initiator: str
    deadline_at: dt.datetime


class VoteChoiceIn(BaseModel):
    user: str
    restaurant_id: int


class VoteCandidateOut(BaseModel):
    restaurant_id: int
    restaurant_name: str
    count: int


class VoteBatchOut(BaseModel):
    id: int
    initiator: str
    deadline_at: dt.datetime
    status: str
    candidates: List[VoteCandidateOut]
    my_selection: Optional[int] = None
    my_locked: bool = False


# ---------- History / Payments ----------
class HistoryLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_label: str
    user: str
    quantity: int
    amount: int


class HistoryPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: str
    total_amount: int
    is_paid: bool


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    restaurant_name: str
    initiator: str
    closed_date: str
    people_count: int
    total_amount: int
    lines: List[HistoryLineOut] = []
    payments: List[HistoryPaymentOut] = []


# ---------- Permissions ----------
class PermissionRuleUpdateIn(BaseModel):
    can_create: str
    can_read: str
    can_update: str
    can_delete: str


class PermissionRuleCreateIn(BaseModel):
    module: str
    role: str
    can_create: str = "-"
    can_read: str = "-"
    can_update: str = "-"
    can_delete: str = "-"


class PermissionRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module: str
    role: str
    can_create: str
    can_read: str
    can_update: str
    can_delete: str
