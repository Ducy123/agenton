from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.common.pagination import Page
from app.db import get_session
from app.deps import get_current_user
from app.marketplace import service
from app.marketplace.schemas import AgentTemplateCreate, AgentTemplateRead, AgentTemplateSummary

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/categories", response_model=list[str])
def get_categories(session: Session = Depends(get_session)):
    return service.list_categories(session)


@router.get("/agents", response_model=Page[AgentTemplateSummary])
def browse_agents(
    category: str | None = None,
    q: str | None = Query(default=None, description="Free-text search over name/description"),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    items, total = service.list_templates(session, category=category, query=q, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/agents/{template_id}", response_model=AgentTemplateRead)
def get_agent_detail(template_id: str, session: Session = Depends(get_session)):
    return service.get_template(session, template_id)


@router.post("/agents", response_model=AgentTemplateRead, status_code=201)
def publish_agent(
    data: AgentTemplateCreate,
    session: Session = Depends(get_session),
    _current_user=Depends(get_current_user),
):
    # NOTE: any authenticated user can publish today; swap in a role check
    # (e.g. current_user.is_admin) once operator vs. renter roles exist.
    return service.create_template(session, data)
