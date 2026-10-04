# Security hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a token on API writes, cap inputs, limit scan abuse, and add safe headers with no new dependencies.

**Architecture:** Read SELLER_API_TOKEN from env with config.toml [auth] fallback. Enforce on POST writes via a FastAPI dependency with constant-time compare. Tighten Pydantic models. Add small in-memory sliding-window limiter plus a headers middleware. Dashboard sends the stored token from localStorage when set.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, stdlib hmac/os/time, pytest with FastAPI TestClient.

## Global Constraints

- No new dependencies.
- No hardcoded secrets, no secret logging, no traceback to clients.
- GET endpoints stay open. POST writes require token only when one is configured.
- Scan query max 200 chars. Classifier cap 2000 chars stays.
- Scan limit 10/min per IP. Other POST writes 60/min per IP. 429 includes Retry-After.
- Headers on every response: X-Content-Type-Options nosniff, X-Frame-Options DENY, Referrer-Policy no-referrer.
- pytest -q must pass before each commit.

---

### Task 1: Token config plus auth dependency

**Files:**
- Modify: `buyerradar/config.py`
- Modify: `buyerradar/api/app.py`
- Modify: `config.example.toml`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: os.environ SELLER_API_TOKEN, data auth.token from config.toml.
- Produces: Config.auth_token: str, require_write_auth() FastAPI dependency used by all POST routes.

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

def test_post_blocked_without_token(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLER_API_TOKEN", "s3cret-token")
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "Shop", "city": "Accra"})
    assert res.status_code == 401

def test_post_passes_with_bearer(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLER_API_TOKEN", "s3cret-token")
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec2.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "Shop", "city": "Accra"}, headers={"Authorization": "Bearer s3cret-token"})
    assert res.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py::test_post_blocked_without_token tests/test_security.py::test_post_passes_with_bearer -v`
Expected: FAIL. No auth yet, POST returns 201.

- [ ] **Step 3: Write minimal implementation**

In `buyerradar/config.py`, add:

```python
import os

# inside Config.__init__, after existing fields:
self.auth_token = os.environ.get("SELLER_API_TOKEN", "") or data.get("auth", {}).get("token", "")
```

In `buyerradar/api/app.py`, add:

```python
import hmac
from fastapi import Header

def _request_token(authorization: str | None, x_api_token: str | None, cfg):
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return (x_api_token or "").strip()

def require_write_auth(authorization: str | None = Header(default=None), x_api_token: str | None = Header(default=None)):
    if not cfg.auth_token:
        return
    got = _request_token(authorization, x_api_token, cfg)
    if not got or not hmac.compare_digest(got, cfg.auth_token):
        raise HTTPException(status_code=401, detail="unauthorized")
```

Attach `dependencies=[Depends(require_write_auth)]` or explicit `Depends` param on each POST route: create_seller, create_product, scan, approve, dismiss. Log one warning at startup when `not cfg.auth_token`.

In `config.example.toml`, append:

```toml
[auth]
token = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add buyerradar/config.py buyerradar/api/app.py config.example.toml tests/test_security.py
git commit -m "feat: require token on API writes"
```

### Task 2: Tighten input validation

**Files:**
- Modify: `buyerradar/api/app.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: require_write_auth from Task 1.
- Produces: SellerIn, ProductIn, scan query/source validation with 422 on bad input.

- [ ] **Step 1: Write the failing test**

```python
def test_rejects_oversize_and_bad_source(monkeypatch, tmp_path):
    monkeypatch.delenv("SELLER_API_TOKEN", raising=False)
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec3.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "x" * 200, "city": "Accra"})
    assert res.status_code == 422
    res2 = client.post("/api/scan?source=nope&query=hi")
    assert res2.status_code in (400, 422)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py::test_rejects_oversize_and_bad_source -v`
Expected: FAIL. Oversize name currently passes.

- [ ] **Step 3: Write minimal implementation**

In `buyerradar/api/app.py`:

```python
from pydantic import Field
from typing import Literal

class SellerIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=60)
    whatsapp: str = Field(default="", max_length=30)

class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: str = Field(min_length=1, max_length=30)
    tags: list[str] = Field(default=[], max_length=20)
```

Normalize in create_product: strip, drop empties, lowercase, cap each tag at 30 chars, cap list at 20.

Change scan signature to:

```python
from fastapi import Query

def scan(source: Literal["sample", "bluesky"] = "sample", query: str = Query(default="sneakers accra", max_length=200)):
```

Strip query, default when empty. Keep 400 for unconfigured Bluesky.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add buyerradar/api/app.py tests/test_security.py
git commit -m "fix: cap API input lengths and scan source"
```

### Task 3: Rate limits plus security headers

**Files:**
- Modify: `buyerradar/api/app.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: FastAPI app from Task 1 and Task 2.
- Produces: 429 with Retry-After on abuse, safe headers on every response.

- [ ] **Step 1: Write the failing test**

```python
def test_scan_rate_limited_and_headers(monkeypatch, tmp_path):
    monkeypatch.delenv("SELLER_API_TOKEN", raising=False)
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec4.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    last = None
    for _ in range(12):
        last = client.post("/api/scan?source=sample&query=hi")
    assert last.status_code == 429
    assert "Retry-After" in last.headers
    res = client.get("/api/status")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py::test_scan_rate_limited_and_headers -v`
Expected: FAIL. No limiter or headers yet.

- [ ] **Step 3: Write minimal implementation**

In `buyerradar/api/app.py`:

```python
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse

_hits: dict[tuple[str, str], list[float]] = defaultdict(list)

def _allow(key, limit, window=60.0):
    now = time.monotonic()
    slot = _hits[key]
    while slot and now - slot[0] > window:
        slot.pop(0)
    if len(slot) >= limit:
        return False, max(0, int(slot[0] + window - now))
    slot.append(now)
    return True, 0

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method == "POST":
        scope = "scan" if request.url.path == "/api/scan" else "write"
        limit = 10 if scope == "scan" else 60
        ip = request.client.host if request.client else "unknown"
        ok, retry = _allow((scope, ip), limit)
        if not ok:
            return JSONResponse(status_code=429, content={"detail": "rate limited"}, headers={"Retry-After": str(retry or 60)})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
```

Document in code comment that the store is per-process and needs a shared store with more workers.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q`
Expected: PASS, full suite green including old 17 tests.

- [ ] **Step 5: Commit**

```bash
git add buyerradar/api/app.py tests/test_security.py
git commit -m "feat: add rate limits and security headers"
```

### Task 4: Dashboard token send plus docs touch-up

**Files:**
- Modify: `static/index.html`
- Modify: `README.md`
- Test: manual plus `python -m pytest -q`

**Interfaces:**
- Consumes: X-API-Token header from Task 1.
- Produces: dashboard api() sends stored token, README documents SELLER_API_TOKEN.

- [ ] **Step 1: Update dashboard api helper**

```js
async function api(path,opts={}){
  const token = localStorage.getItem('buyeradar_token') || '';
  const headers = {'Content-Type':'application/json', ...(opts.headers||{})};
  if(token) headers['X-API-Token'] = token;
  const res=await fetch(path,{...opts, headers});
  ...
}
```

Add a password input in Sources view labeled API token with Save and Clear buttons storing to localStorage. No token baked into HTML.

- [ ] **Step 2: Update README security note**

Add short section: set SELLER_API_TOKEN env or [auth] token, restart, enter token in dashboard Sources view. GETs stay open. Scan limited to 10 per minute.

- [ ] **Step 3: Run full suite**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add static/index.html README.md
git commit -m "docs: document API token and dashboard use"
```
