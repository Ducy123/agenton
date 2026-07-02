from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.instances import service
from app.instances.schemas import InstanceCreate, InstanceExecuteRequest, InstanceExecuteResponse, InstanceRead

router = APIRouter(prefix="/instances", tags=["instances"])


@router.post("", response_model=InstanceRead, status_code=201)
def create_instance(
    data: InstanceCreate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return service.create_instance_from_order(session, current_user.id, data.order_id, data.task_params)


@router.get("", response_model=list[InstanceRead])
def list_my_instances(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.list_instances(session, current_user.id)


@router.get("/{instance_id}", response_model=InstanceRead)
def get_instance(instance_id: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.get_instance(session, instance_id, current_user.id)


@router.post("/{instance_id}/start", response_model=InstanceRead)
def start_instance(instance_id: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.start_instance(session, instance_id, current_user.id)


@router.post("/{instance_id}/pause", response_model=InstanceRead)
def pause_instance(instance_id: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.pause_instance(session, instance_id, current_user.id)


@router.post("/{instance_id}/stop", response_model=InstanceRead)
def stop_instance(instance_id: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.stop_instance(session, instance_id, current_user.id)


@router.post("/{instance_id}/release", response_model=InstanceRead)
def release_instance(instance_id: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.release_instance(session, instance_id, current_user.id)


@router.post("/{instance_id}/execute", response_model=InstanceExecuteResponse)
async def execute_instance(
    instance_id: str,
    data: InstanceExecuteRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    result, instance = await service.execute_instance_task(session, instance_id, current_user.id, data.params_override)
    return InstanceExecuteResponse(
        success=result.success,
        message=result.message,
        data=result.data,
        instance_status=instance.status,
    )
