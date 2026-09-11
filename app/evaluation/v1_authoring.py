from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from app.evaluation import BINARY_RELEVANCE_THRESHOLD, DATASET_VERSION
from app.evaluation.dataset import (
    EvaluationDataset,
    EvaluationJob,
    EvaluationResume,
    RelevanceLabel,
)
from app.services.skill_extractor import extract_skills

SENIORITY_ORDER = ("internship", "entry", "junior", "mid", "senior", "lead")
ADJACENT_FAMILIES = {
    "da": {"da", "analytics"},
    "ds": {"ds", "mle"},
    "de": {"de", "analytics"},
    "mle": {"mle", "ds"},
    "be": {"be"},
    "analytics": {"analytics", "da", "de"},
}

# Independent of ranker scores. Applied only while authoring the fixture.
LABEL_OVERRIDES: Dict[Tuple[str, int], Tuple[int, str]] = {
    ("r_da_junior", 15): (0, "Clinical admin posting; Python/SQL mention is incidental."),
    ("r_ds_mid", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_de_mid", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_de_senior", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_mle_mid", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_be_mid", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_da_mid", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_ds_senior", 15): (0, "Clinical admin posting; lexical bait."),
    ("r_be_mid", 7): (1, "Backend title but Go/Java stack, not the candidate's Python API work."),
    ("r_ds_senior", 12): (3, "NLP research role matches senior transformer background."),
    ("r_ds_mid", 12): (2, "Research scientist is adjacent; mid DS can be qualified with gaps."),
    ("r_de_mid", 29): (1, "Fresh posting but marketing-ops intern work, not data engineering."),
    ("r_da_junior", 9): (2, "Internship is below junior, but same analyst family."),
}


def author_label(
    resume_family: str,
    resume_seniority: str,
    job_family: str,
    job_seniority: Optional[str],
) -> int:
    """Role-family/seniority rubric. Does not use TF-IDF, embeddings, or hybrid scores."""
    if job_family == "other":
        return 0
    same = resume_family == job_family
    adjacent = job_family in ADJACENT_FAMILIES.get(resume_family, set())
    if not same and not adjacent:
        return 0
    if job_seniority not in SENIORITY_ORDER:
        distance = 1
    else:
        distance = abs(
            SENIORITY_ORDER.index(resume_seniority) - SENIORITY_ORDER.index(job_seniority)
        )
    if same:
        if distance == 0:
            return 3
        if distance == 1:
            return 2
        if distance == 2:
            return 1
        return 0
    if distance == 0:
        return 2
    if distance == 1:
        return 1
    return 0


def build_v1_dataset() -> EvaluationDataset:
    resumes = _resumes()
    jobs = []
    for job in _jobs():
        skills = extract_skills(job.description) or []
        jobs.append(
            EvaluationJob(
                id=job.id,
                title=job.title,
                description=job.description,
                company=job.company,
                location=job.location,
                experience_level=job.experience_level,
                posted_at=job.posted_at,
                skills=skills,
                role_family=job.role_family,
                notes=job.notes,
            )
        )
    labels = _labels(resumes, jobs)
    return EvaluationDataset(
        version=DATASET_VERSION,
        resumes=resumes,
        jobs=jobs,
        labels=labels,
        binary_threshold=BINARY_RELEVANCE_THRESHOLD,
        description=(
            "Synthetic v1 ranking benchmark. Profiles and jobs are authored fixtures, "
            "not real applicants or live Adzuna rows. Labels follow the role-family/"
            "seniority rubric in docs/EVALUATION_GUIDE.md and do not use model scores."
        ),
        split_strategy="profile-level",
        labeling_method="author-rubric-v1",
    )


def _dt(days_ago: int) -> datetime:
    return datetime(2026, 9, 11, tzinfo=timezone.utc) - timedelta(days=days_ago)


