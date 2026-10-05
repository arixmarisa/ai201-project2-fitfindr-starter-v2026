# FitFindr

Arianna Mekovich

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is a multi-tool shopping and styling agent that helps a user search thrift
listings using a plain-language request such as `vintage graphic tee under $30`.
The agent searches the available listings, compares prices between similar items,
and selects an item to continue with. It then uses the user's wardrobe to suggest
outfits and generates a short fit-card caption containing information about the
selected listing. FitFindr also remembers successfully selected items between
runs so they can become part of the user's wardrobe for future outfit suggestions.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches the listings data for items matching the user's description and optionally filters results by size and maximum price.
- **Inputs:** `description` (`str`), `size` (`str | None`), `max_price` (`float | None`)
- **Returns:** A `list[dict]` of matching listing dictionaries ordered from best keyword match to lowest. Each result contains listing information including `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **When it has nothing:** Returns an empty list `[]`.

### `suggest_outfit`

- **What it does:** Uses the selected listing and the user's wardrobe to generate one or two outfit suggestions.
- **Inputs:** `new_item` (`dict`), `wardrobe` (`dict`)
- **Returns:** A non-empty `str` containing outfit suggestions that use the selected item and, when available, pieces from the user's wardrobe.
- **When it has nothing:** If the wardrobe contains no items, it returns general styling advice for the selected item instead of failing.

### `create_fit_card`

- **What it does:** Turns an outfit suggestion and selected listing into a short social-style caption about the thrift find.
- **Inputs:** `outfit` (`str`), `new_item` (`dict`)
- **Returns:** A `str` containing a two-to-four sentence caption that mentions the item, its price, its platform, and the overall outfit vibe.
- **When it has nothing:** If `outfit` is empty or whitespace, it returns a descriptive message instead of calling the model or raising an error.

### `compare_prices`

- **What it does:** Compares the selected item's price with similar matching listings in the same category.
- **Inputs:** `selected_item` (`dict`), `matches` (`list[dict]`)
- **Returns:** A `dict` containing the selected item's price, the average price of comparable listings, the cheapest comparable listing, and an assessment of whether the selected item is above, below, or equal to the average price.
- **When it has nothing:** If no comparable listings are available, it returns a dictionary with no average price and keeps the selected item as the comparison result.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:**

If `search_listings` returns an empty list, the agent stores a helpful message
in `session["error"]` and stops before calling `suggest_outfit`. Otherwise, it
selects the first search result and sends it to the price comparison step.

The second branch occurs after `compare_prices`. If the selected listing is
priced above the average price of comparable listings in the same category,
the agent switches `session["selected_item"]` to the cheapest comparable
listing. Otherwise, it keeps the original selected listing.

After the branches are complete, the selected item is passed through the
session to `suggest_outfit`, and the resulting outfit is then passed through
the session to `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** The query is parsed with regular expressions.
The parser extracts phrases such as `under $30` into `max_price` and
`size M` into `size`. The remaining words are used as the listing description.

