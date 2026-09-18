#!/usr/bin/env python3
"""Run the prepared Part C IMF prompts through the OpenAI Responses API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mpie.config import RuntimeConfig
from mpie.llm import OpenAIResponsesLLM
from mpie.schemas import RecommendationQualityResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "outputs" / "reference_inputs"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "reference_results"


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def run(input_dir: Path, output_dir: Path, *, model: str | None = None) -> int:
    config = RuntimeConfig.from_env()
    api_key = config.resolved_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be set for a live reference run")

    metadata = load_json(input_dir / "metadata.json")
    runs = metadata.get("runs")
    if not isinstance(runs, list):
        raise TypeError("reference metadata must contain a runs array")

    llm = OpenAIResponsesLLM.from_api_key(api_key, model=model or config.model)
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in runs:
        if not isinstance(item, dict):
            raise TypeError("every run metadata entry must be an object")
        report_id = str(item["report_id"])
        prompt_path = PROJECT_ROOT / str(item["prompt_path"])
        prompt = prompt_path.read_text(encoding="utf-8")
        result = llm.parse(prompt, RecommendationQualityResult)
        if result.report_id != report_id:
            raise ValueError(f"model returned the wrong report_id for {report_id}")
        destination = output_dir / f"{report_id}.json"
        destination.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {destination.relative_to(PROJECT_ROOT)}")
    return len(runs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", help="Override OPENAI_MODEL for this run")
    args = parser.parse_args()
    count = run(
        args.input_dir.resolve(),
        args.output_dir.resolve(),
        model=args.model,
    )
    print(f"Completed {count} report evaluations.")


if __name__ == "__main__":
    main()
