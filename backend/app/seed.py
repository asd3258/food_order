"""
Seed the database with the same demo data used in wireframe.html, so the API
is immediately testable end-to-end. Run with: python -m app.seed
"""
import datetime as dt

from app.database import Base, engine, SessionLocal, wait_for_db
from app import models

RESTAURANTS = [
    dict(name="日式烤肉飯 南崬", type="便當", phone="(03) 312-8111", addr="桃園市蘆竹區南崁路300號",
         photos=[("🍚 招牌雙拼飯", "#c2410c"), ("🥩 烤牛肉飯特寫", "#7c2d12"), ("🏠 店內環境", "#78350f")],
         menu=[
             ("烤牛雙拼飯", 129, [("口味", "radio", [("原味", 0), ("泰式", 0), ("五辣", 0)])]),
             ("烤雞雙拼飯", 119, [("口味", "radio", [("原味", 0), ("泰式", 0)])]),
             ("烤牛肉飯", 99, [("口味", "radio", [("原味", 0), ("泰式", 0), ("五辣", 0)]),
                              ("加購", "checkbox", [("白飯加量", 20), ("半熟蛋", 15), ("泡菜", 20)])]),
             ("烤雞腿飯", 99, [("口味", "radio", [("原味", 0), ("泰式", 0)]),
                              ("加購", "checkbox", [("白飯加量", 20), ("半熟蛋", 15)])]),
         ]),
    dict(name="鬍鬚張魯肉飯", type="便當", phone="(03) 555-2222", addr="桃園市蘆竹區中正路100號",
         photos=[("🍱 魯肉飯", "#92400e"), ("🍗 雞腿飯", "#b45309")],
         menu=[
             ("魯肉飯", 35, [("口味", "radio", [("小份", 0), ("大份", 10)])]),
             ("雞腿飯", 89, [("加購", "checkbox", [("滷蛋", 10), ("燙青菜", 20)])]),
         ]),
    dict(name="八方雲集", type="便當", phone="(03) 777-8888", addr="桃園市蘆竹區南崁北路50號",
         photos=[("🥟 鍋貼", "#155e75"), ("🍲 酸辣湯", "#0e7490")],
         menu=[("鍋貼(10顆)", 60, []), ("酸辣湯", 35, [])]),
    dict(name="50嵐", type="飲料", phone="(03) 888-1234", addr="桃園市蘆竹區中山路20號",
         photos=[("🧋 招牌飲品", "#065f46")],
         menu=[
             ("珍珠奶茶", 55, [("甜度", "radio", [("正常", 0), ("少糖", 0), ("半糖", 0), ("無糖", 0)]),
                             ("冰塊", "radio", [("正常冰", 0), ("少冰", 0), ("去冰", 0)])]),
             ("四季春茶", 30, [("甜度", "radio", [("正常", 0), ("少糖", 0), ("無糖", 0)])]),
         ]),
    dict(name="貴族世家牛排", type="牛排", phone="(03) 999-5678", addr="桃園市蘆竹區介壽路88號",
         photos=[("🥩 嫩煎牛排", "#7c2d12")],
         menu=[
             ("嫩煎沙朗牛排", 220, [("熟度", "radio", [("三分", 0), ("五分", 0), ("七分", 0), ("全熟", 0)])]),
             ("蘑菇醬牛排", 250, [("熟度", "radio", [("三分", 0), ("五分", 0), ("七分", 0)])]),
         ]),
    dict(name="義麵坊", type="義大利麵", phone="(03) 222-3456", addr="桃園市蘆竹區忠孝路15號",
         photos=[("🍝 奶油培根義大利麵", "#92400e")],
         menu=[
             ("奶油培根義大利麵", 150, [("份量", "radio", [("正常", 0), ("加大", 30)])]),
             ("紅醬肉丸義大利麵", 160, []),
         ]),
]


SEED_USERS = ["Mike Chen", "Tony Su", "Asa Wang", "Vincent Yu"]
ADMIN_USERS = ["mike_admin"]  # v0.8: is_admin=True -- log in as this name to manage users / delete history
# (renamed from admin_mike -- see app/migrations.py for the upgrade path on
# already-deployed databases that already seeded the old name)


def seed():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Restaurant).count() > 0:
            print("Already seeded, skipping.")
            return

        for name in SEED_USERS:
            db.add(models.User(name=name))
        for name in ADMIN_USERS:
            db.add(models.User(name=name, is_admin=True))
        db.commit()

        restaurant_objs = []
        for spec in RESTAURANTS:
            r = models.Restaurant(name=spec["name"], type=spec["type"], phone=spec["phone"],
                                   address=spec["addr"], created_by="Mike Chen")
            db.add(r)
            db.flush()
            for i, (label, color) in enumerate(spec["photos"]):
                db.add(models.RestaurantPhoto(restaurant_id=r.id, image_url=f"placeholder:{color}",
                                               caption=label, sort_order=i))
            for name, price, opt_groups in spec["menu"]:
                mi = models.MenuItem(restaurant_id=r.id, name=name, price=price)
                db.add(mi)
                db.flush()
                for group, otype, choices in opt_groups:
                    for cname, extra in choices:
                        db.add(models.MenuItemOption(menu_item_id=mi.id, option_group=group,
                                                       option_type=otype, option_name=cname,
                                                       extra_price=extra))
            restaurant_objs.append(r)
        db.commit()

        # Seed one open order on restaurant #1, matching wireframe.html
        r1 = restaurant_objs[0]
        beef = next(m for m in r1.menu_items if m.name == "烤牛肉飯")
        combo = next(m for m in r1.menu_items if m.name == "烤牛雙拼飯")
        order = models.Order(restaurant_id=r1.id, initiator="Mike Chen",
                              deadline_at=dt.datetime.utcnow() + dt.timedelta(hours=2))
        db.add(order)
        db.flush()
        db.add(models.OrderItem(order_id=order.id, user="Tony Su", menu_item_id=beef.id,
                                 selected_options=["原味"], quantity=1))
        db.add(models.OrderItem(order_id=order.id, user="Asa Wang", menu_item_id=combo.id,
                                 selected_options=["泰式"], quantity=1))
        db.commit()

        # Seed one closed history entry with payments, matching wireframe.html
        history = models.OrderHistory(order_id=9999, restaurant_name=r1.name, initiator="Mike Chen",
                                        closed_date="2026-06-25", people_count=4, total_amount=654)
        db.add(history)
        db.flush()
        lines = [
            ("烤牛肉飯(原味)", "Tony Su", 2, 198),
            ("烤牛肉飯(泰式)", "Mike Chen", 1, 99),
            ("烤牛雙拼飯(泰式)", "Asa Wang", 2, 258),
            ("烤雞腿飯(原味)", "Vincent Yu", 1, 99),
        ]
        for label, user, qty, amount in lines:
            db.add(models.OrderHistoryLine(order_history_id=history.id, item_label=label,
                                             user=user, quantity=qty, amount=amount))
        payments = [("Tony Su", 198, False), ("Mike Chen", 99, True),
                    ("Asa Wang", 258, False), ("Vincent Yu", 99, True)]
        for user, total, paid in payments:
            db.add(models.OrderHistoryPayment(order_history_id=history.id, user=user,
                                               total_amount=total, is_paid=paid))
        db.commit()
        print(f"Seeded {len(restaurant_objs)} restaurants, 1 open order, 1 history entry.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
