import re

BUYING_PATTERNS = [
    r"where can i (get|buy)",
    r"anyone selling",
    r"looking for",
    r"\bneed\b",
    r"who sells",
    r"any recommendations",
    r"\brecommend",
    r"want to buy",
    r"how can i get",
    r"\bbudget\b",
]

SELLING_PATTERNS = [
    r"^\s*(i am|i'm)?\s*selling\b",
    r"dm me to (buy|order)",
    r"check out my (shop|store)",
    r"order now",
]


def classify_intent(text, llm_fallback=None):
    t = text.lower()
    if any(re.search(p, t) for p in SELLING_PATTERNS):
        return "selling", "seller post"
    for p in BUYING_PATTERNS:
        m = re.search(p, t)
        if m:
            return "buying", m.group(0)
    if llm_fallback is not None:
        try:
            capped = text[:2000]
            kind, phrase = llm_fallback(capped)
            if kind in ("buying", "selling", "none"):
                return kind, phrase
        except Exception:
            pass
    return "none", None
