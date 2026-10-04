import os
import tomllib
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config.toml")


class Config:
    def __init__(self, data=None):
        data = data or {}
        bluesky = data.get("bluesky", {})
        self.bluesky_identifier = bluesky.get("identifier", "")
        self.bluesky_password = bluesky.get("app_password", "")
        self.bluesky_enabled = bool(self.bluesky_identifier and self.bluesky_password)
        self.db_path = os.environ.get("BUYERADAR_DB") or data.get("db", {}).get("path", "data/buyerradar.db")
        self.query = data.get("scan", {}).get("query", "")
        self.auth_token = os.environ.get("SELLER_API_TOKEN", "") or data.get("auth", {}).get("token", "")


def load_config(path=DEFAULT_CONFIG_PATH):
    if not Path(path).exists():
        return Config()
    with open(path, "rb") as f:
        return Config(tomllib.load(f))
