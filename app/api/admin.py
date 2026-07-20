import json
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.config import settings
from app.database import get_db
from app.models.lead import Lead
from app.models.order import Order
from app.models.user import User
from app.models.news import News
from app.models.training_lesson import TrainingLesson
from app.models.site_order import SiteOrder
from app.models.promo import Promo
from app.models.max_order import MaxOrder

router = APIRouter()
security = HTTPBasic()

LEAD_STATUSES = ["new", "contacted", "paid", "done"]
SITE_ORDER_STATUSES = ["new", "processing", "done"]
BOT_ORDER_STATUSES = ["created", "completed", "cancelled"]
MAX_ORDER_STATUSES = ["new", "confirmed", "done", "cancelled"]

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

NAV_ITEMS = [
    ("dashboard", "/admin", "Главная"),
    ("site-orders", "/admin/site-orders", "Заказы через сайт"),
    ("bot-orders", "/admin/bot-orders", "Заказы через приложение"),
    ("training", "/admin/training", "Обучение"),
    ("stats", "/admin/stats", "Статистика"),
    ("content", "/admin/content", "Контент"),
]


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


def _slugify(title: str) -> str:
    letters = "".join(TRANSLIT.get(c, c) for c in title.lower())
    slug = "".join(c if c.isalnum() else "-" for c in letters)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-") or "lesson"
    return f"{slug}-{secrets.token_hex(3)}"


