from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, List, Sequence, Tuple

from app.domain.skills import ExtractedSkill, SkillDefinition
from app.services.taxonomy import SkillTaxonomy, load_skill_taxonomy


def _alias_pattern(alias: str, match_strategy: str) -> re.Pattern[str]:
    if match_strategy == "isolated_letter":
        return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])")
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


@lru_cache
def _compiled_patterns() -> Tuple[Tuple[SkillDefinition, str, re.Pattern[str]], ...]:
    taxonomy = load_skill_taxonomy()
    compiled: List[Tuple[SkillDefinition, str, re.Pattern[str]]] = []
    for skill in taxonomy.skills:
        aliases = sorted(skill.aliases, key=len, reverse=True)
        for alias in aliases:
            compiled.append((skill, alias, _alias_pattern(alias, skill.match_strategy)))
    return tuple(compiled)


def clear_extractor_cache() -> None:
    _compiled_patterns.cache_clear()


def extract_skill_records(text: str | None) -> List[ExtractedSkill]:
    """Return unique canonical skills in taxonomy order."""
    if not text:
        return []

    found: dict[str, ExtractedSkill] = {}
    for skill, alias, pattern in _compiled_patterns():
        if skill.canonical_name in found:
            continue
        if pattern.search(text):
            found[skill.canonical_name] = ExtractedSkill(
                canonical_name=skill.canonical_name,
                category=skill.category,
                matched_alias=alias,
            )

    taxonomy = load_skill_taxonomy()
    return [
        found[name]
        for name in taxonomy.canonical_names
        if name in found
    ]


def extract_skills(text: str | None) -> List[str]:
    """Canonical skill names for ranking and overlap."""
    return [skill.canonical_name for skill in extract_skill_records(text)]


def skill_overlap(
    resume_skills: Sequence[str],
    job_skills: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """Return (matched_skills, missing_skills) in taxonomy order."""
    resume_set = set(resume_skills)
    job_set = set(job_skills)
    try:
        order = load_skill_taxonomy().canonical_names
    except Exception:
        order = list(dict.fromkeys(list(job_skills) + list(resume_skills)))

    matched = [skill for skill in order if skill in resume_set and skill in job_set]
    missing = [skill for skill in order if skill in job_set and skill not in resume_set]
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
    """Overlap ratio. Empty job skills yield 0 (known limitation)."""
    job_skill_list = list(job_skills)
    if not job_skill_list:
        return 0.0
    return len(list(matched_skills)) / len(job_skill_list)


def taxonomy_skill_names() -> List[str]:
    return list(load_skill_taxonomy().canonical_names)


# Back-compat alias used by older tests; now canonical names from the taxonomy.
SKILLS = taxonomy_skill_names()
