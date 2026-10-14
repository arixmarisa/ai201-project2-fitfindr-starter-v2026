# FitFindr

**Arianna Mekovich**

> **Start here:** Read [RUNNING.md](RUNNING.md) for setup, commands, and troubleshooting.
>
> After `python test.py` passes, try:
>
> ```bash
> python app.py listings --full -n 6
> python app.py fields
> python app.py ask 'vintage graphic tee under $30' --trace
> ```
>
> **Project repository:** https://github.com/arixmarisa/ai201-project2-fitfindr-starter-v2026

---

## What This Does

FitFindr is a multi-tool shopping and styling agent that helps a user search thrift listings using a plain-language request such as `vintage graphic tee under $30`. The agent searches available listings, compares prices among similar items, and selects an item to continue with. It uses the user's wardrobe to suggest outfits and generates a short fit-card caption containing details about the selected listing. FitFindr can save selected items to style memory so they become available in future outfit suggestions.

## Tool Inventory

### `search_listings`

- **What it does:** Searches the listing data by description, with optional size and maximum-price filters; ranks results by overlapping keywords.
- **Inputs:** `description` (`str`), `size` (`str | None`), `max_price` (`float | None`).
- **Returns:** A `list[dict]` of matching listings, ranked by keyword overlap. Listings include `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **When it has nothing:** Returns `[]`. The agent may retry once with the size constraint removed before stopping.

### `suggest_outfit`

- **What it does:** Generates one or two outfit ideas using the selected thrift item and, when available, pieces already in the user's wardrobe.
- **Inputs:** `new_item` (`dict`), `wardrobe` (`dict`).
- **Returns:** A `str` containing practical outfit suggestions and named wardrobe pieces when available.
- **When it has nothing:** If the wardrobe has no items, generates general styling ideas instead of crashing. If the external model is unavailable, the agent reports an actionable error.

### `create_fit_card`

- **What it does:** Produces a short social-style caption about the selected thrift find.
- **Inputs:** `outfit` (`str`), `new_item` (`dict`).
- **Returns:** A `str` describing the item and overall vibe, including its price and platform. The current prompt requests exactly three sentences; the original acceptance criterion still permits two to four.
- **When it has nothing:** If `outfit` is empty or whitespace, returns an explanatory message without calling the model. Model unavailability is handled by the agent.

### `compare_prices`

- **What it does:** Compares prices only among matching listings in the same category as the selected item.
- **Inputs:** `selected_item` (`dict`), `matches` (`list[dict]`).
- **Returns:** A `dict` with `selected_price`, `average_price`, `cheapest_item`, and `assessment` (`above_average`, `below_average`, `average`, or `no_comparison`).
- **When it has nothing:** Returns `average_price: None`, `assessment: no_comparison`, and keeps the selected item as the cheapest item.

## Planning Loop

**Implementation:** `agent.py::run_agent`.

The parser extracts price constraints such as `under $30` and sizes such as `size M` using regular expressions. The remaining words become the description sent to `search_listings`.

**First branch — search results:** If an initial search returns no results **and a size was provided**, the agent retries the MCP search once with the size filter removed, explicitly tracing the dropped constraint. If results remain empty (or there was no size to relax), it saves a helpful message in `session["error"]` and stops without comparing prices or invoking either model tool. Otherwise it selects the first ranked listing.

**Second branch — price comparison:** The selected item is passed to `compare_prices`. When it is above the average price of comparable listings in the same category, the agent switches `session["selected_item"]` to the cheapest comparable listing. Otherwise, it keeps the original selection.

**State flow:** `query` → `parsed` → `search_results` → `selected_item` → `price_comparison` → `outfit_suggestion` → `fit_card`. Relevant intermediate state is stored in the session. Style memory is loaded and merged into the supplied wardrobe; selected items can be saved for later runs. The agent traces each decision and MCP call.

## Sample Run

**Full successful query** (`agent.py::run_agent`, illustrated by a recorded successful run):

```text
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] compare_prices (via MCP)
      out: dict with keys: selected_price, average_price, cheapest_item, assessment
