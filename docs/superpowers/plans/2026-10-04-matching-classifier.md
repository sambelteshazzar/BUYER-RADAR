# Matching + classifier improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix kicks/AF1 misses and cleaning-service false positives while keeping the scan green.

**Architecture:** Normalize text and tags to lowercase tokens with a small synonym map and a service-word veto in match.py. Keep regex first in classify/rules.py and add an optional llm_fallback called only on none. No new dependencies.

**Tech Stack:** Python 3.11+, stdlib re, existing pytest suite.

## Global Constraints

- Offline default with no new dependencies.
- MIN_CONFIDENCE stays 0.5 in buyerradar/match.py.
- score_lead, location_score, freshness_score signatures unchanged.
- classify_intent default call classify_intent(text) keeps working.
- Fallback input capped at 2000 chars, output limited to buying, selling, none.
- pytest -q must pass before each commit.

---

### Task 1: Normalize match with synonyms and service veto

**Files:**
- Modify: `buyerradar/match.py`
- Test: `tests/test_match.py`

**Interfaces:**
- Consumes: Seller.inventory tags from buyerradar/models.py Product(name, price, tags).
- Produces: normalize_text(text: str) -> str, match_products(text: str, seller: Seller) -> list[Product] used by pipeline.py run_scan.

- [ ] **Step 1: Write the failing test**

```python
def test_match_kicks_and_af1_synonyms():
    from buyerradar.match import match_products
    post_kicks = "My Air Force 1s are done, I need new kicks for work"
    hits = match_products(post_kicks, SELLER)
    assert len(hits) >= 1

    post_af1 = "Where can I get AF1 in Accra?"
    hits_af1 = match_products(post_af1, SELLER)
    assert any(p.name == "Nike Air Force 1" for p in hits_af1)

def test_match_rejects_cleaning_service():
    from buyerradar.match import match_products
    hits = match_products("Recommend a good sneaker cleaning service in Accra please", SELLER)
    assert hits == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_match.py::test_match_kicks_and_af1_synonyms tests/test_match.py::test_match_rejects_cleaning_service -v`
Expected: FAIL. kicks has no tag hit, cleaning service matches generic sneakers.

- [ ] **Step 3: Write minimal implementation**

In `buyerradar/match.py`, add above match_products:

```python
import re

SYNONYMS = {
    "kicks": "sneakers",
    "sneaks": "sneakers",
    "sneak": "sneakers",
    "af1": "air force",
    "jordans": "jordan",
}

NEGATIVE_TAGS = ["cleaning", "cleaner", "repair", "wash", "laundry"]
SPECIFIC_TOKENS = ["nike", "jordan", "adidas", "air force", "af1", "samba", "campus"]

def normalize_text(text):
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for short, full in SYNONYMS.items():
        t = re.sub(r"\b" + short + r"\b", full, t)
    return t
```

Replace match_products with:

```python
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
```

Keep location_score, freshness_score, score_lead unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_match.py -v`
Expected: PASS, all 6 old tests plus 2 new ones.

- [ ] **Step 5: Commit**

```bash
git add buyerradar/match.py tests/test_match.py
git commit -m "feat: normalize match with synonyms and service veto"
```

### Task 2: Add optional LLM fallback to classifier

**Files:**
- Modify: `buyerradar/classify/rules.py`
- Modify: `buyerradar/classify/__init__.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: rules classify_intent from Task 1 unchanged behavior.
- Produces: classify_intent(text: str, llm_fallback=None) -> tuple[str, str | None] used by pipeline.py run_scan classifier hook.

- [ ] **Step 1: Write the failing test**

```python
def test_fallback_only_on_none():
    from buyerradar.classify import classify_intent
    calls = []
    def stub(text):
        calls.append(text)
        return ("buying", "stub hit")
    kind, _ = classify_intent("Anyone selling a fairly used iPhone 13?", llm_fallback=stub)
    assert kind == "buying"
    assert calls == []
    kind2, phrase2 = classify_intent("This weather in Accra e no dey easy", llm_fallback=stub)
    assert kind2 == "buying"
    assert phrase2 == "stub hit"

def test_fallback_rejects_bad_values():
    from buyerradar.classify import classify_intent
    kind, _ = classify_intent("quiet post about nothing", llm_fallback=lambda t: ("shouting", "x"))
    assert kind == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rules.py::test_fallback_only_on_none tests/test_rules.py::test_fallback_rejects_bad_values -v`
Expected: FAIL with unexpected keyword argument llm_fallback.

- [ ] **Step 3: Write minimal implementation**

In `buyerradar/classify/rules.py`, change signature to:

```python
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
```

In `buyerradar/classify/__init__.py`, keep:

```python
from .rules import classify_intent

__all__ = ["classify_intent"]
```

No change needed in pipeline.py because run_scan already accepts classifier kwarg.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rules.py -v`
Expected: PASS, 3 old tests plus 2 new ones.

- [ ] **Step 5: Commit**

```bash
git add buyerradar/classify/rules.py tests/test_rules.py
git commit -m "feat: add optional fallback hook to classifier"
```

### Task 3: Full regression and pipeline check

**Files:**
- Modify: none, verify only
- Test: `tests/test_pipeline.py`, `tests/test_match.py`, `tests/test_rules.py`

**Interfaces:**
- Consumes: match_products and classify_intent from Task 1 and Task 2.
- Produces: green pytest run, sample scan still yields 4 leads with cleaning post excluded.

- [ ] **Step 1: Run full suite**

Run: `pytest -q`
Expected: PASS, 13 tests (6 match + 5 rules + 4 pipeline, counts include new ones).

- [ ] **Step 2: Run sample scan sanity**

Run: `python -m buyerradar.main scan --source sample`
Expected: Scanned 12 posts, leads 4 or 5 depending on kicks fix, skipped rest, duplicates 0 on fresh DB. Cleaning post has verdict buying but no lead.

- [ ] **Step 3: Code review gate**

Check: no secrets, parameterized queries untouched, length cap present, veto conservative, names clear, no dead code.

- [ ] **Step 4: Commit if fixes needed**

```bash
git add -A
git commit -m "test: verify pipeline regression after match fix"
```
Only commit if Step 1 or 2 required a fix. Otherwise skip this commit.
