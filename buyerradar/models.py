from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Product:
    name: str
    price: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Seller:
    name: str
    city: str
    whatsapp: str = ""
    inventory: list[Product] = field(default_factory=list)


@dataclass
class SocialPost:
    source: str
    source_id: str
    author: str
    text: str
    city: str = ""
    posted_at: datetime | None = None


@dataclass
class Lead:
    post: SocialPost
    seller: Seller
    confidence: float
    matched_products: list[Product]
    draft: str
    status: str = "new"
