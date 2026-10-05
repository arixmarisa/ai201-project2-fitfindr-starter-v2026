"""
Persistent style memory for FitFindr.

Items selected during successful runs are saved to a JSON file so they can be
used as wardrobe items during later runs.
"""

import json
from pathlib import Path


MEMORY_FILE = Path("data/style_memory.json")


def load_style_memory() -> dict:
    """
    Load saved wardrobe items from previous FitFindr runs.

    Returns:
        A wardrobe dictionary with an "items" list.
    """

    if not MEMORY_FILE.exists():
        return {"items": []}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "items" not in data:
            return {"items": []}

        return data

    except (json.JSONDecodeError, OSError):
        return {"items": []}


def merge_wardrobes(base_wardrobe: dict, saved_wardrobe: dict) -> dict:
    """
    Combine the provided wardrobe with saved style-memory items.

    Duplicate item IDs are only included once.
    """

    combined_items = []
    seen_ids = set()

    for item in base_wardrobe.get("items", []):
        item_id = item.get("id")

        if item_id not in seen_ids:
            combined_items.append(item)
            seen_ids.add(item_id)

    for item in saved_wardrobe.get("items", []):
        item_id = item.get("id")

        if item_id not in seen_ids:
            combined_items.append(item)
            seen_ids.add(item_id)

    return {"items": combined_items}


def save_item_to_memory(listing: dict) -> None:
    """
    Save a selected listing as a wardrobe item for future runs.
    """

    memory = load_style_memory()

    wardrobe_item = {
        "id": f"saved_{listing.get('id')}",
        "name": listing.get("title", "Saved thrift item"),
        "category": listing.get("category", ""),
        "colors": listing.get("colors", []),
        "style_tags": listing.get("style_tags", []),
        "notes": (
            f"Saved from {listing.get('platform', 'unknown platform')} "
            f"for ${listing.get('price', 0):.2f}"
        ),
    }

    existing_ids = {
        item.get("id")
        for item in memory.get("items", [])
    }

    if wardrobe_item["id"] in existing_ids:
        return

    memory.setdefault("items", []).append(wardrobe_item)

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def clear_style_memory() -> None:
    """
    Clear saved FitFindr style memory.
    """

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump({"items": []}, file, indent=2)