"""
The FitFindr planning loop.

This file connects the FitFindr tools and decides what to do next based on
what each tool returns.
"""

import re

import config
import trace
from tools import (
    search_listings,
    suggest_outfit,
    create_fit_card,
    compare_prices,
)
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    Create a fresh session for one user interaction.
    """

    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "price_comparison": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def parse_query(query: str) -> dict:
    """
    Parse a plain-language query into description, size, and max_price.

    Examples:
        "vintage graphic tee under $30"
        "graphic tee size M under $25"
    """

    description = query.strip()

    # Find price patterns such as:
    # under $30
    # under 30
    price_match = re.search(
        r"\bunder\s+\$?(\d+(?:\.\d{1,2})?)",
        query,
        re.IGNORECASE,
    )

    max_price = None

    if price_match:
        max_price = float(price_match.group(1))

        # Remove price phrase from the searchable description.
        description = re.sub(
            r"\bunder\s+\$?\d+(?:\.\d{1,2})?",
            "",
            description,
            flags=re.IGNORECASE,
        )

    # Find sizes such as:
    # size M
    # size L
    # size W30
    # size W30 L30
    size_match = re.search(
        r"\bsize\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)",
        description,
        re.IGNORECASE,
    )

    size = None

    if size_match:
        size = size_match.group(1).strip()

        # Remove the size phrase from the description.
        description = (
            description[:size_match.start()]
            + description[size_match.end():]
        )

    # Remove common request words that are not useful search terms.
    description = re.sub(
        r"\b(looking for|find me|show me|i want|i need|a|an)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )

    # Clean up extra spaces and punctuation.
    description = re.sub(r"\s+", " ", description)
    description = description.strip(" ,.-")

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the FitFindr planning loop once and return the completed session.
    """

    session = new_session(query, wardrobe)

    step = "parse"
    iteration_count = 0

    while step != "done":
        iteration_count += 1
        trace.check_iterations(iteration_count)

        # ── Step 1: Parse query ────────────────────────────────────────────────

        if step == "parse":
            session["parsed"] = parse_query(session["query"])
            step = "search"

        # ── Step 2: Search listings ───────────────────────────────────────────

        elif step == "search":
            parsed = session["parsed"]

            session["search_results"] = search_listings(
                description=parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )

            # REQUIRED BRANCH:
            # Stop if search_listings returned nothing.
            if not session["search_results"]:
                session["error"] = (
                    "I couldn't find a matching listing. Try using fewer "
                    "description words, choosing a different size, or "
                    "increasing your maximum price."
                )

                step = "done"
                continue

            session["selected_item"] = session["search_results"][0]
            step = "compare_price"

        # ── Step 3: Compare prices ────────────────────────────────────────────

        elif step == "compare_price":
            session["price_comparison"] = compare_prices(
                session["selected_item"],
                session["search_results"],
            )

            comparison = session["price_comparison"]

            # STRETCH BRANCH:
            # If the selected item costs more than the average comparable
            # listing, switch to the cheapest comparable option.
            if comparison["assessment"] == "above_average":
                cheapest_item = comparison["cheapest_item"]

                if (
                    cheapest_item is not None
                    and cheapest_item["id"]
                    != session["selected_item"]["id"]
                ):
                    session["selected_item"] = cheapest_item

            step = "suggest_outfit"

        # ── Step 4: Suggest outfit ────────────────────────────────────────────

        elif step == "suggest_outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"],
                session["wardrobe"],
            )

            step = "create_fit_card"

        # ── Step 5: Create fit card ───────────────────────────────────────────

        elif step == "create_fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"],
                session["selected_item"],
            )

            step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(
            f"  fit_card is {session['fit_card']!r} "
            "— it should still be None here"
        )
        return

    item = session["selected_item"] or {}

    print(
        f"  found:    {item.get('title')} — "
        f"${item.get('price')} on {item.get('platform')}"
    )

    if session["price_comparison"]:
        comparison = session["price_comparison"]

        print(
            f"  price:    ${comparison.get('selected_price')} selected / "
            f"${comparison.get('average_price')} average"
        )

        print(
            f"  price assessment: "
            f"{comparison.get('assessment')}"
        )

    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")

    _show(
        run_agent(
            query="looking for a vintage graphic tee under $30",
            wardrobe=get_example_wardrobe(),
        )
    )

    print("\n=== A query it can't ===")

    _show(
        run_agent(
            query="designer ballgown size XXS under $5",
            wardrobe=get_example_wardrobe(),
        )
    )

    print(
        "\nThe second one should stop before the fit card. "
        "If both paths look the same,\n"
        "the branch isn't doing anything yet."
    )