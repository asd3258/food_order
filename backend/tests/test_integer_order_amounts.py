import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base
from app.routers.orders import add_item, update_own_item, _validate_integer_amount


class IntegerOrderAmountTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        restaurant = models.Restaurant(name='測試餐廳')
        self.db.add(restaurant)
        self.db.flush()
        self.menu = models.MenuItem(restaurant_id=restaurant.id, name='新蔬食水餃', price=7.5)
        self.order = models.Order(restaurant_id=restaurant.id, initiator='tester')
        self.db.add_all([self.menu, self.order])
        self.db.commit()
        self.permission = patch('app.routers.orders.check_permission', return_value=True)
        self.permission.start()

    def tearDown(self):
        self.permission.stop()
        self.db.close()
        self.engine.dispose()

    def payload(self, quantity, options=None):
        return schemas.OrderItemCreateIn(user='tester', menu_item_id=self.menu.id,
                                         quantity=quantity, selected_options=options or [])

    def test_add_rejects_fractional_total_without_saving(self):
        with self.assertRaises(HTTPException) as error:
            add_item(self.order.id, self.payload(3), BackgroundTasks(), self.db)
        self.assertEqual(error.exception.status_code, 422)
        self.assertIn('22.5', error.exception.detail)
        self.assertEqual(self.db.query(models.OrderItem).count(), 0)

    def test_add_accepts_integer_total_and_update_rejects_fractional_total(self):
        item = add_item(self.order.id, self.payload(2), BackgroundTasks(), self.db)
        self.assertEqual(item.quantity, 2)
        with self.assertRaises(HTTPException):
            update_own_item(self.order.id, item.id, self.payload(3), BackgroundTasks(), self.db)
        self.db.refresh(item)
        self.assertEqual(item.quantity, 2)

    def test_options_are_included_in_total(self):
        self.db.add(models.MenuItemOption(menu_item_id=self.menu.id, option_group='加購',
                    option_type='checkbox', option_name='加料', extra_price=0.5))
        self.db.commit()
        _validate_integer_amount(self.db, self.menu.id, ['加料'], 3)
        self.menu.price = 7
        self.db.commit()
        with self.assertRaises(HTTPException):
            _validate_integer_amount(self.db, self.menu.id, ['加料'], 3)

    def test_decimal_arithmetic_allows_integer_total(self):
        self.menu.price = 0.1
        self.db.add(models.MenuItemOption(menu_item_id=self.menu.id, option_group='加購',
                    option_type='checkbox', option_name='加料', extra_price=0.2))
        self.db.commit()
        _validate_integer_amount(self.db, self.menu.id, ['加料'], 10)


if __name__ == '__main__':
    unittest.main()
