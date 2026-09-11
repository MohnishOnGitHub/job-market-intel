from __future__ import annotations

from pathlib import Path

import scripts.evaluate_ranking as evaluate_ranking

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_ranking.py"


def test_evaluate_cli_help_lists_options():
    help_text = evaluate_ranking.build_parser().format_help()
    assert "--dataset" in help_text
    assert "--methods" in help_text
    assert "--split" in help_text
    assert "--output" in help_text
    source = SCRIPT.read_text(encoding="utf-8")
    assert "evaluate_dataset" in source
    assert "password=" not in source
