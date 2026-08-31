# Evaluator Guide — Running and Interpreting the Pilot Evaluation

This guide is for whoever is running the human playtester pilot for the
Game Balance Tool and analyzing its results — it doesn't assume you were
part of the original design discussions, so some background is included.

---

## 1. Background: what the pilot is testing

Earlier versions of this tool were evaluated using AI agents playing
through levels. This pilot instead uses **real human playtesters**, so
that recommendations can be checked against what a person actually
experiences, not just what an automated agent's telemetry shows.

The tool itself is unchanged for this purpose — playtesters use the same
Streamlit interface as any other user. The only addition is a short survey
(Section 06 of the UI) that captures how the playtester felt about what
the tool told them, tied to the specific session and iteration they just
saw. See `docs/participant_survey_guide.md` for what playtesters are told.

## 2. What "iteration" means here

A **balancing session** starts when a playtester uploads their first batch
of gameplay data (**iteration 1**, the baseline). If they then act on any
of the tool's suggestions and upload new gameplay data reflecting those
changes, that's **iteration 2** (a follow-up), and so on.

Playtesters are asked to fill in the Section 06 survey **after every
iteration**, not just once. This is deliberate: it lets you compare
ratings *before* changes were applied against ratings *after*, which is a
much stronger signal than a single end-of-session opinion. If a
playtester only ever does one iteration, that's still useful data — it
just won't contribute to the before/after comparison.

## 3. Telemetry coverage — what the in-app warning means

If a playtester's upload doesn't populate most of the optional fields for
the selected Gameplay Data Type, the tool shows a warning in Section 04:
**"Low telemetry coverage — check Gameplay Data Type or logging setup."**

This isn't about the free-text description fields in Section 01 (those
are purely descriptive and never affect the analysis). It's about the
actual telemetry data. Two likely causes:

- The **wrong Gameplay Data Type** was selected for the game (e.g.
  "Generic" chosen for a pathfinding game, so pathfinding-specific fields
  are never populated).
- The **telemetry logging integration** genuinely isn't sending those
  optional fields yet.

**What to do when you see this flagged for a session:** treat that
session's recommendations as lower-confidence. Check with the playtester
or the game's telemetry setup before drawing conclusions from it. Don't
exclude it automatically — `analyze_pilot.py` (below) surfaces this
per-session so you can decide case by case, but a quick sanity check with
whoever ran that session is usually enough to explain it.

This value is also saved (not just shown) — every session's result JSON
contains a `telemetry_coverage` object with the overall coverage
percentage, a `low_coverage_flag`, and a list of fields that were never
once populated. You don't need to read this manually — the pilot analysis
script below pulls it out automatically.

## 4. Running the evaluation script

After collecting a batch of pilot sessions, run:

```bash
python scripts/analyze_pilot.py
```

This reads everything already saved on disk under `data/` — no server
needs to be running, and nothing is modified. It's safe to re-run any
time, including partway through the pilot to check progress.

Useful flags:
```bash
# Point at a different data folder
python scripts/analyze_pilot.py --data-dir data --out-dir data/pilot_reports

# Change the telemetry coverage flag threshold (default 40%)
python scripts/analyze_pilot.py --low-coverage-threshold 0.4

# Skip PNG chart generation (e.g. if matplotlib isn't installed)
python scripts/analyze_pilot.py --no-charts
```

It writes, to `data/pilot_reports/`:
- **`pilot_summary_<timestamp>.md`** — a human-readable report. This is
  the one to read first, and the easiest to paste sections from into a
  deliverable.
- **`pilot_summary_<timestamp>.json`** — the same data, machine-readable.
- **`pilot_iterations_<timestamp>.csv`** — one row per session × iteration,
  with every objective metric and matched survey rating. Open this in
  Excel/Sheets if you want to slice the data yourself.
