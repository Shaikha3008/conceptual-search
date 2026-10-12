.PHONY: help install check dry-run mock-smoke estimate-full check-live \
        run-full run-polish run-baseline run-baseline-entrants run-universe-scoring \
        run-championship run-baseline-championship run-semantic figures robustness-tests \
        gov-mock gov-one gov-full air-seeds air-search air-polish air-championship air-mock

# Run id of the searches reported in the paper.  Set RUN_ID=... to reproduce
# the pipeline under a new id.
RUN_ID ?= 2026-08-08_deepseekv32-evalrank15-full
PYTHON ?= python3
MODEL := deepseek/deepseek-v3.2
FIRM_SET := in/firm-set-15-evalrank.txt
STEPS := 12
CACHE := out/$(RUN_ID)-call-cache.sqlite3
export PYTHONDONTWRITEBYTECODE := 1

help:
	@printf '%s\n' \
	  'Conceptual search: code and records for the paper' \
	  '' \
	  'Setup and validation (no API calls):' \
	  '  make install            Install the Python dependencies (src/requirements.txt)' \
	  '  make check              Syntax checks and deterministic unit tests' \
	  '  make dry-run            Print the search workflow and write a manifest without running it' \
	  '  make mock-smoke         Run the one-step pipeline offline with mock model responses' \
	  '  make figures            Rebuild the paper figures and tables from the preserved records' \
	  '  make robustness-tests   Unit tests of the two cross-evaluator checks' \
	  '' \
	  'Live stages, in order (paid; require OPENROUTER_API_KEY; set RUN_ID for a new run):' \
	  '  make estimate-full             Cost estimate for run-full' \
	  '  make run-full                  Global search, local search, seed-benchmark scoring, semantic scores' \
	  '  make run-polish                Twelve rounds of local search on each final-generation concept' \
	  '  make run-baseline              Local search from each of the other 14 seeds (local-only comparison)' \
	  '  make run-baseline-entrants     Collect the 14 local-only finals into a tournament entrants file' \
	  '  make run-universe-scoring      Score every searched concept against the 30-venture reference set' \
	  '  make run-championship          Final tournament: polished descendants, parents, finals, and the 30 originals' \
	  '  make run-baseline-championship Same tournament for the local-only finals' \
	  '  make run-semantic              Semantic distances of the local-only finals and the polished slate (no API calls)' \
	  '' \
	  '' \
	  'Government initiatives (see GOVERNMENT.md; results go to out-gov/):' \
	  '  make gov-mock    Free offline test with fake AI answers' \
	  '  make gov-one     Improve ONE idea step by step (paid, cheap). GOV_IDEA=<id> picks the idea' \
	  '  make gov-full    Improve, mix, and rank all 15 ideas (paid)' \
	  '' \
	  'Air-pollution experiment (AIR.md; results go to out-air/):' \
	  '  make air-mock          Every stage offline with fake AI answers' \
	  '  make air-seeds         The model writes 15 UAE initiatives (paid, small)' \
	  '  make air-search        12 rounds of search over them (paid)' \
	  '  make air-polish        Polish the best AIR_POLISH_TOP finalists (paid)' \
	  '  make air-championship  Finalists vs 30 real global initiatives (paid)' \
	  '' \
	  'The README documents every stage, its outputs, and the numbers it supports.'

install:
	$(PYTHON) -m pip install -r src/requirements.txt

check:
	$(PYTHON) -c 'import ast, pathlib; [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in list(pathlib.Path("src").glob("*.py")) + list(pathlib.Path("analysis").glob("*.py"))]'
	$(PYTHON) -m unittest discover -s src/tests -v

dry-run:
	$(PYTHON) src/run_pipeline.py --firm-set $(FIRM_SET) --model $(MODEL) --steps $(STEPS) \
	  --run-id dry-run-check --run-kind full --quality-scope all-points --dry-run

mock-smoke:
	$(PYTHON) src/run_pipeline.py --firm-set $(FIRM_SET) --model $(MODEL) --steps 1 \
	  --run-id offline-smoke --run-kind smoke --quality-scope all-points --max-concurrent-calls 20 --mock

estimate-full:
	$(PYTHON) src/estimate_cost.py --firms 15 --steps $(STEPS) --model $(MODEL) \
	  --common-quality seed-benchmark --common-quality-scope all-points

check-live:
	@test -n "$$OPENROUTER_API_KEY" || { printf '%s\n' 'ERROR: Export OPENROUTER_API_KEY before starting a paid run.'; exit 2; }

run-full: check-live
	$(PYTHON) src/run_pipeline.py --firm-set $(FIRM_SET) --model $(MODEL) --steps $(STEPS) \
	  --quality-calibration seed-benchmark --quality-scope all-points \
	  --run-id "$(RUN_ID)" --run-kind full --max-concurrent-calls 40

run-polish: check-live
	$(PYTHON) src/polish_population.py --run-id "$(RUN_ID)" --model $(MODEL) --steps $(STEPS) --per-run-concurrency 8

