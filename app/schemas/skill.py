from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class SkillItem(BaseModel):
    skill: str
    category: str
    slug: Optional[str] = None


class SkillListResponse(BaseModel):
    skills: List[SkillItem]
