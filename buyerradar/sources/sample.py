from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..models import SocialPost

RAW = [
    ("x", "@ama_thrifts", "Accra", 2.0, "Abeg where can I get original Nike sneakers in Accra? Tired of buying fake ones"),
    ("x", "@lagos_tweep", "Lagos", 2.0, "I hate Mondays eii, the traffic in this city is too much"),
    ("facebook", "Jay Gh", "Accra", 3.0, "Selling my PS5 with 2 pads, GHS 4,500. DM me if you're serious"),
    ("bluesky", "@nana.bsky", "Accra", 1.0, "Need a good wig installer in Accra asap, I have an event on Saturday. Any recommendations?"),
    ("bluesky", "@sneakhead.bsky", "Accra", 3.0, "Who sells Jordans in Accra? I need proof they are real before I pay"),
    ("facebook", "Yaw Boateng", "Kumasi", 4.0, "Anyone selling a fairly used iPhone 13 around Kumasi? My budget is 3k"),
    ("reddit", "u/waakye_lover", "Accra", 5.0, "Best waakye spots in Accra? Going tomorrow morning early"),
    ("facebook", "Efe D.", "Tema", 1.0, "Looking for affordable Adidas sneakers for my son, size 42. Prefer Tema based sellers"),
    ("x", "@jesse_kicks", "Accra", 0.3, "My Air Force 1s are done, I need new kicks for work. Who has originals in Accra?"),
    ("facebook", "Thrift Mama", "Accra", 6.0, "Selling thrift sneakers cheap cheap. Inbox me"),
    ("x", "@kojo_og", "Accra", 0.5, "Recommend a good sneaker cleaning service in Accra please"),
    ("x", "@accra_vibes", "Accra", 0.2, "This weather in Accra e no dey easy at all. Sun dey burn"),
]


@dataclass
class SampleSource:
    now: datetime | None = None

    def fetch(self, query, limit=None):
        now = self.now or datetime.now(timezone.utc)
        posts = [
            SocialPost(
                source=source,
                source_id=f"sample-{i}",
                author=author,
                text=text,
                city=city,
                posted_at=now - timedelta(hours=hours),
            )
            for i, (source, author, city, hours, text) in enumerate(RAW)
        ]
        return posts[:limit] if limit else posts
