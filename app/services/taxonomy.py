from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from app.core.exceptions import TaxonomyError
from app.domain.skills import VALID_CATEGORIES, VALID_MATCH_STRATEGIES, SkillDefinition

DEFAULT_TAXONOMY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "taxonomy" / "skills.yml"
)

_CACHE: Dict[str, "SkillTaxonomy"] = {}


def slugify(canonical_name: str) -> str:
    lowered = canonical_name.strip().lower()
    lowered = lowered.replace("++", " plus plus ").replace("#", " sharp ")
    slug = []
    previous_dash = False
    for char in lowered:
        if char.isalnum():
            slug.append(char)
            previous_dash = False
        elif not previous_dash:
            slug.append("-")
            previous_dash = True
    return "".join(slug).strip("-")


class SkillTaxonomy:
    def __init__(self, skills: List[SkillDefinition]) -> None:
        self.skills = skills
        self.canonical_names = [skill.canonical_name for skill in skills]
        self.by_canonical = {skill.canonical_name: skill for skill in skills}
        self.by_normalized_alias: Dict[str, SkillDefinition] = {}
        for skill in skills:
            for alias in skill.aliases:
                key = alias if skill.match_strategy == "isolated_letter" else alias.lower()
                self.by_normalized_alias[key] = skill

    def __len__(self) -> int:
        return len(self.skills)

    def alias_count(self) -> int:
        return sum(len(skill.aliases) for skill in self.skills)

    def categories(self) -> List[str]:
        seen = []
        for skill in self.skills:
            if skill.category not in seen:
                seen.append(skill.category)
        return seen


def load_skill_taxonomy(
    path: Path | str | None = None,
    force_reload: bool = False,
) -> SkillTaxonomy:
    taxonomy_path = Path(path) if path is not None else DEFAULT_TAXONOMY_PATH
    cache_key = str(taxonomy_path.resolve())
    if force_reload or cache_key not in _CACHE:
        _CACHE[cache_key] = _parse_taxonomy(taxonomy_path)
    return _CACHE[cache_key]


def clear_taxonomy_cache() -> None:
    _CACHE.clear()


def _parse_taxonomy(path: Path) -> SkillTaxonomy:
    if not path.is_file():
        raise TaxonomyError(f"Skill taxonomy file was not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaxonomyError("Skill taxonomy YAML is malformed.") from exc

    if not isinstance(raw, dict) or not raw:
        raise TaxonomyError("Skill taxonomy must be a non-empty mapping of canonical names.")

    skills: List[SkillDefinition] = []
    canonical_seen: set[str] = set()
    alias_seen: dict[str, str] = {}

    for canonical_name, payload in raw.items():
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            raise TaxonomyError("Every skill must have a non-empty canonical name.")
        canonical_name = canonical_name.strip()
        if canonical_name in canonical_seen:
            raise TaxonomyError(f"Duplicate canonical skill: {canonical_name}")
        canonical_seen.add(canonical_name)

        if not isinstance(payload, dict):
            raise TaxonomyError(f"Skill '{canonical_name}' must be a mapping.")

        category = payload.get("category")
        if category not in VALID_CATEGORIES:
            raise TaxonomyError(
                f"Skill '{canonical_name}' has invalid category '{category}'."
            )

        aliases = payload.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise TaxonomyError(f"Skill '{canonical_name}' must declare at least one alias.")

        match_strategy = payload.get("match_strategy", "boundary")
        if match_strategy not in VALID_MATCH_STRATEGIES:
            raise TaxonomyError(
                f"Skill '{canonical_name}' has invalid match_strategy '{match_strategy}'."
            )

        cleaned_aliases: List[str] = []
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                raise TaxonomyError(f"Skill '{canonical_name}' has an empty alias.")
            alias = alias.strip()
            alias_key = alias if match_strategy == "isolated_letter" else alias.lower()
            owner = alias_seen.get(alias_key)
            if owner and owner != canonical_name:
                raise TaxonomyError(
                    f"Alias '{alias}' is assigned to both '{owner}' and '{canonical_name}'."
                )
            alias_seen[alias_key] = canonical_name
            if alias not in cleaned_aliases:
                cleaned_aliases.append(alias)

        if canonical_name.lower() not in {item.lower() for item in cleaned_aliases}:
            cleaned_aliases.insert(0, canonical_name)

        skills.append(
            SkillDefinition(
                canonical_name=canonical_name,
                category=category,
                aliases=tuple(cleaned_aliases),
                match_strategy=match_strategy,
            )
        )

    return SkillTaxonomy(skills)