- **`ratings_overview.png`**, **`baseline_vs_followup.png`** — quick
  charts, generated only if `matplotlib` is installed
  (`pip install matplotlib`).

## 5. Reading the output

**Drop-off rate** — the share of sessions that never got a follow-up
iteration. A high drop-off rate might mean playtesters didn't find it
worthwhile to act on suggestions and re-test, or ran out of time — worth
noting as context, not necessarily a tool failure.

**XAI method breakdown** — shows how many iterations used `shap`,
`feature_importances`, or `variance_heuristic`. This matters because
`shap` is the default explainability method as of v4, but it (and
`feature_importances`) both require at least 2 sessions in that upload to
train a model — a single-session upload falls back to
`variance_heuristic`, a weaker heuristic. **When citing SHAP-based
explainability results specifically, filter to `shap` iterations only** —
mixing in fallback iterations would overstate how much of the pilot
actually used the "real" explainable model.

**Recommendation apply rate** — of the recommendations shown at an
iteration that was followed by another iteration, what fraction were
marked as applied before the next upload. Only counted where a follow-up
actually exists (a session with no follow-up doesn't tell you whether its
recommendations would have been applied).

**Survey ratings** — mean, response count, and 1–5 distribution for each
of the five questions, across all iterations.

**Baseline vs. follow-up** — the same five ratings, split by iteration 1
vs. iteration ≥2. This is the core "did perception improve after changes
were applied" comparison.

**Success rate vs. rating correlation (Spearman ρ)** — reported
descriptively only. See §6 below for why no significance testing is
applied.

**Written reviews** — listed verbatim at the end of the report for
qualitative reading. These aren't summarized or coded automatically —
read them yourself for themes, quotes, or context the numbers miss.

## 6. Methodological notes (for write-ups / deliverables)

**Why no LLM in the recommendation loop.** The tool's recommendations are
generated entirely by a deterministic rule engine plus a trained
GBM/SHAP model — no LLM is involved in diagnosing or phrasing
recommendations. This is deliberate: it keeps every recommendation
traceable to a specific numeric threshold or feature importance, so
disagreement in the pilot (a playtester finding a recommendation
unhelpful) can be attributed to a specific, checkable cause rather than
being entangled with an LLM's phrasing or non-determinism. In effect, the
pilot is testing **criterion validity** — do the tool's statistical flags
line up with what playtesters actually experience — rather than also
having to validate a language model's reasoning at the same time.

**Sample size.** The number of pilot participants isn't fixed in advance
and isn't under the evaluator's control. For this reason, `analyze_pilot.py`
reports everything **descriptively** (means, distributions, correlation
coefficients) rather than running significance tests. Avoid phrasing
results as "statistically significant" — "a trend was observed" or "N out
of M sessions showed X" is more honest regardless of how many
participants end up taking part.

**Section 01 fields (Start/End/Success/Failure Condition).** These are
descriptive metadata only — they are never read by the rule engine or ML
pipeline. A playtester leaving them at the default text does not weaken
their session's recommendations. If you want to note data-quality caveats
for a session, telemetry coverage (§3) is the relevant signal, not
Section 01.

**Fixed thresholds.** The rule engine uses fixed heuristic thresholds
(e.g. success rate below 30% is flagged as "too hard") applied uniformly
regardless of genre or level type. This is a known scope limitation worth
naming explicitly in any written evaluation — the tool doesn't currently
calibrate thresholds per game type.

## 7. Quick checklist for a pilot batch

- [ ] Confirm each playtester was shown `docs/participant_survey_guide.md`
      (or the gist of it) before starting
- [ ] After the batch, run `python scripts/analyze_pilot.py`
- [ ] Skim `pilot_summary_<timestamp>.md`
- [ ] Check the XAI method breakdown before citing SHAP-specific results
- [ ] Check for any `low_coverage_flag` sessions and follow up if needed
- [ ] Read the written reviews for qualitative context
- [ ] Report results descriptively, not as significance-tested claims
