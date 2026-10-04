from datetime import datetime, timedelta, timezone

from buyerradar.match import freshness_score, match_products, score_lead
from buyerradar.models import Product, Seller, SocialPost

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
SELLER = Seller(
    "SneakerPlug GH",
    "Accra",
    inventory=[
        Product("Nike Air Force 1", "GHS 450", ["nike", "sneakers", "air force"]),
        Product("Air Jordan 4", "GHS 800", ["jordan", "nike", "sneakers"]),
    ],
)


def test_match_products():
    hits = match_products("where can I get original Nike sneakers in Accra", SELLER)
    assert len(hits) == 2
    assert hits[0].name == "Nike Air Force 1"


def test_no_inventory_match():
    assert match_products("Need a good wig installer in Accra", SELLER) == []


def test_score_same_city_fresh_post():
    post = SocialPost("x", "1", "@a", "where can I get Nike sneakers in Accra", "Accra", NOW - timedelta(hours=1))
    confidence = score_lead(post, SELLER, match_products(post.text, SELLER), now=NOW)
    assert confidence > 0.85


def test_score_cross_city_is_lower():
    same = SocialPost("x", "1", "@a", "where can I get Nike sneakers in Accra", "Accra", NOW - timedelta(hours=1))
    away = SocialPost("x", "2", "@b", "where can I get Nike sneakers in Kumasi", "Kumasi", NOW - timedelta(hours=1))
    c_same = score_lead(same, SELLER, match_products(same.text, SELLER), now=NOW)
    c_away = score_lead(away, SELLER, match_products(away.text, SELLER), now=NOW)
    assert c_away < c_same
    assert c_away >= 0.5


def test_no_match_returns_none():
    post = SocialPost("x", "1", "@a", "where can I get a wig installer", "Accra", NOW - timedelta(hours=1))
    assert score_lead(post, SELLER, match_products(post.text, SELLER), now=NOW) is None


def test_stale_post_scores_lower():
    fresh = SocialPost("x", "1", "@a", "need Nike sneakers", "Accra", NOW - timedelta(minutes=30))
    stale = SocialPost("x", "2", "@b", "need Nike sneakers", "Accra", NOW - timedelta(days=2))
    assert freshness_score(fresh.posted_at, NOW) > freshness_score(stale.posted_at, NOW)
