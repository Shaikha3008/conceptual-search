"""Government-initiative versions of the search prompts.

Loaded instead of the crowdfunding prompts when AI_ENTREP_DOMAIN=government
(see the end of local_search_prompts.py and global_search_prompts.py).  Every
template keeps the same placeholders and the same section markers as the
original, so the agents and the offline mock parse them unchanged.  The judge
gives the most weight to impact on people and to innovation.
"""

EVALUATION_CRITERIA = """\
1. Impact on people: how many residents, families, workers, or businesses benefit, and how much their lives improve (highest weight)
2. Innovation: how new the approach is compared with existing government services and common practice (highest weight)
3. Clarity of the problem and of the proposed initiative
4. Feasibility and delivery plan
5. Funding and long-term sustainability
6. Measurable outcomes and evidence plan (clear indicators and how they will be tracked)
7. Risk awareness, inclusion, privacy, and mitigation"""

FACTUAL_FIDELITY_RULES = """\
Treat the supplied initiative description(s) as the complete factual record. You may propose \
new services, target groups, delivery channels, funding models, pilots, partnerships, targets, \
indicators, projections, or plans only when they are explicitly framed as proposed, \
hypothetical, planned, or to be tested. Do not invent or imply existing pilots, users, \
beneficiaries, adoption figures, budgets, approvals, legal mandates, endorsements by named \
ministries, agencies, or officials, signed partnerships, awards, rankings, completed systems, \
launch status, team credentials, dates, or quantified results. Do not convert a recommendation \
or aspiration into an accomplished fact. Preserve any factual claims that are carried forward \
from a source without strengthening them."""

GENERATOR_PROMPT = """\
You are an expert government innovation advisor. Below is a proposed government initiative:

--- BEGIN PROJECT ---
{plan}
--- END PROJECT ---

Evaluate this initiative along these dimensions:
{criteria}

Suggest exactly {num_ideas} concrete, actionable improvement ideas that would make this \
initiative more valuable to the people it serves and more innovative. Each idea should propose \
a *small, targeted change* (not a complete rewrite). Suggestions must obey these rules:
{fidelity_rules}

Respond with a JSON object: {{"ideas": ["idea 1", "idea 2", ...]}}
Output only valid JSON, nothing else."""

SPECIALIZED_GENERATOR_PROMPT = """\
You are an expert writer of government initiative proposals. Below is a proposed government \
initiative followed by one specific improvement idea.

--- BEGIN PROJECT ---
{plan}
--- END PROJECT ---

--- IMPROVEMENT IDEA ---
{idea}
--- END IDEA ---

Rewrite the initiative description incorporating the improvement idea above. \
Keep the overall structure, Markdown headings, and tone, but integrate the improvement \
naturally. The updated description should be approximately 500 words and must obey these rules:
{fidelity_rules}

Respond with a JSON object: {{"plan": "updated initiative description", \
"evidence_notes": "brief note identifying any proposed or source-supported claims"}}
Output only valid JSON, nothing else."""

EVALUATOR_PROMPT = """\
You are an expert reviewer of government initiatives, deciding which proposals deserve \
public investment. Compare the two initiative descriptions below along these criteria:
{criteria}

Give the most weight to impact on people and to innovation.

--- PROJECT A ---
{plan_a}
--- END PROJECT A ---

--- PROJECT B ---
{plan_b}
--- END PROJECT B ---

For each initiative, list its pros and cons as bullet points (use "•" as the bullet marker), \
grounded in the criteria above. Do not reward unsupported specificity: claims of existing \
pilots, adoption, approvals, partnerships, budgets, or quantified results should improve an \
initiative's assessment only when they are genuine source facts. Then state which initiative \
wins overall and why.

Respond with a JSON object: {{"analysis": "your analysis here", "winner": "A" or "B"}}
Output only valid JSON, nothing else."""

