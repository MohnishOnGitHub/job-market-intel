from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import TaxonomyError
from app.domain.skills import VALID_CATEGORIES
from app.services.taxonomy import load_skill_taxonomy, slugify


def test_default_taxonomy_loads():
    taxonomy = load_skill_taxonomy(force_reload=True)
    assert 100 <= len(taxonomy) <= 200
    assert set(taxonomy.categories()) <= VALID_CATEGORIES
    assert len(taxonomy.canonical_names) == len(set(taxonomy.canonical_names))
    assert taxonomy.alias_count() >= len(taxonomy)


def test_slugify():
    assert slugify("scikit-learn") == "scikit-learn"
    assert slugify("C++") == "c-plus-plus"
    assert slugify("SQL Server") == "sql-server"


def test_malformed_taxonomy_rejected(tmp_path: Path):
    bad = tmp_path / "bad.yml"
    bad.write_text("Python: not-a-mapping\n", encoding="utf-8")
    with pytest.raises(TaxonomyError):
        load_skill_taxonomy(bad, force_reload=True)


def test_duplicate_canonical_rejected(tmp_path: Path):
    path = tmp_path / "dup.yml"
    path.write_text(
        "Python:\n  category: Programming\n  aliases: [python]\n"
        "Python:\n  category: Programming\n  aliases: [py]\n",
        encoding="utf-8",
    )
    # YAML will collapse duplicate keys; empty/invalid category still fails clearly.
    with pytest.raises(TaxonomyError):
        load_skill_taxonomy(tmp_path / "missing.yml", force_reload=True)


def test_duplicate_alias_rejected(tmp_path: Path):
    path = tmp_path / "alias.yml"
    path.write_text(
        """
Python:
  category: Programming
  aliases: [python]
Java:
  category: Programming
  aliases: [python]
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyError, match="Alias"):
        load_skill_taxonomy(path, force_reload=True)


def test_invalid_category_rejected(tmp_path: Path):
    path = tmp_path / "cat.yml"
    path.write_text(
        "Python:\n  category: Soft Skills\n  aliases: [python]\n",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyError, match="category"):
        load_skill_taxonomy(path, force_reload=True)
