"""
Persistent style memory for FitFindr.

This module saves selected thrift items so they can be used as wardrobe
pieces during future FitFindr runs.
"""

import json

import config


# Store memory relative to the project's configured data directory rather
# than relative to whichever directory the program was launched from.
MEMORY_FILE = config.DATA_DIR / "style_memory.json"


def load_style_memory() -> dict:
    """
    Load saved wardrobe items from persistent style memory.

    Returns:
        A dictionary containing an "items" list.
    """

    if not MEMORY_FILE.exists():
        return {
            "items": []
        }

    try:
        with MEMORY_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (json.JSONDecodeError, OSError):
        return {
            "items": []
        }

    if not isinstance(data, dict):
        return {
            "items": []
        }

    if "items" not in data:
        return {
            "items": []
        }

    if not isinstance(data["items"], list):
        return {
            "items": []
        }

    return data


def merge_wardrobes(
    base_wardrobe: dict,
    saved_wardrobe: dict,
) -> dict:
    """
    Combine the supplied wardrobe with saved style-memory items.

    Duplicate items are ignored using their IDs.
    """

    combined_items = []
    seen_ids = set()

    for item in base_wardrobe.get("items", []):
        item_id = item.get("id")

        if item_id not in seen_ids:
            combined_items.append(item)

            if item_id is not None:
                seen_ids.add(item_id)

    for item in saved_wardrobe.get("items", []):
        item_id = item.get("id")

        if item_id not in seen_ids:
            combined_items.append(item)

            if item_id is not None:
                seen_ids.add(item_id)

    return {
        "items": combined_items
    }


def save_item_to_memory(listing: dict) -> None:
    """
    Save a successful thrift listing as a future wardrobe item.

    If the same listing has already been saved, it is not duplicated.
    """

    memory = load_style_memory()

    listing_id = listing.get("id")

    wardrobe_item = {
        "id": f"saved_{listing_id}",
        "name": listing.get(
            "title",
            "Saved thrift item",
        ),
        "category": listing.get(
            "category",
            "",
        ),
        "colors": listing.get(
            "colors",
            [],
        ),
        "style_tags": listing.get(
            "style_tags",
            [],
        ),
        "notes": (
            f"Saved from {listing.get('platform')} "
            f"for ${listing.get('price', 0):.2f}"
        ),
    }

    existing_ids = {
        item.get("id")
        for item in memory.get("items", [])
    }

    if wardrobe_item["id"] in existing_ids:
        return

    memory["items"].append(
        wardrobe_item
    )

    MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MEMORY_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            memory,
            file,
            indent=2,
        )


def clear_style_memory() -> None:
    """
    Clear all saved FitFindr style-memory items.
    """

    MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MEMORY_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "items": []
            },
            file,
            indent=2,
        )