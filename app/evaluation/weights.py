from __future__ import annotations

from typing import Iterable, List, Tuple

from app.services.hybrid_ranking import RankingWeights

DESIGN_WEIGHT_TUPLE = (0.50, 0.25, 0.10, 0.10, 0.05)


def normalize_weight_tuple(values: Iterable[float]) -> Tuple[float, float, float, float, float]:
    items = [float(value) for value in values]
    if len(items) != 5:
        raise ValueError("expected five ranking weights")
    if any(value < 0 for value in items):
        raise ValueError("ranking weights must be >= 0")
    total = sum(items)
    if total <= 0:
        raise ValueError("ranking weights must sum to a positive number")
    normalized = tuple(value / total for value in items)
    return (
        normalized[0],
        normalized[1],
        normalized[2],
        normalized[3],
        normalized[4],
    )


def ranking_weights_from_tuple(values: Iterable[float]) -> RankingWeights:
    semantic, skill, experience, recency, location = normalize_weight_tuple(values)
    return RankingWeights(semantic, skill, experience, recency, location)


def coarse_weight_grid() -> List[RankingWeights]:
    """Small explicit grid. Not a large hyperparameter search."""
    seen = set()
    grid: List[RankingWeights] = []
    for semantic in (0.30, 0.50, 0.70):
        for skill in (0.10, 0.25, 0.40):
            for recency in (0.00, 0.10):
                for experience in (0.00, 0.10):
                    for location in (0.00, 0.05):
                        try:
                            weights = ranking_weights_from_tuple(
                                (semantic, skill, experience, recency, location)
                            )
                        except ValueError:
                            continue
                        key = (
                            round(weights.semantic, 4),
                            round(weights.skill, 4),
                            round(weights.experience, 4),
                            round(weights.recency, 4),
                            round(weights.location, 4),
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        grid.append(weights)
    design = ranking_weights_from_tuple(DESIGN_WEIGHT_TUPLE)
    design_key = (
        round(design.semantic, 4),
        round(design.skill, 4),
        round(design.experience, 4),
        round(design.recency, 4),
        round(design.location, 4),
    )
    if design_key not in seen:
        grid.insert(0, design)
    return grid
