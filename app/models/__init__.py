from app.models.user import User
from app.models.menu import MenuCategory, MenuItem
from app.models.order import Order
from app.models.bonus_transaction import BonusTransaction
from app.models.lead import Lead
from app.models.news import News
from app.models.training_lesson import TrainingLesson
from app.models.site_order import SiteOrder
from app.models.promo import Promo
from app.models.max_order import MaxOrder

__all__ = [
    "User",
    "MenuCategory",
    "MenuItem",
    "Order",
    "BonusTransaction",
    "Lead",
    "News",
    "TrainingLesson",
    "SiteOrder",
    "Promo",
    "MaxOrder",
]
