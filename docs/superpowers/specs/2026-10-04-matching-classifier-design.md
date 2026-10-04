# BuyerRadar matching + classifier improvement

Date: 2026-10-04
Scope: match.py + classify/rules.py only. No API, DB, or UI changes.
Success: kicks and AF1 match inventory, sneaker cleaning creates no lead, current pytest suite stays green.

## 1. Match layer

Add `normalize()` in `buyerradar/match.py`:
- Lowercase, strip punctuation, collapse whitespace.
- Simple plural strip (sneakers to sneaker stem for compare, or compare both forms).
- Synonym map: kicks, sneaks, sneak to sneakers; af1 to air force; jordans to jordan.

Change `match_products(text, seller)`:
- Tokenize normalized post text once.
- Match when any normalized tag appears as token or phrase.
- Veto list `NEGATIVE_TAGS = ["cleaning", "cleaner", "repair", "wash", "laundry"]`: if a veto word is present, a generic `sneakers` tag alone is not enough. A lead needs a specific token such as nike, jordan, adidas, air force, af1, or samba. This stops "sneaker cleaning service" from becoming a lead while keeping "need Nike sneakers cleaned" out of scope for now.
- Keep `location_score`, `freshness_score`, `score_lead`, and `MIN_CONFIDENCE = 0.5` unchanged.

## 2. Classify layer

Change signature to `classify_intent(text, llm_fallback=None)` in `buyerradar/classify/rules.py`:
- Run existing BUYING and SELLING regex first. Return on hit, unchanged behavior.
- Only when verdict is none and a fallback is passed, call it. Cap input at 2000 chars.
- Accept only buying, selling, or none from fallback. Anything else maps to none.
- Default path stays offline with no secrets, no network, no new deps.
- `pipeline.py` passes through an optional classifier already, so no pipeline change needed beyond wiring.

## 3. Data flow

Sample or Bluesky post -> normalize -> regex classify (or fallback) -> save_post with verdict -> token match with veto -> score_lead -> save_lead + draft. Unmatched buying posts still store with verdict buying and note no inventory match, visible in Recently scanned.

## 4. Error handling

Empty text returns none. None posted_at keeps freshness 0.5. LLM fallback exceptions fall back to none and never break a scan. Veto list is conservative: it only blocks service words, never blocks a post that names a specific product plus a service word unless no product token matches.

## 5. Testing

Keep `tests/test_rules.py`, `tests/test_match.py`, `tests/test_pipeline.py` green.
Add:
- kicks for work matches Nike inventory.
- AF1 matches Air Force 1.
- sneaker cleaning service yields no products and no lead.
- classify_intent with a stub fallback returns fallback verdict only on none, and ignores bad fallback values.

Run `pytest -q` before each commit.

## 6. Security notes

No new trust boundary. No user input reaches SQL except through existing parameterized queries in db.py. No secrets added. Fallback hook validates length and output enum. No log of post text with PII beyond current console notifier.

## 7. Git plan

Atomic commits: one for match, one for classify, one for tests. Messages in `type: short desc` form. Run quality review per change for correctness, readability, architecture fit, security, and performance. No push until user approves the diff.
