import hmac
import logging
import time
from collections import defaultdict
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from ..config import load_config
from ..db import (
    add_product,
    connect,
    count_posts,
    list_leads,
    list_posts,
    list_sellers,
    save_seller,
    set_lead_status,
)
from ..models import Product, Seller
from ..pipeline import run_scan
from ..sources import BlueskySource, SampleSource


class SellerIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=60)
    whatsapp: str = Field(default="", max_length=30)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: str = Field(min_length=1, max_length=30)
    tags: list[str] = Field(default=[], max_length=20)


# NOTE: in-memory per-process store; use a shared store (e.g. redis) with more workers.
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


def sellers_payload(conn):
    return [
        {
            "id": seller_id,
            "name": seller.name,
            "city": seller.city,
            "whatsapp": seller.whatsapp,
            "inventory": [
                {"name": p.name, "price": p.price, "tags": p.tags} for p in seller.inventory
            ],
        }
        for seller_id, seller in list_sellers(conn)
    ]


def create_app():
    app = FastAPI(title="BuyerRadar")
    cfg = load_config()

    if not cfg.auth_token:
        logging.getLogger("buyerradar").warning(
            "SELLER_API_TOKEN is not set; API writes are unauthenticated"
        )

    def _request_token(authorization: str | None, x_api_token: str | None):
        if authorization and authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return (x_api_token or "").strip()

    def require_write_auth(
        authorization: str | None = Header(default=None),
        x_api_token: str | None = Header(default=None),
    ):
        if not cfg.auth_token:
            return
        got = _request_token(authorization, x_api_token)
        if not got or not hmac.compare_digest(got, cfg.auth_token):
            raise HTTPException(status_code=401, detail="unauthorized")

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

    @app.get("/api/status")
    def status():
        conn = connect(cfg.db_path)
        leads = list_leads(conn)
        return {
            "sellers": len(list_sellers(conn)),
            "leads": len(leads),
            "new_leads": sum(1 for l in leads if l["status"] == "new"),
            "approved_leads": sum(1 for l in leads if l["status"] == "approved"),
            "posts_scanned": count_posts(conn),
            "bluesky_enabled": cfg.bluesky_enabled,
        }

    @app.get("/api/leads")
    def leads(status: str | None = None):
        conn = connect(cfg.db_path)
        return list_leads(conn, status=status)

    @app.post("/api/leads/{lead_id}/approve", dependencies=[Depends(require_write_auth)])
    def approve(lead_id: int):
        conn = connect(cfg.db_path)
        set_lead_status(conn, lead_id, "approved")
        return {"ok": True}

    @app.post("/api/leads/{lead_id}/dismiss", dependencies=[Depends(require_write_auth)])
    def dismiss(lead_id: int):
        conn = connect(cfg.db_path)
        set_lead_status(conn, lead_id, "dismissed")
        return {"ok": True}

    @app.get("/api/posts")
    def posts(limit: int = 20):
        conn = connect(cfg.db_path)
        return list_posts(conn, limit=min(max(limit, 1), 100))

    @app.get("/api/sellers")
    def get_sellers():
        conn = connect(cfg.db_path)
        return sellers_payload(conn)

    @app.post("/api/sellers", status_code=201, dependencies=[Depends(require_write_auth)])
    def create_seller(body: SellerIn):
        conn = connect(cfg.db_path)
        seller_id = save_seller(conn, Seller(body.name, body.city, body.whatsapp))
        return {"id": seller_id}

    @app.post("/api/sellers/{seller_id}/products", status_code=201, dependencies=[Depends(require_write_auth)])
    def create_product(seller_id: int, body: ProductIn):
        conn = connect(cfg.db_path)
        row = conn.execute("SELECT id FROM sellers WHERE id=?", (seller_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="seller not found")
        tags = [t.strip().lower()[:30] for t in body.tags]
        tags = [t for t in tags if t][:20]
        product_id = add_product(conn, seller_id, Product(body.name, body.price, tags))
        return {"id": product_id}

    @app.post("/api/scan", dependencies=[Depends(require_write_auth)])
    def scan(source: Literal["sample", "bluesky"] = "sample", query: str = Query(default="sneakers accra", max_length=200)):
        conn = connect(cfg.db_path)
        query = query.strip() or "sneakers accra"
        if source == "bluesky":
            if not cfg.bluesky_enabled:
                raise HTTPException(status_code=400, detail="bluesky is not configured")
            src = BlueskySource(cfg.bluesky_identifier, cfg.bluesky_password)
        elif source == "sample":
            src = SampleSource()
        else:
            raise HTTPException(status_code=400, detail="unknown source")
        return run_scan(conn, src, query)

    static_dir = Path(__file__).resolve().parents[2] / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
