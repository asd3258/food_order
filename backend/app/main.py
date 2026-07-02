import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, wait_for_db
from app.routers import users, restaurants, orders, votes, history

wait_for_db()
Base.metadata.create_all(bind=engine)

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
app.include_router(orders.router)
app.include_router(votes.router)
app.include_router(history.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
