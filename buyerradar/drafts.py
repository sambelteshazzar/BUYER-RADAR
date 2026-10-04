def build_draft(post, seller, products):
    first = post.author.lstrip("@").split(".")[0].split("_")[0].split()[0].title()
    items = " and ".join(f"{p.name} ({p.price})" for p in products[:2])
    if post.city and post.city.lower() == seller.city.lower():
        loc = f"I'm right here in {seller.city}"
    elif post.city:
        loc = f"I'm based in {seller.city} and can arrange delivery to {post.city}"
    else:
        loc = f"I'm based in {seller.city}"
    return (
        f"Hi {first}! I run {seller.name} - {loc}. "
        f"Saw your post - I have {items} available right now. "
        f"Want me to send photos or answer any questions?"
    )
