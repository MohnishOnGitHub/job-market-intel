from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def test_frontend_uses_same_origin_and_current_endpoints():
    market = (FRONTEND / "index.html").read_text(encoding="utf-8")
    match = (FRONTEND / "match.html").read_text(encoding="utf-8")
    evaluation = (FRONTEND / "evaluation.html").read_text(encoding="utf-8")
    api = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    market_js = (FRONTEND / "js" / "market.js").read_text(encoding="utf-8")
    match_js = (FRONTEND / "js" / "match.js").read_text(encoding="utf-8")
    assert "127.0.0.1" not in market + match + api + market_js + match_js
    assert "/api/v1/analytics/overview" in market_js
    assert "/api/v1/analytics/skills" in market_js
    assert "/upload-resume" in match_js
    assert "/api/v1/matches/upload" in match_js
    assert "Match score" in match_js
    assert "chance of getting hired" not in match.lower()
    assert "not statistically significant" in evaluation.lower()
    assert "sentence-transformer" in evaluation.lower()
    assert "0.852" in evaluation
    assert "hashing-v1" in evaluation
    assert "chart.js@4.4.1" in market.lower()
