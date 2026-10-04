from datetime import datetime, timezone

MIN_CONFIDENCE = 0.5


def match_products(text, seller):
    t = text.lower()
    return [p for p in seller.inventory if any(tag in t for tag in p.tags)]


def location_score(post_city, seller_city):
    if not post_city:
        return 0.5
    return 1.0 if post_city.lower() == seller_city.lower() else 0.35


def freshness_score(posted_at, now=None):
    if posted_at is None:
        return 0.5
    now = now or datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    hours = max((now - posted_at).total_seconds() / 3600, 0)
    if hours <= 3:
        return 1.0
    if hours <= 8:
        return 0.8
    return 0.5


def score_lead(post, seller, matched_products, now=None):
    if not matched_products:
        return None
    product_score = min(1.0, 0.7 + 0.15 * (len(matched_products) - 1))
    confidence = (
        0.45 * product_score
        + 0.25
        + 0.20 * location_score(post.city, seller.city)
        + 0.10 * freshness_score(post.posted_at, now)
    )
    if confidence < MIN_CONFIDENCE:
        return None
    return round(confidence, 3)