[5] suggest_outfit
      out: Here are two outfit ideas using the Y2K butterfly baby tee ...
[6] create_fit_card
      out: Flutter back to the year 2000 with this sweet butterfly baby tee ...
```

A recorded complete fit card for this item:

```text
Flutter back to the year 2000 with this sweet butterfly baby tee, giving off the ultimate nostalgic streetwear vibes! You can grab this Y2K treasure on Depop right now for just $18.00. Style it with baggy denim for a classic look or toughen it up with combat boots.
```

**Impossible query:**

```text
$ python app.py ask 'designer ballgown under $1' --trace
[1] parse_query
[2] search_listings (via MCP)
      out: [] (empty)
[3] empty_search_branch
      out: [] (empty)
      → No listings found; stopping before price comparison.
I couldn't find a matching listing. Try using fewer description words, choosing a different size, or increasing your maximum price.
```

**Individual tool tests (Unit 3):**

```bash
python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Pair these jeans with a fitted white tee and sneakers for a casual streetwear look.', load_listings()[0]))"
```

The recorded search returned, among others, the Y2K Butterfly Baby Tee ($18), 2003 Tour Bootleg Graphic Tee ($24), and Faded Grey Vintage Band Tee ($19). The outfit test produced suggestions using Vintage Levi's 501 jeans and pieces such as a white tank, black denim jacket, sneakers, and combat boots. The fit-card test returned a caption for $38 vintage Levi's jeans with a Depop mention.

## How I Used AI

**Moment 1 — Search ranking and size matching.** I asked AI how to rank thrift listings while supporting description, size, and price filters. The suggested approach counted keyword overlap and removed zero-overlap matches. During testing, I improved size matching to compare separate size tokens instead of relying on substring matches, so a request for `S` would not accidentally match an unrelated size such as `US 9`.

**Moment 2 — Category-aware price comparison.** I asked AI to review my fourth-tool idea and the planning-loop price branch. The initial approach compared unrelated search results, so a baby tee could be treated as a comparable cheaper alternative to jeans. I limited price comparisons to listings in the same category. In the recorded jeans example, $38 Levi's were compared against bottoms, giving a $34 average and identifying $30 black jeans as the cheaper comparable.

---

# Unit 4 — Testing and MCP Integration

## Acceptance Criteria

The five numbered acceptance criteria and targets were established before the Unit 4 evaluations. The targets were not changed after testing.

| # | Original criterion | Target |
|---|---|---|
| 1 | A matching query completes the full three-tool sequence (`search_listings`, `suggest_outfit`, `create_fit_card`) | 4/5 |
| 2 | An impossible query stops before the second tool, without generating an outfit or card | 5/5 |
| 3 | The chosen item remains consistent in session state and is passed to the next tool | 5/5 |
| 4 | The fit card includes price, platform, and two to four sentences | 4/5 |
| 5 | A selected item saved to style memory is available to a later run | 5/5 |

`scenarios.py` defines one scenario per criterion plus an additional empty-wardrobe diagnostic. `run_eval.py` executes five tries for each scenario with caching disabled, records the session and trace, and writes Markdown logs. The evaluator intentionally leaves final PASS/FAIL judgments to manual review. Criterion 5 uses an isolated temporary memory file for each attempt, so the user's normal saved memory is not overwritten.

## Run Log — Before

**Source:** `results/run_2026-10-14_1248_before_full.md` (`run_eval.py::main` → `agent.py::run_agent`). Earlier partial runs `run_2026-10-14_1236_before.md` and `run_2026-10-14_1238_before_complete.md` remain in `results/` as additional historical evidence, but did not measure all five criteria.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes | 4/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 2. Impossible query stops early | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 3. Selected item passed correctly | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 4. Fit card includes price/platform and 2–4 sentences | 4/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)**¹ |
| 5. Saved style memory loads on a second run | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |

¹ Fit-card sentence counts are from the evaluator's approximate punctuation-based count and should be checked against the actual text. Baseline counts were **3, 3, 4, 3, 3**; all five recorded price and platform checks were true.

**Real output — selected-item consistency, criterion 3:**

```text
[5] above_average_branch
      out: Denim Vest — Medium Wash, Studded ($27.0, depop)
      → Switched to cheapest comparable listing.