def _resumes() -> List[EvaluationResume]:
    return [
        EvaluationResume(
            id="r_da_junior",
            profile="Data Analyst",
            seniority="junior",
            split="validation",
            preferred_location="Bengaluru",
            preferred_experience="junior",
            notes="Synthetic junior analyst.",
            text=(
                "SYNTHETIC PROFILE. Junior Data Analyst in Bengaluru. Two years of SQL, "
                "Excel, and Tableau reporting for a retail operations team. Built weekly "
                "dashboards, wrote ad-hoc queries against PostgreSQL, and cleaned CSV "
                "extracts in Python pandas. Comfortable with A/B readout slides and "
                "basic statistics. No Spark, Airflow, or production ML experience. "
                "Seeking a junior or early mid analytics role, not a platform engineering job."
            ),
        ),
        EvaluationResume(
            id="r_ds_mid",
            profile="Data Scientist",
            seniority="mid",
            split="validation",
            preferred_location="Remote",
            preferred_experience="mid",
            notes="Synthetic mid data scientist.",
            text=(
                "SYNTHETIC PROFILE. Mid-level Data Scientist. Python, pandas, scikit-learn, "
                "and SQL for churn and propensity models. Experience with experiment design, "
                "feature stores at a small scale, and model monitoring notebooks. Some AWS "
                "SageMaker batch jobs. No large-scale Spark pipelines and limited deep "
                "learning. Prefers remote applied science roles rather than analytics-only "
                "dashboard work or backend API ownership."
            ),
        ),
        EvaluationResume(
            id="r_de_senior",
            profile="Data Engineer",
            seniority="senior",
            split="validation",
            preferred_location="Remote",
            preferred_experience="senior",
            notes="Synthetic senior data engineer.",
            text=(
                "SYNTHETIC PROFILE. Senior Data Engineer. Designed batch and streaming "
                "platforms with Apache Spark, Kafka, Airflow, and dbt on Snowflake and GCP. "
                "Owned lakehouse modeling, data contracts, and on-call for ingestion SLAs. "
                "Mentored mid engineers. Python and SQL daily. Not looking for analyst "
                "dashboard work or research-scientist roles. Open to remote senior or lead "
                "data platform positions."
            ),
        ),
        EvaluationResume(
            id="r_mle_mid",
            profile="Machine Learning Engineer",
            seniority="mid",
            split="validation",
            preferred_location="Bengaluru",
            preferred_experience="mid",
            notes="Synthetic mid ML engineer.",
            text=(
                "SYNTHETIC PROFILE. Mid Machine Learning Engineer in Bengaluru. Ships "
                "PyTorch training jobs, ONNX export, and FastAPI model services on AWS. "
                "Experience with feature pipelines, model registry, and CI for training. "
                "Comfortable with SQL and Docker. Less interested in Tableau reporting or "
                "pure Java backend. Looking for mid ML engineering or applied ML platform work."
            ),
        ),
        EvaluationResume(
            id="r_da_mid",
            profile="Data Analyst / Analytics Engineer",
            seniority="mid",
            split="validation",
            preferred_location="Pune",
            preferred_experience="mid",
            notes="Synthetic mid analytics engineer.",
            text=(
                "SYNTHETIC PROFILE. Mid Data Analyst moving toward analytics engineering. "
                "Strong SQL, dbt, Looker, and warehouse modeling on BigQuery. Partners with "
                "finance and growth teams. Light Python for analyses, no Spark clusters, no "
                "deep learning. Based around Pune and open to hybrid. Wants analytics "
                "engineer or mid analyst roles, not backend microservices."
            ),
        ),
        EvaluationResume(
            id="r_de_mid",
            profile="Data Engineer",
            seniority="mid",
            split="test",
            preferred_location="Bengaluru",
            preferred_experience="mid",
            notes="Synthetic mid data engineer. Held-out test profile.",
            text=(
                "SYNTHETIC PROFILE. Mid Data Engineer in Bengaluru. Builds Python and SQL "
                "ETL with Apache Spark, Airflow, and AWS (S3, Glue, Redshift). Has production "
                "on-call experience and unit-tested ingestion jobs. Some dbt. No NLP research "
                "and limited frontend work. Targeting mid data engineering roles in Bengaluru "
                "or remote data platform teams."
            ),
        ),
        EvaluationResume(
            id="r_ds_senior",
            profile="Data Scientist",
            seniority="senior",
            split="test",
            preferred_location="Remote",
            preferred_experience="senior",
            notes="Synthetic senior NLP scientist. Held-out test profile.",
            text=(
                "SYNTHETIC PROFILE. Senior Data Scientist focused on NLP. Fine-tuned "
                "transformer models, evaluation sets, and retrieval prototypes. Python, "
                "PyTorch, Hugging Face, and SQL. Has led a small applied-science pod. Weak "
                "Spark platform background. Seeking senior applied science or NLP roles, "
                "remote. Not targeting junior dashboard analyst seats."
            ),
        ),
        EvaluationResume(
            id="r_be_mid",
            profile="Backend Software Engineer",
            seniority="mid",
            split="test",
            preferred_location="Hyderabad",
            preferred_experience="mid",
            notes="Synthetic mid backend engineer. Held-out test profile.",
            text=(
                "SYNTHETIC PROFILE. Mid Backend Software Engineer in Hyderabad. Builds "
                "Python FastAPI services, PostgreSQL schemas, Redis caching, and Docker "
                "deployments. Writes integration tests and owns API latency. Some Kafka "
                "consumer work. Not a data warehouse modeler and not an ML researcher. "
                "Looking for mid backend or platform API roles."
            ),
        ),
    ]


