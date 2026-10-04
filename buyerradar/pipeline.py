from .classify import classify_intent
from .db import lead_exists, list_sellers, save_lead, save_post
from .drafts import build_draft
from .match import match_products, score_lead
from .models import Lead


def run_scan(conn, source, query, notifier=None, classifier=None, now=None):
    classify = classifier or classify_intent
    summary = {"scanned": 0, "leads": 0, "skipped": 0, "duplicates": 0}
    posts = source.fetch(query)
    summary["scanned"] = len(posts)
    for post in posts:
        kind, phrase = classify(post.text)
        note = phrase or ("seller post" if kind == "selling" else "no buying signal")
        post_id = save_post(conn, post, verdict=kind, note=note)
        if post_id is None:
            summary["duplicates"] += 1
            continue
        if kind != "buying":
            summary["skipped"] += 1
            continue
        matched_any = False
        for seller_id, seller in list_sellers(conn):
            products = match_products(post.text, seller)
            confidence = score_lead(post, seller, products, now=now)
            if confidence is None or lead_exists(conn, post_id, seller_id):
                continue
            lead = Lead(
                post=post,
                seller=seller,
                confidence=confidence,
                matched_products=products,
                draft=build_draft(post, seller, products),
            )
            save_lead(conn, lead, post_id, seller_id)
            summary["leads"] += 1
            matched_any = True
            if notifier:
                notifier.notify(lead)
        if not matched_any:
            summary["skipped"] += 1
    return summary
