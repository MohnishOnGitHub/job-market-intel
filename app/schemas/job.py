from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class JobSkill(BaseModel):
    name: str
    category: Optional[str] = None


class Job(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = ""
    persisted_skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    posted_at: Optional[datetime] = None


class JobListItem(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobListItem]


class JobDetail(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = ""
    source: Optional[str] = None
    source_url: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    posted_at: Optional[datetime] = None
    skills: List[JobSkill] = []
