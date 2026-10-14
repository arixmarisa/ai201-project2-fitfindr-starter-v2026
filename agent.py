
"""
The FitFindr planning loop.

This file connects the FitFindr tools and decides what to do next based on
what each tool returns.
"""

import re

import config
import trace

from mcp_client import call_tool, MCPError
from tools import (
    suggest_outfit,
    create_fit_card,
)

from style_memory import (
    load_style_memory,
    merge_wardrobes,
    save_item_to_memory,
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
        "price_branch_taken": False,
        "wardrobe": wardrobe,
        "memory_items_loaded": [],
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
        "retry_dropped_constraint": None,
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

    # Remove common request words that do not help the search.
    description = re.sub(
        r"\b(looking for|find me|show me|i want|i need|a|an)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )

    # Clean up spaces and punctuation.
    description = re.sub(r"\s+", " ", description)
    description = description.strip(" ,.-")

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(
    query: str,
    wardrobe: dict,
    save_memory: bool = True,
) -> dict:
    """
    Run the FitFindr planning loop once and return the completed session.

    save_memory controls whether a successful run permanently stores the
    selected item. Evaluation runs can set it to False so repeated tests
    do not change persistent style memory.
    """
    # Load items remembered from previous runs.
    saved_wardrobe = load_style_memory()

    # Combine saved items with the wardrobe supplied for this run.
    combined_wardrobe = merge_wardrobes(
        wardrobe,
        saved_wardrobe,
    )

    session = new_session(
        query,
        combined_wardrobe,
    )

    # Keep track of which saved items were loaded for this run.
    session["memory_items_loaded"] = [
        item.get("name")
        for item in saved_wardrobe.get("items", [])
    ]

    step = "parse"
    iteration_count = 0

    while step != "done":
        iteration_count += 1
        trace.check_iterations(iteration_count)

        # ── Step 1: Parse query ───────────────────────────────────────────────
        if step == "parse":
            session["parsed"] = parse_query(
                session["query"]
            )

            trace.step(
                "parse_query",
                inputs={"query": session["query"]},
                returned=session["parsed"],
            )

            step = "search"

        # ── Step 2: Search listings ──────────────────────────────────────────
        elif step == "search":
            parsed = session["parsed"]
            search_inputs = {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            }

            try:
                # UNIT 4: Search listings through the MCP server.
                session["search_results"] = call_tool(
                    "search_listings", search_inputs
                )
                trace.step(
                    "search_listings (via MCP)",
                    inputs=search_inputs,
                    returned=session["search_results"],
                )

                # UNIT 4 STRETCH: Retry once without the size filter.
                if not session["search_results"] and parsed["size"] is not None:
                    session["retry_dropped_constraint"] = (
                        f"size={parsed['size']}"
                    )
                    retry_inputs = {
                        "description": parsed["description"],
                        "size": None,
                        "max_price": parsed["max_price"],
                    }
                    print(
                        "No matching listings found. "
                        f"Retrying without size {parsed['size']}."
                    )
                    session["search_results"] = call_tool(
                        "search_listings", retry_inputs
                    )
                    trace.step(
                        "search_listings retry (via MCP)",
                        inputs=retry_inputs,
                        returned=session["search_results"],
                        note=f"Dropped size constraint: {parsed['size']}",
                    )
            except MCPError as exc:
                session["error"] = (
                    "The listing search tool couldn't be reached through MCP. "
                    f"Details: {exc}. Please check the MCP server and try again."
                )
                trace.step(
                    "search_listings (via MCP) error",
                    inputs=search_inputs,
                    note=str(exc),
                )
                step = "done"
                continue

            # REQUIRED BRANCH:
            # Stop if search_listings returned nothing.
            if not session["search_results"]:
                session["error"] = (
                    "I couldn't find a matching listing. Try using fewer "
                    "description words, choosing a different size, or "
                    "increasing your maximum price."
                )
                trace.step(
                    "empty_search_branch",
                    returned=session["search_results"],
                    note="No listings found; stopping before price comparison.",
                )
                step = "done"
                continue

            # Start with the highest-ranked search result.
            session["selected_item"] = (
                session["search_results"][0]
            )
            trace.step(
                "select_item",
                inputs={"result_count": len(session["search_results"])},
                returned=session["selected_item"],
            )

            step = "compare_price"

        # ── Step 3: Compare prices ───────────────────────────────────────────
        elif step == "compare_price":
            compare_inputs = {
                "selected_item": session["selected_item"],
                "matches": session["search_results"],
            }
            try:
                # UNIT 4 STRETCH: Price comparison through MCP as well.
                session["price_comparison"] = call_tool(
                    "compare_prices", compare_inputs
                )
            except MCPError as exc:
                session["error"] = (
                    "The price comparison tool couldn't be reached through MCP. "
                    f"Details: {exc}. Please check the MCP server and try again."
                )
                trace.step(
                    "compare_prices (via MCP) error",
                    inputs=compare_inputs,
                    note=str(exc),
                )
                step = "done"
                continue

            trace.step(
                "compare_prices (via MCP)",
                inputs=compare_inputs,
                returned=session["price_comparison"],
            )
            comparison = session["price_comparison"]

            # STRETCH BRANCH:
            # If the selected item is above the average price,
            # switch to the cheapest comparable listing.
            if comparison["assessment"] == "above_average":
                cheapest_item = comparison["cheapest_item"]
                if (
                    cheapest_item is not None
                    and cheapest_item["id"]
                    != session["selected_item"]["id"]
                ):
                    session["selected_item"] = cheapest_item
                    session["price_branch_taken"] = True
                    trace.step(
                        "above_average_branch",
                        returned=session["selected_item"],
                        note="Switched to cheapest comparable listing.",
                    )

            step = "suggest_outfit"

        # ── Step 4: Suggest outfit ───────────────────────────────────────────
        elif step == "suggest_outfit":
            outfit_inputs = {
                "selected_item": session["selected_item"],
                "wardrobe": session["wardrobe"],
            }
            try:
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"],
                    session["wardrobe"],
                )
            except ModelUnavailable as exc:
                session["error"] = (
                    "The model is temporarily unavailable, so I couldn't "
                    "generate an outfit suggestion. Please check your "
                    "connection or API key and try again."
                )
                trace.step(
                    "suggest_outfit error",
                    inputs=outfit_inputs,
                    note=str(exc),
                )
                step = "done"
                continue

            trace.step(
                "suggest_outfit",
                inputs=outfit_inputs,
                returned=session["outfit_suggestion"],
            )
            step = "create_fit_card"

        # ── Step 5: Create fit card ──────────────────────────────────────────
        elif step == "create_fit_card":
            card_inputs = {
                "outfit_suggestion": session["outfit_suggestion"],
                "selected_item": session["selected_item"],
            }
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"],
                    session["selected_item"],
                )
            except ModelUnavailable as exc:
                session["error"] = (
                    "The model is temporarily unavailable, so I couldn't "
                    "create the fit card. Please check your connection "
                    "or API key and try again."
                )
                trace.step(
                    "create_fit_card error",
                    inputs=card_inputs,
                    note=str(exc),
                )
                step = "done"
                continue

            trace.step(
                "create_fit_card",
                inputs=card_inputs,
                returned=session["fit_card"],
            )

            # STRETCH FEATURE:
            # Save the selected item only when persistent memory is enabled.
            if save_memory:
                save_item_to_memory(
                    session["selected_item"]
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

    if session["price_branch_taken"]:
        print(
            "  branch:   above_average branch taken — "
            f"switched to {item.get('title')} at ${item.get('price')}"
        )

    if session["memory_items_loaded"]:
        print(
            "  memory:   loaded "
            + ", ".join(session["memory_items_loaded"])
        )

    print(
        f"  outfit:   {session['outfit_suggestion']}"
    )

    print(
        f"  fit card: {session['fit_card']}"
    )


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
