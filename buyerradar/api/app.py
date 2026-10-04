from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
    name: str
    city: str
    whatsapp: str = ""


class ProductIn(BaseModel):
    name: str
    price: str
    tags: list[str] = []


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

    @app.post("/api/leads/{lead_id}/approve")
    def approve(lead_id: int):
        conn = connect(cfg.db_path)
        set_lead_status(conn, lead_id, "approved")
        return {"ok": True}

    @app.post("/api/leads/{lead_id}/dismiss")
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

    @app.post("/api/sellers", status_code=201)
    def create_seller(body: SellerIn):
        conn = connect(cfg.db_path)
        seller_id = save_seller(conn, Seller(body.name, body.city, body.whatsapp))
        return {"id": seller_id}

    @app.post("/api/sellers/{seller_id}/products", status_code=201)
    def create_product(seller_id: int, body: ProductIn):
        conn = connect(cfg.db_path)
        row = conn.execute("SELECT id FROM sellers WHERE id=?", (seller_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="seller not found")
        product_id = add_product(conn, seller_id, Product(body.name, body.price, body.tags))
        return {"id": product_id}

    @app.post("/api/scan")
    def scan(source: str = "sample", query: str = "sneakers accra"):
        conn = connect(cfg.db_path)
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
