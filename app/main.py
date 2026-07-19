from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.menu import router as menu_router, items_router
from app.api.user import router as user_router
from app.api.order import router as order_router, history_router
from app.api.bonus import router as bonus_router
from app.api.lead import router as lead_router
from app.api.admin import router as admin_router
from app.api.news import router as news_router
from app.api.training_lessons import router as training_lessons_router
from app.bot.webhook import router as webhook_router
from app.bot.news_webhook import router as news_webhook_router

app = FastAPI(title="Irma Bot API", version="0.1.0")

for _dir in ("news", "training"):
    Path("uploads", _dir).mkdir(parents=True, exist_ok=True)

app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(items_router, prefix="/item", tags=["menu"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(order_router, prefix="/order", tags=["order"])
app.include_router(history_router, prefix="/orders", tags=["order"])
app.include_router(bonus_router, prefix="/bonuses", tags=["bonus"])
app.include_router(lead_router, prefix="/leads", tags=["lead"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(news_router, prefix="/news", tags=["news"])
app.include_router(training_lessons_router, prefix="/training-lessons", tags=["training"])
app.include_router(webhook_router, tags=["bot"])
app.include_router(news_webhook_router, tags=["news-bot"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Лендинг — монтируется последним, не перекрывает API-роуты
app.mount("/", StaticFiles(directory="landing", html=True), name="landing")
