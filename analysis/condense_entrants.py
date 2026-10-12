#!/usr/bin/env python3
"""Add length-matched copies of the polished finalists to a tournament.

The search lets texts grow, and the evaluator tends to favour longer texts,
so a 1,400-word finalist against a 540-word reference initiative partly
measures length.  This script asks the model to shorten each polished
descendant in an entrants CSV to the reference set's length, without adding
anything, checks each short version with the fidelity auditor against its
long original, and appends the accepted versions to the entrants CSV with
kind "polished-condensed".  Requires AI_ENTREP_DOMAIN=government.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import statistics

import config
from agents_common import FidelityAuditor, _chat, _strip_fences, _track_planned, get_usage_stats
from semantic_novelty import COMPONENTS, component_texts

csv.field_size_limit(10**9)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ROLE = "Condenser"
MAX_DRAFTS = 4
SLACK = 1.15  # accept up to 15% over the target length

CONDENSE_PROMPT = """\
Below is a proposed government initiative.

--- BEGIN PROJECT ---
{plan}
--- END PROJECT ---

Shorten it to at most {words} words. Keep every Markdown heading, in order, \
and keep the most important content of each section. Do not add any new idea, \
fact, number, name or claim; only shorten and rephrase what is there. Keep every \
proposal framed as proposed or planned.

Respond with a JSON object: {{"plan": "the shortened initiative"}}
Output only valid JSON, nothing else."""


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--entrants-csv", required=True)
    ap.add_argument("--reference-csv", required=True,
                    help="Reference set whose median length is the target.")
    ap.add_argument("--model", default=config.DEFAULT_OPENROUTER_MODEL)
    return ap.parse_args()


async def condense(row: dict, words: int, auditor: FidelityAuditor) -> dict | None:
    prompt = CONDENSE_PROMPT.format(plan=row["plan_text"], words=words)
    for draft in range(1, MAX_DRAFTS + 1):
        _track_planned(ROLE)
        raw = await _chat(config.GENERATOR_MODEL, prompt, role=ROLE,
                          context=f"{row['id']} (draft {draft})",
                          temperature=config.GENERATOR_TEMPERATURE)
        try:
            plan = str(json.loads(_strip_fences(raw))["plan"])
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("%s draft %d: unreadable answer", row["id"], draft)
            continue
        n = len(plan.split())
        missing = [c for c, t in component_texts(plan).items() if t == "Not specified."]
        if n > words * SLACK or missing:
            logger.warning("%s draft %d: %d words, missing %s", row["id"], draft, n, missing)
            continue
        audit = await auditor.audit([("LONG VERSION", row["plan_text"])], plan,
                                    context=f"condensed {row['id']} (draft {draft})")
        if audit.get("unavailable"):
            raise RuntimeError("fidelity audit unavailable; rerun to resume")
        if audit["passed"]:
            logger.info("%s condensed to %d words on draft %d", row["id"], n, draft)
            return {"id": row["id"].replace("-polished", "-condensed"),
                    "kind": "polished-condensed", "plan_text": plan}
        logger.warning("%s draft %d rejected: %s", row["id"], draft, audit["unsupported_claims"])
    logger.error("%s: no acceptable short version; left out", row["id"])
    return None


async def main() -> None:
    args = parse_args()
    if os.environ.get("AI_ENTREP_DOMAIN", "").strip().lower() != "government":
        raise SystemExit("set AI_ENTREP_DOMAIN=government")
    config.set_all_agent_models(args.model)
    with open(args.reference_csv, newline="", encoding="utf-8") as f:
        words = int(statistics.median(len(r["description"].split()) for r in csv.DictReader(f)))
    with open(args.entrants_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if any(r["kind"] == "polished-condensed" for r in rows):
        raise SystemExit("entrants file already holds condensed versions")
    auditor = FidelityAuditor()
    polished = [r for r in rows if r["kind"] == "polished-descendant"]
    short = [s for s in await asyncio.gather(*(condense(r, words, auditor) for r in polished)) if s]
    with open(args.entrants_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "kind", "plan_text"], quoting=csv.QUOTE_ALL)
        w.writerows(short)
    logger.info("Target %d words; added %d of %d condensed entrants | usage %s",
                words, len(short), len(polished), get_usage_stats())


if __name__ == "__main__":
    asyncio.run(main())
