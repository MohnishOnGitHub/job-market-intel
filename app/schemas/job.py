from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Job(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = ""


class JobListItem(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobListItem]
