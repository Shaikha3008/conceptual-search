# Using conceptual search for government initiatives

This setup runs the same AI search as the paper, but on **government
initiative ideas** instead of crowdfunding projects. The AI judge gives the
most weight to **impact on people** and **innovation**.

## What is in the setup

| File | What it is |
|---|---|
| `in/gov-ideas.csv` | The 15 starting ideas: one row per idea (`id`, `area`, `description`) |
| `in/gov-firm-set-15.txt` | The list of the 15 idea ids the search starts from. The first one is the idea that "improve one idea" mode uses |
| `src/government_prompts.py` | What each AI agent is told: the advisor, the writer, the judge, the fact-checker, and the mixer |

The government prompts are only used when `AI_ENTREP_DOMAIN=government` is
set. The `make gov-...` commands set it for you. Without it, the repository
behaves exactly as in the paper.

## The 15 starting ideas

Automatic social benefits, one-stop business licensing, heat safety for
outdoor workers, companionship for seniors, a feedback loop for government
services, micro-internships for students, recycling rewards, home
tele-rehabilitation, a traffic digital twin, water-leak alerts, a citizen
policy lab, a skills passport, school wellbeing checks, flash-flood warnings,
and easier procurement for small businesses.

The ideas are **deliberately mixed in quality**. Some are detailed and some
are short and vague, so the AI has room to improve them. Everything is written
as a *proposal* ("the initiative proposes…", "would…"), with no invented
facts, budgets, or approvals.

## How to run it

One-time setup:

```bash
pip install -r src/requirements.txt
```

**1. Free test (fake AI answers, no key, no cost)**

```bash
make gov-mock
```

This only checks that everything works. The ideas it produces are not real.

**2. Improve one idea (real AI, cheap)**

```bash
export OPENROUTER_API_KEY=your-key       # from openrouter.ai
make gov-one                             # improves proactive-benefits
make gov-one GOV_IDEA=skills-passport    # or pick any id from the list
make gov-one GOV_STEPS=3                 # fewer rounds = cheaper test
```

**3. Improve, mix, and rank all 15 ideas (real AI)**

```bash
make gov-full
```

Use `GOV_RUN_ID=my-run-02` to start a new run instead of resuming the old one.

**Rough cost**, estimated from the paper's run (about $0.0005 per AI call on
DeepSeek). Your real cost may differ:

- `gov-one`, 12 rounds: about 500 calls, well under $1
- `gov-full`: about 5,300 calls, a few dollars, and about an hour

If a run stops halfway, run the same command again. Calls that already
finished are reused from the cache, so you don't pay for them twice.

## Where to look at the results

Everything goes into the `out-gov/` folder. You can open the `.csv` files in
Excel.

| File | What it tells you |
|---|---|
| `…-local-search-narrative.txt` | A plain-English story of how one idea changed, round by round |
| `…-local-candidates.csv` | Every version the AI wrote. The last row with `selected = True` is the final improved idea |
| `…-global-candidates.csv` | Every idea in every generation, including mixes of two ideas (`crossover`). Rows with `step = 12` are the final generation |
| `…-commit-round.csv` | The row with `selected = True` is the overall winner |
| `…-fidelity-audits.csv` | Which texts the fact-checker rejected, and why |

## How to change it for your own work

- **Your own ideas:** edit `in/gov-ideas.csv`.
  - Keep the same headings, because the system uses them to split each idea
    into its 6 parts: `## Problem`, `## Target Beneficiaries & Use Cases`,
    `## Solution / Service Overview`, `## Delivery Model`,
    `## Funding & Sustainability`, `## What Makes It New`.
  - Then update the id list in `in/gov-firm-set-15.txt`. The full search
    needs **exactly 15** ideas.
  - The first id in the list must match `GOV_SEED` in the `Makefile`.
- **What the judge cares about:** edit `EVALUATION_CRITERIA` (and the "Give
  the most weight to…" line in `EVALUATOR_PROMPT`) in
  `src/government_prompts.py`.
- **Check your changes:** run `make check`. The tests catch broken prompts
  and ideas with a missing heading.

## Be careful

- **The AI judges its own work.** Use the rankings as a helper, not the
  truth. A person should review the final ideas.
- **Mixed ideas can be patchy.** When two ideas are combined, the parts don't
  always fit together. Read them before using them.
- **Don't put confidential or sensitive information in the ideas.** Every
  text is sent to an outside AI service (OpenRouter).
