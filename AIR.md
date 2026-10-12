# Air-pollution experiment: AI-written UAE initiatives against 30 real ones

This experiment keeps the paper's flow (search, polish, final tournament
against a fixed reference set) and changes the setting.

- **Topic:** air pollution in the United Arab Emirates.
- **Starting ideas:** the model writes them itself.
- **Reference set:** 30 real air-pollution initiatives from around the world,
  with their measured results. They replace the paper's 30 crowdfunding
  campaigns.

It runs on the government prompts (`AI_ENTREP_DOMAIN=government`, see
`GOVERNMENT.md`).

## Inputs (`in/`)

| File | What it is |
|---|---|
| `air-uae-brief-sources.md` | A sourced brief on UAE air quality (28 links) |
| `air-uae-brief.md` | 37 facts from that brief: the only UAE facts the starting ideas may state, and the fact-checker's source |
| `air-levers.txt` | 15 levers (road transport, ports, power and desalination, construction dust, sandstorms, indoor air, …), one starting idea each |
| `air-ideas.csv`, `air-firm-set-15.txt` | The 15 initiatives the model wrote (`make air-seeds`), each one passing the fact-check |
| `air-reference-30.csv`, `air-firm-set-30.txt` | 30 real initiatives (London ULEZ, Kraków coal ban, US Acid Rain Program, IMO 2020, Delhi GRAP, …). Each is about 540 words under the same nine headings, with the 142 source URLs in the `sources` column |

## Stages

```bash
make air-mock          # every stage offline with fake AI answers (free)
make air-seeds         # the model writes the 15 initiatives
make air-search        # 12 rounds of search, commit round, local search from clean-road-transport
make air-polish        # 12 rounds of polish on the AIR_POLISH_TOP (default 5) best finalists
# optional fairness control: add ~540-word versions of the polished finalists
AI_ENTREP_DOMAIN=government AI_ENTREP_CALL_CACHE=out-air/air-run-01-call-cache.sqlite3 PYTHONPATH=src \
  python3 analysis/condense_entrants.py --entrants-csv out-air/air-run-01-polish-entrants.csv \
  --reference-csv in/air-reference-30.csv
make air-championship  # every finalist and all 30 real initiatives, every pair, both orders
# the 15 first drafts against the 30 real initiatives
AI_ENTREP_DOMAIN=government AI_ENTREP_CALL_CACHE=out-air/air-run-01-call-cache.sqlite3 PYTHONPATH=src \
  python3 analysis/score_against_reference.py --ideas-csv in/air-ideas.csv \
  --reference-csv in/air-reference-30.csv \
  --matches-out out-air/air-run-01-seeds-vs-reference-matches.csv \
  --summary-out out-air/air-run-01-seeds-vs-reference.csv
```

## Results of run `air-run-01` (October 2026, DeepSeek V3.2, $13.98)

Performance is each idea's win rate against the 30 real initiatives. Each idea
meets each real initiative in both orders.

| Group | Win rate against the 30 real |
|---|---|
| Real initiatives (each against the other 29) | 10%–88%; the top 13 places are all real |
| The model's 15 first drafts | 40%–65%, median 50% |
| Best finalist after 12 rounds of search | 60% (rank 14 of 45) |
| Commit-round champion (picked against the 15 drafts) | 18% |
| The 5 finalists after polishing | 22%–53% (all lower than before polishing) |
| Polished finalists shortened to about 540 words | 30%–50% |

What this run shows:

1. **Search did not beat the best first draft.**
   - The best first draft ("Flare-to-Fuel", gas capture in oil and gas, 65%) scored above every searched or polished idea.
   - Most first drafts were already level with the middle of the real set.
2. **Polishing made the finalists worse against real initiatives.** Texts grew to about 1,400 words, three times the real ones. Shortened versions did better than the long polished ones in 2 of 3 cases.
3. **The internal yardstick misled.**
   - The champion was picked because it beat the 15 first drafts, yet it scored 18% against real initiatives.
   - A near-identical sibling scored 60%, so single judgments of long texts are noisy.
4. **Convergence again.** All 5 finalists descend from the same mix of urban greening, ports, road transport, heavy industry and sandstorms. The final ideas centre on an emissions standard for commercial fleets.
5. **The judge rewards proven, measured results.**
   - Real programmes with strong evidence (the transboundary air-pollution convention, Kraków, China's power-plant standards, IMO 2020, the Acid Rain Program) lead.
   - Information-only or weak-result programmes (Breathe London, Delhi GRAP, Mexico City's driving ban) trail.

**Caveats:**
- One run, one judge model.
- The AI's ideas are proposals, while the real initiatives report results.
- The model's own texts ran longer than the reference descriptions throughout.

## Records (`out-air/`)

These follow the same file layout as `out/` (see README):
- `air-run-01-global-*`, `-local-*` and `-commit-round.csv`: the search.
- `-polish-*`: the polish runs.
- `-championship*`: the final tournament.
- `-seeds-vs-reference*`: the first drafts against the 30 real initiatives.

The SQLite call caches stay out of git.