FIDELITY_AUDITOR_PROMPT = """\
You are auditing factual fidelity in a generated government initiative proposal.

--- AUTHORIZED SOURCE MATERIAL ---
{sources}
--- END AUTHORIZED SOURCE MATERIAL ---

--- GENERATED CANDIDATE ---
{candidate}
--- END GENERATED CANDIDATE ---

Apply this standard:
{fidelity_rules}

Pass the candidate only if every statement about existing real-world evidence or status is \
supported by the authorized source material. New ideas are allowed when clearly framed as \
proposals, plans, targets, hypotheses, or future tests. Unsupported claims include invented \
pilots, users, beneficiaries, adoption figures, budgets, approvals, legal mandates, \
endorsements, signed partnerships, awards, completed systems, launch status, team \
credentials, dates, and quantified results.

Apply the tense distinction literally. Specificity does not turn a future proposal into an \
existing fact. For example, "we plan to pilot the service in two districts," "the initiative \
proposes tracking waiting times monthly," and "a future phase would target 5,000 households" \
are allowed new ideas even when those targets are absent from the source. Reject only when the \
candidate states or implies that such evidence, activity, status, or relationship already \
exists. Do not reject a candidate merely because a proposed plan is new, detailed, or \
quantified. When every addition is explicitly prospective, the candidate must pass.

Distinguish the initiative's proposed design from claims of accomplished evidence. A \
proposal's account of what the service is, does, or would offer -- its features, channels, \
target groups, funding model, or positioning -- is the proposal itself, even when written in \
present tense, and may legitimately be new relative to the sources, including an initiative \
assembled from components of multiple source proposals. Do not reject design descriptions for \
being absent from the sources. Reject only assertions of existing real-world accomplishments or \
status -- completed systems, running pilots, current users or beneficiaries, approved budgets, \
signed agreements, endorsements, awards, or measured results -- that the sources do not support.

Respond with a JSON object: {{"passed": true or false, \
"unsupported_claims": ["exact or concise claim", ...], \
"analysis": "brief explanation"}}
Output only valid JSON, nothing else."""

NARRATIVE_DIFF_PROMPT = """\
Below are two versions of a government initiative proposal.

--- OLD VERSION ---
{old_plan}
--- END OLD VERSION ---

--- NEW VERSION ---
{new_plan}
--- END NEW VERSION ---

Summarize in 2-3 sentences what changed between the old and new version. \
Focus on the key differences in content, emphasis, or strategy. \
Output only the summary, nothing else."""


# --- Global search (mutation and crossover) ---------------------------------

MUTATION_COMPONENT_GUIDANCE = {
    "problem": "the public problem, unmet need, or pain point people face",
    "customer": "the people who benefit (residents, families, workers, businesses) and their situation",
    "solution": "the service, program, or mechanism that addresses the problem",
    "delivery_model": "how the government develops, delivers, and supports the service, and through which channels",
    "revenue_logic": "who funds it (government budget, fees, partners, savings) and how it stays sustainable",
    "distinctiveness": "why this approach is new and differs meaningfully from existing services",
}

MUTATOR_PROMPT = """\
You are an expert government innovation advisor. Here is a proposed government initiative:

--- BEGIN PROJECT ---
{plan}
--- END PROJECT ---

The search algorithm selected this component for mutation:
{component}: {component_guidance}

Make one substantive change to that component only. Preserve the other five \
components and all source-grounded facts as closely as possible. Keep the \
existing Markdown headings so that the components remain machine-readable.

Rewrite the initiative description incorporating only that one improvement. \
The updated description should be approximately 500 words and must obey these rules:
{fidelity_rules}

Respond with a JSON object: {{"component": "{component}", "plan": "rewritten initiative description"}}
Output only valid JSON, nothing else."""

