---
name: max-news-pipeline
description: Use when working with the MAX-messenger channel integration for the IrMa site, or its admin-managed content (News/Blog/Training lessons) — reading channel posts via the news-bot API, debugging/testing the auto-publish news webhook (images or video), the 5-minute publish delay, moderating or CRUD-editing news/blog/training content in the admin panel, fixing a detail page, or building a curated landing page (like a hand-built training lesson) from a channel post. Triggers on "MAX", "канал", "новости", "вебхук", "новостной бот", "автопубликация", "news-item.html", "blog-item.html", "training-item.html", "training-*.html", "админка", "id312332413602_3_bot", "irma-cafe.ru".
---

# MAX channel → IrMa site publishing, and admin-managed content

Three related but distinct systems live here:

1. An **automatic** pipeline — every MAX channel post becomes a news card,
   no review, just a 5-minute delay before it's public (see below).
2. A **generic admin CRUD** system for News, Blog posts, and Training
   lessons — `/admin` has add/edit/delete forms for all three.
3. A **manual/curated** one-off workflow — hand-build a rich landing page
   like `training-cake-motorcycle.html` from a specific flyer-style channel
   post, when it needs a layout the generic CRUD template can't express.

Pick the right one: don't hand-build a page for something the auto-pipeline
or the admin CRUD already covers; don't expect the generic CRUD template to
reproduce a bespoke hand-built page's exact layout; don't expect the
auto-pipeline to produce a priced, structured lesson page from a plain post.

## Architecture

- **Source**: MAX channel "Семейное кафе «IrMa by Marinich»", `chat_id = -71665082178843`.
- **Reader bot**: `id312332413602_3_bot` ("Ирма Новости"), member of the channel.
  Token lives in `.env` as `token_bot_max` — **do not confuse with `MAX_TOKEN`**,
  which is the customer-order bot's token used by `app/bot/handlers.py` /
  `app/bot/max_adapter.py`.
- **Push subscription**: already registered with MAX Bot API, pointed at
  `https://irma-cafe.ru/webhook/news`, `update_types: [bot_added,
  bot_removed, message_created]`. Don't re-register unless it's gone (check
  first, see below).
- **Webhook handler**: `app/bot/news_webhook.py`. On `message_created` for the
  channel's `chat_id`, it derives `title` = first non-empty line of the post
  text, `text` = the rest, downloads the first `image`-type attachment (falling
  back to a video's `thumbnail.url` as the card image if there's no photo),
  **and** downloads the first `video`-type attachment's actual file (not just
  its thumbnail) into `video_path` — inserts a `News` row that's **idempotent
  on the MAX message id (`mid`)**, so redelivery never duplicates. If the row
  already exists but is missing `video_path`, redelivery **backfills** it
  instead of no-opping — see "Backfilling a published post" below.
- **Storage**: `news` table in Postgres (`app/models/news.py`), images/videos
  in a dedicated Docker volume `news_uploads` mounted at `/app/uploads`,
  served at `/uploads/...`. `landing/` is baked into the image at *build* time
  (see `Dockerfile`) — it is **not** persistent, so anything the running app
  writes must go in `uploads/`, never under `landing/`.
- **Publish delay**: `GET /news/` and `GET /news/{id}` only return rows where
  `created_at <= now() - NEWS_PUBLISH_DELAY_MINUTES` (default 5, in
  `app/config.py`/`.env`). The row is written to the DB immediately on
  webhook receipt — the delay is a **read-side filter**, not a queued job —
  so `/admin` (which queries the table directly, not through this filter)
  always shows a just-arrived post right away. This is the window for
  catching and deleting a bad auto-post before the public sees it.
- **Read API** (`app/api/news.py`): `GET /news/?limit=N` (list, newest first)
  and `GET /news/{id}` (single item, used by the detail page).
