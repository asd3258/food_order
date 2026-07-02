"""
SQLAlchemy models mirroring SPEC.md v0.5 section 3 (Data Model).

v0.6 change: `User` is now a shared roster of known people (a "login as"
picker), not a per-browser profile keyed by a client_id. Anyone can pick any
name from the roster or type a new one -- there's still no password/real
auth, this is a lightweight identity switcher matching the informal, shared
nature of the tool (see SPEC.md section 8 risk notes on identity).

Every "who did this" field elsewhere (initiator / user / created_by) is still
stored as a plain display-name *string*, not a foreign key to User.id. This
means renaming or deleting a roster entry does not retroactively change past
orders/votes/history -- those keep whatever name was current when the action
happened. This is a known limitation: if someone is renamed, actions on
records created under their old name (e.g. "only the initiator can delete
this order") will stop matching until the name is changed back. Acceptable
tradeoff for a small team; would need a real foreign-key identity model to
fix properly.

v0.7: added `User.is_admin`. There is still no password -- whoever logs in
as the roster entry named "admin_mike" (seeded with is_admin=True) gets
admin rights (delete history entries, access 管理使用者). This matches the
project's existing no-real-auth posture, but is worth flagging explicitly:
anyone who knows/guesses that name can become admin. Ask if you want a PIN
added to admin accounts.
"""
import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)  # v0.7: gates 管理使用者 + 刪除歷史訂單
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    address = Column(String, default="")
    map_url = Column(String, default="")
    type = Column(String, nullable=False, default="便當")  # 便當/飲料/牛排/義大利麵
    created_by = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    photos = relationship("RestaurantPhoto", back_populates="restaurant",
                           cascade="all, delete-orphan", order_by="RestaurantPhoto.sort_order")
    menu_items = relationship("MenuItem", back_populates="restaurant",
                               cascade="all, delete-orphan")


class RestaurantPhoto(Base):
    __tablename__ = "restaurant_photos"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    image_url = Column(Text, nullable=False)  # data URL or file-storage URL
    caption = Column(String, default="")
    sort_order = Column(Integer, default=0)

    restaurant = relationship("Restaurant", back_populates="photos")


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    # NOTE: v0.5 removed the `category` column per spec — menus are flat lists.

    restaurant = relationship("Restaurant", back_populates="menu_items")
    options = relationship("MenuItemOption", back_populates="menu_item",
                            cascade="all, delete-orphan")


class MenuItemOption(Base):
    __tablename__ = "menu_item_options"
    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    option_group = Column(String, nullable=False)   # e.g. "口味"
    option_type = Column(String, nullable=False)    # "radio" | "checkbox"
    option_name = Column(String, nullable=False)     # e.g. "原味"
    extra_price = Column(Integer, default=0)

    menu_item = relationship("MenuItem", back_populates="options")


class VoteBatch(Base):
    __tablename__ = "vote_batches"
    id = Column(Integer, primary_key=True, index=True)
    initiator = Column(String, nullable=False)
    deadline_at = Column(DateTime, nullable=False)
    status = Column(String, default="open")  # open | decided | deleted
    created_at = Column(DateTime, default=utcnow)

    candidates = relationship("VoteBatchCandidate", back_populates="batch",
                               cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="batch", cascade="all, delete-orphan")


class VoteBatchCandidate(Base):
    __tablename__ = "vote_batch_candidates"
    id = Column(Integer, primary_key=True, index=True)
    vote_batch_id = Column(Integer, ForeignKey("vote_batches.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    batch = relationship("VoteBatch", back_populates="candidates")
    restaurant = relationship("Restaurant")


class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    vote_batch_id = Column(Integer, ForeignKey("vote_batches.id"), nullable=False)
    user = Column(String, nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    status = Column(String, default="draft")  # draft | locked
    created_at = Column(DateTime, default=utcnow)
    locked_at = Column(DateTime, nullable=True)

    batch = relationship("VoteBatch", back_populates="votes")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    initiator = Column(String, nullable=False)
    source_vote_batch_id = Column(Integer, nullable=True)
    deadline_at = Column(DateTime, nullable=False)
    status = Column(String, default="open")  # open | closed | deleted
    created_at = Column(DateTime, default=utcnow)
    closed_at = Column(DateTime, nullable=True)

    restaurant = relationship("Restaurant")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user = Column(String, nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    selected_options = Column(JSON, default=list)  # list[str]
    quantity = Column(Integer, default=1)
    note = Column(String, default="")
    is_deleted = Column(Boolean, default=False)
    deleted_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")


class OrderHistory(Base):
    __tablename__ = "order_history"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=True)
    restaurant_name = Column(String, nullable=False)
    initiator = Column(String, nullable=False)
    closed_date = Column(String, nullable=False)  # YYYY-MM-DD
    people_count = Column(Integer, default=0)
    total_amount = Column(Integer, default=0)

    lines = relationship("OrderHistoryLine", back_populates="history",
                          cascade="all, delete-orphan")
    payments = relationship("OrderHistoryPayment", back_populates="history",
                             cascade="all, delete-orphan")


class OrderHistoryLine(Base):
    __tablename__ = "order_history_lines"
    id = Column(Integer, primary_key=True, index=True)
    order_history_id = Column(Integer, ForeignKey("order_history.id"), nullable=False)
    item_label = Column(String, nullable=False)
    user = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    amount = Column(Integer, default=0)

    history = relationship("OrderHistory", back_populates="lines")


class OrderHistoryPayment(Base):
    __tablename__ = "order_history_payments"
    id = Column(Integer, primary_key=True, index=True)
    order_history_id = Column(Integer, ForeignKey("order_history.id"), nullable=False)
    user = Column(String, nullable=False)
    total_amount = Column(Integer, default=0)
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)

    history = relationship("OrderHistory", back_populates="payments")