[6] suggest_outfit
      in: dict with keys: selected_item, wardrobe
      out: Here are two ways to style your new studded denim vest ...
evidence: {'passed_item_id': 'lst_038', 'session_item_id': 'lst_038', 'ids_match': True}
```

**Real output — style memory, criterion 5:**

```text
saved_item_id: saved_lst_002
memory_after_first_run: {'items': [{'id': 'saved_lst_002', 'name': 'Y2K Baby Tee — Butterfly Print', ...}]}
loaded_in_session: True
received_by_outfit_tool: True
```

In each of the five memory attempts, the first run saved the selected item to its isolated memory file; the second run received that item in the wardrobe sent to `suggest_outfit`.

## Verdicts and Diagnoses

| # | Criterion | Target | Baseline verdict | How I decided |
|---|---|---|---|---|
| 1 | Full three-tool sequence | 4/5 | **MET — 5/5** | All five matching-query trials reached outfit generation and fit-card creation after the MCP search. |
| 2 | Empty-search early stop | 5/5 | **MET — 5/5** | Each impossible-query trial returned empty searches and stopped before `compare_prices`, `suggest_outfit`, or `create_fit_card`. |
| 3 | Selected-item state | 5/5 | **MET — 5/5** | The final `session_item_id` matched the item ID actually passed to `suggest_outfit` in every attempt. |
| 4 | Fit-card requirements | 4/5 | **MET — 5/5**¹ | Five cards included price and platform; approximate sentence counts were within 2–4. |
| 5 | Style-memory persistence | 5/5 | **MET — 5/5** | Every isolated two-run test loaded its saved item and passed it into the next run's outfit-tool wardrobe. |

**Diagnoses:** No original acceptance criterion was missed in the baseline. However, two concrete weaknesses were identified during repeated testing: (a) the fit-card prompt permitted variable sentence counts, and (b) temporary Gemini HTTP 503 failures could stop the agent even when a retry might succeed. The latter produced actual criterion-1 failures during the first improvement evaluation.

## Required Failure-Mode Tests

### 1. Empty search

**Input:** `python app.py ask 'designer ballgown under $1' --trace`.

**Observed:** `search_listings` returned `[]`; `empty_search_branch` stopped before price comparison or either model tool; the agent displayed a suggestion to use fewer keywords, change size, or increase price. **Handled without a crash.**

### 2. Empty wardrobe

**Input:** `python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --trace`.

**Observed:** The agent completed outfit generation and fit-card creation rather than crashing. **Qualification:** the CLI's empty input wardrobe was merged with preexisting persistent style memory, so that initial test was not a completely empty *effective* wardrobe. The isolated first run of the criterion-5 test supplied an empty wardrobe and empty temporary memory, directly exercising the general-styling behavior; it also completed.

### 3. Model unavailable

**Setup:** Temporarily altered one character in `GEMINI_API_KEY` in `.env`, disabled caching with `AI201_CACHE=0`, and ran a model-requiring query. The original key was restored before evaluations.

```text
$ AI201_CACHE=0 python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
[2] search_listings (via MCP)
[3] select_item
[4] compare_prices (via MCP)
[5] suggest_outfit error
      → The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
The model is temporarily unavailable, so I couldn't generate an outfit suggestion. Please check your connection or API key and try again.
1 model calls this session
```

The agent caught `ModelUnavailable`, surfaced an actionable message, and did not attempt fit-card creation. **Handled without a raw traceback.**

## Loop Trace

**Happy path:** `agent.py::run_agent` through the two MCP tools and both generative tools.

```text
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in: dict with keys: query
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in: dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      in: dict with keys: result_count
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] compare_prices (via MCP)
      in: dict with keys: selected_item, matches
      out: dict with keys: selected_price, average_price, cheapest_item, assessment
