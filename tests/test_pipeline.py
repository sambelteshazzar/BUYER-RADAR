from buyerradar.db import add_product, connect, list_leads, list_posts, list_sellers, save_seller
from buyerradar.main import SEED_SELLER
from buyerradar.models import Product
from buyerradar.pipeline import run_scan
from buyerradar.sources import SampleSource


def seeded_conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    save_seller(conn, SEED_SELLER)
    return conn


def test_scan_finds_expected_leads(tmp_path):
    conn = seeded_conn(tmp_path)
    summary = run_scan(conn, SampleSource(), "sneakers accra")
    assert summary["scanned"] == 12
    assert summary["leads"] == 4
    rows = list_leads(conn)
    assert len(rows) == 4
    assert all(r["status"] == "new" for r in rows)
    top = rows[0]
    assert top["author"] == "@ama_thrifts"
    assert top["seller_name"] == "SneakerPlug GH"
    assert any(m["name"] == "Nike Air Force 1" for m in top["matched"])


def test_scan_persists_verdicts(tmp_path):
    conn = seeded_conn(tmp_path)
    run_scan(conn, SampleSource(), "sneakers accra")
    posts = list_posts(conn)
    assert len(posts) == 12
    kinds = {}
    for post in posts:
        kinds[post["verdict"]] = kinds.get(post["verdict"], 0) + 1
    assert kinds == {"buying": 7, "selling": 2, "none": 3}
    assert len([p for p in posts if p["lead_id"]]) == 4
    buying_without_lead = [p for p in posts if p["verdict"] == "buying" and not p["lead_id"]]
    assert len(buying_without_lead) == 3


def test_rerun_creates_no_duplicates(tmp_path):
    conn = seeded_conn(tmp_path)
    run_scan(conn, SampleSource(), "sneakers accra")
    summary = run_scan(conn, SampleSource(), "sneakers accra")
    assert summary["duplicates"] == 12
    assert summary["leads"] == 0
    assert len(list_leads(conn)) == 4


def test_add_product_grows_inventory(tmp_path):
    conn = seeded_conn(tmp_path)
    seller_id = list_sellers(conn)[0][0]
    add_product(conn, seller_id, Product("Adidas Campus", "GHS 480", ["adidas", "campus"]))
    seller = list_sellers(conn)[0][1]
    assert len(seller.inventory) == 4
    assert seller.inventory[-1].name == "Adidas Campus"
