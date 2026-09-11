from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from app.evaluation import BINARY_RELEVANCE_THRESHOLD, DATASET_VERSION
from app.schemas.job import Job
from app.services.skill_extractor import extract_skills

VALID_LABELS = {0, 1, 2, 3}
VALID_SPLITS = {"validation", "test"}


class EvaluationDatasetError(ValueError):
    """The evaluation fixture is invalid."""


@dataclass(frozen=True)
class EvaluationResume:
    id: str
    text: str
    profile: str
    seniority: str
    split: str
    synthetic: bool = True
    preferred_location: Optional[str] = None
    preferred_experience: Optional[str] = None
    notes: str = ""


@dataclass(frozen=True)
class EvaluationJob:
    id: int
    title: str
    description: str
    company: Optional[str] = None
    location: Optional[str] = None
    experience_level: Optional[str] = None
    posted_at: Optional[datetime] = None
    skills: Optional[List[str]] = None
    role_family: Optional[str] = None
    notes: str = ""


@dataclass(frozen=True)
class RelevanceLabel:
    resume_id: str
    job_id: int
    relevance: int
    notes: str = ""
    labeler: str = "author-v1"
    split: Optional[str] = None


@dataclass
class EvaluationDataset:
    version: str
    resumes: List[EvaluationResume]
    jobs: List[EvaluationJob]
    labels: List[RelevanceLabel]
    binary_threshold: int = BINARY_RELEVANCE_THRESHOLD
    description: str = ""
    split_strategy: str = "profile-level"
    labeling_method: str = ""

    def resume_by_id(self) -> Dict[str, EvaluationResume]:
        return {item.id: item for item in self.resumes}

    def job_by_id(self) -> Dict[int, EvaluationJob]:
        return {item.id: item for item in self.jobs}

    def resumes_for_split(self, split: Optional[str]) -> List[EvaluationResume]:
        if split in (None, "", "all"):
            return list(self.resumes)
        if split not in VALID_SPLITS:
            raise EvaluationDatasetError(f"Unknown split: {split}")
        return [item for item in self.resumes if item.split == split]

    def labels_for_resume(self, resume_id: str) -> List[RelevanceLabel]:
        return [item for item in self.labels if item.resume_id == resume_id]

    def graded_relevance(self, resume_id: str) -> Dict[int, int]:
        return {item.job_id: item.relevance for item in self.labels_for_resume(resume_id)}

    def to_jobs(self) -> List[Job]:
        jobs: List[Job] = []
        for item in self.jobs:
            skills = item.skills
            if skills is None:
                skills = extract_skills(item.description) or None
            jobs.append(
                Job(
                    id=item.id,
                    title=item.title,
                    company=item.company,
                    location=item.location,
                    description=item.description,
                    persisted_skills=skills,
                    experience_level=item.experience_level,
                    posted_at=item.posted_at,
                )
            )
        return jobs


def load_evaluation_dataset(path: str | Path) -> EvaluationDataset:
    dataset_path = _resolve_dataset_path(path)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset = _dataset_from_payload(payload)
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: EvaluationDataset) -> None:
    resume_ids = [item.id for item in dataset.resumes]
    job_ids = [item.id for item in dataset.jobs]
    if not resume_ids:
        raise EvaluationDatasetError("Dataset has no resumes.")
    if not job_ids:
        raise EvaluationDatasetError("Dataset has no jobs.")
    if len(resume_ids) != len(set(resume_ids)):
        raise EvaluationDatasetError("Duplicate resume ids.")
    if len(job_ids) != len(set(job_ids)):
        raise EvaluationDatasetError("Duplicate job ids.")
    for resume in dataset.resumes:
        if resume.split not in VALID_SPLITS:
            raise EvaluationDatasetError(f"Resume {resume.id} has invalid split.")
        if not (resume.text or "").strip():
            raise EvaluationDatasetError(f"Resume {resume.id} has empty text.")
    pairs = []
    for label in dataset.labels:
        if label.relevance not in VALID_LABELS:
            raise EvaluationDatasetError(
                f"Invalid relevance {label.relevance} for {label.resume_id}/{label.job_id}."
            )
        if label.resume_id not in set(resume_ids):
            raise EvaluationDatasetError(f"Unknown resume_id: {label.resume_id}")
        if label.job_id not in set(job_ids):
            raise EvaluationDatasetError(f"Unknown job_id: {label.job_id}")
        pairs.append((label.resume_id, label.job_id))
    if len(pairs) != len(set(pairs)):
        raise EvaluationDatasetError("Duplicate resume/job judgments.")