async def _save_upload(file: UploadFile | None, subdir: str) -> str | None:
    if not file or not file.filename:
        return None
    ext = Path(file.filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    dest_dir = Path("uploads", subdir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}{ext}"
    content = await file.read()
    if content:
        (dest_dir / filename).write_bytes(content)
        return f"/uploads/{subdir}/{filename}"
    return None


def _delete_file(path: str | None) -> None:
    if not path:
        return
    file_path = Path(path.lstrip("/"))
    if file_path.exists():
        file_path.unlink()


async def _nav_counts(db: AsyncSession) -> tuple[int, int]:
    site_new = await db.scalar(select(func.count()).select_from(SiteOrder).where(SiteOrder.status == "new")) or 0
    bot_new = await db.scalar(select(func.count()).select_from(Order).where(Order.status == "created")) or 0
    max_new = await db.scalar(select(func.count()).select_from(MaxOrder).where(MaxOrder.status == "new")) or 0
    return site_new, bot_new + max_new


def _nav_html(active: str, site_new: int, bot_new: int) -> str:
    badges = {"site-orders": site_new, "bot-orders": bot_new}
    links = []
    for key, href, label in NAV_ITEMS:
        cls = "active" if key == active else ""
        badge = badges.get(key, 0)
        badge_html = f'<span class="tab-badge">{badge}</span>' if badge else ""
        links.append(f'<a href="{href}" class="{cls}">{label}{badge_html}</a>')
    return f'<nav class="admin-tabs">{"".join(links)}</nav>'


def _page(body: str, active: str = "dashboard", site_new: int = 0, bot_new: int = 0) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>IrMa — Админ-панель</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; background: #fdf6f7; color: #3a3a3a; margin: 0; padding: 0 32px 32px; }}
  h1 {{ font-size: 1.3rem; padding: 24px 0 16px; margin: 0; }}
  h2 {{ font-size: 1.1rem; margin: 32px 0 12px; display: flex; align-items: center; gap: 12px; }}
  h2 a.add-link {{ font-size: .78rem; font-weight: 600; color: #8fa87c; text-decoration: none; background: #fff; border: 1px solid #c8d9be; padding: 4px 12px; border-radius: 20px; }}
  h2 a.add-link:hover {{ background: #eef4ea; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid #f2c4ce; font-size: .85rem; vertical-align: top; }}
  th {{ background: #f8eef0; font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  .empty {{ color: #7a7a7a; font-size: .85rem; padding: 16px 0; }}
  select {{ font-size: .8rem; padding: 4px 6px; border-radius: 6px; border: 1px solid #f2c4ce; }}
  button {{ font-size: .8rem; padding: 4px 10px; border-radius: 6px; border: none; background: #8fa87c; color: #fff; cursor: pointer; }}
  .row-actions {{ display: flex; gap: 6px; }}
  a.btn-edit {{ font-size: .78rem; padding: 4px 10px; border-radius: 6px; background: #f2c4ce; color: #3a3a3a; text-decoration: none; }}
  .status-new {{ color: #d98a9a; font-weight: 600; }}
  .status-contacted {{ color: #a08a3a; font-weight: 600; }}
  .status-paid {{ color: #6fa8a0; font-weight: 600; }}
  .status-done {{ color: #8fa87c; font-weight: 600; }}
  form.edit-form {{ background: #fff; border-radius: 12px; padding: 24px 28px; max-width: 640px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  form.edit-form label {{ display: block; font-size: .8rem; font-weight: 600; margin: 14px 0 4px; }}
  form.edit-form input[type=text], form.edit-form input[type=file], form.edit-form textarea {{
    width: 100%; padding: 8px 10px; border: 1px solid #f2c4ce; border-radius: 8px; font-size: .85rem; font-family: inherit; box-sizing: border-box;
  }}
  form.edit-form textarea {{ min-height: 80px; }}
  form.edit-form .hint {{ font-size: .74rem; color: #7a7a7a; margin-top: 2px; }}
  form.edit-form .current-img {{ max-width: 200px; border-radius: 8px; margin-top: 6px; display: block; }}
  form.edit-form button {{ margin-top: 20px; padding: 10px 22px; }}

  .admin-tabs {{ position: sticky; top: 0; background: #fdf6f7; z-index: 10; display: flex; gap: 4px; flex-wrap: wrap; padding: 8px 0 16px; border-bottom: 1px solid #f2c4ce; margin-bottom: 8px; }}
  .admin-tabs a {{ position: relative; text-decoration: none; color: #7a7a7a; font-size: .82rem; font-weight: 600; padding: 8px 16px; border-radius: 20px; background: #fff; border: 1px solid #f2c4ce; }}
  .admin-tabs a:hover {{ background: #f8eef0; }}
  .admin-tabs a.active {{ background: #8fa87c; border-color: #8fa87c; color: #fff; }}
  .tab-badge {{ display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; margin-left: 6px; border-radius: 10px; background: #d98a9a; color: #fff; font-size: .68rem; font-weight: 700; }}
  .admin-tabs a.active .tab-badge {{ background: #fff; color: #d98a9a; }}

  .content-subtabs {{ display: flex; gap: 8px; margin-bottom: 20px; }}
  .content-subtabs a {{ text-decoration: none; color: #7a7a7a; font-size: .8rem; font-weight: 600; padding: 6px 14px; border-radius: 16px; background: #fff; border: 1px solid #f2c4ce; }}
  .content-subtabs a.active {{ background: #d98a9a; border-color: #d98a9a; color: #fff; }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 16px 0 32px; }}
  .kpi-tile {{ background: #fff; border-radius: 14px; padding: 18px 20px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  .kpi-tile .kpi-label {{ font-size: .74rem; color: #7a7a7a; margin-bottom: 6px; }}
  .kpi-tile .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: #3a3a3a; }}
  .kpi-tile .kpi-value.pink {{ color: #d98a9a; }}
  .kpi-tile .kpi-value.green {{ color: #8fa87c; }}

  .chart-box {{ background: #fff; border-radius: 14px; padding: 20px 24px; box-shadow: 0 2px 12px rgba(0,0,0,.06); margin-bottom: 32px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 24px; }}
  .stats-card {{ background: #fff; border-radius: 14px; padding: 20px 22px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  .stats-card h3 {{ font-size: .95rem; margin: 0 0 12px; }}
  .stats-row {{ display: flex; justify-content: space-between; font-size: .85rem; padding: 6px 0; border-bottom: 1px solid #f8eef0; }}
  .stats-row:last-child {{ border-bottom: none; }}
  .stats-row span:last-child {{ font-weight: 700; }}
</style>
</head>
<body>
<h1>IrMa — Админ-панель</h1>
{_nav_html(active, site_new, bot_new)}
{body}
</body>
</html>"""


# ---------------------------------------------------------------- Dashboard

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)

    today = datetime.utcnow().date()
    since = datetime.utcnow() - timedelta(days=30)
    week_ago = datetime.utcnow() - timedelta(days=7)

    site_orders = (await db.execute(select(SiteOrder).where(SiteOrder.created_at >= since))).scalars().all()
    bot_orders = (await db.execute(select(Order).where(Order.created_at >= since))).scalars().all()
    max_orders_recent = (await db.execute(select(MaxOrder).where(MaxOrder.created_at >= since))).scalars().all()
    app_orders = bot_orders + max_orders_recent  # "через приложение" = бот IrMa + ChatMarket

    orders_today = sum(1 for o in site_orders + app_orders if o.created_at.date() == today)
    revenue_week = sum(
        o.total_amount for o in site_orders + app_orders if o.created_at >= week_ago
    )
    new_leads = await db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "new")) or 0

    days = [(today - timedelta(days=i)) for i in range(29, -1, -1)]
    site_by_day = {d: 0 for d in days}
    bot_by_day = {d: 0 for d in days}
    for o in site_orders:
        d = o.created_at.date()
        if d in site_by_day:
            site_by_day[d] += 1
    for o in app_orders:
        d = o.created_at.date()
        if d in bot_by_day:
            bot_by_day[d] += 1

    labels = json.dumps([d.strftime("%d.%m") for d in days])
    site_series = json.dumps([site_by_day[d] for d in days])
    bot_series = json.dumps([bot_by_day[d] for d in days])

    recent_leads = (
        await db.execute(select(Lead).order_by(Lead.created_at.desc()).limit(15))
    ).scalars().all()
    recent_leads_rows = "".join(
        f"""<tr>
          <td>{lead.created_at:%d.%m %H:%M}</td>
          <td>{lead.name}</td>
          <td>{lead.phone}</td>
          <td>{lead.source}</td>
          <td>
            <form method="post" action="/admin/leads/{lead.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == lead.status else ""}>{s}</option>' for s in LEAD_STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
          </td>
        </tr>"""
        for lead in recent_leads
    ) or '<tr><td colspan="5" class="empty">Заявок пока нет</td></tr>'

    body = f"""
    <div class="kpi-grid">
      <div class="kpi-tile"><div class="kpi-label">Заказов сегодня</div><div class="kpi-value">{orders_today}</div></div>
      <div class="kpi-tile"><div class="kpi-label">Выручка за 7 дней</div><div class="kpi-value green">{revenue_week:,.0f} ₽</div></div>
      <div class="kpi-tile"><div class="kpi-label">Новых заказов с сайта</div><div class="kpi-value pink">{site_new}</div></div>
      <div class="kpi-tile"><div class="kpi-label">Новых через приложение</div><div class="kpi-value pink">{bot_new}</div></div>
      <div class="kpi-tile"><div class="kpi-label">Новых заявок</div><div class="kpi-value pink">{new_leads}</div></div>
    </div>

    <div class="chart-box">
      <canvas id="ordersChart" height="90"></canvas>
    </div>

    <h2>Последние заявки</h2>
    <table>
      <tr><th>Дата</th><th>Имя</th><th>Телефон</th><th>Источник</th><th>Статус</th></tr>
      {recent_leads_rows}
    </table>

    <h2>Для ChatMarket</h2>
    <p class="empty">
      <a href="/menu/export.xlsx">Скачать меню в Excel</a> — для ручной загрузки файлом
      (на вашем тарифе доступен только этот способ).<br>
      <a href="https://irma-cafe.ru/menu/export.yml" target="_blank">https://irma-cafe.ru/menu/export.yml</a> —
      тот же каталог фидом по ссылке, пригодится, если перейдёте на тариф «Бизнес»
      (там есть импорт по URL).<br>
      Колонки/формат — стандартные, не по шаблону ChatMarket (нигде не публикуют его) —
      если у них в кабинете есть готовый шаблон для скачивания, ориентируйтесь на него,
      и дайте знать, поправлю выгрузку под него.
    </p>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById('ordersChart'), {{
      type: 'line',
      data: {{
        labels: {labels},
        datasets: [
          {{ label: 'Заказы с сайта', data: {site_series}, borderColor: '#d98a9a', backgroundColor: 'rgba(217,138,154,.12)', tension: .3, fill: true }},
          {{ label: 'Заказы через приложение', data: {bot_series}, borderColor: '#8fa87c', backgroundColor: 'rgba(143,168,124,.12)', tension: .3, fill: true }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ title: {{ display: true, text: 'Заказы по дням за последние 30 дней' }} }},
        scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }}
      }}
    }});
    </script>
    """
    return HTMLResponse(_page(body, "dashboard", site_new, bot_new))


# ---------------------------------------------------------------- Site orders

@router.get("/site-orders", response_class=HTMLResponse)
async def admin_site_orders(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)
    orders = (await db.execute(select(SiteOrder).order_by(SiteOrder.created_at.desc()).limit(200))).scalars().all()

    rows = "".join(
        f"""<tr>
          <td>{o.created_at:%d.%m.%Y %H:%M}</td>
          <td>{o.phone}</td>
          <td>{"; ".join(f"{i['name']} × {i['qty']}" for i in o.items)}</td>
          <td>{o.total_amount:,.0f} ₽</td>
          <td class="row-actions">
            <form method="post" action="/admin/site-orders/{o.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == o.status else ""}>{s}</option>' for s in SITE_ORDER_STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
            <form method="post" action="/admin/site-orders/{o.id}/delete" onsubmit="return confirm('Удалить этот заказ?')">
              <button type="submit" style="background:#d98a9a">Удалить</button>
            </form>
          </td>
        </tr>"""
        for o in orders
    ) or '<tr><td colspan="5" class="empty">Заказов пока нет</td></tr>'

    body = f"""
    <h2>Заказы через сайт ({len(orders)})</h2>
    <table>
      <tr><th>Дата</th><th>Телефон</th><th>Состав</th><th>Сумма</th><th>Статус</th></tr>
      {rows}
    </table>
    <p class="empty">Заказы из корзины на сайте — телефон и состав, без привязки к аккаунту. Уведомление о каждом также уходит в MAX.</p>
    """
    return HTMLResponse(_page(body, "site-orders", site_new, bot_new))


@router.post("/site-orders/{order_id}/status")
async def site_order_update_status(
    order_id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    if status_value not in SITE_ORDER_STATUSES:
        raise HTTPException(status_code=422, detail="Недопустимый статус")
    order = await db.get(SiteOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = status_value
    await db.commit()
    return RedirectResponse(url="/admin/site-orders", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/site-orders/{order_id}/delete")
async def site_order_delete(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    order = await db.get(SiteOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    await db.delete(order)
    await db.commit()
    return RedirectResponse(url="/admin/site-orders", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- Bot orders

@router.get("/bot-orders", response_class=HTMLResponse)
async def admin_bot_orders(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)
    result = await db.execute(
        select(Order, User)
        .join(User, Order.user_id == User.id)
        .order_by(Order.created_at.desc())
        .limit(200)
    )
    orders = result.all()

    rows = "".join(
        f"""<tr>
          <td>{order.created_at:%d.%m.%Y %H:%M}</td>
          <td>{user.name} {user.phone or ''}</td>
          <td>{len(order.items)} поз.</td>
          <td>{order.total_amount} ₽</td>
          <td>
            <form method="post" action="/admin/bot-orders/{order.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == order.status else ""}>{s}</option>' for s in BOT_ORDER_STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
          </td>
        </tr>"""
        for order, user in orders
    ) or '<tr><td colspan="5" class="empty">Заказов пока нет</td></tr>'

    max_orders = (await db.execute(select(MaxOrder).order_by(MaxOrder.created_at.desc()).limit(200))).scalars().all()
    max_rows = "".join(
        f"""<tr>
          <td>{o.created_at:%d.%m.%Y %H:%M}</td>
          <td>{o.phone or '—'}</td>
          <td>{o.description}</td>
          <td>{o.total_amount:,.0f} ₽</td>
          <td class="row-actions">
            <form method="post" action="/admin/max-orders/{o.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == o.status else ""}>{s}</option>' for s in MAX_ORDER_STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
            <form method="post" action="/admin/max-orders/{o.id}/delete" onsubmit="return confirm('Удалить этот заказ?')">
              <button type="submit" style="background:#d98a9a">Удалить</button>
            </form>
          </td>
        </tr>"""
        for o in max_orders
    ) or '<tr><td colspan="5" class="empty">Заказов пока нет</td></tr>'

    body = f"""
    <h2>Заказы через бота IrMa ({len(orders)})</h2>
    <table>
      <tr><th>Дата</th><th>Клиент</th><th>Состав</th><th>Сумма</th><th>Статус</th></tr>
      {rows}
    </table>

    <h2>Заказы из магазина ChatMarket ({len(max_orders)}) <a class="add-link" href="/admin/max-orders/new">+ Внести заказ</a></h2>
    <table>
      <tr><th>Дата</th><th>Телефон</th><th>Состав</th><th>Сумма</th><th>Статус</th></tr>
      {max_rows}
    </table>
    <p class="empty">ChatMarket не отдаёт заказы по API — присылает уведомления в Telegram/почту. Заносите их сюда вручную, чтобы они попадали в общую статистику с пометкой источника.</p>
    """
    return HTMLResponse(_page(body, "bot-orders", site_new, bot_new))


@router.post("/bot-orders/{order_id}/status")
async def bot_order_update_status(
    order_id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    if status_value not in BOT_ORDER_STATUSES:
        raise HTTPException(status_code=422, detail="Недопустимый статус")
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = status_value
    await db.commit()
    return RedirectResponse(url="/admin/bot-orders", status_code=status.HTTP_303_SEE_OTHER)


def _max_order_form() -> str:
    return """
    <h2>Внести заказ из ChatMarket</h2>
    <form class="edit-form" method="post" action="/admin/max-orders/new">
      <label>Телефон (необязательно)</label>
      <input type="text" name="phone">

      <label>Состав заказа</label>
      <textarea name="description" required placeholder="Например: Капучино 0.4 x2, Круассан x1"></textarea>

      <label>Сумма, ₽</label>
      <input type="text" name="total_amount" required placeholder="850">
      <p class="hint">Заполняйте по уведомлению из Telegram/почты от ChatMarket.</p>

      <button type="submit">Сохранить</button>
    </form>
    """


@router.get("/max-orders/new", response_class=HTMLResponse)
async def max_order_new_form(_: str = Depends(require_admin)):
    return HTMLResponse(_page(_max_order_form(), "bot-orders"))


@router.post("/max-orders/new")
async def max_order_create(
    phone: str = Form(""),
    description: str = Form(...),
    total_amount: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        amount = Decimal(total_amount.replace(",", ".").strip())
    except Exception:
        raise HTTPException(status_code=422, detail="Некорректная сумма")
    db.add(MaxOrder(phone=phone or None, description=description, total_amount=amount))
    await db.commit()
    return RedirectResponse(url="/admin/bot-orders", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/max-orders/{order_id}/status")
async def max_order_update_status(
    order_id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    if status_value not in MAX_ORDER_STATUSES:
        raise HTTPException(status_code=422, detail="Недопустимый статус")
    order = await db.get(MaxOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = status_value
    await db.commit()
    return RedirectResponse(url="/admin/bot-orders", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/max-orders/{order_id}/delete")
async def max_order_delete(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    order = await db.get(MaxOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    await db.delete(order)
    await db.commit()
    return RedirectResponse(url="/admin/bot-orders", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- Training (leads)

@router.get("/training", response_class=HTMLResponse)
async def admin_training_leads(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)
    result = await db.execute(
        select(Lead)
        .where(Lead.source.like("training-%"))
        .order_by(Lead.created_at.desc())
        .limit(200)
    )
    leads = result.scalars().all()

    rows = "".join(
        f"""<tr>
          <td>{lead.created_at:%d.%m.%Y %H:%M}</td>
          <td>{lead.name}</td>
          <td>{lead.phone}</td>
          <td>{lead.email or '—'}</td>
          <td>{lead.source.removeprefix('training-')}</td>
          <td>
            <form method="post" action="/admin/leads/{lead.id}/status" style="display:flex;gap:6px">
              <select name="status">
                {"".join(f'<option value="{s}" {"selected" if s == lead.status else ""}>{s}</option>' for s in LEAD_STATUSES)}
              </select>
              <button type="submit">Сохранить</button>
            </form>
          </td>
        </tr>"""
        for lead in leads
    ) or '<tr><td colspan="6" class="empty">Заявок на уроки пока нет</td></tr>'

    body = f"""
    <h2>Заявки на обучение ({len(leads)})</h2>
    <table>
      <tr><th>Дата</th><th>Имя</th><th>Телефон</th><th>Почта</th><th>Урок</th><th>Статус</th></tr>
      {rows}
    </table>
    <p class="empty">Заявки с формы «Записаться на урок» на страницах уроков. Статус «paid» — отметка об оплате.</p>
    """
    return HTMLResponse(_page(body, "training", site_new, bot_new))


@router.post("/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    if status_value not in LEAD_STATUSES:
        raise HTTPException(status_code=422, detail="Недопустимый статус")
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    lead.status = status_value
    await db.commit()
    referer = "/admin/training" if lead.source.startswith("training-") else "/admin"
    return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- Stats

@router.get("/stats", response_class=HTMLResponse)
async def admin_stats(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)

    site_orders = (await db.execute(select(SiteOrder))).scalars().all()
    bot_orders = (await db.execute(select(Order))).scalars().all()
    max_orders = (await db.execute(select(MaxOrder))).scalars().all()

    def _stats_block(orders: list, statuses: list[str]) -> dict:
        total = len(orders)
        revenue = sum((o.total_amount for o in orders), Decimal(0))
        avg = (revenue / total) if total else Decimal(0)
        by_status = {s: sum(1 for o in orders if o.status == s) for s in statuses}
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        week = [o for o in orders if o.created_at >= week_ago]
        month = [o for o in orders if o.created_at >= month_ago]
        return dict(
            total=total, revenue=revenue, avg=avg, by_status=by_status,
            week_count=len(week), week_revenue=sum((o.total_amount for o in week), Decimal(0)),
            month_count=len(month), month_revenue=sum((o.total_amount for o in month), Decimal(0)),
        )

    site_stats = _stats_block(site_orders, SITE_ORDER_STATUSES)
    bot_stats = _stats_block(bot_orders, BOT_ORDER_STATUSES)
    max_stats = _stats_block(max_orders, MAX_ORDER_STATUSES)
    combined_total = site_stats["total"] + bot_stats["total"] + max_stats["total"]
    combined_revenue = site_stats["revenue"] + bot_stats["revenue"] + max_stats["revenue"]

    def _card(title: str, s: dict) -> str:
        status_rows = "".join(
            f'<div class="stats-row"><span>{name}</span><span>{count}</span></div>'
            for name, count in s["by_status"].items()
        )
        return f"""
        <div class="stats-card">
          <h3>{title}</h3>
          <div class="stats-row"><span>Всего заказов</span><span>{s['total']}</span></div>
          <div class="stats-row"><span>Выручка всего</span><span>{s['revenue']:,.0f} ₽</span></div>
          <div class="stats-row"><span>Средний чек</span><span>{s['avg']:,.0f} ₽</span></div>
          <div class="stats-row"><span>За 7 дней</span><span>{s['week_count']} / {s['week_revenue']:,.0f} ₽</span></div>
          <div class="stats-row"><span>За 30 дней</span><span>{s['month_count']} / {s['month_revenue']:,.0f} ₽</span></div>
          {status_rows}
        </div>
        """

    body = f"""
    <h2>Статистика по заказам</h2>
    <div class="kpi-grid">
      <div class="kpi-tile"><div class="kpi-label">Всего заказов (все каналы)</div><div class="kpi-value">{combined_total}</div></div>
      <div class="kpi-tile"><div class="kpi-label">Общая выручка</div><div class="kpi-value green">{combined_revenue:,.0f} ₽</div></div>
    </div>
    <div class="stats-grid">
      {_card("Заказы через сайт", site_stats)}
      {_card("Заказы через бота IrMa", bot_stats)}
      {_card("Заказы из ChatMarket (MAX)", max_stats)}
    </div>
    """
    return HTMLResponse(_page(body, "stats", site_new, bot_new))


# ---------------------------------------------------------------- Content hub

@router.get("/content", response_class=HTMLResponse)
async def admin_content(section: str = "news", db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    site_new, bot_new = await _nav_counts(db)
    section = section if section in ("news", "promos", "training") else "news"

    subtabs = "".join(
        f'<a href="/admin/content?section={key}" class="{"active" if key == section else ""}">{label}</a>'
        for key, label in [("news", "Новости"), ("promos", "Акции"), ("training", "Обучение")]
    )

    if section == "news":
        news_items = (await db.execute(select(News).order_by(News.published_at.desc()).limit(100))).scalars().all()
        rows = "".join(
            f"""<tr>
              <td>{item.published_at:%d.%m.%Y}</td>
              <td>{item.tag}</td>
              <td>{item.title}</td>
              <td>{'бот' if item.mid else 'вручную'}</td>
              <td class="row-actions">
                <a class="btn-edit" href="/admin/news/{item.id}/edit">Изменить</a>
                <form method="post" action="/admin/news/{item.id}/delete" onsubmit="return confirm('Удалить эту новость?')">
                  <button type="submit" style="background:#d98a9a">Удалить</button>
                </form>
              </td>
            </tr>"""
            for item in news_items
        ) or '<tr><td colspan="5" class="empty">Новостей пока нет</td></tr>'
        section_body = f"""
        <h2>Новости ({len(news_items)}) <a class="add-link" href="/admin/news/new">+ Добавить</a></h2>
        <table>
          <tr><th>Дата</th><th>Тег</th><th>Заголовок</th><th>Источник</th><th></th></tr>
          {rows}
        </table>
        <p class="empty">Новости из канала MAX публикуются автоматически (с задержкой {settings.news_publish_delay_minutes} мин) — здесь можно поправить или удалить пост.</p>
        """
    elif section == "promos":
        promo_items = (await db.execute(select(Promo).order_by(Promo.created_at.asc()))).scalars().all()
        rows = "".join(
            f"""<tr>
              <td>{item.icon}</td>
              <td>{item.badge}</td>
              <td>{item.title}</td>
              <td class="row-actions">
                <a class="btn-edit" href="/admin/promos/{item.id}/edit">Изменить</a>
                <form method="post" action="/admin/promos/{item.id}/delete" onsubmit="return confirm('Удалить эту акцию?')">
                  <button type="submit" style="background:#d98a9a">Удалить</button>
                </form>
              </td>
            </tr>"""
            for item in promo_items
        ) or '<tr><td colspan="4" class="empty">Акций пока нет</td></tr>'
        section_body = f"""
        <h2>Акции ({len(promo_items)}) <a class="add-link" href="/admin/promos/new">+ Добавить</a></h2>
        <table>
          <tr><th>Иконка</th><th>Плашка</th><th>Заголовок</th><th></th></tr>
          {rows}
        </table>
        <p class="empty">Показываются на главной (первые 5) и на странице «Акции» (все).</p>
        """
    else:
        lessons = (await db.execute(select(TrainingLesson).order_by(TrainingLesson.created_at.desc()))).scalars().all()
        rows = "".join(
            f"""<tr>
              <td>{lesson.title}</td>
              <td>{lesson.price_label or '—'}</td>
              <td><a href="/training-item.html?slug={lesson.slug}" target="_blank">{lesson.slug}</a></td>
              <td class="row-actions">
                <a class="btn-edit" href="/admin/training-lessons/{lesson.id}/edit">Изменить</a>
                <form method="post" action="/admin/training-lessons/{lesson.id}/delete" onsubmit="return confirm('Удалить этот урок?')">
                  <button type="submit" style="background:#d98a9a">Удалить</button>
                </form>
              </td>
            </tr>"""
            for lesson in lessons
        ) or '<tr><td colspan="4" class="empty">Уроков пока нет</td></tr>'
        section_body = f"""
        <h2>Уроки обучения ({len(lessons)}) <a class="add-link" href="/admin/training-lessons/new">+ Добавить</a></h2>
        <table>
          <tr><th>Заголовок</th><th>Цена</th><th>Ссылка</th><th></th></tr>
          {rows}
        </table>
        <p class="empty">9 уже существующих уроков (мотоцикл, пицца и т.д.) — отдельные страницы, здесь не редактируются. Уроки, добавленные здесь, попадают в каталог на странице «Обучение» отдельным блоком.</p>
        """

    body = f'<div class="content-subtabs">{subtabs}</div>{section_body}'
    return HTMLResponse(_page(body, "content", site_new, bot_new))


# ---------------------------------------------------------------- News

def _news_form(action: str, item: News | None = None) -> str:
    img_preview = f'<img class="current-img" src="{item.image_path}">' if item and item.image_path else ""
    return f"""
    <h2>{"Изменить новость" if item else "Добавить новость"}</h2>
    <form class="edit-form" method="post" action="{action}" enctype="multipart/form-data">
      <label>Тег</label>
      <input type="text" name="tag" value="{item.tag if item else 'Новости'}">

      <label>Заголовок</label>
      <input type="text" name="title" required value="{item.title if item else ''}">

      <label>Текст</label>
      <textarea name="text">{item.text if item else ''}</textarea>

      <label>Фото {"(оставьте пустым, чтобы не менять)" if item else "(необязательно)"}</label>
      <input type="file" name="image" accept="image/*">
      {img_preview}

      <button type="submit">Сохранить</button>
    </form>
    """


@router.get("/news/new", response_class=HTMLResponse)
async def news_new_form(_: str = Depends(require_admin)):
    return HTMLResponse(_page(_news_form("/admin/news/new"), "content"))


@router.post("/news/new")
async def news_create(
    tag: str = Form("Новости"),
    title: str = Form(...),
    text: str = Form(""),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    image_path = await _save_upload(image, "news")
    db.add(
        News(
            tag=tag,
            title=title,
            text=text,
            image_path=image_path,
            published_at=datetime.utcnow(),
        )
    )
    await db.commit()
    return RedirectResponse(url="/admin/content?section=news", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/news/{news_id}/edit", response_class=HTMLResponse)
async def news_edit_form(news_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    item = await db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return HTMLResponse(_page(_news_form(f"/admin/news/{news_id}/edit", item), "content"))


@router.post("/news/{news_id}/edit")
async def news_update(
    news_id: int,
    tag: str = Form("Новости"),
    title: str = Form(...),
    text: str = Form(""),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    item.tag = tag
    item.title = title
    item.text = text
    new_image = await _save_upload(image, "news")
    if new_image:
        _delete_file(item.image_path)
        item.image_path = new_image
    await db.commit()
    return RedirectResponse(url="/admin/content?section=news", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/news/{news_id}/delete")
async def delete_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    _delete_file(item.image_path)
    _delete_file(item.video_path)
    await db.delete(item)
    await db.commit()
    return RedirectResponse(url="/admin/content?section=news", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- Promos

def _promo_form(action: str, item: Promo | None = None) -> str:
    return f"""
    <h2>{"Изменить акцию" if item else "Добавить акцию"}</h2>
    <form class="edit-form" method="post" action="{action}">
      <label>Иконка (эмодзи)</label>
      <input type="text" name="icon" value="{item.icon if item else '🎁'}">

      <label>Плашка (например «Каждый день»)</label>
      <input type="text" name="badge" value="{item.badge if item else ''}">

      <label>Заголовок</label>
      <input type="text" name="title" required value="{item.title if item else ''}">

      <label>Текст</label>
      <textarea name="text">{item.text if item else ''}</textarea>

      <button type="submit">Сохранить</button>
    </form>
    """


@router.get("/promos/new", response_class=HTMLResponse)
async def promo_new_form(_: str = Depends(require_admin)):
    return HTMLResponse(_page(_promo_form("/admin/promos/new"), "content"))


@router.post("/promos/new")
async def promo_create(
    icon: str = Form("🎁"),
    badge: str = Form(""),
    title: str = Form(...),
    text: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    db.add(Promo(icon=icon, badge=badge, title=title, text=text))
    await db.commit()
    return RedirectResponse(url="/admin/content?section=promos", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/promos/{promo_id}/edit", response_class=HTMLResponse)
async def promo_edit_form(promo_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    item = await db.get(Promo, promo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    return HTMLResponse(_page(_promo_form(f"/admin/promos/{promo_id}/edit", item), "content"))


@router.post("/promos/{promo_id}/edit")
async def promo_update(
    promo_id: int,
    icon: str = Form("🎁"),
    badge: str = Form(""),
    title: str = Form(...),
    text: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(Promo, promo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    item.icon = icon
    item.badge = badge
    item.title = title
    item.text = text
    await db.commit()
    return RedirectResponse(url="/admin/content?section=promos", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/promos/{promo_id}/delete")
async def promo_delete(
    promo_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(Promo, promo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    await db.delete(item)
    await db.commit()
    return RedirectResponse(url="/admin/content?section=promos", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- Training lessons

def _training_form(action: str, item: TrainingLesson | None = None) -> str:
    img_preview = f'<img class="current-img" src="{item.image_path}">' if item and item.image_path else ""
    return f"""
    <h2>{"Изменить урок" if item else "Добавить урок"}</h2>
    <form class="edit-form" method="post" action="{action}" enctype="multipart/form-data">
      <label>Тег</label>
      <input type="text" name="tag" value="{item.tag if item else 'Видеоурок · Новинка'}">

      <label>Заголовок</label>
      <input type="text" name="title" required value="{item.title if item else ''}">

      <label>Подзаголовок / короткое описание</label>
      <textarea name="subtitle">{item.subtitle if item else ''}</textarea>

      <label>Цена (например «3000 ₽», оставьте пустым, если не указывать)</label>
      <input type="text" name="price_label" value="{item.price_label or '' if item else ''}">

      <label>Фото {"(оставьте пустым, чтобы не менять)" if item else ""}</label>
      <input type="file" name="image" accept="image/*">
      {img_preview}

      <label>Заголовок первого списка (например «Что вы узнаете на уроке»)</label>
      <input type="text" name="section1_heading" value="{item.section1_heading or '' if item else 'Что вы получите'}">
      <label>Пункты списка — по одному на строку</label>
      <textarea name="section1_items">{item.section1_items if item else ''}</textarea>

      <label>Заголовок второго списка (необязательно)</label>
      <input type="text" name="section2_heading" value="{item.section2_heading or '' if item else ''}">
      <label>Пункты второго списка — по одному на строку</label>
      <textarea name="section2_items">{item.section2_items if item else ''}</textarea>

      <label>Подарок / примечание (необязательно)</label>
      <textarea name="bonus_note">{item.bonus_note or '' if item else ''}</textarea>
      <p class="hint">Урок появится в каталоге на странице «Обучение» и по ссылке /training-item.html?slug=...</p>

      <button type="submit">Сохранить</button>
    </form>
    """


@router.get("/training-lessons/new", response_class=HTMLResponse)
async def training_new_form(_: str = Depends(require_admin)):
    return HTMLResponse(_page(_training_form("/admin/training-lessons/new"), "content"))


@router.post("/training-lessons/new")
async def training_create(
    tag: str = Form("Видеоурок · Новинка"),
    title: str = Form(...),
    subtitle: str = Form(""),
    price_label: str = Form(""),
    section1_heading: str = Form(""),
    section1_items: str = Form(""),
    section2_heading: str = Form(""),
    section2_items: str = Form(""),
    bonus_note: str = Form(""),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    image_path = await _save_upload(image, "training")
    db.add(
        TrainingLesson(
            slug=_slugify(title),
            tag=tag,
            title=title,
            subtitle=subtitle,
            price_label=price_label or None,
            image_path=image_path,
            section1_heading=section1_heading or None,
            section1_items=section1_items,
            section2_heading=section2_heading or None,
            section2_items=section2_items,
            bonus_note=bonus_note or None,
        )
    )
    await db.commit()
    return RedirectResponse(url="/admin/content?section=training", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/training-lessons/{lesson_id}/edit", response_class=HTMLResponse)
async def training_edit_form(lesson_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    item = await db.get(TrainingLesson, lesson_id)
    if not item:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return HTMLResponse(_page(_training_form(f"/admin/training-lessons/{lesson_id}/edit", item), "content"))


@router.post("/training-lessons/{lesson_id}/edit")
async def training_update(
    lesson_id: int,
    tag: str = Form("Видеоурок · Новинка"),
    title: str = Form(...),
    subtitle: str = Form(""),
    price_label: str = Form(""),
    section1_heading: str = Form(""),
    section1_items: str = Form(""),
    section2_heading: str = Form(""),
    section2_items: str = Form(""),
    bonus_note: str = Form(""),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(TrainingLesson, lesson_id)
    if not item:
        raise HTTPException(status_code=404, detail="Урок не найден")
    item.tag = tag
    item.title = title
    item.subtitle = subtitle
    item.price_label = price_label or None
    item.section1_heading = section1_heading or None
    item.section1_items = section1_items
    item.section2_heading = section2_heading or None
    item.section2_items = section2_items
    item.bonus_note = bonus_note or None
    new_image = await _save_upload(image, "training")
    if new_image:
        _delete_file(item.image_path)
        item.image_path = new_image
    await db.commit()
    return RedirectResponse(url="/admin/content?section=training", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/training-lessons/{lesson_id}/delete")
async def training_delete(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(TrainingLesson, lesson_id)
    if not item:
        raise HTTPException(status_code=404, detail="Урок не найден")
    _delete_file(item.image_path)
    await db.delete(item)
    await db.commit()
    return RedirectResponse(url="/admin/content?section=training", status_code=status.HTTP_303_SEE_OTHER)