def _jobs() -> List[EvaluationJob]:
    specs = [
        (1, "Data Engineer", "Nimbus Labs", "Bengaluru", _de_mid_blr(), "mid", 4, "de"),
        (2, "Senior Data Engineer", "Northwind Data", "Remote", _de_senior_remote(), "senior", 12, "de"),
        (3, "Junior Data Analyst", "Retail Insights", "Bengaluru", _da_junior_blr(), "junior", 7, "da"),
        (4, "Data Scientist", "Harbor Analytics", "Remote", _ds_mid_remote(), "mid", 9, "ds"),
        (5, "Machine Learning Engineer", "Orchid ML", "Bengaluru", _mle_mid_blr(), "mid", 6, "mle"),
        (6, "Backend Engineer", "Lotus Payments", "Hyderabad", _be_mid_hyd(), "mid", 5, "be"),
        (7, "Senior Backend Engineer", "Cobalt Systems", "Hyderabad", _be_senior_go(), "senior", 20, "be"),
        (8, "Lead Data Engineer", "Atlas Freight", "Remote", _de_lead(), "lead", 15, "de"),
        (9, "Data Analyst Intern", "Campus Metrics", "Bengaluru", _da_intern(), "internship", 2, "da"),
        (10, "Analytics Engineer", "Brightline", "Pune", _analytics_mid(), "mid", 8, "analytics"),
        (11, "BI Developer", "Ledger Soft", "Pune", _bi_dev(), "mid", 18, "da"),
        (12, "NLP Research Scientist", "Vector Institute Contract", "Remote", _nlp_research(), "senior", 11, "ds"),
        (13, "MLOps Engineer", "Forge Models", "Bengaluru", _mlops(), "mid", 14, "mle"),
        (14, "Data Engineer Intern", "PipeStart", "Bengaluru", _de_intern(), "internship", 3, "de"),
        (15, "Clinical Data Coordinator", "City Hospital", "Bengaluru", _clinical_bait(), None, 1, "other"),
        (16, "Registered Nurse", "City Hospital", "Bengaluru", _nurse(), None, 6, "other"),
        (17, "Account Executive", "SaaS North", "Mumbai", _sales(), None, 10, "other"),
        (18, "Product Manager", "Orbit Apps", "Remote", _pm(), "mid", 16, "other"),
        (19, "Senior Data Scientist", "Helio Speech", "Remote", _ds_senior_nlp(), "senior", 13, "ds"),
        (20, "Junior Data Engineer", "Kite Batch", "Bengaluru", _de_junior(), "junior", 9, "de"),
        (21, "Data Analyst", "Market Basket", "Pune", _da_mid_pune(), "mid", 17, "da"),
        (22, "Platform Engineer", "Mesh Cloud", "Hyderabad", _platform_k8s(), "mid", 21, "be"),
        (23, "Senior Analytics Engineer", "North Star BI", "Remote", _analytics_senior(), "senior", 19, "analytics"),
        (24, "Senior Machine Learning Engineer", "Aero Vision", "Bengaluru", _mle_senior(), "senior", 22, "mle"),
        (25, "Data Engineer", "West End Retail", "Mumbai", _de_mumbai(), "mid", 8, "de"),
        (26, "Senior Backend Engineer", "Pagoda API", "Hyderabad", _be_senior_python(), "senior", 25, "be"),
        (27, "Quantitative Analyst", "Harbor Desk", "Remote", _quant(), "mid", 28, "ds"),
        (28, "DevOps Engineer", "Stackyard", "Hyderabad", _devops(), "mid", 30, "other"),
        (29, "Marketing Data Intern", "AdBloom", "Bengaluru", _marketing_intern(), "internship", 1, "other"),
        (30, "Junior Data Scientist", "Leaf Health", "Remote", _ds_junior(), "junior", 12, "ds"),
        (31, "Full Stack Engineer", "Canvas Web", "Hyderabad", _fullstack(), "mid", 14, "be"),
        (32, "Data Engineer", "Slow River", "Bengaluru", _de_stale(), "mid", 180, "de"),
    ]
    return [
        EvaluationJob(
            id=job_id,
            title=title,
            description=description,
            company=company,
            location=location,
            experience_level=experience,
            posted_at=_dt(days_ago),
            role_family=family,
        )
        for job_id, title, company, location, description, experience, days_ago, family in specs
    ]