CROSSOVER_PROMPT = """\
You are an expert government strategist. Here are two proposed government initiatives:

--- PARENT A ---
{plan_a}
--- END PARENT A ---

--- PARENT B ---
{plan_b}
--- END PARENT B ---

Create a NEW government initiative by RECOMBINING the two parents at the level of \
their six components: problem, customer, solution, delivery_model, \
revenue_logic, distinctiveness.

Recombination rules:
1. For each of the six components, choose exactly ONE parent as its source. Take at \
least two components from each parent. Use these criteria to decide which parent \
supplies the stronger version of each component:
{criteria}
2. Carry each chosen component's substantive DESIGN over faithfully: its approach, \
mechanism, target group, framing, and reasoning. But the child is a brand-new \
proposal with no history of its own: do NOT carry claims of existing pilots, users, \
beneficiaries, budgets, approvals, completed systems, launch status, partners, awards, \
or any other accomplished evidence from either parent. Where a source component's \
strength rests on such evidence, re-express the underlying idea as an explicitly \
proposed plan or target for the new initiative.
3. Rewrite only the connective tissue -- the one-sentence summary and minimal \
transitional phrasing -- so the recombined description reads as ONE coherent new \
initiative built from those components, approximately 500 words, not a patchwork. \
The problem, the people served, and the solution must fit together.
4. Keep the source proposals' Markdown headings so the six components remain \
machine-readable. The child must not be a restatement of either parent.

Treat the parents as the complete factual record and obey these rules:
{fidelity_rules}

Every statement about evidence, validation, partnerships, or performance in the \
child must be framed as proposed, planned, or to-be-tested -- never as an \
accomplishment inherited from a parent.

Respond with a JSON object: {{"component_map": {{"problem": "A" or "B", "customer": "A" or "B", "solution": "A" or "B", "delivery_model": "A" or "B", "revenue_logic": "A" or "B", "distinctiveness": "A" or "B"}}, "plan": "the new initiative description"}}
Output only valid JSON, nothing else."""

CROSSOVER_FIDELITY_AUDITOR_PROMPT = """\
You are auditing a proposed government initiative that was deliberately \
assembled by RECOMBINING components of the two source proposals below. The \
recombined initiative itself -- what the proposed service is, does, or would \
offer, its features, channels, target groups, funding model, positioning, and \
plans -- is ALLOWED to be new relative to the sources, even when written in \
present tense. Do not flag design, feature, positioning, or plan statements \
for being absent from the sources.

--- AUTHORIZED SOURCE MATERIAL ---
{sources}
--- END AUTHORIZED SOURCE MATERIAL ---

--- GENERATED CANDIDATE ---
{candidate}
--- END GENERATED CANDIDATE ---

Your ONLY task: list every statement in the candidate that asserts an \
ALREADY-EXISTING real-world accomplishment or status of this new initiative -- \
for example: completed or running systems, pilots already run, current users \
or beneficiaries, approved budgets, legal mandates already granted, measured \
results, endorsements, awards, signed partners, or team credentials. The \
candidate is a brand-new proposal with no operating history, so ANY such \
assertion about this initiative is unsupported and must be listed -- including \
accomplishments copied from a source proposal, because those belong to the \
source, not to this new one. Statements framed as proposed, planned, targeted, \
hypothetical, or to-be-tested are allowed and must not be listed. Apply this \
standard:
{fidelity_rules}

If the candidate asserts no already-existing accomplishments of its own, it \
passes.

Respond with a JSON object: {{"passed": true or false, "unsupported_claims": \
["exact or concise claim", ...], "analysis": "brief explanation"}}
Output only valid JSON, nothing else."""

NARRATIVE_MUTATION_PROMPT = """\
Here is a parent government initiative proposal:

--- PARENT ---
{parent_plan}
--- END PARENT ---

Here is the mutated child proposal, which was modified along the "{dimension}" dimension:

--- CHILD ---
{child_plan}
--- END CHILD ---

In 2-3 sentences, describe how the mutation changed the proposal along the \
{dimension} dimension. Focus on what specifically was added, removed, or altered."""

NARRATIVE_CROSSOVER_PROMPT = """\
Here are two parent government initiative proposals:

--- PARENT A ({a_id}) ---
{a_plan}
--- END PARENT A ---

--- PARENT B ({b_id}) ---
{b_plan}
--- END PARENT B ---

Here is the child proposal produced by crossing the two parents:

--- CHILD ---
{child_plan}
--- END CHILD ---

In 2-3 sentences, describe what the child inherited from each parent. \
Identify which elements came from {a_id} and which from {b_id}."""
