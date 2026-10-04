from datetime import datetime

import httpx

from ..models import SocialPost

API_BASE = "https://bsky.social/xrpc"


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class BlueskySource:
    def __init__(self, identifier, app_password):
        if not identifier or not app_password:
            raise RuntimeError(
                "Bluesky source needs an identifier and app password. "
                "Copy config.example.toml to config.toml and fill in [bluesky]."
            )
        self.identifier = identifier
        self.app_password = app_password
        self._token = None

    def _session_token(self):
        if self._token:
            return self._token
        resp = httpx.post(
            f"{API_BASE}/com.atproto.server.createSession",
            json={"identifier": self.identifier, "password": self.app_password},
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["accessJwt"]
        return self._token

    def fetch(self, query, limit=25):
        token = self._session_token()
        posts = []
        cursor = None
        while len(posts) < limit:
            params = {"q": query, "limit": min(limit - len(posts), 100)}
            if cursor:
                params["cursor"] = cursor
            resp = httpx.get(
                f"{API_BASE}/app.bsky.feed.searchPosts",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("posts", []):
                record = item.get("record", {})
                posts.append(
                    SocialPost(
                        source="bluesky",
                        source_id=item["uri"],
                        author=item.get("author", {}).get("handle", "unknown"),
                        text=record.get("text", ""),
                        city="",
                        posted_at=_parse_time(record.get("createdAt")),
                    )
                )
            cursor = data.get("cursor")
            if not cursor:
                break
        return posts
