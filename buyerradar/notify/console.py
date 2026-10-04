class ConsoleNotifier:
    def notify(self, lead):
        names = ", ".join(f"{p.name} ({p.price})" for p in lead.matched_products)
        print()
        print("=" * 64)
        print(f"NEW LEAD  {lead.confidence * 100:.0f}%  for {lead.seller.name}")
        print("=" * 64)
        print(f"Buyer:   {lead.post.author} ({lead.post.city or 'location unknown'}) via {lead.post.source}")
        print(f'Post:    "{lead.post.text}"')
        print(f"Matched: {names}")
        print("Draft reply (awaiting seller approval):")
        print(f'  "{lead.draft}"')
