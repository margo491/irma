import secrets
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.lead import Lead
from app.models.order import Order
from app.models.user import User
from app.models.news import News
from app.models.training_lesson import TrainingLesson

router = APIRouter()
security = HTTPBasic()

STATUSES = ["new", "contacted", "done"]

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


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


def _page(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>IrMa — Админ-панель</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; background: #fdf6f7; color: #3a3a3a; margin: 0; padding: 32px; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  h1 a {{ font-size: .8rem; color: #7a7a7a; text-decoration: none; font-weight: 400; margin-left: 12px; }}
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
</style>
</head>
<body>
<h1>IrMa — Админ-панель <a href="/admin">← ко всем разделам</a></h1>
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

    news_result = await db.execute(select(News).order_by(News.published_at.desc()).limit(100))
    news_items = news_result.scalars().all()

    lessons_result = await db.execute(select(TrainingLesson).order_by(TrainingLesson.created_at.desc()))
    lessons = lessons_result.scalars().all()

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

    news_rows = "".join(
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

    lessons_rows = "".join(
        f"""<tr>
          <td>{lesson.title}</td>
          <td>{lesson.price_label or '—'}</td>
          <td><a href="/training-item.html?slug={lesson.slug}" target="_blank">{lesson.slug}</a></td>
          <td class="row-actions">
            <a class="btn-edit" href="/admin/training/{lesson.id}/edit">Изменить</a>
            <form method="post" action="/admin/training/{lesson.id}/delete" onsubmit="return confirm('Удалить этот урок?')">
              <button type="submit" style="background:#d98a9a">Удалить</button>
            </form>
          </td>
        </tr>"""
        for lesson in lessons
    ) or '<tr><td colspan="4" class="empty">Уроков пока нет</td></tr>'

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

    <h2>Новости ({len(news_items)}) <a class="add-link" href="/admin/news/new">+ Добавить</a></h2>
    <table>
      <tr><th>Дата</th><th>Тег</th><th>Заголовок</th><th>Источник</th><th></th></tr>
      {news_rows}
    </table>
    <p class="empty">Новости из канала MAX публикуются автоматически (с задержкой {settings.news_publish_delay_minutes} мин) — здесь можно поправить или удалить пост.</p>

    <h2>Уроки обучения ({len(lessons)}) <a class="add-link" href="/admin/training/new">+ Добавить</a></h2>
    <table>
      <tr><th>Заголовок</th><th>Цена</th><th>Ссылка</th><th></th></tr>
      {lessons_rows}
    </table>
    <p class="empty">Уроки, добавленные здесь, попадают в общий каталог на странице «Обучение» отдельным блоком.</p>
    """
    return HTMLResponse(_page(body))


# ---------------------------------------------------------------- Leads

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
    return HTMLResponse(_page(_news_form("/admin/news/new")))


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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/news/{news_id}/edit", response_class=HTMLResponse)
async def news_edit_form(news_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    item = await db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return HTMLResponse(_page(_news_form(f"/admin/news/{news_id}/edit", item)))


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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


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


@router.get("/training/new", response_class=HTMLResponse)
async def training_new_form(_: str = Depends(require_admin)):
    return HTMLResponse(_page(_training_form("/admin/training/new")))


@router.post("/training/new")
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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/training/{lesson_id}/edit", response_class=HTMLResponse)
async def training_edit_form(lesson_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    item = await db.get(TrainingLesson, lesson_id)
    if not item:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return HTMLResponse(_page(_training_form(f"/admin/training/{lesson_id}/edit", item)))


@router.post("/training/{lesson_id}/edit")
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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/training/{lesson_id}/delete")
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
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
