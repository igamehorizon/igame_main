"""
scripts/analyze_pilot.py

Post-hoc evaluation script for the v4 human playtester pilot.

Reads everything the tool already saves during normal use —
  data/balancing_sessions/session_<id>/   (metadata + per-iteration results + applied recs)
  data/logs/reviews.jsonl                 (structured Likert ratings + free text)
  data/logs/usage.jsonl                   (request-level log, used for error/status counts)
— joins it into one row per (session_id, iteration_number), and writes:
  data/pilot_reports/pilot_summary_<ts>.json   machine-readable summary
  data/pilot_reports/pilot_summary_<ts>.md     human-readable report (paste into D4.2)
  data/pilot_reports/pilot_iterations_<ts>.csv flat table, one row per iteration (Excel-friendly)
  data/pilot_reports/*.png                     rating charts (only if matplotlib is installed)

This script does not talk to the API and does not require the server to be
running — it only reads what's already on disk. Run it any time after
collecting pilot sessions; re-running is always safe (nothing is mutated).

Usage:
    python scripts/analyze_pilot.py
    python scripts/analyze_pilot.py --data-dir data --out-dir data/pilot_reports
    python scripts/analyze_pilot.py --low-coverage-threshold 0.4
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

RATING_QUESTIONS = [
    "clarity",
    "recommendation_quality",
    "explainability",
    "implementability",
    "overall",
]

RATING_LABELS = {
    "clarity":                "Workflow was clear",
    "recommendation_quality": "Recommendations felt useful/actionable",
    "explainability":         "Explanations were understandable",
    "implementability":       "Could see applying suggestions",
    "overall":                "Would use the tool again",
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_sessions(sessions_dir: Path) -> List[dict]:
    """
    Returns one row per (session_id, iteration_number) with objective
    metrics pulled from that iteration's saved result.json, plus whether
    a next-iteration "applied recommendations" file exists.
    """
    rows: List[dict] = []
    if not sessions_dir.exists():
        return rows

    for sdir in sorted(sessions_dir.glob("session_*")):
        meta = load_json(sdir / "metadata.json")
        if not meta:
            continue
        session_id   = meta.get("session_id", sdir.name.replace("session_", "", 1))
        gameplay_type = meta.get("gameplay_type")
        instance_id   = meta.get("instance_id")
        iterations    = meta.get("iterations", [])
        n_iterations  = len(iterations)

        for it in iterations:
            iter_num    = it.get("iteration_number")
            result_file = it.get("result_file")
            result = load_json(sdir / result_file) if result_file else None
            if not result:
                continue

            analysis = result.get("analysis") or {}
            recs     = result.get("recommendations") or []
            warnings = analysis.get("warnings") or []
            warning_codes = [w.split("|", 1)[0] for w in warnings if "|" in w]

            priority_counts = {"high": 0, "medium": 0, "low": 0}
            for r in recs:
                p = (r.get("priority") or "low").lower()
                if p in priority_counts:
                    priority_counts[p] += 1

            coverage_data = analysis.get("telemetry_coverage") or {}
            coverage = coverage_data.get("overall_family_coverage")
            low_coverage_flag = coverage_data.get("low_coverage_flag")
            never_populated = coverage_data.get("never_populated_fields") or []

            # Was a next-iteration applied-recommendations file saved for THIS iteration's output?
            next_iter_num = (iter_num or 0) + 1
            applied_file = sdir / f"iteration_{next_iter_num:02d}_applied_recommendations.json"
            applied_data = load_json(applied_file)
            n_applied = len(applied_data.get("applied_recommendations", [])) if applied_data else None

            rows.append({
                "session_id":            session_id,
                "iteration_number":      iter_num,
                "n_iterations_total":    n_iterations,
                "gameplay_type":         gameplay_type,
                "instance_id":           instance_id,
                "status":                result.get("status"),
                "n_sessions_uploaded":   analysis.get("n_sessions"),
                "n_levels":              analysis.get("n_levels"),
                "overall_success_rate":  analysis.get("overall_success_rate"),
                "xai_method":            analysis.get("xai_method"),
                "telemetry_coverage":    coverage,
                "low_coverage_flag":     low_coverage_flag,
                "never_populated_fields": never_populated,
                "warning_codes":         warning_codes,
                "n_recommendations":     len(recs),
                "n_recs_high":           priority_counts["high"],
                "n_recs_medium":         priority_counts["medium"],
                "n_recs_low":            priority_counts["low"],
                "n_recs_applied_next":   n_applied,
            })
    return rows


def load_reviews(reviews_path: Path) -> List[dict]:
    raw = load_jsonl(reviews_path)
    rows = []
    for r in raw:
        ratings = r.get("ratings") or {}
        row = {
            "session_id":       r.get("session_id"),
            "iteration_number": r.get("iteration_number"),
            "gameplay_type":    r.get("gameplay_type"),
            "instance_id":      r.get("instance_id"),
            "review_text":      r.get("review"),
            "timestamp":        r.get("timestamp"),
        }
        for q in RATING_QUESTIONS:
            row[f"rating_{q}"] = ratings.get(q)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Joining
# ---------------------------------------------------------------------------

def join_iterations_and_reviews(
    iter_rows: List[dict], review_rows: List[dict]
) -> "tuple[pd.DataFrame, List[dict]]":
    """
    Returns (merged_df, unmatched_reviews). unmatched_reviews holds any
    review that could NOT be attached to a saved iteration — either it has
    no session_id, or its (session_id, iteration_number) doesn't match any
    saved iteration on disk. These are real participant feedback and must
    never be silently dropped from the report.
    """
    it_df = pd.DataFrame(iter_rows)
    rv_df = pd.DataFrame(review_rows)

    if rv_df.empty:
        return it_df, []

    no_session_id = rv_df[~(rv_df["session_id"].notna() & (rv_df["session_id"] != ""))]
    matched_reviews = rv_df[rv_df["session_id"].notna() & (rv_df["session_id"] != "")]

    unmatched: List[dict] = no_session_id.to_dict("records")

    if it_df.empty:
        # Nothing to join against — every review with a session_id is also unmatched.
        unmatched.extend(matched_reviews.to_dict("records"))
        return it_df, unmatched

    # Which (session_id, iteration_number) pairs actually exist as saved iterations?
    valid_keys = set(zip(it_df["session_id"], it_df["iteration_number"]))
    has_match_mask = matched_reviews.apply(
        lambda r: (r["session_id"], r["iteration_number"]) in valid_keys, axis=1
    )
    unmatched.extend(matched_reviews[~has_match_mask].to_dict("records"))
    joinable_reviews = matched_reviews[has_match_mask]

    merged = it_df.merge(
        joinable_reviews,
        on=["session_id", "iteration_number"],
        how="left",
        suffixes=("", "_review"),
    )
    return merged, unmatched


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

def safe_mean(values: List[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None and not (isinstance(v, float) and pd.isna(v))]
    if not clean:
        return None
    return round(statistics.mean(clean), 3)


def rating_distribution(series: pd.Series) -> Dict[str, int]:
    clean = series.dropna()
    return {str(i): int((clean == i).sum()) for i in range(1, 6)}


def compute_summary(
    merged: pd.DataFrame, unmatched_reviews: List[dict], low_coverage_threshold: float
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    n_sessions = merged["session_id"].nunique() if not merged.empty else 0
    n_iterations = len(merged)
    summary["n_sessions"] = int(n_sessions)
    summary["n_iterations"] = int(n_iterations)
    summary["n_unmatched_reviews"] = len(unmatched_reviews)

    if merged.empty:
        return summary

    # --- Drop-off: sessions that never got a follow-up iteration ---
    per_session_max_iter = merged.groupby("session_id")["n_iterations_total"].max()
    n_single_iteration = int((per_session_max_iter <= 1).sum())
    summary["dropoff"] = {
        "n_single_iteration_sessions": n_single_iteration,
        "n_multi_iteration_sessions": int(n_sessions - n_single_iteration),
        "dropoff_rate": round(n_single_iteration / n_sessions, 3) if n_sessions else None,
    }

    # --- XAI method breakdown ---
    xai_counts = merged["xai_method"].value_counts(dropna=False).to_dict()
    summary["xai_method_breakdown"] = {str(k): int(v) for k, v in xai_counts.items()}

    # --- Telemetry coverage ---
    coverage_vals = merged["telemetry_coverage"].dropna().tolist()
    low_cov_mask = merged["telemetry_coverage"].dropna() < low_coverage_threshold
    summary["telemetry_coverage"] = {
        "mean_coverage": safe_mean(coverage_vals),
        "n_iterations_below_threshold": int(low_cov_mask.sum()),
        "threshold_used": low_coverage_threshold,
    }

    # --- Recommendations & apply rate ---
    total_recs_offered_with_followup = merged.loc[
        merged["n_recs_applied_next"].notna(), "n_recommendations"
    ].sum()
    total_applied = merged["n_recs_applied_next"].dropna().sum()
    summary["recommendations"] = {
        "total_recommendations_all_iterations": int(merged["n_recommendations"].sum()),
        "priority_breakdown": {
            "high":   int(merged["n_recs_high"].sum()),
            "medium": int(merged["n_recs_medium"].sum()),
            "low":    int(merged["n_recs_low"].sum()),
        },
        "apply_rate_when_followup_exists": (
            round(float(total_applied) / float(total_recs_offered_with_followup), 3)
            if total_recs_offered_with_followup else None
        ),
    }

    # --- Survey ratings (overall) ---
    ratings_summary = {}
    for q in RATING_QUESTIONS:
        col = f"rating_{q}"
        if col in merged.columns:
            ratings_summary[q] = {
                "label": RATING_LABELS[q],
                "mean": safe_mean(merged[col].tolist()),
                "n_responses": int(merged[col].notna().sum()),
                "distribution_1to5": rating_distribution(merged[col]),
            }
    summary["ratings_overall"] = ratings_summary

    # --- Baseline (iteration 1) vs follow-up (iteration >= 2) ---
    baseline = merged[merged["iteration_number"] == 1]
    followup = merged[merged["iteration_number"] >= 2]
    baseline_vs_followup = {}
    for q in RATING_QUESTIONS:
        col = f"rating_{q}"
        if col in merged.columns:
            baseline_vs_followup[q] = {
                "baseline_mean": safe_mean(baseline[col].tolist()) if not baseline.empty else None,
                "followup_mean": safe_mean(followup[col].tolist()) if not followup.empty else None,
            }
    summary["baseline_vs_followup"] = baseline_vs_followup

    # --- Correlation: objective success rate vs subjective ratings ---
    # Spearman via pandas (no scipy dependency). With small pilot N this is
    # reported descriptively only — no significance testing, per the
    # evaluation methodology (N is not controlled, see D4.2 discussion).
    correlations = {}
    if merged["overall_success_rate"].notna().sum() >= 3:
        for q in RATING_QUESTIONS:
            col = f"rating_{q}"
            if col in merged.columns and merged[col].notna().sum() >= 3:
                corr = merged[["overall_success_rate", col]].corr(method="spearman").iloc[0, 1]
                correlations[q] = round(float(corr), 3) if pd.notna(corr) else None
    summary["success_rate_vs_rating_spearman"] = correlations

    # --- Review text (qualitative — listed, not summarized) ---
    texts = merged["review_text"].dropna().tolist() if "review_text" in merged.columns else []
    summary["n_written_reviews"] = len(texts)

    return summary


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def write_markdown_report(
    summary: Dict[str, Any], merged: pd.DataFrame, unmatched_reviews: List[dict], out_path: Path
) -> None:
    lines: List[str] = []
    lines.append("# Game Balance Tool — Pilot Evaluation Summary")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append(f"- Sessions: **{summary.get('n_sessions', 0)}**")
    lines.append(f"- Iterations analysed: **{summary.get('n_iterations', 0)}**")
    lines.append(f"- Written reviews collected: **{summary.get('n_written_reviews', 0)}**")
    n_unmatched = summary.get("n_unmatched_reviews", 0)
    if n_unmatched:
        lines.append(
            f"- ⚠️ **{n_unmatched} review(s) could not be matched to a saved session/iteration** "
            f"— see 'Unmatched reviews' section below. These are NOT counted anywhere above "
            f"and must be checked manually so no participant feedback is lost."
        )
    lines.append("")

    dropoff = summary.get("dropoff", {})
    lines.append("## Engagement / drop-off")
    lines.append(
        f"- {dropoff.get('n_single_iteration_sessions', 0)} session(s) had no follow-up iteration; "
        f"{dropoff.get('n_multi_iteration_sessions', 0)} went through at least one follow-up."
    )
    if dropoff.get("dropoff_rate") is not None:
        lines.append(f"- Drop-off rate: **{dropoff['dropoff_rate']:.0%}**")
    lines.append("")

    lines.append("## XAI method used (SHAP vs fallback)")
    lines.append("| Method | Iterations |")
    lines.append("|---|---|")
    for method, count in summary.get("xai_method_breakdown", {}).items():
        lines.append(f"| {method} | {count} |")
    lines.append("")
    lines.append(
        "_Only `shap` iterations should be used when citing SHAP-based explainability "
        "validity claims; `variance_heuristic` iterations had &lt;2 sessions and used a weaker fallback._"
    )
    lines.append("")

    cov = summary.get("telemetry_coverage", {})
    lines.append("## Telemetry coverage")
    lines.append(f"- Mean coverage across iterations: **{cov.get('mean_coverage')}**")
    lines.append(
        f"- Iterations below the {cov.get('threshold_used', 0):.0%} coverage threshold: "
        f"**{cov.get('n_iterations_below_threshold', 0)}** (recommendations here should be treated as low-confidence)"
    )
    lines.append("")

    recs = summary.get("recommendations", {})
    lines.append("## Recommendations generated")
    pb = recs.get("priority_breakdown", {})
    lines.append(f"- Total: **{recs.get('total_recommendations_all_iterations', 0)}** "
                 f"(high: {pb.get('high', 0)}, medium: {pb.get('medium', 0)}, low: {pb.get('low', 0)})")
    ar = recs.get("apply_rate_when_followup_exists")
    lines.append(f"- Apply rate (when a follow-up iteration exists): "
                 f"**{f'{ar:.0%}' if ar is not None else 'n/a'}**")
    lines.append("")

    lines.append("## Survey ratings (1–5 scale, all iterations)")
    lines.append("| Question | Mean | N | 1 | 2 | 3 | 4 | 5 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for q, data in summary.get("ratings_overall", {}).items():
        dist = data.get("distribution_1to5", {})
        lines.append(
            f"| {data.get('label', q)} | {data.get('mean')} | {data.get('n_responses')} | "
            f"{dist.get('1', 0)} | {dist.get('2', 0)} | {dist.get('3', 0)} | {dist.get('4', 0)} | {dist.get('5', 0)} |"
        )
    lines.append("")

    lines.append("## Baseline (iteration 1) vs follow-up (iteration ≥2)")
    lines.append("| Question | Baseline mean | Follow-up mean |")
    lines.append("|---|---|---|")
    for q, data in summary.get("baseline_vs_followup", {}).items():
        lines.append(f"| {RATING_LABELS.get(q, q)} | {data.get('baseline_mean')} | {data.get('followup_mean')} |")
    lines.append("")

    corr = summary.get("success_rate_vs_rating_spearman", {})
    lines.append("## Objective success rate vs. subjective ratings (Spearman ρ, descriptive only)")
    if corr:
        lines.append("| Question | ρ |")
        lines.append("|---|---|")
        for q, v in corr.items():
            lines.append(f"| {RATING_LABELS.get(q, q)} | {v} |")
    else:
        lines.append("_Not enough paired data points yet to compute correlations (need ≥3 rated iterations)._")
    lines.append("")

    written = merged["review_text"].dropna().tolist() if "review_text" in merged.columns else []
    if written:
        lines.append("## Written reviews (verbatim, for qualitative reading)")
        for t in written:
            lines.append(f"> {t}")
            lines.append("")

    if unmatched_reviews:
        lines.append("## ⚠️ Unmatched reviews (could not be joined to a session/iteration)")
        lines.append(
            "These reviews exist in `reviews.jsonl` but either had no `session_id`, or "
            "referenced a `session_id`/`iteration_number` pair with no saved iteration on "
            "disk. They are excluded from every statistic above — read them manually so "
            "this feedback isn't lost."
        )
        lines.append("")

        def _clean(v: Any) -> Any:
            return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        for r in unmatched_reviews:
            sid, itn, iid = _clean(r.get("session_id")), _clean(r.get("iteration_number")), _clean(r.get("instance_id"))
            lines.append(
                f"- `{r.get('timestamp', '?')}` | session_id={sid!r} | "
                f"iteration={itn} | instance_id={iid!r}"
            )
            review_text = _clean(r.get("review_text"))
            if review_text:
                lines.append(f"  > {review_text}")
            ratings_present = {
                k.replace("rating_", ""): v for k, v in r.items()
                if k.startswith("rating_") and _clean(v) is not None
            }
            if ratings_present:
                lines.append(f"  ratings: {ratings_present}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Optional charts
# ---------------------------------------------------------------------------

def write_charts(summary: Dict[str, Any], out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[analyze_pilot] matplotlib not installed — skipping charts "
              "(pip install matplotlib to enable them).")
        return

    ratings = summary.get("ratings_overall", {})
    if ratings:
        labels = [RATING_LABELS[q] for q in RATING_QUESTIONS if q in ratings]
        means  = [ratings[q]["mean"] or 0 for q in RATING_QUESTIONS if q in ratings]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(labels, means, color="#6a5acd")
        ax.set_xlim(0, 5)
        ax.set_xlabel("Mean rating (1-5)")
        ax.set_title("Pilot survey — mean ratings")
        fig.tight_layout()
        fig.savefig(out_dir / "ratings_overview.png", dpi=150)
        plt.close(fig)

    bvf = summary.get("baseline_vs_followup", {})
    if bvf:
        labels = [RATING_LABELS[q] for q in RATING_QUESTIONS if q in bvf]
        baseline_means = [bvf[q]["baseline_mean"] or 0 for q in RATING_QUESTIONS if q in bvf]
        followup_means = [bvf[q]["followup_mean"] or 0 for q in RATING_QUESTIONS if q in bvf]
        x = range(len(labels))
        fig, ax = plt.subplots(figsize=(9, 4))
        width = 0.35
        ax.bar([i - width / 2 for i in x], baseline_means, width, label="Baseline (iter 1)", color="#8090c0")
        ax.bar([i + width / 2 for i in x], followup_means, width, label="Follow-up (iter ≥2)", color="#ffe066")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylim(0, 5)
        ax.set_ylabel("Mean rating (1-5)")
        ax.set_title("Baseline vs follow-up ratings")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "baseline_vs_followup.png", dpi=150)
        plt.close(fig)

    print(f"[analyze_pilot] charts written to {out_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a game balance tool pilot evaluation.")
    parser.add_argument("--data-dir", default="data", help="Path to the data/ directory (default: data)")
    parser.add_argument("--out-dir", default=None,
                         help="Where to write reports (default: <data-dir>/pilot_reports)")
    parser.add_argument("--low-coverage-threshold", type=float, default=0.4,
                         help="Telemetry coverage below this fraction is flagged (default: 0.4)")
    parser.add_argument("--no-charts", action="store_true", help="Skip PNG chart generation")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir  = Path(args.out_dir) if args.out_dir else data_dir / "pilot_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    iter_rows   = load_sessions(data_dir / "balancing_sessions")
    review_rows = load_reviews(data_dir / "logs" / "reviews.jsonl")
    merged, unmatched_reviews = join_iterations_and_reviews(iter_rows, review_rows)

    summary = compute_summary(merged, unmatched_reviews, args.low_coverage_threshold)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"pilot_summary_{ts}.json"
    md_path   = out_dir / f"pilot_summary_{ts}.md"
    csv_path  = out_dir / f"pilot_iterations_{ts}.csv"
    unmatched_csv_path = out_dir / f"pilot_unmatched_reviews_{ts}.csv"

    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    write_markdown_report(summary, merged, unmatched_reviews, md_path)
    if not merged.empty:
        merged.to_csv(csv_path, index=False)
    if unmatched_reviews:
        pd.DataFrame(unmatched_reviews).to_csv(unmatched_csv_path, index=False)
    if not args.no_charts:
        write_charts(summary, out_dir)

    print("=" * 60)
    print("Pilot evaluation summary")
    print("=" * 60)
    print(f"Sessions:            {summary.get('n_sessions', 0)}")
    print(f"Iterations analysed: {summary.get('n_iterations', 0)}")
    print(f"Written reviews:     {summary.get('n_written_reviews', 0)}")
    print(f"Drop-off rate:       {summary.get('dropoff', {}).get('dropoff_rate')}")
    print(f"Mean telemetry cov.: {summary.get('telemetry_coverage', {}).get('mean_coverage')}")
    if unmatched_reviews:
        print()
        print(f"⚠️  {len(unmatched_reviews)} review(s) could NOT be matched to a session/iteration "
              f"— see {unmatched_csv_path.name} and the report's 'Unmatched reviews' section.")
    print()
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    if not merged.empty:
        print(f"Wrote: {csv_path}")
    if unmatched_reviews:
        print(f"Wrote: {unmatched_csv_path}")


if __name__ == "__main__":
    main()
