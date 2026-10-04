from buyerradar.classify import classify_intent


def test_buying_intent():
    assert classify_intent("Abeg where can I get original Nike sneakers in Accra?")[0] == "buying"
    assert classify_intent("Anyone selling a fairly used iPhone 13?")[0] == "buying"
    assert classify_intent("I need new kicks for work")[0] == "buying"
    assert classify_intent("Who sells Jordans in Accra?")[0] == "buying"
    assert classify_intent("Looking for a tailor who can sew by Friday")[0] == "buying"


def test_seller_post():
    kind, _ = classify_intent("Selling my PS5 with 2 pads, GHS 4,500. DM me")
    assert kind == "selling"
    kind, _ = classify_intent("Selling thrift sneakers cheap cheap. Inbox me")
    assert kind == "selling"


def test_noise():
    assert classify_intent("This weather in Accra e no dey easy")[0] == "none"
    assert classify_intent("Best waakye spots in Accra? Going tomorrow")[0] == "none"


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
