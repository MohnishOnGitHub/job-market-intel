from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

# Phase 1 keeps the existing vocabulary. Taxonomy/aliases are Phase 3.
SKILLS: List[str] = [
    "python",
    "sql",
    "excel",
    "machine learning",
    "deep learning",
    "django",
    "flask",
    "fastapi",
    "pandas",
    "numpy",
    "react",
    "javascript",
    "html",
    "css",
    "aws",
    "docker",
    "kubernetes",
    "rest api",
    "graphql",
    "spark",
    "hadoop",
]

_SKILL_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        skill,
        re.compile(
            r"(?<!\w)" + re.escape(skill).replace(r"\ ", r"\s+") + r"(?!\w)",
            re.IGNORECASE,
        ),
    )
    for skill in SKILLS
]


def extract_skills(text: str | None) -> List[str]:
    """Return vocabulary skills that appear as whole tokens/phrases.

    Matching is case-insensitive and boundary-aware so that substrings
    such as ``sql`` inside ``postgresql`` or ``aws`` inside ``laws``
    are not treated as skills.
    """
    if not text:
        return []

    found: List[str] = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text) and skill not in found:
            found.append(skill)
    return found


def skill_overlap(
    resume_skills: Sequence[str],
    job_skills: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """Return (matched_skills, missing_skills) in SKILLS list order."""
    resume_set = set(resume_skills)
    job_set = set(job_skills)
    matched = [skill for skill in SKILLS if skill in resume_set and skill in job_set]
    missing = [skill for skill in SKILLS if skill in job_set and skill not in resume_set]
    extras_matched = [
        skill for skill in resume_skills if skill in job_set and skill not in matched
    ]
    extras_missing = [
        skill for skill in job_skills if skill not in resume_set and skill not in missing
    ]
    return matched + extras_matched, missing + extras_missing


def compute_skill_score(
    matched_skills: Iterable[str],
    job_skills: Sequence[str],
) -> float:
    """Overlap ratio. Empty job skills yield 0 (known Phase 1 limitation)."""
    job_skill_list = list(job_skills)
    if not job_skill_list:
        return 0.0
    return len(list(matched_skills)) / len(job_skill_list)
