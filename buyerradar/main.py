import argparse

from .config import load_config
from .db import connect, list_leads, list_sellers, save_seller
from .models import Product, Seller
from .notify.console import ConsoleNotifier
from .pipeline import run_scan
from .sources import BlueskySource, SampleSource

SEED_SELLER = Seller(
    name="SneakerPlug GH",
    city="Accra",
    whatsapp="+233 24 333 4444",
    inventory=[
        Product("Nike Air Force 1", "GHS 450", ["nike", "sneakers", "air force", "af1"]),
        Product("Air Jordan 4", "GHS 800", ["jordan", "jordans", "nike", "sneakers"]),
        Product("Adidas Samba", "GHS 520", ["adidas", "sneakers", "samba"]),
    ],
)


def build_source(name, cfg):
    if name == "sample":
        return SampleSource()
    if name == "bluesky":
        return BlueskySource(cfg.bluesky_identifier, cfg.bluesky_password)
    raise SystemExit(f"unknown source: {name}")


def default_query(cfg, conn):
    if cfg.query:
        return cfg.query
    tags = []
    for _, seller in list_sellers(conn):
        for product in seller.inventory:
            for tag in product.tags:
                if tag not in tags:
                    tags.append(tag)
    return " OR ".join(tags[:10]) or "sneakers"


def cmd_seed(args):
    cfg = load_config()
    conn = connect(cfg.db_path)
    save_seller(conn, SEED_SELLER)
    print(f"Seeded {SEED_SELLER.name} ({SEED_SELLER.city}) with {len(SEED_SELLER.inventory)} products -> {cfg.db_path}")


def cmd_scan(args):
    cfg = load_config()
    conn = connect(cfg.db_path)
    source = build_source(args.source, cfg)
    query = args.query or default_query(cfg, conn)
    summary = run_scan(conn, source, query, notifier=ConsoleNotifier())
    print()
    print(
        f"Scanned {summary['scanned']} posts: "
        f"{summary['leads']} leads, {summary['skipped']} skipped, {summary['duplicates']} already seen"
    )


def cmd_leads(args):
    cfg = load_config()
    conn = connect(cfg.db_path)
    rows = list_leads(conn, status=args.status)
    if not rows:
        print("No leads stored yet.")
        return
    for r in rows:
        print(f"#{r['id']} [{r['status']}] {r['confidence'] * 100:.0f}%  {r['author']} ({r['city'] or '?'}) -> {r['seller_name']}")
        print(f'    "{r["text"][:90]}"')


def cmd_serve(args):
    import uvicorn

    from .api.app import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="buyerradar", description="Buyer lead agent for social sellers")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seed", help="seed the demo seller and inventory")
    p.set_defaults(func=cmd_seed)

    p = sub.add_parser("scan", help="run one scan pass")
    p.add_argument("--source", choices=["sample", "bluesky"], default="sample")
    p.add_argument("--query", default="")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("leads", help="list stored leads")
    p.add_argument("--status", default=None)
    p.set_defaults(func=cmd_leads)

    p = sub.add_parser("serve", help="run the dashboard API server")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
