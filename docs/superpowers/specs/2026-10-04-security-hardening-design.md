# BuyerRadar security hardening (minimal, no new deps)

Date: 2026-10-04
Scope: API auth, input validation, rate limits, security headers. No new dependencies. No hardcoded secrets. DB queries stay parameterized. Dashboard GET polling stays open.

## 1. Auth + secrets

- Read token from env `SELLER_API_TOKEN`, fallback to `config.toml [auth] token`. Env wins when both set.
- When no token is configured, writes stay open for local dev and the server logs one warning line at startup. No warning per request.
- When a token is configured, require it on POST writes only: create seller, create product, run scan, approve lead, dismiss lead. Header `X-API-Token` or `Authorization: Bearer <token>`. Compare with hmac.compare_digest. Wrong or missing token returns 401 with generic detail.
- GET endpoints (/api/status, /api/leads, /api/posts, /api/sellers) stay open so the dashboard auto-refresh keeps working.
- No token, password, or Bluesky secret is logged. No token in query strings. Example config documents the field with an empty placeholder.

## 2. Validation + errors

- SellerIn: name max 80 stripped non-empty, city max 60 stripped non-empty, whatsapp max 30.
- ProductIn: name max 100 stripped non-empty, price max 30 stripped non-empty, tags max 20 items each max 30 chars lowercased stripped. Reject empty tag list entries silently by filtering.
- Scan: source must be sample or bluesky (enum), query max 200 chars stripped, default sneakers accra when empty.
- Posts limit already clamped 1 to 100. Keep it.
- Keep 404 for unknown seller and 400 for unconfigured Bluesky or unknown source. Validation failures return 422 from FastAPI. Error bodies stay generic with no traceback.
- Bluesky timeouts stay 15 seconds. Classifier fallback cap 2000 chars stays.

## 3. Rate limits + headers

- In-memory sliding window per client IP, single process only. Document that a second worker needs a shared store.
- Scan endpoint: 10 requests per minute per IP. Other POST writes: 60 per minute per IP. Over limit returns 429 with Retry-After header.
- Add middleware headers on every response: X-Content-Type-Options nosniff, X-Frame-Options DENY, Referrer-Policy no-referrer. No CORS wildcard change since CORS is not enabled.
- Dashboard static mount unchanged. No inline secret injection into HTML or JS.

## 4. What stays untouched

- db.py query style: all ? placeholders, no string-built SQL.
- match.py and classify logic from the prior round.
- File layout and dashboard behavior except sending the token header on POST when configured.

## 5. Testing

- Unauthed POST blocked with 401 when token set. Authed POST passes with either header form.
- No-token mode keeps current behavior with one startup warning.
- Oversize name, too many tags, bad source, and over-limit scan return 422 or 429 as appropriate.
- Full pytest -q stays green. New tests live in tests/test_security.py and use FastAPI TestClient with isolated temp DB and env override.

## 6. Git plan

Atomic commits: auth first, then validation, then limits plus headers, then tests if split. Messages in type: short desc form. Quality review per change for correctness, architecture fit, security, and performance. Push only after user approves the diff.
