# Vendor Questionnaire Automation

A Python tool that automates first-pass review of vendor security questionnaires. It parses incoming questions, matches them against a standing control baseline using keyword scoring, auto-generates responses where controls exist, flags gaps requiring human review, and produces a self-contained HTML report.

Built to cut the manual triage step out of early-stage vendor risk assessments — a GRC analyst spends time on gaps, not on re-answering questions the organization has already answered a hundred times.

---

## How it works

```
vendor_questionnaire.csv  ─┐
                            ├──► automate_questionnaire.py ──► report.html
control_baseline.csv      ─┘
```

1. **Ingest** — loads the vendor's questionnaire and the organization's control baseline
2. **Match** — scores each question against baseline controls using category matching and keyword overlap
3. **Respond** — auto-fills answers, response detail, evidence references, and control owners for matched questions
4. **Flag** — surfaces unmatched questions as gaps requiring manual review
5. **Report** — generates a styled HTML report with a summary dashboard, gap section, and full response table

---

## Structure

```
vendor-questionnaire-automation/
├── vendor_questionnaire.csv     # Sample incoming vendor questionnaire (25 questions)
├── control_baseline.csv         # Standing control answers and evidence references
├── automate_questionnaire.py    # Main script
├── report.html                  # Generated output (created by running the script)
└── README.md
```

---

## Quickstart

Requires Python 3.10+. No external dependencies.

```bash
# Generate the HTML report
python3 automate_questionnaire.py

# Print summary to terminal only
python3 automate_questionnaire.py --summary

# Print summary + list of gaps
python3 automate_questionnaire.py --gaps

# Custom output filename
python3 automate_questionnaire.py --output acme_vendor_review
```

Open `report.html` in any browser to view the report.

---

## File formats

### vendor_questionnaire.csv

The incoming questionnaire from a vendor or customer. One row per question.

| Column | Description |
|--------|-------------|
| `question_id` | Unique identifier (e.g. VQ-001) |
| `category` | Question category (e.g. Data Encryption, Access Control) |
| `question` | The question text |
| `response_required` | Yes / No |

### control_baseline.csv

The organization's standing control posture. One row per control.

| Column | Description |
|--------|-------------|
| `control_id` | Unique identifier (e.g. CB-001) |
| `category` | Control category — should align with questionnaire categories |
| `keywords` | Comma-separated keywords used for question matching |
| `answer` | Yes / No / Partial |
| `detail` | Full response text |
| `evidence` | Evidence artifact or document reference |
| `owner` | Team or role responsible for this control |
| `confidence` | High / Medium / Low — confidence in the response |
| `last_reviewed` | ISO 8601 date of last review |

---

## Matching logic

Each question is scored against every baseline control:

- **+3** — category match between question and control
- **+2** — a baseline keyword appears in the question text
- **+1** — partial word overlap between question and keywords

A minimum score of **4** is required for a match. The highest-scoring control above the threshold is used. Questions that don't reach the threshold are flagged as gaps.

To improve match rates for your environment: add domain-specific keywords to `control_baseline.csv` and ensure category names are consistent between both files.

---

## Adapting to a real questionnaire

To use with an actual vendor questionnaire:

1. Export the questionnaire to CSV with the columns above (or reformat it in Excel)
2. Replace `vendor_questionnaire.csv` with your file
3. Update `control_baseline.csv` to reflect your organization's actual control posture, answers, and evidence references
4. Run the script — gaps will surface in the report for manual completion

The baseline is designed to be maintained once and reused across many questionnaires.

---

## Report output

The generated `report.html` includes:

- **Summary dashboard** — total questions, auto-answered count, gaps flagged, automation rate
- **Gap section** — questions requiring manual review, highlighted and listed at the top
- **Full response table** — all questions with auto-generated answers, response detail, evidence references, control owners, and confidence ratings
- **Category sidebar** — quick navigation by question category

The report is self-contained (single HTML file) and can be shared directly with reviewers or stored as a record of the vendor review.

---

## References

- [NIST SP 800-161 — Cybersecurity Supply Chain Risk Management](https://doi.org/10.6028/NIST.SP.800-161r1)
- [ISO/IEC 27036 — Information Security for Supplier Relationships](https://www.iso.org/standard/82905.html)
- [SIG Questionnaire (Shared Assessments)](https://sharedassessments.org/sig/)

---

## Author

**Joseph Lee** — GRC & Privacy Program Manager  
CIPP/US · CIPP/E · AWS Cloud Practitioner · OneTrust Certified  
[LinkedIn](https://linkedin.com/in/[your-handle]) · [Portfolio](https://joe-lee10.github.io)
