
#!/usr/bin/env python3
"""
Run your scenarios repeatedly and write the results down. ← UNIT 4

    python run_eval.py --label before      five tries, the default
    python run_eval.py --label after       after your improvement
    python run_eval.py --tries 10          more tries

This does the mechanical half of unit 4 for you. It runs every scenario in
`scenarios.py` five separate times, **with caching off** so you get five real
answers, captures the trace and the session for each, and writes it all into
`results/` in the table format the submission asks for.

Five, because your criteria are written out of five — "4 of 5 tries", "5 of 5
tries". One column per try means you count the passes and read the verdict
straight off the row, with no arithmetic in between.

⚠️ What it does NOT do is decide whether a try passed.

That judgment is yours, and it has to be, because it depends on criteria you
wrote. The Verdict column comes out blank and you fill it in from the output
underneath. Deciding what counts as a pass is the lesson — a scorer handed to
you would teach you nothing.

**Two of your three tools call a model, so tries will legitimately differ.**
That is expected here, unlike pair 1. If all five tries come back identical
on a criterion that involves the fit card, check that you're really in test
mode — caching is what usually explains it.
"""

import argparse
import datetime as dt
import re
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

import config
import scenarios as scenario_module


def run_once(scenario, use_trace=True):
    """One scenario, one try. Returns everything worth recording."""
    import agent
    import style_memory
    import trace as trace_module
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    wardrobe = (
        get_empty_wardrobe() if scenario["wardrobe"] == "empty"
        else get_example_wardrobe()
    )

    record = {
        "error": None,
        "session": None,
        "trace": "",
        "crashed": None,
        "evidence": {},
    }

    # UNIT 4: Observe the actual argument received by suggest_outfit.
    # This wrapper does not change its input or output.
    real_suggest_outfit = agent.suggest_outfit

    def observed_suggest_outfit(selected_item, current_wardrobe):
        record["evidence"]["passed_item_id"] = selected_item.get("id")
        record["evidence"]["passed_wardrobe_ids"] = [
            item.get("id") for item in current_wardrobe.get("items", [])
        ]
        return real_suggest_outfit(selected_item, current_wardrobe)

    try:
        with patch.object(agent, "suggest_outfit", observed_suggest_outfit):
            if scenario.get("criterion") == 5:
                # Give each try its own memory file. Restore the real user's
                # memory path afterward, even if the run fails.
                with tempfile.TemporaryDirectory(prefix="fitfindr_eval_") as folder:
                    with patch.object(
                        style_memory, "MEMORY_FILE",
                        Path(folder) / "style_memory.json",
                    ):
                        # First run saves its item into isolated memory.
                        first = agent.run_agent(
                            scenario["query"], wardrobe, save_memory=True
                        )
                        first_item = first.get("selected_item") or {}
                        saved_id = (
                            f"saved_{first_item['id']}"
                            if not first.get("error") and first_item.get("id")
                            else None
                        )
                        record["evidence"]["first_run_error"] = first.get("error")
                        record["evidence"]["saved_item_id"] = saved_id
                        record["evidence"]["memory_after_first_run"] = (
                            style_memory.load_style_memory()
                        )

                        if use_trace:
                            trace_module.start_trace()

                        # Second run must load the previously saved item.
                        # Disable additional saving so the evidence stays focused.
                        record["session"] = agent.run_agent(
                            scenario["followup_query"],
                            wardrobe,
                            save_memory=False,
                        )
            else:
                if use_trace:
                    trace_module.start_trace()
                record["session"] = agent.run_agent(
                    scenario["query"], wardrobe, save_memory=False
                )
    except Exception as exc:  # noqa: BLE001 — a crash is a result worth logging
        record["crashed"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()

    if use_trace:
        record["trace"] = trace_module.get_trace()

    session = record["session"] or {}
    item = session.get("selected_item") or {}
    record["evidence"]["session_item_id"] = item.get("id")

    if scenario.get("criterion") == 3:
        record["evidence"]["ids_match"] = bool(
            item.get("id") and item.get("id") ==
            record["evidence"].get("passed_item_id")
        )

    if scenario.get("criterion") == 4:
        card = session.get("fit_card") or ""
        price = item.get("price")
        platform = str(item.get("platform") or "")
        price_options = []
        if isinstance(price, (int, float)):
            price_options = [f"${price:g}", f"${price:.2f}"]
        sentences = [
            part for part in re.split(r"(?<=[.!?])\s+", card.strip())
            if part
        ]
        record["evidence"].update({
            "price_present": any(p in card for p in price_options),
            "platform_present": bool(
                platform and platform.lower() in card.lower()
            ),
            "sentence_count_approx": len(sentences),
            "sentence_count_note": "Review punctuation manually for final scoring",
        })

    if scenario.get("criterion") == 5:
        saved_id = record["evidence"].get("saved_item_id")
        record["evidence"]["loaded_in_session"] = bool(
            saved_id and saved_id in {
                i.get("id") for i in session.get("wardrobe", {}).get("items", [])
            }
        )
        record["evidence"]["received_by_outfit_tool"] = bool(
            saved_id and saved_id in record["evidence"].get(
                "passed_wardrobe_ids", []
            )
        )

    return record


def main():
    parser = argparse.ArgumentParser(
        description="Run the scenarios and log the results."
    )
    parser.add_argument(
        "--tries", "--trials",
        type=int,
        default=5,
        dest="tries",
        help="tries per scenario (default 5, matching your criteria)",
    )
    parser.add_argument(
        "--label",
        default="",
        help="a name for this run, e.g. 'before'",
    )
    args = parser.parse_args()

    problems = scenario_module.validate()
    if problems:
        print("scenarios.py has problems:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        sys.exit(1)

    if not scenario_module.SCENARIOS:
        print(
            "scenarios.py is empty. Milestone 3 starts by filling it in.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.tries < 5:
        print(
            f"⚠️  {args.tries} tries. Your criteria are written out of five.\n"
        )

    # Caching off. Five tries have to be five real answers.
    config.CACHE_ENABLED = False
    print("Cache is OFF for this run — that's deliberate.\n")

    rows = []
    for scenario in scenario_module.SCENARIOS:
        print(f"{scenario['name']}  ({scenario['wardrobe']} wardrobe)")
        print(f"  query: {scenario['query']}")

        if scenario.get("followup_query"):
            print(f"  second query: {scenario['followup_query']}")

        tries = []
        for attempt in range(1, args.tries + 1):
            record = run_once(scenario)
            tries.append(record)

            if record["crashed"]:
                print(
                    f"  try {attempt}: CRASHED — {record['crashed']}"
                )
            else:
                session = record["session"] or {}

                if session.get("error"):
                    print(
                        f"  try {attempt}: stopped early — "
                        f"{str(session['error'])[:60]}"
                    )
                else:
                    card = session.get("fit_card") or ""
                    print(
                        f"  try {attempt}: completed — "
                        f"fit card {len(card)} chars"
                    )

                if scenario.get("criterion") in (3, 4, 5):
                    print(f"    evidence: {record['evidence']}")

        rows.append({
            "scenario": scenario,
            "tries": tries,
        })
        print()

    write_report(rows, args)


def write_report(rows, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)

    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"run_{stamp}{label}.md"

    n = args.tries
    headers = " | ".join(f"Try {i}" for i in range(1, n + 1))
    divider = "|".join(["---"] * n)

    lines = [
        f"# Run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `run_eval.py::main`",
        "- Loop: `agent.py::run_agent` · MCP tools: `mcp_server.py`",
        f"- Tries per scenario: {n}, caching off",
        f"- Temperature: {config.TEMPERATURE}",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Paste the table below into your README. Fill in the Criterion and",
        "Target columns from `criteria.md`, then mark each try PASS or FAIL",
        "from the output underneath and count them for the Verdict.",
        "",
        f"| Criterion | Target | {headers} | Verdict |",
        f"|---|---|{divider}|---|",
    ]

    for row in rows:
        scenario = row["scenario"]
        number = scenario.get("criterion")

        # A scenario with "criterion": None is a diagnostic run, not one of
        # your five. It's marked so you don't paste an unnumbered row into a
        # table the README asks you to number 1-5.
        label_text = (
            f"{number}. {scenario['name']}"
            if number
            else (
                f"{scenario['name']} "
                "_(diagnostic — not one of your five)_"
            )
        )

        lines.append(
            f"| {label_text} |  | {' | '.join([' '] * n)} |  |"
        )

    lines += [
        "",
        "> The Try and Verdict columns are blank on purpose. Whether a try",
        "> passed depends on the criterion you wrote, so it's yours to decide.",
        "> Count the passes, then read that count against your target: a row",
        "> targeting 4 of 5 with three PASS cells is MISSED (3/5).",
        "",
        "---",
        "",
        "## What actually happened",
        "",
        "Real output, as text. Paste the relevant parts into your README —",
        "the rubric asks for output, not a description of it.",
        "",
    ]

    for row in rows:
        scenario = row["scenario"]

        lines += [
            f"### {scenario['name']}",
            "",
            f"- Query: `{scenario['query']}`",
            f"- Wardrobe: {scenario['wardrobe']}",
            "",
        ]

        if scenario.get("followup_query"):
            lines += [
                f"- Follow-up query: `{scenario['followup_query']}`",
                "",
            ]

        for i, record in enumerate(row["tries"], 1):
            lines.append(f"**Try {i}**")
            lines.append("")

            if record["crashed"]:
                lines += [
                    "Crashed:",
                    "",
                    "```",
                    record["crashed"],
                    "```",
                    "",
                ]
                lines += [
                    "Traceback:",
                    "",
                    "```",
                    record.get("traceback", ""),
                    "```",
                    "",
                ]
                continue

            session = record["session"] or {}
            item = session.get("selected_item") or {}

            lines += [
                (
                    "- stopped early: "
                    + (
                        "yes — " + str(session.get("error"))
                        if session.get("error") else "no"
                    )
                ),
                f"- selected_item: {item.get('title', '(none)')}"
                + (
                    f" (${item.get('price')}, {item.get('platform')})"
                    if item else ""
                ),
                f"- search_results: {len(session.get('search_results') or [])}",
                "",
            ]

            if record["evidence"]:
                lines += [
                    "Measured evidence:",
                    "",
                    "```",
                    repr(record["evidence"]),
                    "```",
                    "",
                ]

            if session.get("outfit_suggestion"):
                lines += [
                    "Outfit suggestion:",
                    "",
                    "```",
                    str(session["outfit_suggestion"]),
                    "```",
                    "",
                ]

            if session.get("fit_card"):
                lines += [
                    "Fit card:",
                    "",
                    "```",
                    str(session["fit_card"]),
                    "```",
                    "",
                ]

            if record["trace"]:
                lines += [
                    "Trace:",
                    "",
                    "```",
                    record["trace"],
                    "```",
                    "",
                ]

    path.write_text("\n".join(lines), encoding="utf-8")

    import generate

    print(f"Wrote {path.relative_to(config.ROOT)}")
    print(generate.usage())
    print("\nCommit this file. It's the evidence the test actually happened.")

    if not any(r["tries"][0]["trace"] for r in rows):
        print(
            "\nNote: no trace was captured. You haven't added trace.step() calls\n"
            "to run_agent() yet — that's Milestone 2, and the trace is required\n"
            "evidence worth a point."
        )


if __name__ == "__main__":
    main()
