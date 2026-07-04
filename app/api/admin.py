import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.lead import Lead
from app.models.order import Order
from app.models.user import User

router = APIRouter()
security = HTTPBasic()

STATUSES = ["new", "contacted", "done"]


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    if not settings.admin_email or not settings.admin_password:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin not configured")
    correct_email = secrets.compare_digest(credentials.username, settings.admin_email)
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_email and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _page(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>IrMa — Админ-панель</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; background: #fdf6f7; color: #3a3a3a; margin: 0; padding: 32px; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  h2 {{ font-size: 1.1rem; margin: 32px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid #f2c4ce; font-size: .85rem; vertical-align: top; }}
  th {{ background: #f8eef0; font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  .empty {{ color: #7a7a7a; font-size: .85rem; padding: 16px 0; }}
  select {{ font-size: .8rem; padding: 4px 6px; border-radius: 6px; border: 1px solid #f2c4ce; }}
  button {{ font-size: .8rem; padding: 4px 10px; border-radius: 6px; border: none; background: #8fa87c; color: #fff; cursor: pointer; }}
  .status-new {{ color: #d98a9a; font-weight: 600; }}
  .status-contacted {{ color: #a08a3a; font-weight: 600; }}
  .status-done {{ color: #8fa87c; font-weight: 600; }}
</style>
</head>
<body>
<h1>IrMa — Админ-панель</h1>
{body}
</body>
</html>"""


@router.get("", response_class=HTMLResponse)
async def admin_home(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    leads_result = await db.execute(select(Lead).order_by(Lead.created_at.desc()).limit(200))
    leads = leads_result.scalars().all()

    orders_result = await db.execute(
        select(Order, User)
        .join(User, Order.user_id == User.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    )
    orders = orders_result.all()

    leads_rows = "".join(
        f"""<tr>
          <td>{lead.created_at:%d.%m.%Y %H:%M}</td>
          <td>{lead.name}</td>
          <td>{lead.phone}</td>
          <td>{lead.email or '—'}</td>
          <td>{lead.source}</td>
          <td>
            <form method="post" action="/admin/leads/{lead.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == lead.status else ""}>{s}</option>' for s in STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
          </td>
        </tr>"""
        for lead in leads
    ) or '<tr><td colspan="6" class="empty">Заявок пока нет</td></tr>'

    orders_rows = "".join(
        f"""<tr>
          <td>{order.created_at:%d.%m.%Y %H:%M}</td>
          <td>{user.name} {user.phone or ''}</td>
          <td>{len(order.items)} поз.</td>
          <td>{order.total_amount} ₽</td>
          <td>{order.status}</td>
        </tr>"""
        for order, user in orders
    ) or '<tr><td colspan="5" class="empty">Заказов пока нет</td></tr>'

    body = f"""
    <h2>Заявки с сайта ({len(leads)})</h2>
    <table>
      <tr><th>Дата</th><th>Имя</th><th>Телефон</th><th>Почта</th><th>Источник</th><th>Статус</th></tr>
      {leads_rows}
    </table>

    <h2>Заказы через бота ({len(orders)})</h2>
    <table>
      <tr><th>Дата</th><th>Клиент</th><th>Состав</th><th>Сумма</th><th>Статус</th></tr>
      {orders_rows}
    </table>
    <p class="empty">Заказы из корзины на сайте пока не сохраняются в базу — только уходят уведомлением в MAX.</p>
    """
    return HTMLResponse(_page(body))


@router.post("/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    if status_value not in STATUSES:
        raise HTTPException(status_code=422, detail="Недопустимый статус")
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    lead.status = status_value
    await db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
