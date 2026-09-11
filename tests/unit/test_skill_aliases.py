from __future__ import annotations

from app.services.skill_extractor import extract_skills


def test_case_variants_map_to_python():
    assert extract_skills("Python") == ["Python"]
    assert extract_skills("python") == ["Python"]
    assert extract_skills("PYTHON") == ["Python"]


def test_postgres_aliases_map_to_postgresql():
    assert extract_skills("postgres") == ["PostgreSQL"]
    assert extract_skills("postgresql") == ["PostgreSQL"]
    assert extract_skills("PostgreSQL") == ["PostgreSQL"]


def test_sklearn_aliases_map_to_scikit_learn():
    assert extract_skills("sklearn") == ["scikit-learn"]
    assert extract_skills("scikit learn") == ["scikit-learn"]
    assert extract_skills("scikit-learn") == ["scikit-learn"]


def test_aws_aliases():
    assert extract_skills("amazon web services") == ["AWS"]
    assert extract_skills("AWS") == ["AWS"]


def test_spark_aliases():
    assert extract_skills("pyspark and apache spark") == ["Apache Spark"]


def test_r_does_not_match_ordinary_words():
    assert extract_skills("for our team are ready") == []
    assert extract_skills("experience with R and Python") == ["Python", "R"]


def test_go_does_not_match_english_go():
    assert extract_skills("we go to the office") == []
    assert extract_skills("Golang and Python") == ["Python", "Golang"]


def test_lambda_word_is_not_aws_lambda():
    assert "AWS Lambda" not in extract_skills("use a python lambda function")


def test_cv_is_not_computer_vision():
    assert extract_skills("please attach your cv") == []