def write_labels_csv(dataset: EvaluationDataset, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "resume_id",
                "job_id",
                "relevance_label",
                "notes",
                "labeler",
                "split",
            ],
        )
        writer.writeheader()
        resume_split = {item.id: item.split for item in dataset.resumes}
        for label in dataset.labels:
            writer.writerow(
                {
                    "resume_id": label.resume_id,
                    "job_id": label.job_id,
                    "relevance_label": label.relevance,
                    "notes": label.notes,
                    "labeler": label.labeler,
                    "split": label.split or resume_split.get(label.resume_id, ""),
                }
            )


def write_dataset_json(dataset: EvaluationDataset, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": dataset.version,
        "description": dataset.description,
        "split_strategy": dataset.split_strategy,
        "labeling_method": dataset.labeling_method,
        "binary_threshold": dataset.binary_threshold,
        "resumes": [
            {
                "id": item.id,
                "text": item.text,
                "profile": item.profile,
                "seniority": item.seniority,
                "split": item.split,
                "synthetic": item.synthetic,
                "preferred_location": item.preferred_location,
                "preferred_experience": item.preferred_experience,
                "notes": item.notes,
            }
            for item in dataset.resumes
        ],
        "jobs": [
            {
                "id": item.id,
                "title": item.title,
                "company": item.company,
                "location": item.location,
                "description": item.description,
                "experience_level": item.experience_level,
                "posted_at": item.posted_at.isoformat() if item.posted_at else None,
                "skills": item.skills,
                "role_family": item.role_family,
                "notes": item.notes,
            }
            for item in dataset.jobs
        ],
        "labels": [
            {
                "resume_id": item.resume_id,
                "job_id": item.job_id,
                "relevance_label": item.relevance,
                "notes": item.notes,
                "labeler": item.labeler,
            }
            for item in dataset.labels
        ],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation" / DATASET_VERSION / "dataset.json"


def _resolve_dataset_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "dataset.json"
    if not candidate.exists():
        raise EvaluationDatasetError(f"Evaluation dataset not found: {candidate}")
    return candidate


def _dataset_from_payload(payload: dict) -> EvaluationDataset:
    resumes = [
        EvaluationResume(
            id=item["id"],
            text=item["text"],
            profile=item.get("profile", ""),
            seniority=item.get("seniority", ""),
            split=item["split"],
            synthetic=bool(item.get("synthetic", True)),
            preferred_location=item.get("preferred_location"),
            preferred_experience=item.get("preferred_experience"),
            notes=item.get("notes", ""),
        )
        for item in payload.get("resumes", [])
    ]
    jobs = []
    for item in payload.get("jobs", []):
        posted = item.get("posted_at")
        posted_at = None
        if posted:
            posted_at = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
        jobs.append(
            EvaluationJob(
                id=int(item["id"]),
                title=item.get("title") or "",
                company=item.get("company"),
                location=item.get("location"),
                description=item.get("description") or "",
                experience_level=item.get("experience_level"),
                posted_at=posted_at,
                skills=item.get("skills"),
                role_family=item.get("role_family"),
                notes=item.get("notes", ""),
            )
        )
    labels = [
        RelevanceLabel(
            resume_id=item["resume_id"],
            job_id=int(item["job_id"]),
            relevance=int(item.get("relevance_label", item.get("relevance"))),
            notes=item.get("notes", ""),
            labeler=item.get("labeler", "author-v1"),
        )
        for item in payload.get("labels", [])
    ]
    return EvaluationDataset(
        version=payload.get("version", DATASET_VERSION),
        resumes=resumes,
        jobs=jobs,
        labels=labels,
        binary_threshold=int(payload.get("binary_threshold", BINARY_RELEVANCE_THRESHOLD)),
        description=payload.get("description", ""),
        split_strategy=payload.get("split_strategy", "profile-level"),
        labeling_method=payload.get("labeling_method", ""),
    )
