import re
from datetime import datetime, timezone

MIN_CONFIDENCE = 0.5

SYNONYMS = {
    "kicks": "sneakers",
    "sneaks": "sneakers",
    "sneak": "sneakers",
    "af1": "air force",
    "jordans": "jordan",
}

NEGATIVE_TAGS = ["cleaning", "cleaner", "repair", "wash", "laundry"]
SPECIFIC_TOKENS = ["nike", "jordan", "adidas", "air force", "samba", "campus"]

def normalize_text(text):
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for short, full in SYNONYMS.items():
        t = re.sub(r"\b" + short + r"\b", full, t)
    return t


def match_products(text, seller):
    t = normalize_text(text)
    tokens = set(t.split())
    phrases = t
    hits = []
    for p in seller.inventory:
        matched = False
        for tag in p.tags:
            norm_tag = normalize_text(tag)
            if " " in norm_tag:
                if norm_tag in phrases:
                    matched = True
                    break
            elif norm_tag in tokens or norm_tag in phrases:
                matched = True
                break
        if matched:
            hits.append(p)
    if any(v in tokens for v in NEGATIVE_TAGS):
        if not any(s in phrases for s in SPECIFIC_TOKENS):
            return []
    return hits


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
