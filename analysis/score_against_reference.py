#!/usr/bin/env python3
"""Score ideas against a reference set, both presentation orders.

Each idea in --ideas-csv (id, description) meets every initiative in
--reference-csv twice, once in each position, with the search's Evaluator.
Writes one row per judgment and a summary of each idea's win rate against
the reference set.  Requires AI_ENTREP_DOMAIN=government for government runs.
"""

import argparse
import asyncio
import csv
import logging

import config
from agents_common import Evaluator, get_usage_stats

csv.field_size_limit(10**9)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ideas-csv", required=True)
    ap.add_argument("--reference-csv", required=True)
    ap.add_argument("--matches-out", required=True)
    ap.add_argument("--summary-out", required=True)
    ap.add_argument("--model", default=config.DEFAULT_OPENROUTER_MODEL)
    return ap.parse_args()


def read(path: str) -> list[tuple[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["id"], r["description"]) for r in csv.DictReader(f)]


async def main() -> None:
    args = parse_args()
    config.set_all_agent_models(args.model)
    ideas, refs = read(args.ideas_csv), read(args.reference_csv)
    evaluator = Evaluator()
    specs = [(i, r, first) for i in ideas for r in refs for first in ("idea", "reference")]
    results = []
    for start in range(0, len(specs), config.MATCH_BATCH_SIZE):
        batch = specs[start:start + config.MATCH_BATCH_SIZE]
        results += await asyncio.gather(*(
            evaluator._match(i[1], r[1], i[0], r[0]) if first == "idea"
            else evaluator._match(r[1], i[1], r[0], i[0])
            for i, r, first in batch
        ))
        logger.info("%d / %d judgments done", len(results), len(specs))
    wins: dict[str, float] = {}
    with open(args.matches_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["idea_id", "reference_id", "idea_position", "winner", "analysis"])
        for (i, r, first), (letter, analysis) in zip(specs, results):
            idea_letter = "A" if first == "idea" else "B"
            if letter == "TIE":
                winner, score = "tie", 0.5
            elif letter == idea_letter:
                winner, score = i[0], 1.0
            else:
                winner, score = r[0], 0.0
            wins[i[0]] = wins.get(i[0], 0.0) + score
            w.writerow([i[0], r[0], "A" if first == "idea" else "B", winner, analysis])
    n = 2 * len(refs)
    with open(args.summary_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["idea_id", "wins", "matches", "win_rate"])
        for idea_id, _ in sorted(ideas, key=lambda x: -wins[x[0]]):
            w.writerow([idea_id, f"{wins[idea_id]:.1f}", n, f"{wins[idea_id] / n:.6f}"])
            logger.info("  %-26s %5.1f%%", idea_id, wins[idea_id] / n * 100)
    logger.info("Usage: %s", get_usage_stats())


if __name__ == "__main__":
    asyncio.run(main())
