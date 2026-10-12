import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base


class DecimalPriceTests(unittest.TestCase):
    def test_create_update_and_read_decimal_price(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            restaurant = models.Restaurant(name="測試餐廳")
            db.add(restaurant)
            db.flush()
            payload = schemas.MenuItemIn(name="新蔬食水餃", price=7.5)
            item = models.MenuItem(
                restaurant_id=restaurant.id, name=payload.name, price=payload.price
            )
            db.add(item)
            db.commit()
            db.expire_all()
            saved = db.get(models.MenuItem, item.id)
            self.assertEqual(schemas.MenuItemOut.model_validate(saved).price, 7.5)
            saved.price = schemas.MenuItemIn(name=saved.name, price=8.25).price
            db.commit()
            db.expire_all()
            self.assertEqual(schemas.MenuItemOut.model_validate(saved).price, 8.25)
        engine.dispose()

    def test_integer_prices_remain_valid(self):
        self.assertEqual(schemas.MenuItemIn(name="水餃", price=7).price, 7)


if __name__ == "__main__":
    unittest.main()
