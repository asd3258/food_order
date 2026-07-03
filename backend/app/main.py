import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, wait_for_db
from app.migrations import run_light_migrations
from app.routers import users, restaurants, orders, votes, history, ws

wait_for_db()
Base.metadata.create_all(bind=engine)
run_light_migrations()

app = FastAPI(title="訂餐統計 App API", version="0.5.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(restaurants.router)
# IMPORTANT: history.router must be included *before* orders.router.
# history.router's path is "/api/orders/history/..." and orders.router has a
# catch-all "/api/orders/{order_id}" route. FastAPI/Starlette match routes in
# registration order, so if orders.router came first, a request to
# "/api/orders/history" would get captured by "/api/orders/{order_id}" (with
# order_id="history"), fail int conversion, and return a 422 instead of ever
# reaching the real history endpoint -- history would always look empty.
app.include_router(history.router)
app.include_router(orders.router)
app.include_router(votes.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
