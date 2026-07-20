---
name: admin-panel
description: Use when working on the IrMa admin panel's structure, navigation, orders (site cart or MAX-bot), leads, the dashboard chart, or order statistics — anything under `/admin` that isn't content management (News/Акции/Training-lesson CRUD, which is the separate `max-news-pipeline` skill's "Контент" tab). Triggers on "админка", "/admin", "дашборд", "заказы через сайт", "заказы через приложение", "статистика по заказам", "site_orders", "bot orders", "вкладка", "badge", "счётчик новых".
---

# IrMa admin panel: tabs, orders, dashboard, stats

All in `app/api/admin.py` (plain f-string HTML, no Jinja, HTTP Basic auth
via `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`, `require_admin` dependency on
every route). The panel is a **tabbed app** — every page shares the same
`_page(body, active, site_new, bot_new)` shell, which renders the top
`.admin-tabs` nav via `_nav_html()`. `NAV_ITEMS` at the top of the file is
the single source of truth for the six tabs; add a new tab there and it
shows up in the nav automatically.

## The six tabs

1. **Главная** (`GET /admin`) — KPI tiles (orders today, 7-day revenue, new
   counts per channel, new leads) + a Chart.js line chart of daily
   site-vs-app order counts for the last 30 days + an editable "Последние
   заявки" table (all leads, not just training ones — this is the *only*
   place a generic, non-training lead's status can be changed; there's no
   dedicated leads tab by design, see "Обучение" below for why).
2. **Заказы через сайт** (`GET/POST /admin/site-orders`) — `SiteOrder` rows
   (cart checkouts from `landing/menu.html`, persisted since 2026-07-20 —
   before that, `POST /order/landing` only sent a MAX notification and
   never touched the DB). Status dropdown (`new/processing/done`) +
   delete per row.
3. **Заказы через приложение** (`GET/POST /admin/bot-orders`) — `Order` rows
   (checkout inside the MAX bot conversation), joined to `User`. Status
   dropdown (`created/completed/cancelled`); no delete here (bot orders are
   treated as a real transaction log, unlike site-order cart junk).
4. **Обучение** (`GET /admin/training`) — `Lead` rows filtered to
   `source LIKE 'training-%'` (the lesson sign-up forms on
   `training-*.html`/`training-item.html`). Status dropdown now includes a
   4th value, `paid`, on top of the original `new/contacted/done` — this is
   literally "оплаченные услуги": there's no payment gateway, so `paid` is
   the admin manually confirming money changed hands. Reuses the generic
   `POST /admin/leads/{id}/status` endpoint (not scoped to training — same
   endpoint the dashboard's lead table posts to).
5. **Статистика** (`GET /admin/stats`) — per-channel (site/app) totals,
   revenue, average order value, status breakdown, and 7-/30-day rollups,
   built by `_stats_block()` in Python (not SQL aggregates — order volumes
   are small enough that fetching all rows and summing in Python is simpler
   and avoids DB-specific date-bucketing code).
6. **Контент** — belongs to the `max-news-pipeline` skill, not this one.

## Nav badges

`_nav_counts(db)` returns `(site_new, bot_new)` — `count(SiteOrder where
status='new')` and `count(Order where status='created')`. Every route calls
this once and passes it into `_page()`; there's no caching, it's a live
count on every page load. The badge is a small red pill next to the tab
label (`.tab-badge` CSS, inverts to white-on-accent when the tab is active)
and disappears (0 == no badge rendered) once every order in that channel has
been moved off its initial status. **This is the actual mechanism behind
"когда есть новые заказы — горит циферка"** — it is driven purely by
`status`, not by a separate "viewed" flag, so changing an order's status via
its dropdown is what clears the badge, not just looking at the list.

## Dashboard chart

Chart.js loaded from `cdn.jsdelivr.net` (fine — this is a normal
server-rendered page, not a sandboxed Artifact, external `<script src>` is
allowed). Data is computed in Python (`admin_dashboard()` in `admin.py`):
last 30 calendar days as dict keys, `SiteOrder`/`Order` rows bucketed by
`.created_at.date()`, then `json.dumps()`'d straight into the inline
`<script>` that constructs the `Chart(...)`. Two-series line chart (site vs
app), zero-filled for days with no orders — don't switch this to a raw SQL
`GROUP BY date_trunc(...)` unless volume actually becomes a problem; the
Python approach is simpler and this is a small cafe, not a query-performance
case.

## Adding a 7th tab or a new order/lead view

1. Add `(key, href, label)` to `NAV_ITEMS`.
2. Write the `GET` handler, call `_nav_counts(db)` at the top, pass
   `active=key` to `_page()`.
3. If it needs a badge, extend `_nav_counts()`'s return and `_nav_html()`'s
   `badges` dict — both are small, edit them together.
4. Follow the existing status-dropdown-plus-save-button `<form>` pattern for
   any per-row mutable state (see `site-orders`/`bot-orders`/leads) rather
   than inventing a new interaction style.

## Testing changes here

Same discipline as the content-CRUD skill: this environment mangles
Cyrillic through `curl -F`/`curl -d` (git-bash codepage issue) — use Python
`httpx` for anything with non-ASCII form data, and dump JSON responses to a
file instead of `print()`-ing them (Windows console codepage can't encode
`₽`, emoji, etc. either). For a synthetic site order:

```bash
cat > payload.json <<'EOF'
{"phone": "+79991234567", "items": [{"name": "ТЕСТ (удалить)", "price": 500, "qty": 1}]}
EOF
curl -sS -X POST "https://irma-cafe.ru/order/landing" -H "Content-Type: application/json" --data @payload.json
```

Then check it landed (`GET /admin/site-orders` with Basic auth, or grep the
saved HTML for the test marker), confirm the nav badge incremented, exercise
the status-update / delete forms the same way as content CRUD (`POST` with
`httpx`, reading admin creds from `.env`), and clean up — `POST
/admin/site-orders/{id}/delete` exists specifically so test/junk orders
don't have to be left lying around in production.
