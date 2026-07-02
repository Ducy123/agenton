from app.common.enums import InstanceStatus

# Created -> Running -> Paused (optional) -> Stopped -> Expired -> Released/Deleted
# (matches the lifecycle diagram in the AgentOn spec)
_ALLOWED_TRANSITIONS: dict[InstanceStatus, set[InstanceStatus]] = {
    InstanceStatus.CREATED: {InstanceStatus.RUNNING, InstanceStatus.RELEASED},
    InstanceStatus.RUNNING: {InstanceStatus.PAUSED, InstanceStatus.STOPPED, InstanceStatus.EXPIRED},
    InstanceStatus.PAUSED: {InstanceStatus.RUNNING, InstanceStatus.STOPPED, InstanceStatus.EXPIRED},
    InstanceStatus.STOPPED: {InstanceStatus.RELEASED},
    InstanceStatus.EXPIRED: {InstanceStatus.RELEASED},
    InstanceStatus.RELEASED: set(),
}


class InvalidTransitionError(ValueError):
    pass


def assert_transition_allowed(current: InstanceStatus, target: InstanceStatus) -> None:
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(f"Cannot move an instance from '{current.value}' to '{target.value}'")
