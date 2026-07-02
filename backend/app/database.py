import os
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./food_order.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    """Retry connecting until Postgres is actually accepting connections.

    docker-compose's `depends_on: condition: service_healthy` already covers
    the normal case, but this is defense-in-depth for anyone who runs the API
    without that (e.g. `docker compose restart food_order_api` while the DB
    container is still coming back up after a host reboot).
    """
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                return
        except OperationalError as exc:
            if attempt == max_attempts:
                raise
            print(f"[wait_for_db] DB not ready yet (attempt {attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)
