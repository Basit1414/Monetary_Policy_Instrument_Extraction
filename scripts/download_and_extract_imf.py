#!/usr/bin/env python3
"""Download, fingerprint, extract, and render the selected IMF TA reports.

The script intentionally keeps the source PDFs and page-aware extraction together so
that every downstream recommendation can be traced back to an IMF-hosted document.
It uses pdfplumber when available and falls back to pypdf for text extraction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORTS: tuple[dict[str, Any], ...] = (
    {
        "slug": "azerbaijan_modernizing_central_bank_communication_2025",
        "title": (
            "Republic of Azerbaijan: Technical Assistance Report-Modernizing "
            "Central Bank Communication"
        ),
        "country": "Azerbaijan",
        "publication_date": "2025-02-12",
        "landing_url": (
            "https://www.imf.org/en/publications/technical-assistance-reports/"
            "issues/2025/02/12/azerbaijan-technical-assistance-report-"
            "modernizing-central-bank-communication-561816"
        ),
        "pdf_url": (
            "https://www.imf.org/-/media/files/publications/tar/2025/english/"
            "tarea2025013-print-pdf.pdf"
        ),
        "expected_page_count": 46,
        "recommendation_printed_pages": [10],
        "recommendation_pdf_page_numbers": [10],
        "body_pages": "11-37",
    },
    {
        "slug": "ukraine_counterparty_eligibility_and_ela_2025",
        "title": (
            "Ukraine: Technical Assistance Report-Review of the Counterparty "
            "Eligibility for Monetary Policy Operations and the Emergency Liquidity "
            "Assistance Framework"
        ),
        "country": "Ukraine",
        "publication_date": "2025-06-25",
        "landing_url": (
            "https://www.imf.org/en/publications/technical-assistance-reports/"
            "issues/2025/06/25/ukraine-technical-assistance-report-review-of-the-"
            "counterparty-eligibility-for-monetary-568011"
        ),
        "pdf_url": (
            "https://www.imf.org/-/media/files/publications/tar/2025/english/"
            "tarea2025067-print-pdf.pdf"
        ),
        "expected_page_count": 38,
        "recommendation_printed_pages": [8],
        "recommendation_pdf_page_numbers": [8],
        "body_pages": "9-36",
    },
    {
        "slug": "sri_lanka_liquidity_monitoring_and_monetary_operations_2024",
        "title": (
            "Sri Lanka: Technical Assistance Report-Liquidity Monitoring and Monetary Operations"
        ),
        "country": "Sri Lanka",
        "publication_date": "2024-09-20",
        "landing_url": (
            "https://www.elibrary.imf.org/view/journals/019/2024/078/019.2024.issue-078-en.xml"
        ),
        "pdf_url": (
            "https://www.imf.org/-/media/files/publications/tar/2024/english/"
            "tarea2024078-print-pdf.pdf"
        ),
        "expected_page_count": 35,
        "recommendation_printed_pages": [7, 8],
        "recommendation_pdf_page_numbers": [7, 8],
        "body_pages": "9-32",
    },
)


MANIFEST_FIELDS = (
    "slug",
    "title",
    "country",
    "publication_date",
    "landing_url",
    "pdf_url",
    "accessed_at",
    "report_page_count",
    "recommendation_printed_pages",
    "recommendation_pdf_page_indices",
    "body_pages",
    "sha256",
    "raw_pdf_path",
    "extracted_text_path",
    "extracted_pages_json_path",
    "extraction_engine",
    "notes",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, force: bool = False) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not force:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 IMF-TA-research/1.0",
            "Accept": "application/pdf,*/*;q=0.8",
        },
    )
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.", dir=destination.parent, delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                shutil.copyfileobj(response, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
            if tmp_path.stat().st_size < 1024:
                raise RuntimeError(f"Downloaded file is unexpectedly small: {url}")
            with tmp_path.open("rb") as downloaded:
                if downloaded.read(5) != b"%PDF-":
                    raise RuntimeError(f"Downloaded response is not a PDF: {url}")
            tmp_path.replace(destination)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise


def extract_with_pdfplumber(pdf_path: Path) -> tuple[list[dict[str, Any]], str]:
    import pdfplumber  # type: ignore

    page_records: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as document:
        for page_index, page in enumerate(document.pages):
            page_number = page_index + 1
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            page_records.append(
                {
                    "pdf_page_index": page_index,
                    "pdf_page_number": page_number,
                    "printed_page_number": page_number,
                    "width_points": round(float(page.width), 3),
                    "height_points": round(float(page.height), 3),
                    "text": text,
                }
            )
    return page_records, f"pdfplumber {pdfplumber.__version__}"


def extract_with_pypdf(pdf_path: Path) -> tuple[list[dict[str, Any]], str]:
    import pypdf  # type: ignore

    reader = pypdf.PdfReader(str(pdf_path))
    page_records: list[dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages):
        page_number = page_index + 1
        box = page.mediabox
        page_records.append(
            {
                "pdf_page_index": page_index,
                "pdf_page_number": page_number,
                "printed_page_number": page_number,
                "width_points": round(float(box.width), 3),
                "height_points": round(float(box.height), 3),
                "text": page.extract_text() or "",
            }
        )
    return page_records, f"pypdf {pypdf.__version__}"


def extract_pages(pdf_path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        return extract_with_pdfplumber(pdf_path)
    except (ImportError, ModuleNotFoundError):
        return extract_with_pypdf(pdf_path)


def write_page_outputs(
    report: dict[str, Any],
    page_records: list[dict[str, Any]],
    engine: str,
    extracted_dir: Path,
    project_root: Path,
) -> tuple[Path, Path]:
    text_path = extracted_dir / f"{report['slug']}.txt"
    pages_path = extracted_dir / f"{report['slug']}.pages.json"

    text_parts = []
    for record in page_records:
        text_parts.append(
            "===== "
            f"PDF_PAGE_INDEX: {record['pdf_page_index']} | "
            f"PDF_PAGE_NUMBER: {record['pdf_page_number']} | "
            f"PRINTED_PAGE: {record['printed_page_number']}"
            " =====\n"
            f"{record['text'].rstrip()}\n"
        )
    text_path.write_text("\n".join(text_parts), encoding="utf-8")

    payload = {
        "schema_version": "1.0",
        "slug": report["slug"],
        "title": report["title"],
        "country": report["country"],
        "source_pdf": str(
            (project_root / "data" / "reports" / "raw" / f"{report['slug']}.pdf").relative_to(
                project_root
            )
        ),
        "extraction_engine": engine,
        "page_numbering_note": (
            "pdf_page_index is zero-based; pdf_page_number and printed_page_number "
            "are one-based. These three IMF files number the cover as printed page 1."
        ),
        "pages": page_records,
    }
    pages_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return text_path, pages_path


def find_pdftoppm() -> str | None:
    configured = os.environ.get("PDFTOPPM")
    if configured and Path(configured).is_file():
        return configured
    discovered = shutil.which("pdftoppm")
    if discovered:
        return discovered
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pdftoppm"
    return str(bundled) if bundled.is_file() else None


def render_recommendation_pages(
    report: dict[str, Any], pdf_path: Path, rendered_root: Path, dpi: int
) -> None:
    executable = find_pdftoppm()
    if executable is None:
        raise RuntimeError("pdftoppm was not found. Install Poppler or set PDFTOPPM to its path.")

    report_dir = rendered_root / report["slug"]
    report_dir.mkdir(parents=True, exist_ok=True)
    for page_number in report["recommendation_pdf_page_numbers"]:
        output_prefix = report_dir / f"page_{page_number:03d}"
        subprocess.run(
            [
                executable,
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-singlefile",
                str(pdf_path),
                str(output_prefix),
            ],
            check=True,
        )


def write_manifest(rows: list[dict[str, Any]], reports_root: Path) -> None:
    json_path = reports_root / "manifest.json"
    csv_path = reports_root / "manifest.csv"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["recommendation_printed_pages"] = ";".join(
                str(value) for value in row["recommendation_printed_pages"]
            )
            csv_row["recommendation_pdf_page_indices"] = ";".join(
                str(value) for value in row["recommendation_pdf_page_indices"]
            )
            writer.writerow(csv_row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root (defaults to the parent of scripts/).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Require existing PDFs and only extract/render them.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Replace existing PDFs from the authoritative IMF URLs.",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Render every recommendation-table page to PNG with pdftoppm.",
    )
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI (default: 150).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.root.resolve()
    reports_root = project_root / "data" / "reports"
    raw_dir = reports_root / "raw"
    extracted_dir = reports_root / "extracted"
    rendered_dir = reports_root / "rendered"
    for directory in (raw_dir, extracted_dir, rendered_dir):
        directory.mkdir(parents=True, exist_ok=True)

    accessed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest_rows: list[dict[str, Any]] = []
    for report in REPORTS:
        pdf_path = raw_dir / f"{report['slug']}.pdf"
        if not args.skip_download:
            download(report["pdf_url"], pdf_path, force=args.force_download)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

        page_records, engine = extract_pages(pdf_path)
        page_count = len(page_records)
        if page_count != report["expected_page_count"]:
            raise RuntimeError(
                f"{report['slug']}: expected {report['expected_page_count']} pages, "
                f"found {page_count}"
            )
        text_path, pages_path = write_page_outputs(
            report, page_records, engine, extracted_dir, project_root
        )
        if args.render:
            render_recommendation_pages(report, pdf_path, rendered_dir, args.dpi)

        manifest_rows.append(
            {
                "slug": report["slug"],
                "title": report["title"],
                "country": report["country"],
                "publication_date": report["publication_date"],
                "landing_url": report["landing_url"],
                "pdf_url": report["pdf_url"],
                "accessed_at": accessed_at,
                "report_page_count": page_count,
                "recommendation_printed_pages": report["recommendation_printed_pages"],
                "recommendation_pdf_page_indices": [
                    value - 1 for value in report["recommendation_pdf_page_numbers"]
                ],
                "body_pages": report["body_pages"],
                "sha256": sha256_file(pdf_path),
                "raw_pdf_path": str(pdf_path.relative_to(project_root)),
                "extracted_text_path": str(text_path.relative_to(project_root)),
                "extracted_pages_json_path": str(pages_path.relative_to(project_root)),
                "extraction_engine": engine,
                "notes": (
                    "Authoritative IMF-hosted source; printed page numbers were "
                    "checked against the rendered recommendation pages."
                ),
            }
        )

    write_manifest(manifest_rows, reports_root)
    print(f"Prepared {len(manifest_rows)} IMF reports under {reports_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