- **Frontend**: `landing/index.html` (top 5) and `landing/news.html` (all)
  render cards client-side via `fetch('/news/...')`; each card links to
  `landing/news-item.html?id=<id>`, which fetches `GET /news/{id}` and renders
  the full post — a `<video controls poster="{image_path}">` if `video_path`
  is set, otherwise the image at full size (`object-fit: contain`, **not**
  `cover` — a fixed `max-height` + `cover` crops portrait photos hard, that's
  a recurring complaint, don't reintroduce it). All three pages build
  `innerHTML` with `escapeHtml()` in plain JS, no server templating — the post
  text/title is untrusted external content, never remove the escaping.
  "Новости" is in the shared nav/footer on every landing page.
- **Moderation**: `/admin` (HTTP Basic — `ADMIN_EMAIL`/`ADMIN_PASSWORD` in
  `.env`) has a "Новости" section with add/edit/delete per row (delete also
  removes the downloaded image/video files). Since bot-published news has no
  pre-review step, edit/delete there is the way to fix or take down a bad
  auto-post — the 5-minute delay just buys time to notice it first.
- **Deploy**: push to `master` on **`origin`** (GitHub) →
  `.github/workflows/deploy.yml` SSHes into the VPS, `git pull`,
  rebuilds/restarts the `app` container via `docker compose`, which runs
  `alembic upgrade head` before `uvicorn` starts. Prod is reachable at both
  `https://irma-cafe.ru` (the real domain, use this one when talking to the
  user) and `https://irma.bot-ktu.online` (same server/IP, same deploy — pick
  either for `curl`/testing, they're interchangeable).
- There's also a second remote, `local`
  (`http://192.168.31.250:3002/margo491/irma.git`, a self-hosted
  Gitea/Forgejo on the LAN) — it's a plain mirror the user pushes to
  separately on request. **Pushing to `local` does not deploy anything**; only
  a push to `origin master` triggers the Actions workflow above.

## Admin CRUD: News, Blog, Training lessons

`app/api/admin.py` renders everything as plain f-string HTML (no Jinja) —
stay consistent with that style rather than introducing a templating engine
for one section. All three content types follow the same shape:

- List + "+ Добавить" link on `/admin` (built in `admin_home`).
- `GET /admin/{type}/new` → blank form; `POST /admin/{type}/new` → insert.
- `GET /admin/{type}/{id}/edit` → pre-filled form; `POST .../edit` → update.
- `POST /admin/{type}/{id}/delete` → remove row + any uploaded files.
- Image fields are a `<input type=file>` (`UploadFile`), saved via the shared
  `_save_upload(file, subdir)` helper into `uploads/<subdir>/` (persistent
  volume, same one the MAX pipeline uses) — editing without picking a new
  file leaves the existing image alone; picking one deletes the old file via
  `_delete_file()` first.

**Blog** (`app/models/blog_post.py`, `app/api/blog.py` at prefix
`/blog-posts`, `landing/blog.html` + `landing/blog-item.html?id=`): didn't
exist before — `landing/blog.html` used to be six hardcoded cards linking to
`#`. Those six were seeded into `blog_posts` by the migration so the page
didn't go blank; the hand-written "featured post" hero block at the top of
`blog.html` is untouched/still static (it was never part of the card grid).
No publish delay here — this is manually-authored content, not bot-fed.

**Training lessons** (`app/models/training_lesson.py`,
`app/api/training_lessons.py` at prefix `/training-lessons`,
`landing/training-item.html?slug=`): a **parallel, additive** system, not a
replacement. The 9 existing `landing/training-*.html` pages (motorcycle,
pizza, capybara, etc.) are hand-built with genuinely different layouts each
and are **not** migrated into this table — don't move them. `landing/training.html`
fetches `/training-lessons/` and **appends** those cards after the existing
static ones in the same `.lessons-grid` via `insertAdjacentHTML`; it does not
replace the grid contents (unlike news.html/blog.html, which do replace
theirs — training.html's static cards keep their hand-tuned copy). Each
lesson row has two *optional* bullet-list sections
(`section1_heading`/`section1_items`, `section2_heading`/`section2_items`,
newline-separated in a textarea) plus `price_label` and `bonus_note`, which
covers the range seen across the existing hand-built pages (one list, two
lists, priced, unpriced, with/without a gift note) without needing a fully
dynamic repeater UI. `slug` is auto-generated from the title via a small
Cyrillic transliteration table in `admin.py` (`_slugify`) plus a random
suffix — never ask the admin to type one.

**Testing admin forms — encoding gotcha**: this Windows/git-bash environment
mangles Cyrillic passed through `curl -F field=значение` (the shell's
codepage clobbers it before curl ever sees UTF-8 bytes) — you'll get
mojibake in the DB, not a real bug. Don't debug the server for this. Test
multipart form submits with Python `httpx` instead, reading creds from
`.env` the usual way, and write output to a file instead of `print()`-ing
Cyrillic (the Windows console codepage chokes on it too, e.g. on `₽`):

```bash
python -c "
import httpx
user = pw = None
with open('.env', encoding='utf-8') as f:
    for line in f:
        if line.startswith('ADMIN_EMAIL='): user = line.strip().split('=',1)[1]
        if line.startswith('ADMIN_PASSWORD='): pw = line.strip().split('=',1)[1]
data = {'tag': 'Тест', 'title': 'ТЕСТ (удалить)', 'text': '...'}
r = httpx.post('https://irma-cafe.ru/admin/blog/new', data=data, auth=(user, pw), follow_redirects=False, timeout=20)
print('status:', r.status_code)
"
curl -sS "https://irma-cafe.ru/blog-posts/?limit=1" -o out.json   # inspect via file, not console
```

Same idempotent-cleanup discipline as the webhook tests: create, verify via
the read API / a Playwright screenshot, delete via the admin endpoint,
confirm it's gone — never leave test rows live.

## Reading the MAX Bot API

Always read the token from `.env` inside the command — **never paste the
literal token into a Bash call**, it gets flagged as a leaked credential:

```bash
TOKEN=$(grep -m1 '^token_bot_max=' .env | cut -d= -f2-)
curl -sS "https://botapi.max.ru/me" -H "Authorization: $TOKEN"
curl -sS "https://botapi.max.ru/chats/-71665082178843" -H "Authorization: $TOKEN"
curl -sS "https://botapi.max.ru/messages?chat_id=-71665082178843&count=20" -H "Authorization: $TOKEN"
curl -sS "https://botapi.max.ru/subscriptions" -H "Authorization: $TOKEN"
```

`GET /messages` is how you find a specific past post (search the JSON for
matching text) when someone links you a `max.ru/c/<chat_id>/<short-id>` URL —
that short-id isn't independently fetchable, so pull recent history and match
on text/timestamp instead.

**MAX image/video CDN URLs (`i.oneme.ru`, `*.okcdn.ru`) are signed and
expire** (they carry an `expires=` epoch param) — never store them directly;
download the bytes immediately. Photo attachments are actually **WebP**
regardless of what the URL looks like — detect the real type from the
response `Content-Type` header when downloading, don't trust a `.jpg` guess.

## Debugging / testing the webhook

Raw payloads are buffered **in memory** (last 20) for inspection — this
buffer is process-local and gets **wiped on every redeploy/restart**, so it's
only useful for something that happened since the last deploy:

```bash
curl -sS "https://irma-cafe.ru/webhook/news/debug"
```

For anything older, don't rely on the buffer — refetch the original message
by `mid`/text from `GET /messages` (above) instead, which always reflects
live channel history regardless of when the app last restarted.

To test the full ingestion path end-to-end without waiting for a real post,
POST a synthetic `message_created` event and verify + clean up afterward.
Use a real, already-hosted URL from the site itself for the attachment (not
an external one) — a static image for the image path, or an existing
`/uploads/news/*.mp4` for the video path:

```bash
NOW_MS=$(( $(date +%s) * 1000 ))
MID="test.e2e.${NOW_MS}"
cat > payload.json <<EOF
{
  "update_type": "message_created",
  "message": {
    "recipient": {"chat_id": -71665082178843, "chat_type": "channel"},
    "timestamp": ${NOW_MS},
    "body": {
      "mid": "${MID}",
      "text": "ТЕСТ (можно удалить)\n\nПроверка вебхука.",
      "attachments": [{"type": "image", "payload": {"url": "https://irma-cafe.ru/logo.jpg"}}]
    }
  }
}
EOF
curl -sS -X POST "https://irma-cafe.ru/webhook/news" -H "Content-Type: application/json" --data @payload.json
curl -sS "https://irma-cafe.ru/news/?limit=1"   # confirm it landed, check image_path/video_path
# resend the same payload — total count must NOT increase (idempotency check)
```

Clean up the test row via the admin delete endpoint (reads creds from `.env`,
never inline them):

```bash
USER=$(grep -m1 '^ADMIN_EMAIL=' .env | cut -d= -f2-)
PASS=$(grep -m1 '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
curl -sS -u "${USER}:${PASS}" -X POST "https://irma-cafe.ru/admin/news/<id>/delete"
```

## Backfilling a published post (missing video, wrong media, etc.)

The webhook is safe to redeliver: if a `News` row for that `mid` already
exists, it currently only fills in `video_path` if that's still empty
(see `_handle_event` in `news_webhook.py`) — everything else on an existing
row is left alone. This is how the "Витрина" video posts that predated video
support got fixed after the fact, and it's the general pattern for any future
"we shipped a fix, now backfill what's already live" situation:

1. Find the row's `mid` — either from `/webhook/news/debug` if it's recent
   enough, or by matching title/timestamp against `GET /messages`.
2. Re-fetch that exact message from `GET /messages` (attachment CDN URLs
   expire, so grab a *fresh* copy, don't reuse an old captured payload).
3. Wrap it in the same `message_created` envelope shape as above, using the
   **real** `mid`, and POST it to `/webhook/news`.
4. `GET /news/{id}` to confirm the field actually filled in.

If a future fix needs to *overwrite* a field that's already set (not just
fill in something empty), the idempotency check in `_handle_event` will need
a similar carve-out added for that field — it doesn't blanket-update existing
rows on redelivery by design (that would let a redelivered/duplicated MAX
event clobber manual admin edits).

## Deploying a change

Confirm with the user before pushing — `master` auto-deploys to the live
site. After pushing:

```bash
git push origin master
RUN_ID=$(gh run list --branch master --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

If `deploy`+`smoke` both go green, `alembic upgrade head` succeeded too (a
failed migration crash-loops the container and the health check never turns
green) — that's sufficient migration verification; you generally can't test
migrations against local Postgres from this sandbox (see below).

## Local environment quirks (don't waste time on these)

- This machine's local Postgres (`127.0.0.1:5432`, from `.env`
  `DATABASE_URL`) is **not reliably reachable from the sandboxed Bash/Python
  tools** — `psycopg2`/alembic fails with a `UnicodeDecodeError` (likely the
  Cyrillic `C:\srv\Ирма` path), and raw `asyncpg` connections reset mid-handshake.
  Don't debug this — it's a sandbox limitation, not a code bug. Validate
  locally with `python -m py_compile` and `python -c "import app.main"`
  (install `python-multipart` in `.venv` if missing) instead, then verify for
  real against production after deploying.
- No Docker CLI available locally either — can't `docker compose up` to test
  the full stack; same story, verify on prod post-deploy.

## Building a bespoke curated page instead (beyond what admin CRUD covers)

Some channel posts (flyer-style announcements with a price and curriculum)
deserve a full page like `landing/training-cake-motorcycle.html` — with
layout the generic training-lesson CRUD template can't express (e.g. more
than two bullet sections, a highlighted "included" badge, custom copy
structure) — not just a news card or a CRUD-generated `training-item.html`
entry. If the generic two-section template (above) is good enough, prefer
that — it's zero-code and editable without a deploy. Reach for a fully
hand-built page only when it isn't. When you do:

1. Find the post via `GET /messages` (above), download+inspect every
   attached photo — the "product photo" is often actually a marketing flyer
   with the price and program already laid out as text in the image; crop
   and zoom with Pillow to read it rather than guessing/inventing numbers.
2. Check `landing/training.html` and existing `landing/training-*.html`
   pages first — never republish an already-live lesson.
3. Copy an existing `training-*.html` file as the template and keep its CSS
   byte-for-byte; only change the content block and the `source` field in the
   lead-form fetch.
4. Add a matching card to the catalog grid in `landing/training.html`.
5. Save the flyer photo under `landing/training/<slug>.jpg` (these ARE baked
   into the image at build time, unlike `uploads/` — that's fine, they're
   static content committed to git, not runtime-generated).
6. Verify locally before deploying: serve `landing/` with
   `python -m http.server`, screenshot with Playwright (`npx playwright
   install chromium` once, then a small script), check no console/network
   errors and that the catalog link navigates correctly.