run-baseline: check-live
	$(PYTHON) analysis/run_baseline15.py --run-id "$(RUN_ID)" --firm-set $(FIRM_SET) --model $(MODEL) --steps $(STEPS)

run-baseline-entrants:
	$(PYTHON) analysis/collect_baseline15.py --run-id "$(RUN_ID)" --phase entrants

# Every unique concept from the focal local and global searches against all 30
# reference ventures, both presentation orders.  The seed-benchmark validation
# expects the 30-venture firm set here.
run-universe-scoring: check-live
	AI_ENTREP_EXPECTED_FIRM_COUNT=30 AI_ENTREP_CALL_CACHE=$(CACHE) AI_ENTREP_MAX_CONCURRENT_CALLS=40 \
	$(PYTHON) src/common_quality.py \
	  --local-csv out/$(RUN_ID)-local-search.csv --global-csv out/$(RUN_ID)-global-search.csv \
	  --firm-set in/firm-set-30.txt --model $(MODEL) --run-prefix "$(RUN_ID)-universe" \
	  --input-file in/projects.csv --output-dir out --scope all-points

run-championship: check-live
	AI_ENTREP_CALL_CACHE=$(CACHE) AI_ENTREP_MAX_CONCURRENT_CALLS=40 $(PYTHON) src/championship.py \
	  --input-file in/projects.csv --commit-round out/$(RUN_ID)-commit-round.csv \
	  --local-candidates out/$(RUN_ID)-local-candidates.csv --model $(MODEL) \
	  --run-prefix "$(RUN_ID)" --output-dir out --entrants-csv out/$(RUN_ID)-polish-entrants.csv

run-baseline-championship: check-live
	AI_ENTREP_CALL_CACHE=$(CACHE) AI_ENTREP_MAX_CONCURRENT_CALLS=40 $(PYTHON) src/championship.py \
	  --input-file in/projects.csv --commit-round out/$(RUN_ID)-commit-round.csv \
	  --local-candidates out/$(RUN_ID)-local-candidates.csv --model $(MODEL) \
	  --run-prefix "$(RUN_ID)-baseline15" --output-dir out --entrants-csv out/$(RUN_ID)-baseline15-entrants.csv

run-semantic:
	$(PYTHON) src/semantic_scores.py --input-file in/projects.csv --firm-set $(FIRM_SET) \
	  $(foreach f,$(wildcard out/$(RUN_ID)-baseline15-*-local-candidates.csv),--candidate-csv $(f)) \
	  --output out/$(RUN_ID)-baseline15-semantic-scores.csv
	$(PYTHON) src/semantic_scores.py --input-file in/projects.csv --firm-set $(FIRM_SET) \
	  --candidate-csv out/$(RUN_ID)-polish-entrants.csv \
	  --output out/$(RUN_ID)-polish-semantic-scores.csv

# Figures and tables from the preserved records (no API calls).
figures:
	$(PYTHON) analysis/compute_universe_wr.py --run-id "$(RUN_ID)"
	$(PYTHON) analysis/build_local_figs.py --run-id "$(RUN_ID)" --seed-id clockchain --firm-set $(FIRM_SET)
	$(PYTHON) analysis/build_genealogy_tree.py --run-id "$(RUN_ID)" --feature-slot g12-s04
	$(PYTHON) analysis/build_search_map.py --run-id "$(RUN_ID)" --seed-id clockchain --feature-slot g12-s04
	$(PYTHON) analysis/build_polish_figure.py --run-id "$(RUN_ID)" --firm-set $(FIRM_SET)
	$(PYTHON) analysis/build_universe_table.py
	$(PYTHON) analysis/collect_baseline15.py --run-id "$(RUN_ID)" --phase summary

robustness-tests:
	cd robustness1-gemma3-4b && $(PYTHON) -m unittest -v test_robustness.py
	cd robustness2-qwen2.5-72b && $(PYTHON) -m unittest -v test_robustness.py

# --- Government initiatives ------------------------------------------------
# Same search, government prompts (AI_ENTREP_DOMAIN=government), the 15 ideas
# in in/gov-ideas.csv, and a separate output folder.  GOVERNMENT.md explains it.
GOV_INPUT := in/gov-ideas.csv
GOV_SET := in/gov-firm-set-15.txt
GOV_SEED := proactive-benefits
GOV_IDEA ?= $(GOV_SEED)
GOV_RUN_ID ?= gov-run-01
GOV_STEPS ?= 12
GOV_OUT := out-gov
GOV_ENV := AI_ENTREP_DOMAIN=government AI_ENTREP_SEED_PROJECT_ID=$(GOV_SEED)

gov-mock:
	$(GOV_ENV) $(PYTHON) src/run_pipeline.py --input-file $(GOV_INPUT) --firm-set $(GOV_SET) \
	  --model $(MODEL) --steps 1 --run-id gov-mock --run-kind smoke --quality-calibration none \
	  --output-dir $(GOV_OUT) --max-concurrent-calls 20 --mock --force