**What moves through the session:** The query is stored first, followed by the
parsed description, size, and maximum price. Search results are stored in
`session["search_results"]`, the chosen listing is stored in
`session["selected_item"]`, the price comparison is stored in
`session["price_comparison"]`, the outfit is stored in
`session["outfit_suggestion"]`, and the final caption is stored in
`session["fit_card"]`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```text
$ python agent.py

=== A query the data can match ===
  found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
  price:    $18.0 selected / $20.57 average
  price assessment: below_average
  outfit:   Here are two great ways to style the Y2K baby tee using pieces already in your wardrobe:

**Outfit 1: Classic Y2K Streetwear**
*   **Bottoms:** Baggy straight-leg jeans (dark wash)
*   **Outerwear:** Black cropped zip hoodie (worn open or layered over top)
*   **Shoes:** Chunky white sneakers
*   **Accessories:** Black crossbody bag
*   *Why it works:* The fitted silhouette of the baby tee balances the volume of the baggy jeans, leaning fully into the Y2K aesthetic.

**Outfit 2: High-Low Contrast**
*   **Bottoms:** Wide-leg khaki trousers
*   **Outerwear:** Vintage black denim jacket
*   **Shoes:** Black combat boots
*   **Accessories:** Brown leather belt and black crossbody bag
*   *Why it works:* Pairing the sweet, graphic butterfly tee with structured earth-toned trousers and edgy boots creates a cool, balanced contrast between cottagecore and streetwear.

  fit card: Channel your inner 2000s pop star with this adorable butterfly print Y2K baby tee! It gives the ultimate sweet-yet-edgy nostalgic vibe and is up for grabs on Depop for just $18.00. Grab it before it’s gone and level up your streetwear rotation! 🦋✨

=== A query it can't ===
  stopped: I couldn't find a matching listing. Try using fewer description words, choosing a different size, or increasing your maximum price.
  fit_card is None — it should still be None here

The second one should stop before the fit card. If both paths look the same,
the branch isn't doing anything yet.

## search_listings

$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

Returned matching listings including:
- Y2K Baby Tee — Butterfly Print — $18.00
- Graphic Tee — 2003 Tour Bootleg Style — $24.00
- Vintage Band Tee — Faded Grey — $19.00

## suggest_outfit

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"

Returned two outfit suggestions using the Vintage Levi's 501 Jeans and pieces
from the example wardrobe, including a white ribbed tank, vintage black denim
jacket, chunky white sneakers, and black combat boots.

## create_fit_card

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Pair these jeans with a fitted white tee and sneakers for a casual streetwear look.', load_listings()[0]))"

Nothing beats the fit of true vintage Levi's 501s, and this medium wash pair is
an absolute dream. Throw them on with a crisp white tee and your favorite
sneakers for the ultimate effortless streetwear look. Grab these beauties now
for just $38.00 before they're gone. Head over to my Depop to shop!

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

*What I asked for:* I used AI to review the design for search_listings and help determine a simple way to rank listings while still supporting the required description, size, and maximum-price filters.
*What came back:* The suggested implementation tokenized the user's description and listing fields, counted overlapping keywords, filtered out zero-score results, and ranked the remaining listings by their scores.
*What I changed:* While testing the search, I kept the keyword-overlap approach but added safer size matching instead of using a basic substring comparison. This prevents values such as S from accidentally matching unrelated sizes such as US 9.

**Moment 2**

*What I asked for:* I used AI to review my fourth-tool price comparison idea and the second planning-loop branch.
*What came back:* The first version compared the selected listing against every search result. Testing vintage jeans caused a $18 baby tee to become the cheapest result because it also contained the word vintage.
*What I changed:* I changed compare_prices so it only compares listings in the same category as the selected item. After the change, the $38 Levi's jeans were compared against other bottoms, producing an average price of $34.00 and identifying $30 black jeans as the cheaper comparable listing.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---
## Stretch Features

I plan to implement all three Unit 3 stretch features:

### Fourth Tool — Price Comparison

FitFindr includes a fourth tool named `compare_prices`. It compares the selected
item with matching listings in the same category.

It returns the selected item's price, the average price of comparable listings,
the cheapest comparable listing, and an assessment of whether the selected item
is above, below, or equal to the average price.

During testing with `vintage jeans`, the selected Vintage Levi's 501 Jeans cost
$38.00 while the comparable average was $34.00. The tool returned
`above_average` and identified the $30.00 Straight Leg Black Jeans as the
cheapest comparable option.

### Second Branch — Price Comparison

The planning loop includes a second branch after `compare_prices`.

If the selected item's price is above the average price of comparable listings,
FitFindr replaces `session["selected_item"]` with the cheapest comparable item.
Otherwise, it keeps the original selected item.

The `vintage jeans` run triggered this branch because the initially selected
$38.00 Levi's jeans were above the $34.00 average, so FitFindr selected the
$30.00 Straight Leg Black Jeans instead.

### Style Memory

FitFindr remembers selected items between runs using
`data/style_memory.json`.

After a successful run, the selected listing is saved in the same structure as
a wardrobe item. At the beginning of a later run, `agent.py::run_agent` loads
the saved memory and merges it with the provided wardrobe.

In the first test run, FitFindr saved the Y2K Baby Tee — Butterfly Print.
During the second run, that saved item was loaded into the wardrobe automatically
without the user entering it again. Duplicate saved items are ignored by ID.

---
📖 **How to run this project: [RUNNING.md](RUNNING.md)**
