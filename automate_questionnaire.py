#!/usr/bin/env python3
"""
automate_questionnaire.py
--------------------------
Parses an incoming vendor security questionnaire (vendor_questionnaire.csv),
matches each question against a standing control baseline (control_baseline.csv),
auto-generates responses where matches are found, flags gaps where they aren't,
and produces a self-contained HTML report (report.html).

Usage:
    python3 automate_questionnaire.py                      # generate report
    python3 automate_questionnaire.py --summary            # print summary to terminal
    python3 automate_questionnaire.py --gaps               # print only gaps to terminal
    python3 automate_questionnaire.py --output my_report   # custom output filename
"""

import csv
import sys
import os
from datetime import date
from collections import defaultdict

QUESTIONNAIRE_FILE = "vendor_questionnaire.csv"
BASELINE_FILE      = "control_baseline.csv"
DEFAULT_OUTPUT     = "report.html"

# ── Data loading ──────────────────────────────────────────────────────────────

def load_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Matching engine ───────────────────────────────────────────────────────────

def match_question(question: dict, baseline: list[dict]) -> dict | None:
    """
    Match a questionnaire item to a baseline control using keyword scoring.
    Returns the highest-scoring baseline entry above threshold, or None.
    """
    q_text = question["question"].lower()
    q_cat  = question["category"].lower()

    best_score  = 0
    best_match  = None

    for control in baseline:
        score = 0

        # Category match bonus
        if control["category"].lower() == question["category"].lower():
            score += 3

        # Keyword matching
        keywords = [k.strip().lower() for k in control["keywords"].split(",")]
        for kw in keywords:
            if kw in q_text:
                score += 2

        # Partial word overlap between question and control keywords
        q_words = set(q_text.replace("?", "").split())
        for kw in keywords:
            kw_words = set(kw.split())
            if kw_words & q_words:
                score += 1

        if score > best_score:
            best_score = score
            best_match = control

    # Threshold: require a minimum score to count as a match
    return best_match if best_score >= 4 else None


def process(questionnaire: list[dict], baseline: list[dict]) -> list[dict]:
    """
    Process each question: attempt match, generate response, flag gaps.
    Returns enriched list of result dicts.
    """
    results = []
    for q in questionnaire:
        match = match_question(q, baseline)
        if match:
            results.append({
                "question_id":   q["question_id"],
                "category":      q["category"],
                "question":      q["question"],
                "status":        "Auto-Answered",
                "answer":        match["answer"],
                "detail":        match["detail"],
                "evidence":      match["evidence"],
                "owner":         match["owner"],
                "confidence":    match["confidence"],
                "control_id":    match["control_id"],
                "last_reviewed": match["last_reviewed"],
            })
        else:
            results.append({
                "question_id":   q["question_id"],
                "category":      q["category"],
                "question":      q["question"],
                "status":        "Gap — Needs Review",
                "answer":        "",
                "detail":        "No matching baseline control found. Manual review required.",
                "evidence":      "",
                "owner":         "Unassigned",
                "confidence":    "—",
                "control_id":    "—",
                "last_reviewed": "—",
            })
    return results


# ── Terminal output ───────────────────────────────────────────────────────────

def print_summary(results: list[dict]) -> None:
    total      = len(results)
    answered   = sum(1 for r in results if r["status"] == "Auto-Answered")
    gaps       = total - answered
    categories = defaultdict(lambda: {"answered": 0, "gaps": 0})
    for r in results:
        if r["status"] == "Auto-Answered":
            categories[r["category"]]["answered"] += 1
        else:
            categories[r["category"]]["gaps"] += 1

    print("\n" + "=" * 60)
    print("  VENDOR QUESTIONNAIRE AUTOMATION — SUMMARY")
    print(f"  {date.today().isoformat()}")
    print("=" * 60)
    print(f"\n  Total questions  : {total}")
    print(f"  Auto-answered    : {answered}  ({answered/total*100:.0f}%)")
    print(f"  Gaps flagged     : {gaps}  ({gaps/total*100:.0f}%)")
    print("\n  ── By Category ──────────────────────────────────────")
    for cat, counts in sorted(categories.items()):
        a = counts["answered"]
        g = counts["gaps"]
        flag = "  ✗ GAP" if g > 0 else ""
        print(f"  {cat:<28} {a} answered  {g} gap(s){flag}")
    print("\n" + "=" * 60 + "\n")


