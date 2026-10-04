# BuyerRadar

An agent that finds buyers for small sellers. It scans public posts on social
platforms for buying intent, matches what people are asking for against a
seller's inventory, and hands the seller a lead with a draft reply. The seller
approves before anything is sent.

## Status

| Part | State |
|---|---|
| Pipeline (ingest, classify, match, draft, store, notify) | Works, tested |
| Rules-based intent classifier | Works offline |
| SQLite storage with dedupe and verdict history | Works, tested |
| Bluesky source | Implemented, needs credentials in `config.toml` |
| Dashboard UI | Works, wired to the live API |
| API | Works, tested through the UI |
| WhatsApp / Telegram delivery | Not built yet |
| LLM classifier | Not built yet |

## Quickstart

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m buyerradar.main seed
python -m buyerradar.main scan --source sample
python -m buyerradar.main leads
python -m buyerradar.main serve    # then open http://127.0.0.1:8000
```

The web dashboard is the main interface: run scans, review matched leads,
approve or dismiss them, register a shop and manage inventory. The CLI commands
are development helpers, not the product.

To scan real Bluesky posts, copy `config.example.toml` to `config.toml`, fill
in your Bluesky identifier and an app password (Settings > App passwords on
bluesky.social), then run a scan from the dashboard with the Bluesky source
selected.

## Layout

```
buyerradar/
  main.py          CLI: seed, scan, leads, serve
  config.py        loads config.toml
  models.py        Product, Seller, SocialPost, Lead
  db.py            SQLite schema, migrations, queries
  pipeline.py      the core loop: fetch, classify, match, draft, store, notify
  match.py         inventory matching and confidence scoring
  drafts.py        draft reply builder
  classify/
    rules.py       regex intent classifier (offline, no LLM)
  sources/
    sample.py      12 fixed posts for development and tests
    bluesky.py     live searchPosts via the Bluesky API
  notify/
    console.py     prints leads to the terminal
  api/
    app.py         FastAPI endpoints, serves the dashboard
tests/             pytest suite for classifier, matcher, pipeline, storage
static/            the dashboard (plain HTML, CSS and JS, no build step)
docs/              screenshots
data/              SQLite database (gitignored)
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | /api/status | counts, source availability |
| GET | /api/leads | all leads, joined with posts and sellers |
| POST | /api/leads/{id}/approve | mark a lead approved |
| POST | /api/leads/{id}/dismiss | mark a lead dismissed |
| GET | /api/posts | recently scanned posts with verdicts |
| GET | /api/sellers | shops with inventory |
| POST | /api/sellers | register a shop |
| POST | /api/sellers/{id}/products | add a product |
| POST | /api/scan | run one scan pass (sample or bluesky) |

## Security

Set `SELLER_API_TOKEN` in the environment or add a token under `[auth]` in
`config.toml`, then restart the server. Open the dashboard Sources view and
enter the token once to save it in this browser. The dashboard sends it as
`X-API-Token` on write requests. GET endpoints stay open. Scans are limited
to 10 per minute per IP.

## Roadmap

1. Core loop. Done: rules classifier, sample source, SQLite, console notifier.
2. Dashboard wired to the API. Done: leads review, approve and dismiss, shop
   registration, inventory management, scan control, live refresh.
3. Live scanning. Bluesky credentials in, scan on a schedule, better query
   building from inventory tags.
4. Real delivery. WhatsApp (Cloud API) or Telegram bot so sellers approve
   leads from their phone.
5. Smarter matching. LLM classifier behind the same `classify` interface,
   so "kicks for a wedding" matches "Air Force 1".
6. More sources. Facebook Groups is where Ghanaian buyers actually post, but
   its API is restrictive and needs a look at terms and cost first. X API is
   paid.
# buyer-radar
