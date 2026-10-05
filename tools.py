"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Helper functions ───────────────────────────────────────────────────────────

def _words(text: str) -> set[str]:
    """Return lowercase searchable words from a string."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _size_matches(requested_size: str, listing_size: str) -> bool:
    """Check whether a requested size matches a listing size."""
    requested = requested_size.strip().lower()
    listing = listing_size.strip().lower()

    listing_parts = {
        part
        for part in re.split(r"[^a-z0-9]+", listing)
        if part
    }

    return requested == listing or requested in listing_parts


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search listings using keywords, size, and an optional price ceiling.
    """

    listings = load_listings()
    query_words = _words(description)

    scored_results = []

    for listing in listings:

        # Filter by price when max_price is provided.
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size when size is provided.
        if size is not None and not _size_matches(size, listing["size"]):
            continue

        searchable_parts = [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            listing.get("condition", ""),
            listing.get("brand") or "",
            " ".join(listing.get("style_tags", [])),
            " ".join(listing.get("colors", [])),
        ]

        searchable_text = " ".join(searchable_parts)
        listing_words = _words(searchable_text)

        score = len(query_words & listing_words)

        # Do not return listings with no keyword overlap.
        if score == 0:
            continue

        scored_results.append((score, listing))

    # Highest-scoring matches come first.
    scored_results.sort(key=lambda result: result[0], reverse=True)

    return [
        listing
        for _, listing in scored_results[: config.SEARCH_RESULT_LIMIT]
    ]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Suggest one or two outfits using the selected thrifted item.
    """

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        prompt = f"""
You are a personal styling assistant.

The user is considering this thrifted item:

Title: {new_item.get("title")}
Category: {new_item.get("category")}
Colors: {", ".join(new_item.get("colors", []))}
Style tags: {", ".join(new_item.get("style_tags", []))}

The user's wardrobe is currently empty.

Suggest one or two simple ways to style this item using common clothing pieces.
Keep the response concise and practical.
"""

    else:
        wardrobe_lines = []

        for item in wardrobe_items:
            wardrobe_lines.append(
                f"- {item.get('name')} | "
                f"category: {item.get('category')} | "
                f"colors: {', '.join(item.get('colors', []))} | "
                f"style: {', '.join(item.get('style_tags', []))} | "
                f"notes: {item.get('notes', '')}"
            )

        wardrobe_text = "\n".join(wardrobe_lines)

        prompt = f"""
You are a personal styling assistant.

The user is considering this thrifted item:

Title: {new_item.get("title")}
Category: {new_item.get("category")}
Colors: {", ".join(new_item.get("colors", []))}
Style tags: {", ".join(new_item.get("style_tags", []))}

The user's wardrobe contains:

{wardrobe_text}

Suggest one or two outfits using the thrifted item and specific pieces from
the user's wardrobe.

Name the wardrobe pieces you use and keep the response concise and practical.
"""

    return generate(prompt).strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Create a short social-style caption for the selected thrift find.
    """

    if not outfit or not outfit.strip():
        return (
            "A fit card could not be created because no outfit suggestion "
            "was provided."
        )

    prompt = f"""
Write a short social-media-style caption for this thrift find.

Item: {new_item.get("title")}
Price: ${new_item.get("price"):.2f}
Platform: {new_item.get("platform")}

Outfit idea:
{outfit}

Requirements:
- Write only 2 to 4 sentences.
- Mention the item.
- Mention its price exactly once.
- Mention the platform exactly once.
- Describe the overall vibe.
- Make it sound like something a real person might post.
"""

    return generate(prompt).strip()

# ── Tool 4: compare_prices ────────────────────────────────────────────────────

def compare_prices(selected_item: dict, matches: list[dict]) -> dict:
    """
    Compare the selected item's price with similar matching listings.

    Only listings in the same category as the selected item are compared.
    """

    comparable_items = [
        listing
        for listing in matches
        if listing.get("category") == selected_item.get("category")
    ]

    if not comparable_items:
        return {
            "selected_price": selected_item.get("price"),
            "average_price": None,
            "cheapest_item": selected_item,
            "assessment": "no_comparison",
        }

    prices = [listing["price"] for listing in comparable_items]
    average_price = sum(prices) / len(prices)

    cheapest_item = min(
        comparable_items,
        key=lambda listing: listing["price"],
    )

    selected_price = selected_item["price"]

    if selected_price > average_price:
        assessment = "above_average"
    elif selected_price < average_price:
        assessment = "below_average"
    else:
        assessment = "average"

    return {
        "selected_price": selected_price,
        "average_price": round(average_price, 2),
        "cheapest_item": cheapest_item,
        "assessment": assessment,
    }