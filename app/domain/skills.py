from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


VALID_CATEGORIES = frozenset(
    {
        "Programming",
        "Databases",
        "Data Engineering",
        "Machine Learning",
        "Deep Learning",
        "NLP",
        "Computer Vision",
        "Cloud",
        "MLOps",
        "DevOps",
        "Analytics / BI",
        "Data Warehousing",
        "Frameworks",
    }
)

VALID_MATCH_STRATEGIES = frozenset({"boundary", "isolated_letter"})


@dataclass(frozen=True)
class SkillDefinition:
    canonical_name: str
    category: str
    aliases: tuple[str, ...]
    match_strategy: str = "boundary"


@dataclass(frozen=True)
class ExtractedSkill:
    canonical_name: str
    category: str
    matched_alias: Optional[str] = None
