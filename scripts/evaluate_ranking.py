#!/usr/bin/env python3
"""Offline ranking evaluation against the committed fixture.

  python scripts/evaluate_ranking.py
  python scripts/evaluate_ranking.py --split test --methods skills,tfidf,hashing,semantic,hybrid
  python scripts/evaluate_ranking.py --tune --output artifacts/evaluation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.dataset import default_dataset_path, load_evaluation_dataset
from app.evaluation.runner import evaluate_dataset, format_table, write_results
from app.evaluation.v1_authoring import build_v1_dataset
from app.evaluation.dataset import write_dataset_json, write_labels_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate ranking methods on a labeled fixture.")
    parser.add_argument(
        "--dataset",
        default=str(default_dataset_path()),
        help="Path to dataset.json or its directory.",
    )
    parser.add_argument(
        "--methods",
        default="skills,tfidf,hashing,semantic,hybrid",
        help="Comma-separated method names.",
    )
    parser.add_argument("--split", default="test", choices=["test", "validation", "all"])
    parser.add_argument("--output", default="artifacts/evaluation")
    parser.add_argument("--no-ablations", action="store_true")
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Optional validation-only weight grid. Does not change production defaults.",
    )
    parser.add_argument(
        "--write-fixture",
        action="store_true",
        help="Regenerate the committed v1 JSON/CSV from the authoring module.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write_fixture:
        dataset = build_v1_dataset()
        root = Path("data/evaluation/v1")
        write_dataset_json(dataset, root / "dataset.json")
        write_labels_csv(dataset, root / "labels.csv")
        print(f"Wrote {root / 'dataset.json'} and {root / 'labels.csv'}")
        return 0

    dataset = load_evaluation_dataset(args.dataset)
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    payload = evaluate_dataset(
        dataset,
        methods=methods,
        split=args.split,
        include_ablations=not args.no_ablations,
        tune_weights=args.tune,
    )
    write_results(payload, args.output)
    print(format_table(payload))
    print(f"\nWrote {args.output}/results.json and {args.output}/per_query.csv")
    skipped = [
        name
        for name, method in payload["methods"].items()
        if not method.get("ran")
    ]
    if skipped:
        print("Not run: " + ", ".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