[5] suggest_outfit
      in: dict with keys: selected_item, wardrobe
      out: Here are two outfit ideas using the Y2K butterfly baby tee ...
[6] create_fit_card
      in: dict with keys: outfit_suggestion, selected_item
      out: Flutter back to the year 2000 with this sweet butterfly baby tee ...
```

**Empty search with retry:**

```text
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
[2] search_listings (via MCP)
      out: [] (empty)
No matching listings found. Retrying without size XXS.
[3] search_listings retry (via MCP)
      out: [] (empty)
      → Dropped size constraint: XXS
[4] empty_search_branch
      out: [] (empty)
      → No listings found; stopping before price comparison.
```

**Successful size relaxation:**

```text
$ python app.py ask 'vintage graphic tee size XXXL under $30' --trace
[2] search_listings (via MCP)
      out: [] (empty)
No matching listings found. Retrying without size XXXL.
[3] search_listings retry (via MCP)
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      → Dropped size constraint: XXXL
[4] select_item
[5] compare_prices (via MCP)
[6] suggest_outfit
[7] create_fit_card
```

**On the MCP move:** `mcp_server.py` exposes the existing `search_listings` and `compare_prices` functions. `agent.py::run_agent` invokes both through `mcp_client.call_tool`; the client listed both registered tool schemas during verification. The search, state branch, price comparison, outfit, and fit-card behavior continued to work after the move. Each MCP call is identified in the trace as `via MCP`; the size retry also passes through MCP.

## First Measured Improvement — Fit-Card Consistency

**Diagnosis:** The baseline criterion-4 samples included three- and four-sentence captions. Although the existing 2–4-sentence criterion was met in all five tries, the broad model instruction permitted more variation than needed.

**Single change:** In `tools.py::create_fit_card`, changed `Write only 2 to 4 sentences` to `Write exactly 3 complete sentences`. All other behavior was left unchanged for this phase.

### Run Log — After First Improvement

**Source:** `results/run_2026-10-14_1342_after.md`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes | 4/5 | FAIL | FAIL | PASS | PASS | PASS | **MISSED (3/5)** |
| 2. Impossible query stops early | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 3. Selected item passed correctly | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 4. Fit card includes price/platform and 2–4 sentences | 4/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)**¹ |
| 5. Saved style memory loads | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |

**Result:** The dedicated fit-card test produced exactly three sentences in **5/5** attempts, versus **4/5** baseline. Price and platform remained present in all five.

**Unexpected failure and diagnosis (model service, not the prompt):** Criterion 1 fell from 5/5 to 3/5 because Gemini returned HTTP **503 UNAVAILABLE** during `create_fit_card` on try 1 and `suggest_outfit` on try 2. The errors happened in model calls inside these tools; the agent stopped with a readable message, but no successful fit card was produced in either attempt. The first prompt change did not directly cause the provider outage. The observed failures prompted the second improvement.

```text
[6] create_fit_card error
      → Couldn't reach the model: 503 UNAVAILABLE. ... high demand ...
try 1: stopped early

[5] suggest_outfit error
      → Couldn't reach the model: 503 UNAVAILABLE. ... high demand ...
try 2: stopped early
```

## Second Measured Improvement — Temporary Model Failure Retry

**Diagnosis:** `generate.py::generate` already retried HTTP 429 rate-limit responses, but its prior exception classification treated HTTP 503 as non-retryable. A temporary provider outage therefore terminated a query immediately, even though the agent was capable of completing all tools once the provider recovered.

**Single change:** Extended the existing bounded retry and backoff logic in `generate.py` to include temporary HTTP 503 and service-unavailable errors. Permanent failures such as invalid API keys still raise `ModelUnavailable` immediately. The original three-sentence fit-card instruction remained in place.

### Run Log — After Second Improvement

**Source:** `results/run_2026-10-14_1350_after_second.md`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes | 4/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 2. Impossible query stops early | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 3. Selected item passed correctly | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 4. Fit card includes price/platform and 2–4 sentences | 4/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)**¹ |
| 5. Saved style memory loads | 5/5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |

**Observed retry and recovery:** One diagnostic empty-wardrobe trial emitted `[model retry] Temporary model error. Waiting 27s (attempt 1 of 5).` The retry completed, `suggest_outfit` returned an outfit, and `create_fit_card` returned a caption. This demonstrates successful recovery from a temporary error; the retry message **does not print the error's HTTP status**, so it cannot independently prove that this specific retry was an HTTP 503.

```text
[model retry] Temporary model error. Waiting 27s (attempt 1 of 5).
[rate limit] 15 requests used this minute. Waiting 12s. This is normal.
[6] suggest_outfit
      out: Here is an outfit combining your new denim vest ...
