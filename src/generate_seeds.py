#!/usr/bin/env python3
"""Let the model write the starting ideas for a government search.

Each starting idea is written for one assigned lever (one line of the levers
file), using only the facts in a context brief, and is then checked by the
same fidelity auditor the search uses, with the brief as the authorized
source.  A rejected draft is rewritten (up to MAX_DRAFTS times); an idea that
never passes stops the script, so no unchecked text enters a search.

Writes an input CSV (id, area, description) and a firm-set file listing the
ids, in the format the search stages read.  Requires AI_ENTREP_DOMAIN=government.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import re

import config
from agents_common import (
    FidelityAuditor,
    _chat,
    _strip_fences,
    _track_planned,
    get_call_stats,
    get_usage_stats,
)
from local_search_prompts import FACTUAL_FIDELITY_RULES
from semantic_novelty import COMPONENTS, component_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ROLE = "Seed Generator"
MAX_DRAFTS = 3


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate starting ideas with the model.")
    ap.add_argument("--topic", required=True, help='e.g. "air pollution"')
    ap.add_argument("--place", required=True, help='e.g. "the United Arab Emirates"')
    ap.add_argument("--brief", required=True,
                    help="Markdown file of facts the ideas may use (the audit's source).")
    ap.add_argument("--levers", required=True,
                    help="Text file: one 'id | lever description' per line, one idea each.")
    ap.add_argument("--output", required=True, help="Input CSV to write.")
    ap.add_argument("--firm-set", required=True, help="Firm-set file to write.")
    ap.add_argument("--model", default=config.DEFAULT_OPENROUTER_MODEL)
    return ap.parse_args()


def read_levers(path: str) -> list[tuple[str, str]]:
    levers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            idea_id, lever = (part.strip() for part in line.split("|", 1))
            if not re.fullmatch(r"[a-z0-9-]+", idea_id):
                raise SystemExit(f"bad id {idea_id!r}: use lowercase letters, digits, hyphens")
            levers.append((idea_id, lever))
    return levers


def missing_components(plan: str) -> list[str]:
    projected = component_texts(plan)
    return [c for c in COMPONENTS if projected[c] == "Not specified."]


def mock_plan(idea_id: str, lever: str, place: str) -> str:
    sections = {
        "One-Sentence Summary": f"A proposed initiative for {place} working through {lever}.",
        "Problem": "Offline mock problem statement.",
        "Target Beneficiaries & Use Cases": "Residents who would benefit (offline mock).",
        "Solution / Service Overview": f"The initiative proposes measures on {lever}.",
        "Delivery Model": "The relevant authorities would deliver it (offline mock).",
        "Funding & Sustainability": "Proposed public funding (offline mock).",
        "What Makes It New": f"A proposed new approach for {idea_id} (offline mock).",
        "Measuring Impact": "Proposed indicators would be tracked (offline mock).",
        "Risks & Mitigation": "Proposed mitigations (offline mock).",
    }
    return "\n\n".join(f"## {h}\n\n{t}" for h, t in sections.items())


async def write_one(idea_id: str, lever: str, args, brief: str, auditor) -> dict:
    from government_prompts import SEED_GENERATOR_PROMPT

    prompt = SEED_GENERATOR_PROMPT.format(
        topic=args.topic, place=args.place, lever=lever, brief=brief,
        fidelity_rules=FACTUAL_FIDELITY_RULES,
    )
    last_problem = ""
    for draft in range(1, MAX_DRAFTS + 1):
        if config.MOCK_LLM:
            title, plan = idea_id, mock_plan(idea_id, lever, args.place)
        else:
            _track_planned(ROLE)
            raw = await _chat(
                config.GENERATOR_MODEL, prompt, role=ROLE,
                context=f"{idea_id} (draft {draft})",
                temperature=config.GENERATOR_TEMPERATURE,
            )
            try:
                data = json.loads(_strip_fences(raw))
                title, plan = str(data["title"]), str(data["plan"])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                last_problem = f"unreadable answer: {exc}"
                logger.warning("%s draft %d: %s", idea_id, draft, last_problem)
                continue
        missing = missing_components(plan)
        if missing:
            last_problem = f"missing sections: {missing}"
            logger.warning("%s draft %d: %s", idea_id, draft, last_problem)
            continue
        audit = await auditor.audit(
            [("CONTEXT BRIEF", brief)], plan, context=f"seed {idea_id} (draft {draft})",
        )
        if audit.get("unavailable"):
            raise RuntimeError(f"fidelity audit unavailable for {idea_id}; rerun to resume")
        if audit["passed"]:
            logger.info("%s accepted on draft %d (%d words): %s",
                        idea_id, draft, len(plan.split()), title)
            return {"id": idea_id, "area": lever, "title": title, "description": plan,
                    "drafts": draft, "decision_basis": audit.get("decision_basis", "")}
        last_problem = f"fact-check rejected: {audit['unsupported_claims']}"
        logger.warning("%s draft %d: %s", idea_id, draft, last_problem)
    raise SystemExit(f"{idea_id}: no acceptable draft after {MAX_DRAFTS} tries ({last_problem})")


async def main() -> None:
    args = parse_args()
    if os.environ.get("AI_ENTREP_DOMAIN", "").strip().lower() != "government":
        raise SystemExit("set AI_ENTREP_DOMAIN=government")
    config.set_all_agent_models(args.model)
    if not config.MOCK_LLM:
        config.require_openrouter_api_key()
    with open(args.brief, encoding="utf-8") as f:
        brief = f.read().strip()
    levers = read_levers(args.levers)
    auditor = FidelityAuditor()
    ideas = await asyncio.gather(
        *(write_one(idea_id, lever, args, brief, auditor) for idea_id, lever in levers)
    )
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "area", "title", "description"],
                           quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        w.writerows(ideas)
    with open(args.firm_set, "w", encoding="utf-8") as f:
        f.write(f"# Starting ideas written by the model ({args.output}).\n"
                "# The first id is the local-search seed.\n")
        f.write("\n".join(idea["id"] for idea in ideas) + "\n")
    for idea in ideas:
        logger.info("  %-28s drafts=%d  %s", idea["id"], idea["drafts"], idea["title"])
    logger.info("Calls: %s | usage: %s", get_call_stats(), get_usage_stats())


if __name__ == "__main__":
    asyncio.run(main())
