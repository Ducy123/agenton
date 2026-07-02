from sqlmodel import Session, or_, select

from app.common.errors import ConflictError, NotFoundError
from app.common.pagination import paginate
from app.engine.connectors.registry import is_registered
from app.marketplace.models import AgentTemplate
from app.marketplace.schemas import AgentTemplateCreate


def create_template(session: Session, data: AgentTemplateCreate) -> AgentTemplate:
    if not is_registered(data.task_type):
        raise ConflictError(f"Unknown task_type '{data.task_type}' — register a connector first")

    existing = session.exec(select(AgentTemplate).where(AgentTemplate.slug == data.slug)).first()
    if existing:
        raise ConflictError(f"An agent template with slug '{data.slug}' already exists")

    template = AgentTemplate(**data.model_dump())
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def list_templates(
    session: Session,
    category: str | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AgentTemplate], int]:
    stmt = select(AgentTemplate).where(AgentTemplate.is_active.is_(True))
    if category:
        stmt = stmt.where(AgentTemplate.category == category)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(or_(AgentTemplate.name.ilike(like), AgentTemplate.short_description.ilike(like)))

    all_matches = session.exec(stmt).all()
    total = len(all_matches)
    limit, offset = paginate(total, page, page_size)
    return all_matches[offset : offset + limit], total


def get_template(session: Session, template_id: str) -> AgentTemplate:
    template = session.get(AgentTemplate, template_id)
    if not template or not template.is_active:
        raise NotFoundError(f"Agent template '{template_id}' not found")
    return template


def get_template_by_slug(session: Session, slug: str) -> AgentTemplate:
    template = session.exec(select(AgentTemplate).where(AgentTemplate.slug == slug)).first()
    if not template or not template.is_active:
        raise NotFoundError(f"Agent template '{slug}' not found")
    return template


def list_categories(session: Session) -> list[str]:
    rows = session.exec(select(AgentTemplate.category).where(AgentTemplate.is_active.is_(True))).all()
    return sorted(set(rows))