[7] create_fit_card
      out: Scored this epic studded denim vest for just $27.00 over on Depop! ...
try 3: completed — fit card 225 chars
```

**Outcome:** Criterion 1 returned from **3/5** to **5/5** in the final evaluation, while all other original criteria remained at **5/5**. Provider availability differs between runs, so this comparison alone does not prove a causal reliability gain; the observed retry-and-recovery trace directly supports the mechanism. Full evidence is kept in the separate result files.

### Three-Stage Comparison

| Criterion | Target | Before | After fit-card prompt | After retry handling |
|---|---|---|---|---|
| 1. Complete full tool sequence | 4/5 | 5/5 | 3/5 | 5/5 |
| 2. Stop on impossible query | 5/5 | 5/5 | 5/5 | 5/5 |
| 3. Preserve selected-item state | 5/5 | 5/5 | 5/5 | 5/5 |
| 4. Format fit card correctly | 4/5 | 5/5 | 5/5 | 5/5 |
| 5. Load saved style memory | 5/5 | 5/5 | 5/5 | 5/5 |
| **Exactly three fit-card sentences** | Additional consistency metric | **4/5** | **5/5** | **5/5** |

## What's Still Broken / Future Work

No original criterion was missed in the final evaluation, but the system still has limitations:

- **Provider reliability:** Bounded retries cannot guarantee recovery from a prolonged Gemini outage. Future work could log the HTTP status for each retry and test 503 recovery deterministically with a mocked provider response.
- **Generated-text validation:** Sentence counts are currently estimated in the evaluator, and the runtime relies on prompting rather than strictly validating or repairing caption output. A future validator could enforce price, platform, and sentence count without relying solely on the model's compliance.
- **Wardrobe realism:** The agent can load saved items as wardrobe context, but its model-generated outfit suggestions may still assume ownership of generic pieces. A future refinement could distinguish saved/owned items from hypothetical purchase suggestions.
- **Search relaxation:** Dropping the size filter helps discover alternatives, but the user may still need the original requested size. The trace identifies the relaxed constraint; a future UI could also ask for confirmation before recommending the differently sized result.

## Stretch Features

The following **Unit 4 stretch features were declared in the README before implementation**, and all three were attempted and tested.

### Stretch 1 — Second MCP Tool (+1)

In addition to `search_listings`, `mcp_server.py` registers `compare_prices`. Both tools are called via `mcp_client.py`, and both appear in ordered traces. The second tool returns the selected price, comparable average, cheapest same-category alternative, and price assessment.

### Stretch 2 — Retry With Looser Constraints (+1)

If the search is empty and the user specified a size, FitFindr retries **once** without the size constraint. The trace names the dropped constraint; a successful retry continues, while a second empty result stops before price comparison. Both the `size XXXL` successful relaxation and the `size XXS` still-empty path were exercised.

### Stretch 3 — Two Separately Measured Improvements (+2)

**Stage 1 (before):** `results/run_2026-10-14_1248_before_full.md`.

**Stage 2 (after first change):** `results/run_2026-10-14_1342_after.md` — exactly-three-sentence fit-card prompt.

**Stage 3 (after second change):** `results/run_2026-10-14_1350_after_second.md` — retry temporary HTTP 503 errors with backoff.

The original five acceptance criteria and targets were preserved across all three stages. The actual misses and observed recoveries are reported above.

---

**How to run this project:** [RUNNING.md](RUNNING.md)