def _labels(
    resumes: Sequence[EvaluationResume],
    jobs: Sequence[EvaluationJob],
) -> List[RelevanceLabel]:
    labels: List[RelevanceLabel] = []
    for resume in resumes:
        for job in jobs:
            override = LABEL_OVERRIDES.get((resume.id, job.id))
            if override:
                relevance, notes = override
            else:
                relevance = author_label(
                    _resume_family(resume.id),
                    resume.seniority,
                    job.role_family or "other",
                    job.experience_level,
                )
                notes = "Role-family and seniority rubric."
            labels.append(
                RelevanceLabel(
                    resume_id=resume.id,
                    job_id=job.id,
                    relevance=relevance,
                    notes=notes,
                    labeler="author-v1",
                    split=resume.split,
                )
            )
    return labels


def _resume_family(resume_id: str) -> str:
    return {
        "r_da_junior": "da",
        "r_ds_mid": "ds",
        "r_de_senior": "de",
        "r_mle_mid": "mle",
        "r_da_mid": "da",
        "r_de_mid": "de",
        "r_ds_senior": "ds",
        "r_be_mid": "be",
    }[resume_id]


def _de_mid_blr() -> str:
    return (
        "Mid Data Engineer in Bengaluru. Build Python ETL, SQL models, Apache Spark "
        "jobs, and Airflow DAGs on AWS S3 and Redshift. Own data quality checks and "
        "on-call for failed pipelines. dbt welcome. Not a reporting-only analyst seat."
    )


def _de_senior_remote() -> str:
    return (
        "Senior Data Engineer, remote. Lead lakehouse work with Spark, Kafka, dbt, "
        "and Snowflake on GCP. Set data contracts and mentor engineers. Deep SQL and "
        "Python. No dashboard-only scope."
    )


def _da_junior_blr() -> str:
    return (
        "Junior Data Analyst, Bengaluru. Write SQL and Excel analyses, publish Tableau "
        "dashboards, and support weekly business reviews. Python pandas is a plus. "
        "No requirement for Spark or Kubernetes."
    )


def _ds_mid_remote() -> str:
    return (
        "Remote Data Scientist. Python, scikit-learn, SQL, and experiment analysis. "
        "Ship batch scores and notebooks. Light AWS. Deep learning is optional."
    )


def _mle_mid_blr() -> str:
    return (
        "Machine Learning Engineer, Bengaluru. Train PyTorch models, package them with "
        "Docker, and serve via FastAPI on AWS. SQL for features. MLOps basics expected."
    )


def _be_mid_hyd() -> str:
    return (
        "Backend Engineer, Hyderabad. Design Python FastAPI services, PostgreSQL schemas, "
        "and Docker deployments. Testing and code review required. Not a data science role."
    )


def _be_senior_go() -> str:
    return (
        "Senior Backend Engineer. Must have production Go and Java microservices, gRPC, "
        "and Kubernetes. Python is not the primary stack. Hyderabad office."
    )


def _de_lead() -> str:
    return (
        "Lead Data Engineer. Set platform strategy for Spark, Kafka, and Iceberg. "
        "Manage a team, budget, and multi-year roadmap. Hands-on coding is secondary."
    )


def _da_intern() -> str:
    return (
        "Data Analyst intern. Learn SQL, Excel, and Tableau beside a mentor. "
        "No production pipeline ownership. Bengaluru, summer internship."
    )


def _analytics_mid() -> str:
    return (
        "Analytics Engineer, Pune. Model warehouse tables with dbt and SQL, publish "
        "Looker explores, and partner with data engineers. Python optional. No PyTorch."
    )


