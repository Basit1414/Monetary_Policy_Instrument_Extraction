# IMF recommendations are well supported, but often underspecified as standalone actions

## Executive summary

- Across 24 recommendations from three public IMF technical-assistance reports, the mean internal-consistency score is **4.92/5**, versus **2.92/5** for specificity and **2.83/5** for actionability.
- **22 recommendations are Medium and 2 are High** overall; none are Low. The report bodies support 22 recommendations and partially support 2, with no detected contradiction.
- The recurring weakness is not report alignment. It is that recommendation-table wording often omits the owner, implementation sequence, operating conditions, or completion criterion that would make the action self-contained.

![Mean recommendation-quality scores by report](figures/recommendation_quality_by_report.png)

## Results

| Report | n | Specificity | Actionability | Internal consistency | Overall | High / Medium / Low |
|---|---:|---:|---:|---:|---:|---:|
| Azerbaijan | 8 | 2.88 | 2.75 | 5.00 | 3.56 | 0 / 8 / 0 |
| Ukraine | 8 | 3.00 | 3.00 | 4.88 | 3.64 | 1 / 7 / 0 |
| Sri Lanka | 8 | 2.88 | 2.75 | 4.88 | 3.51 | 1 / 7 / 0 |
| **All three reports** | **24** | **2.92** | **2.83** | **4.92** | **3.57** | **2 / 22 / 0** |

Scores use a 1–5 rubric. The overall score is the one-decimal arithmetic mean of specificity, actionability, and internal consistency for each recommendation; report-level means are then calculated from those recommendation scores.

## Interpretation

The three reports show the same central pattern: their selected recommendations are strongly grounded in the associated analysis, but the recommendation rows are less complete when read on their own. Detailed implementation material often appears in the report body rather than in the table wording. Ukraine is marginally higher in this purposive sample because several recommendations specify an operational mechanism or parameter, but the between-report differences are too small—and the samples too selective—to support a ranking of reports, countries, or IMF teams.

Two recommendations reach a High overall score: Ukraine's institutionalized dialogue between banking supervision and market operations, and Sri Lanka's comprehensive liquidity-monitoring table. Both identify a concrete institutional mechanism or deliverable. At the other end, “Streamline the monetary policy communication cycle,” “Operationalize the ELA framework,” and the visibly incomplete “Introduce fine tuning operations if (please add the conditions here)” each score 3.0 overall. Their high consistency scores lift them into Medium even though their specificity or actionability is weak.

That averaging effect matters. An overall score can obscure a critical low dimension, so users should retain the three component scores and justifications instead of filtering only on the composite. A practical drafting improvement would be to keep recommendation rows concise while adding the responsible institution, key operating condition, sequence or deadline, and a completion test wherever those details are relevant.

## Method

Eight recommendations were selected from each report. Azerbaijan retains the six communications-governance items and two high-priority monetary-policy-communication items; Ukraine uses the first eight table entries; Sri Lanka samples across modernization stages, liquidity monitoring, and policy-rate design and deliberately keeps the source table's incomplete item 13 as an edge case.

The Part C prompt was run once per report against the report's substantive body pages using `gpt-5.6-terra` through the OpenAI Codex CLI at medium reasoning effort. A strict JSON Schema enforced the output structure. Post-run checks validated all 24 rows against the Pydantic model, matched report and recommendation IDs, compared original recommendation text exactly, and verified every quoted evidence span against the corresponding recommendation or report body.

## Limitations

This is a purposive, small sample rather than a representative survey of IMF technical-assistance recommendations. The scores are outputs from one model run and have not been independently adjudicated by an IMF or monetary-policy expert; schema and quotation checks establish structural and source fidelity, not substantive inter-rater reliability. Priority and timeframe columns are preserved as source metadata, while specificity and actionability are deliberately scored from the standalone recommendation text.

## Source reports

- [Republic of Azerbaijan: Technical Assistance Report—Modernizing Central Bank Communication](https://www.imf.org/en/publications/technical-assistance-reports/issues/2025/02/12/azerbaijan-technical-assistance-report-modernizing-central-bank-communication-561816), February 12, 2025.
- [Ukraine: Technical Assistance Report—Review of the Counterparty Eligibility for Monetary Policy Operations and the Emergency Liquidity Assistance Framework](https://www.imf.org/en/publications/technical-assistance-reports/issues/2025/06/25/ukraine-technical-assistance-report-review-of-the-counterparty-eligibility-for-monetary-568011), June 25, 2025.
- [Sri Lanka: Technical Assistance Report—Liquidity Monitoring and Monetary Operations](https://www.elibrary.imf.org/view/journals/019/2024/078/019.2024.issue-078-en.xml), September 20, 2024.

Machine-readable row-level results are in [`data/results/recommendation_quality_assessments.csv`](../data/results/recommendation_quality_assessments.csv) and [`data/results/recommendation_quality_assessments.json`](../data/results/recommendation_quality_assessments.json). The executed notebook is [`notebooks/01_recommendation_quality_assessment.ipynb`](../notebooks/01_recommendation_quality_assessment.ipynb).