gov-one: check-live
	AI_ENTREP_DOMAIN=government AI_ENTREP_CALL_CACHE=$(GOV_OUT)/$(GOV_RUN_ID)-$(GOV_IDEA)-call-cache.sqlite3 \
	$(PYTHON) src/local_search.py --input-file $(GOV_INPUT) --seed-id $(GOV_IDEA) --model $(MODEL) \
	  --steps $(GOV_STEPS) --run-prefix $(GOV_RUN_ID)-$(GOV_IDEA) --output-dir $(GOV_OUT)

gov-full: check-live
	$(GOV_ENV) $(PYTHON) src/run_pipeline.py --input-file $(GOV_INPUT) --firm-set $(GOV_SET) \
	  --model $(MODEL) --steps $(GOV_STEPS) --run-id $(GOV_RUN_ID) --run-kind full \
	  --quality-calibration none --output-dir $(GOV_OUT) --max-concurrent-calls 40

# --- Air-pollution experiment ------------------------------------------------
# The model writes 15 UAE initiatives (in/air-ideas.csv, one per lever in
# in/air-levers.txt, fact-checked against in/air-uae-brief.md), the usual
# search runs over them, the best finalists are polished, and a final
# tournament places them among 30 real air-pollution initiatives from around
# the world (in/air-reference-30.csv).  AIR.md explains it.
AIR_RUN_ID ?= air-run-01
AIR_OUT ?= out-air
AIR_SEED := clean-road-transport
AIR_POLISH_TOP ?= 5
AIR_ENV := AI_ENTREP_DOMAIN=government AI_ENTREP_SEED_PROJECT_ID=$(AIR_SEED)

air-seeds: check-live
	mkdir -p $(AIR_OUT)
	$(AIR_ENV) AI_ENTREP_CALL_CACHE=$(AIR_OUT)/$(AIR_RUN_ID)-call-cache.sqlite3 \
	$(PYTHON) src/generate_seeds.py --topic "air pollution" --place "the United Arab Emirates" \
	  --brief in/air-uae-brief.md --levers in/air-levers.txt --model $(MODEL) \
	  --output in/air-ideas.csv --firm-set in/air-firm-set-15.txt

air-search: check-live
	$(AIR_ENV) $(PYTHON) src/run_pipeline.py --input-file in/air-ideas.csv --firm-set in/air-firm-set-15.txt \
	  --model $(MODEL) --steps $(STEPS) --run-id $(AIR_RUN_ID) --run-kind full \
	  --quality-calibration none --output-dir $(AIR_OUT) --max-concurrent-calls 40

air-polish: check-live
	$(AIR_ENV) $(PYTHON) src/polish_population.py --run-id $(AIR_RUN_ID) --model $(MODEL) --steps $(STEPS) \
	  --per-run-concurrency 8 --top $(AIR_POLISH_TOP) --out-dir $(AIR_OUT) --seeds-file in/air-polish-seeds.csv

air-championship: check-live
	$(AIR_ENV) AI_ENTREP_CALL_CACHE=$(AIR_OUT)/$(AIR_RUN_ID)-call-cache.sqlite3 AI_ENTREP_MAX_CONCURRENT_CALLS=40 \
	$(PYTHON) src/championship.py --input-file in/air-reference-30.csv \
	  --commit-round $(AIR_OUT)/$(AIR_RUN_ID)-commit-round.csv \
	  --local-candidates $(AIR_OUT)/$(AIR_RUN_ID)-local-candidates.csv --model $(MODEL) \
	  --run-prefix $(AIR_RUN_ID) --output-dir $(AIR_OUT) --entrants-csv $(AIR_OUT)/$(AIR_RUN_ID)-polish-entrants.csv

# All four stages offline, in a scratch folder, with fake AI answers.
air-mock:
	rm -rf out-air-mock && mkdir -p out-air-mock
	$(AIR_ENV) AI_ENTREP_MOCK_LLM=1 $(PYTHON) src/generate_seeds.py --topic "air pollution" \
	  --place "the United Arab Emirates" --brief in/air-uae-brief.md --levers in/air-levers.txt \
	  --output out-air-mock/ideas.csv --firm-set out-air-mock/firm-set.txt
	$(AIR_ENV) $(PYTHON) src/run_pipeline.py --input-file out-air-mock/ideas.csv --firm-set out-air-mock/firm-set.txt \
	  --model $(MODEL) --steps 12 --run-id mock --run-kind smoke --quality-calibration none \
	  --output-dir out-air-mock --max-concurrent-calls 20 --mock --force
	$(AIR_ENV) $(PYTHON) src/polish_population.py --run-id mock --steps 1 --top 2 --mock \
	  --out-dir out-air-mock --seeds-file out-air-mock/polish-seeds.csv
	$(AIR_ENV) AI_ENTREP_MOCK_LLM=1 AI_ENTREP_CALL_CACHE= $(PYTHON) src/championship.py \
	  --input-file in/air-reference-30.csv --commit-round out-air-mock/mock-commit-round.csv \
	  --local-candidates out-air-mock/mock-local-candidates.csv --run-prefix mock \
	  --output-dir out-air-mock --entrants-csv out-air-mock/mock-polish-entrants.csv
