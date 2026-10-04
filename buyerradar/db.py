import json
import sqlite3
from pathlib import Path

from .models import Product, Seller

SCHEMA = """
CREATE TABLE IF NOT EXISTS sellers(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    whatsapp TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    price TEXT NOT NULL,
    tags TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts(
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    author TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    verdict TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS leads(
    id INTEGER PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id),
    seller_id INTEGER NOT NULL REFERENCES sellers(id),
    confidence REAL NOT NULL,
    matched_products TEXT NOT NULL,
    draft TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    UNIQUE(post_id, seller_id)
);
"""


def connect(db_path):
    path = Path(db_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(posts)")}
    if "verdict" not in cols:
        conn.execute("ALTER TABLE posts ADD COLUMN verdict TEXT NOT NULL DEFAULT ''")
    if "note" not in cols:
        conn.execute("ALTER TABLE posts ADD COLUMN note TEXT NOT NULL DEFAULT ''")


def save_seller(conn, seller):
    conn.execute(
        "INSERT INTO sellers(name, city, whatsapp) VALUES(?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET city=excluded.city, whatsapp=excluded.whatsapp",
        (seller.name, seller.city, seller.whatsapp),
    )
    seller_id = conn.execute("SELECT id FROM sellers WHERE name=?", (seller.name,)).fetchone()["id"]
    conn.execute("DELETE FROM products WHERE seller_id=?", (seller_id,))
    for product in seller.inventory:
        conn.execute(
            "INSERT INTO products(seller_id, name, price, tags) VALUES(?,?,?,?)",
            (seller_id, product.name, product.price, json.dumps(product.tags)),
        )
    conn.commit()
    return seller_id


def add_product(conn, seller_id, product):
    cur = conn.execute(
        "INSERT INTO products(seller_id, name, price, tags) VALUES(?,?,?,?)",
        (seller_id, product.name, product.price, json.dumps(product.tags)),
    )
    conn.commit()
    return cur.lastrowid


def list_sellers(conn):
    result = []
    for row in conn.execute("SELECT * FROM sellers ORDER BY id"):
        seller = Seller(row["name"], row["city"], row["whatsapp"])
        for prow in conn.execute("SELECT * FROM products WHERE seller_id=? ORDER BY id", (row["id"],)):
            seller.inventory.append(Product(prow["name"], prow["price"], json.loads(prow["tags"])))
        result.append((row["id"], seller))
    return result


def save_post(conn, post, verdict="", note=""):
    cur = conn.execute(
        "INSERT OR IGNORE INTO posts(source, source_id, author, city, text, posted_at, verdict, note) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (
            post.source,
            post.source_id,
            post.author,
            post.city,
            post.text,
            post.posted_at.isoformat(),
            verdict,
            note,
        ),
    )
    if cur.rowcount == 0:
        return None
    conn.commit()
    return cur.lastrowid


def list_posts(conn, limit=20):
    query = (
        "SELECT p.id, p.source, p.author, p.city, p.text, p.posted_at, p.verdict, p.note, "
        "(SELECT l.id FROM leads l WHERE l.post_id = p.id LIMIT 1) AS lead_id "
        "FROM posts p ORDER BY p.id DESC LIMIT ?"
    )
    return [dict(r) for r in conn.execute(query, (limit,))]


def count_posts(conn):
    return conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]


def lead_exists(conn, post_id, seller_id):
    row = conn.execute("SELECT 1 FROM leads WHERE post_id=? AND seller_id=?", (post_id, seller_id)).fetchone()
    return row is not None


def save_lead(conn, lead, post_id, seller_id):
    cur = conn.execute(
        "INSERT OR IGNORE INTO leads(post_id, seller_id, confidence, matched_products, draft) VALUES(?,?,?,?,?)",
        (
            post_id,
            seller_id,
            lead.confidence,
            json.dumps([{"name": p.name, "price": p.price} for p in lead.matched_products]),
            lead.draft,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _normalize_matched(raw):
    items = json.loads(raw) if raw else []
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append({"name": item.get("name", ""), "price": item.get("price", "")})
        else:
            result.append({"name": str(item), "price": ""})
    return result


def list_leads(conn, status=None):
    query = (
        "SELECT l.id, l.confidence, l.draft, l.status, l.matched_products AS matched, "
        "p.source, p.source_id, p.author, p.city, p.text, p.posted_at, "
        "s.name AS seller_name, s.city AS seller_city "
        "FROM leads l JOIN posts p ON l.post_id=p.id JOIN sellers s ON l.seller_id=s.id"
    )
    params = []
    if status:
        query += " WHERE l.status=?"
        params.append(status)
    query += " ORDER BY l.confidence DESC"
    rows = []
    for r in conn.execute(query, params):
        row = dict(r)
        row["matched"] = _normalize_matched(row["matched"])
        rows.append(row)
    return rows


def set_lead_status(conn, lead_id, status):
    conn.execute("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
    conn.commit()