def print_gaps(results: list[dict]) -> None:
    gaps = [r for r in results if r["status"] == "Gap — Needs Review"]
    if not gaps:
        print("\n  No gaps — all questions matched to baseline.\n")
        return
    print(f"\n  {len(gaps)} question(s) need manual review:\n")
    print(f"  {'ID':<12} {'CATEGORY':<26} QUESTION")
    print("  " + "-" * 80)
    for r in gaps:
        q = r["question"][:55] + ("..." if len(r["question"]) > 55 else "")
        print(f"  {r['question_id']:<12} {r['category']:<26} {q}")
    print()


# ── HTML report ───────────────────────────────────────────────────────────────

def status_badge(status: str) -> str:
    if status == "Auto-Answered":
        return '<span class="badge answered">Auto-Answered</span>'
    return '<span class="badge gap">Gap — Needs Review</span>'


def confidence_badge(conf: str) -> str:
    colors = {"High": "conf-high", "Medium": "conf-med", "Low": "conf-low"}
    cls = colors.get(conf, "conf-na")
    return f'<span class="conf {cls}">{conf}</span>'


def build_report(results: list[dict], output_path: str) -> None:
    total    = len(results)
    answered = sum(1 for r in results if r["status"] == "Auto-Answered")
    gaps     = total - answered
    pct      = int(answered / total * 100)

    # Group by category for the sidebar nav
    categories = list(dict.fromkeys(r["category"] for r in results))

    rows_html = ""
    for r in results:
        row_class = "row-gap" if r["status"] == "Gap — Needs Review" else ""
        rows_html += f"""
        <tr class="{row_class}">
          <td class="qid">{r['question_id']}</td>
          <td class="cat">{r['category']}</td>
          <td class="question">{r['question']}</td>
          <td>{status_badge(r['status'])}</td>
          <td class="answer">{r['answer'] if r['answer'] else '<span class="na">—</span>'}</td>
          <td class="detail">{r['detail']}</td>
          <td class="evidence">{r['evidence'] if r['evidence'] else '<span class="na">—</span>'}</td>
          <td>{r['owner']}</td>
          <td>{confidence_badge(r['confidence'])}</td>
        </tr>"""

    gap_rows = ""
    for r in [x for x in results if x["status"] == "Gap — Needs Review"]:
        gap_rows += f"""
        <tr>
          <td class="qid">{r['question_id']}</td>
          <td class="cat">{r['category']}</td>
          <td class="question">{r['question']}</td>
          <td class="owner">{r['owner']}</td>
        </tr>"""

    cat_nav = "".join(
        f'<a href="#cat-{c.replace(" ","").replace("/","")}" class="cat-link">{c}</a>'
        for c in categories
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Vendor Questionnaire Report — {date.today().isoformat()}</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,500;1,6..72,400&display=swap" rel="stylesheet">
<style>
  :root{{
    --bg:#ECEAE3; --panel:#E2DFD5; --ink:#1C2430; --ink-dim:#535C68;
    --ink-faint:#7C8490; --hairline:#C9C4B7; --accent:#6E2A2A;
    --accent-dim:rgba(110,42,42,0.1); --pass:#4F7A5E; --pass-bg:rgba(79,122,94,0.12);
    --gap:#6E2A2A; --gap-bg:rgba(110,42,42,0.10);
    --sans:'IBM Plex Sans',sans-serif; --mono:'IBM Plex Mono',monospace; --serif:'Newsreader',Georgia,serif;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased;}}
  a{{color:var(--accent);text-decoration:none;}}

  /* header */
  .page-header{{background:var(--ink);color:var(--bg);padding:32px 44px;}}
  .page-header .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:rgba(236,234,227,0.5);margin-bottom:8px;}}
  .page-header h1{{font-family:var(--serif);font-size:28px;font-weight:500;margin:0 0 6px;}}
  .page-header .meta{{font-family:var(--mono);font-size:12px;color:rgba(236,234,227,0.6);}}

  /* stat bar */
  .stat-bar{{display:flex;gap:0;border-bottom:1px solid var(--hairline);}}
  .stat{{flex:1;padding:24px 32px;border-right:1px solid var(--hairline);}}
  .stat:last-child{{border-right:none;}}
  .stat .num{{font-family:var(--serif);font-size:36px;color:var(--ink);line-height:1;}}
  .stat .label{{font-family:var(--mono);font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink-faint);margin-top:4px;}}
  .stat.accent .num{{color:var(--accent);}}
  .stat.pass .num{{color:var(--pass);}}

  /* progress bar */
  .progress-wrap{{padding:20px 32px;border-bottom:1px solid var(--hairline);display:flex;align-items:center;gap:16px;}}
  .progress-track{{flex:1;height:6px;background:var(--hairline);border-radius:3px;overflow:hidden;}}
  .progress-fill{{height:100%;background:var(--pass);border-radius:3px;transition:width 1s ease;}}
  .progress-label{{font-family:var(--mono);font-size:12px;color:var(--ink-dim);white-space:nowrap;}}

  /* layout */
  .body-wrap{{display:grid;grid-template-columns:200px 1fr;min-height:calc(100vh - 200px);}}
  .sidebar{{background:var(--panel);border-right:1px solid var(--hairline);padding:28px 18px;position:sticky;top:0;height:100vh;overflow-y:auto;}}
  .sidebar .eyebrow{{font-family:var(--mono);font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-faint);margin-bottom:12px;display:block;}}
  .cat-link{{display:block;font-family:var(--mono);font-size:12px;color:var(--ink-dim);padding:7px 10px;border-left:2px solid transparent;border-radius:0 2px 2px 0;margin-bottom:2px;transition:all .15s;}}
  .cat-link:hover{{color:var(--accent);border-left-color:var(--accent);background:var(--accent-dim);}}
  .sidebar-gap{{margin-top:24px;padding-top:18px;border-top:1px solid var(--hairline);}}
  .gap-count{{font-family:var(--mono);font-size:12px;color:var(--gap);padding:8px 10px;background:var(--gap-bg);border-radius:2px;}}

  /* main content */
  .content{{padding:36px 40px;overflow-x:auto;}}
  .section-head{{margin-bottom:20px;}}
  .section-head h2{{font-family:var(--serif);font-size:22px;font-weight:500;margin:0 0 4px;}}
  .section-head p{{color:var(--ink-dim);font-size:13px;margin:0;}}

  /* table */
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:48px;}}
  thead th{{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink-faint);padding:0 12px 12px;border-bottom:2px solid var(--hairline);white-space:nowrap;}}
  tbody tr{{border-bottom:1px solid var(--hairline);transition:background .1s;}}
  tbody tr:hover{{background:var(--panel);}}
  tbody tr.row-gap{{background:rgba(110,42,42,0.04);}}
  tbody tr.row-gap:hover{{background:rgba(110,42,42,0.08);}}
  td{{padding:14px 12px;vertical-align:top;}}
  td.qid{{font-family:var(--mono);font-size:11px;color:var(--ink-faint);white-space:nowrap;}}
  td.cat{{font-family:var(--mono);font-size:11px;color:var(--ink-dim);white-space:nowrap;}}
  td.question{{font-weight:500;max-width:260px;}}
  td.detail{{color:var(--ink-dim);max-width:280px;font-size:12.5px;}}
  td.evidence{{font-family:var(--mono);font-size:11px;color:var(--ink-dim);max-width:180px;}}
  td.answer{{font-family:var(--mono);font-size:12px;font-weight:500;}}
  .na{{color:var(--ink-faint);}}

  /* badges */
  .badge{{font-family:var(--mono);font-size:10px;letter-spacing:0.04em;text-transform:uppercase;padding:4px 8px;border-radius:20px;white-space:nowrap;}}
  .badge.answered{{color:var(--pass);background:var(--pass-bg);}}
  .badge.gap{{color:var(--gap);background:var(--gap-bg);}}
  .conf{{font-family:var(--mono);font-size:10px;padding:3px 7px;border-radius:2px;}}
  .conf-high{{color:#4F7A5E;background:rgba(79,122,94,0.12);}}
  .conf-med{{color:#8A6A2A;background:rgba(138,106,42,0.12);}}
  .conf-low{{color:#6E2A2A;background:rgba(110,42,42,0.12);}}
  .conf-na{{color:var(--ink-faint);background:transparent;}}

  /* gap summary table */
  .gap-section{{background:var(--gap-bg);border:1px solid rgba(110,42,42,0.2);border-radius:2px;padding:24px 28px;margin-bottom:48px;}}
  .gap-section h2{{font-family:var(--serif);font-size:20px;font-weight:500;color:var(--gap);margin:0 0 16px;}}

  /* footer */
  .report-footer{{border-top:1px solid var(--hairline);padding:20px 40px;font-family:var(--mono);font-size:11px;color:var(--ink-faint);display:flex;justify-content:space-between;}}
</style>
</head>
<body>

<div class="page-header">
  <div class="eyebrow">Vendor Security Review — Auto-Generated</div>
  <h1>Vendor Questionnaire Response Report</h1>
  <div class="meta">Generated: {date.today().isoformat()} &nbsp;·&nbsp; Source: vendor_questionnaire.csv &nbsp;·&nbsp; Baseline: control_baseline.csv</div>
</div>

<div class="stat-bar">
  <div class="stat"><div class="num">{total}</div><div class="label">Total Questions</div></div>
  <div class="stat pass"><div class="num">{answered}</div><div class="label">Auto-Answered</div></div>
  <div class="stat accent"><div class="num">{gaps}</div><div class="label">Gaps Flagged</div></div>
  <div class="stat"><div class="num">{pct}%</div><div class="label">Automation Rate</div></div>
</div>

<div class="progress-wrap">
  <div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div>
  <div class="progress-label">{answered} of {total} questions answered automatically</div>
</div>

<div class="body-wrap">
  <div class="sidebar">
    <span class="eyebrow">Categories</span>
    {cat_nav}
    <div class="sidebar-gap">
      <div class="gap-count">{gaps} gap(s) need review</div>
    </div>
  </div>

  <div class="content">

    {"" if not gaps else f'''
    <div class="gap-section">
      <h2>⚠ Gaps Requiring Manual Review ({gaps})</h2>
      <table>
        <thead><tr><th>ID</th><th>Category</th><th>Question</th><th>Assigned To</th></tr></thead>
        <tbody>{gap_rows}</tbody>
      </table>
    </div>
    '''}

    <div class="section-head">
      <h2>Full Response Table</h2>
      <p>All questions with auto-generated responses and source control references. Rows highlighted in red require manual completion.</p>
    </div>

    <table>
      <thead>
        <tr>
          <th>ID</th><th>Category</th><th>Question</th><th>Status</th>
          <th>Answer</th><th>Response Detail</th><th>Evidence</th>
          <th>Owner</th><th>Confidence</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>

  </div>
</div>

<div class="report-footer">
  <span>DOCUMENT CONTROL — Classification: Confidential · For internal review only</span>
  <span>Generated by automate_questionnaire.py · {date.today().isoformat()}</span>
</div>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  Report written to: {output_path}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    output = DEFAULT_OUTPUT
    if "--output" in args:
        idx = args.index("--output")
        output = args[idx + 1] + ".html" if idx + 1 < len(args) else DEFAULT_OUTPUT

    for filepath in [QUESTIONNAIRE_FILE, BASELINE_FILE]:
        if not os.path.exists(filepath):
            print(f"\n  Could not find '{filepath}'. Run from the repo root.\n")
            sys.exit(1)

    questionnaire = load_csv(QUESTIONNAIRE_FILE)
    baseline      = load_csv(BASELINE_FILE)
    results       = process(questionnaire, baseline)

    if "--summary" in args:
        print_summary(results)
    elif "--gaps" in args:
        print_summary(results)
        print_gaps(results)
    else:
        print_summary(results)
        build_report(results, output)


if __name__ == "__main__":
    main()
