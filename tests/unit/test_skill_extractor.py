from __future__ import annotations

from app.services.skill_extractor import (
    SKILLS,
    compute_skill_score,
    extract_skills,
    skill_overlap,
)


def test_extracts_standalone_skills():
    text = "Experience with Python, SQL, FastAPI, and AWS."
    found = extract_skills(text)
    assert found == ["python", "sql", "fastapi", "aws"]


def test_preserves_skill_list_order():
    text = "aws python sql"
    assert extract_skills(text) == ["python", "sql", "aws"]


def test_postgresql_does_not_infer_sql():
    assert "sql" not in extract_skills("experienced with PostgreSQL")


def test_mysql_does_not_infer_sql():
    assert extract_skills("worked with MySQL") == []


def test_nosql_does_not_infer_sql():
    assert extract_skills("worked on nosql and document stores") == []


def test_sqlite_does_not_infer_sql():
    assert extract_skills("used sqlite for local storage") == []


def test_laws_does_not_match_aws():
    assert extract_skills("laws and awesome clouds") == []


def test_aws_matches_as_its_own_token():
    assert extract_skills("deployed services on AWS.") == ["aws"]


def test_sql_matches_when_it_appears_separately():
    assert "sql" in extract_skills("PostgreSQL and SQL are both used")


def test_multiword_skill_match():
    assert extract_skills("strong machine learning background") == ["machine learning"]


def test_empty_and_none_text():
    assert extract_skills("") == []
    assert extract_skills(None) == []


def test_skill_overlap_and_missing():
    resume = ["python", "sql", "pandas"]
    job = ["python", "sql", "spark", "aws"]
    matched, missing = skill_overlap(resume, job)
    assert matched == ["python", "sql"]
    assert missing == ["aws", "spark"]


def test_skill_score_is_overlap_ratio():
    assert compute_skill_score(["python", "sql"], ["python", "sql", "spark", "aws"]) == 0.5


def test_skill_score_is_zero_when_job_has_no_skills():
    assert compute_skill_score(["python"], []) == 0
    assert compute_skill_score([], []) == 0


def test_existing_vocabulary_is_unchanged():
    assert SKILLS == [
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
