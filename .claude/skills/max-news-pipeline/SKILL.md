---
name: max-news-pipeline
description: Use when working with the MAX-messenger channel integration for the IrMa site — reading channel posts via the news-bot API, debugging/testing the auto-publish news webhook, moderating auto-published news in the admin panel, or building a curated landing page (like a training lesson) from a channel post. Triggers on "MAX", "канал", "новости", "вебхук", "новостной бот", "автопубликация", "training-*.html", "id312332413602_3_bot".
---

# MAX channel → IrMa site publishing

Two related but distinct workflows live here: an **automatic** pipeline (every
channel post becomes a news card, no review) and a **manual/curated** pipeline
(build a rich landing page like `training-cake-motorcycle.html` from one
specific post). Pick the right one — don't hand-build a page for something
the auto-pipeline already covers, and don't expect the auto-pipeline to
produce a priced, structured lesson page.

## Architecture

- **Source**: MAX channel "Семейное кафе «IrMa by Marinich»", `chat_id = -71665082178843`.
- **Reader bot**: `id312332413602_3_bot` ("Ирма Новости"), member of the channel.
  Token lives in `.env` as `token_bot_max` — **do not confuse with `MAX_TOKEN`**,
  which is the customer-order bot's token used by `app/bot/handlers.py` /
  `app/bot/max_adapter.py`.
- **Push subscription**: already registered with MAX Bot API, pointed at
  `https://irma.bot-ktu.online/webhook/news`, `update_types: [bot_added,
  bot_removed, message_created]`. Don't re-register unless it's gone (check
  first, see below).
- **Webhook handler**: `app/bot/news_webhook.py`. On `message_created` for the
  channel's `chat_id`, it derives `title` = first non-empty line of the post
  text, `text` = the rest, downloads the first `image`-type attachment (or a
  video's `thumbnail.url` if no image), and inserts a `News` row — **idempotent
  on the MAX message id (`mid`)**, so redelivery never duplicates.
- **Storage**: `news` table in Postgres (`app/models/news.py`), images in a
  dedicated Docker volume `news_uploads` mounted at `/app/uploads`, served at
  `/uploads/...`. `landing/` is baked into the image at *build* time (see
  `Dockerfile`) — it is **not** persistent, so anything the running app writes
  must go in `uploads/`, never under `landing/`.
- **Read API**: `GET /news/?limit=N` (`app/api/news.py`), ordered by
  `published_at desc`.
- **Frontend**: `landing/index.html` (top 5) and `landing/news.html` (all)
  render cards client-side via `fetch('/news/...')` — no server templating,
  plain JS building `innerHTML` with `escapeHtml()` (the post text is
  untrusted external content; never remove the escaping).
- **Moderation**: `/admin` (HTTP Basic — `ADMIN_EMAIL`/`ADMIN_PASSWORD` in
  `.env`) has a "Новости" section with a delete button per row (removes the DB
  row and its downloaded image file). Since publishing has no pre-review step,
  this is the only way to take down a bad auto-post.
- **Deploy**: push to `master` → `.github/workflows/deploy.yml` SSHes into the
  VPS, `git pull`, rebuilds/restarts the `app` container via `docker compose`,
  which runs `alembic upgrade head` before `uvicorn` starts. Prod:
  `https://irma.bot-ktu.online`.

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

Raw payloads are buffered in memory (last 20) for inspection:

```bash
curl -sS "https://irma.bot-ktu.online/webhook/news/debug"
```

To test the full ingestion path end-to-end without waiting for a real post,
POST a synthetic `message_created` event (use a real, already-hosted image URL
from the site itself, not an external one) and verify + clean up afterward:

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
      "attachments": [{"type": "image", "payload": {"url": "https://irma.bot-ktu.online/logo.jpg"}}]
    }
  }
}
EOF
curl -sS -X POST "https://irma.bot-ktu.online/webhook/news" -H "Content-Type: application/json" --data @payload.json
curl -sS "https://irma.bot-ktu.online/news/?limit=1"   # confirm it landed
# resend the same payload — total count must NOT increase (idempotency check)
```

Clean up the test row via the admin delete endpoint (reads creds from `.env`,
never inline them):

```bash
USER=$(grep -m1 '^ADMIN_EMAIL=' .env | cut -d= -f2-)
PASS=$(grep -m1 '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
curl -sS -u "${USER}:${PASS}" -X POST "https://irma.bot-ktu.online/admin/news/<id>/delete"
```

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

## Building a curated page instead (e.g. a new training lesson)

Some channel posts (flyer-style announcements with a price and curriculum)
deserve a full page like `landing/training-cake-motorcycle.html`, not just a
news card. When asked for that:

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
