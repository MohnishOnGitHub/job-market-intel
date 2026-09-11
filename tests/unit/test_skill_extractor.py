from __future__ import annotations

from app.services.skill_extractor import (
    compute_skill_score,
    extract_skill_records,
    extract_skills,
    skill_overlap,
)


def test_extracts_canonical_names():
    text = "Experience with Python, SQL, FastAPI, and AWS."
    assert extract_skills(text) == ["Python", "SQL", "AWS", "FastAPI"]


def test_preserves_taxonomy_order():
    assert extract_skills("aws python sql") == ["Python", "SQL", "AWS"]


def test_postgresql_does_not_infer_sql():
    found = extract_skills("experienced with PostgreSQL")
    assert found == ["PostgreSQL"]
    assert "SQL" not in found


def test_mysql_does_not_infer_sql():
    found = extract_skills("worked with MySQL")
    assert found == ["MySQL"]
    assert "SQL" not in found


def test_nosql_does_not_infer_sql():
    found = extract_skills("worked on nosql and document stores")
    assert "SQL" not in found
    assert found == ["NoSQL"]


def test_sqlite_does_not_infer_sql():
    found = extract_skills("used sqlite for local storage")
    assert found == ["SQLite"]
    assert "SQL" not in found


def test_laws_does_not_match_aws():
    assert extract_skills("laws and awesome clouds") == []


def test_aws_matches_as_its_own_token():
    assert extract_skills("deployed services on AWS.") == ["AWS"]


def test_sql_matches_when_it_appears_separately():
    found = extract_skills("PostgreSQL and SQL are both used")
    assert found == ["SQL", "PostgreSQL"]


def test_multiword_skill_match():
    assert extract_skills("strong machine learning background") == ["Machine Learning"]


def test_empty_and_none_text():
    assert extract_skills("") == []
    assert extract_skills(None) == []


def test_skill_overlap_and_missing():
    resume = ["Python", "SQL", "pandas"]
    job = ["Python", "SQL", "Apache Spark", "AWS"]
    matched, missing = skill_overlap(resume, job)
    assert matched == ["Python", "SQL"]
    assert missing == ["Apache Spark", "AWS"]


def test_skill_score_is_overlap_ratio():
    assert compute_skill_score(["Python", "SQL"], ["Python", "SQL", "Apache Spark", "AWS"]) == 0.5


def test_skill_score_is_zero_when_job_has_no_skills():
    assert compute_skill_score(["Python"], []) == 0
    assert compute_skill_score([], []) == 0


def test_legacy_vocabulary_still_resolves():
    text = (
        "python sql excel machine learning deep learning django flask fastapi "
        "pandas numpy react javascript html css aws docker kubernetes rest api graphql spark hadoop"
    )
    found = set(extract_skills(text))
    assert {
        "Python",
        "SQL",
        "Excel",
        "Machine Learning",
        "Deep Learning",
        "Django",
        "Flask",
        "FastAPI",
        "pandas",
        "NumPy",
        "React",
        "JavaScript",
        "HTML",
        "CSS",
        "AWS",
        "Docker",
        "Kubernetes",
        "REST",
        "GraphQL",
        "Apache Spark",
        "Hadoop",
    }.issubset(found)


def test_extracted_skill_includes_category_and_alias():
    records = extract_skill_records("we used postgres and sklearn")
    by_name = {item.canonical_name: item for item in records}
    assert by_name["PostgreSQL"].category == "Databases"
    assert by_name["PostgreSQL"].matched_alias == "postgres"
    assert by_name["scikit-learn"].canonical_name == "scikit-learn"
