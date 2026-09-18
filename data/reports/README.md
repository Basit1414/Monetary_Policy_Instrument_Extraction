# IMF technical-assistance report corpus

This directory contains three public IMF technical-assistance reports selected for central-banking and monetary-policy content. The original PDFs remain unchanged, and `manifest.json` / `manifest.csv` record their authoritative IMF URLs, access timestamp, page counts, and SHA-256 hashes.

## Contents

- `raw/`: IMF-hosted source PDFs.
- `extracted/`: page-aware UTF-8 text and JSON. Each page record includes a zero-based `pdf_page_index`, a one-based `pdf_page_number`, and the visible `printed_page_number`.
- `rendered/`: 150-DPI PNG renderings of every recommendation-table page used for visual QA.
- `recommendations.json` / `recommendations.csv`: exactly 24 curated recommendations, eight per report, with verbatim table wording, source priority/timeframe, page provenance, verified body references, grounded excerpts, and uncertainty notes.

## Selection and provenance rules

Recommendation wording is transcribed verbatim from the rendered table cells, with line wraps collapsed to spaces. Priority and timeframe preserve the source labels. Body excerpts are also verbatim except for collapsed line wrapping. Source quirks are not silently repaired.

The sample design is recorded in `recommendations.json`:

- Azerbaijan: all six communication-organization items plus the two high-priority monetary-policy communication items.
- Ukraine: the first eight recommendations, all rated high priority.
- Sri Lanka: a representative spread across reform stages, liquidity monitoring, and policy-rate design. Item 13 is intentionally included as a low-specificity/actionability edge case.

## Visual QA and known source issues

The following rendered pages were inspected against the extracted text:

- Azerbaijan, printed page 10 (`rendered/azerbaijan_modernizing_central_bank_communication_2025/page_010.png`).
- Ukraine, printed page 8 (`rendered/ukraine_counterparty_eligibility_and_ela_2025/page_008.png`).
- Sri Lanka, printed pages 7-8 (`rendered/sri_lanka_liquidity_monitoring_and_monetary_operations_2024/page_007.png` and `page_008.png`).

All selected recommendation text, priority labels, and timeframe labels matched the rendered pages. Two source-level issues are retained and explicitly annotated per record:

1. Ukraine's table paragraph references are generally one paragraph higher than the matching detailed discussion. Both the table citation and the manually verified body paragraph are stored.
2. Sri Lanka table item 13 says, verbatim, `Introduce fine tuning operations if (please add the conditions here).` The visible editorial placeholder is in the IMF PDF and is not an extraction error. Body paragraph 38 supplies the substantive condition.

## Reproduce download, extraction, hashes, manifest, and renderings

From the project root:

```bash
python3 scripts/download_and_extract_imf.py --render
```

The script prefers `pdfplumber`, falls back to `pypdf`, and uses Poppler's `pdftoppm` for PNG rendering. Use `--skip-download` to rebuild extraction and renderings from existing source PDFs or `--force-download` to refresh the PDFs from their recorded IMF URLs.