def _bi_dev() -> str:
    return (
        "BI Developer. Power BI, SQL, and dimensional models for finance dashboards. "
        "Excel power-user. Cloud warehouses nice to have."
    )


def _nlp_research() -> str:
    return (
        "NLP Research Scientist, remote. Publishable work on transformers, evaluation "
        "datasets, and error analysis. PyTorch and Hugging Face required. Production "
        "ETL is out of scope."
    )


def _mlops() -> str:
    return (
        "MLOps Engineer, Bengaluru. CI/CD for training, model registry, feature store "
        "ops, and AWS GPU jobs. Python and Docker. Close partner to ML engineers."
    )


def _de_intern() -> str:
    return (
        "Data Engineer intern. Shadow Airflow and SQL jobs. Educational role, not "
        "on-call ownership. Bengaluru."
    )


def _clinical_bait() -> str:
    return (
        "Clinical Data Coordinator for hospital admissions. Maintain patient spreadsheets, "
        "schedule labs, and update the EHR. Some notes mention python sql report exports "
        "from a vendor tool. Night shifts. Not a software engineering role."
    )


def _nurse() -> str:
    return (
        "Registered Nurse, inpatient ward. Patient care, medication rounds, and handover. "
        "No programming requirements."
    )


def _sales() -> str:
    return (
        "Account Executive selling B2B SaaS. Quota, demos, and CRM hygiene. "
        "No SQL or Python required."
    )


def _pm() -> str:
    return (
        "Product Manager for a consumer app. Roadmaps, user interviews, and OKRs. "
        "Technical PM experience helpful but not a coding role."
    )


def _ds_senior_nlp() -> str:
    return (
        "Senior Data Scientist, speech and NLP. Transformers, evaluation, and mentoring. "
        "Python, PyTorch, SQL. Remote. Platform Spark work is limited."
    )


def _de_junior() -> str:
    return (
        "Junior Data Engineer, Bengaluru. Maintain Python and SQL jobs, learn Airflow, "
        "and fix AWS S3 path issues. Close mentoring. Spark is taught on the job."
    )


def _da_mid_pune() -> str:
    return (
        "Data Analyst, Pune. SQL, Tableau, and stakeholder reporting. Some Python. "
        "No Kafka or Kubernetes."
    )


def _platform_k8s() -> str:
    return (
        "Platform Engineer. Kubernetes, Terraform, and service mesh. On-call for "
        "cluster upgrades. Python glue scripts only. Hyderabad."
    )


def _analytics_senior() -> str:
    return (
        "Senior Analytics Engineer, remote. Own dbt packages, Looker governance, and "
        "semantic-layer design. SQL expert. Mentors analysts."
    )


def _mle_senior() -> str:
    return (
        "Senior Machine Learning Engineer, Bengaluru. Lead PyTorch training, ranking "
        "models, and online inference. AWS and strong software practices."
    )


def _de_mumbai() -> str:
    return (
        "Data Engineer, Mumbai hybrid. Spark, Airflow, Python, SQL, and AWS. "
        "Similar stack to Bengaluru DE roles but different city."
    )


def _be_senior_python() -> str:
    return (
        "Senior Backend Engineer, Hyderabad. Python, FastAPI, PostgreSQL, and system "
        "design. Owns high-traffic APIs. Mentors mid engineers."
    )


def _quant() -> str:
    return (
        "Quantitative Analyst. Time-series models, Python, and SQL for a trading desk. "
        "Statistics heavy. Not a warehouse engineering role."
    )


def _devops() -> str:
    return (
        "DevOps Engineer. AWS, Terraform, CI, and Linux. No data modeling and no ML."
    )


def _marketing_intern() -> str:
    return (
        "Marketing Data Intern, posted yesterday. Pull campaign CSVs, update Google "
        "Sheets, and write python sql snippets for UTM cleanup. Not a data platform role."
    )


def _ds_junior() -> str:
    return (
        "Junior Data Scientist, remote. SQL, Python, and scikit-learn with a mentor. "
        "No production MLOps ownership."
    )


def _fullstack() -> str:
    return (
        "Full Stack Engineer. React, Node, and CSS. Some PostgreSQL. Not a data role."
    )


def _de_stale() -> str:
    return (
        "Data Engineer, Bengaluru. Python, SQL, Spark, Airflow, and AWS. Strong mid-level "
        "match on paper but the posting is six months old."
    )

