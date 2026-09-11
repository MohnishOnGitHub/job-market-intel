from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.repositories.skills import SkillRepository, get_skill_repository
from app.schemas.skill import SkillItem, SkillListResponse
from app.services.taxonomy import load_skill_taxonomy

router = APIRouter()


@router.get(
    "/skills",
    response_model=SkillListResponse,
    summary="Canonical skill taxonomy",
    tags=["skills"],
)
def list_skills(repo: SkillRepository = Depends(get_skill_repository)) -> SkillListResponse:
    try:
        rows = repo.list_taxonomy()
        if rows:
            return SkillListResponse(skills=[SkillItem(**row) for row in rows])
    except Exception:
        pass
    taxonomy = load_skill_taxonomy()
    return SkillListResponse(
        skills=[
            SkillItem(skill=skill.canonical_name, category=skill.category)
            for skill in taxonomy.skills
        ]
    )
