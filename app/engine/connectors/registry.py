from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.connectors.base import TaskConnector

_REGISTRY: dict[str, "TaskConnector"] = {}
_bootstrapped = False


def register(connector: "TaskConnector") -> None:
    _REGISTRY[connector.task_type] = connector


def _ensure_bootstrapped() -> None:
    # Deferred import breaks the registry <-> connectors import cycle: this
    # module must have no top-level dependency on any connector module.
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True
    from app.engine.connectors import bootstrap

    bootstrap.register_all()


def is_registered(task_type: str) -> bool:
    _ensure_bootstrapped()
    return task_type in _REGISTRY


def get_connector(task_type: str) -> "TaskConnector":
    _ensure_bootstrapped()
    if task_type not in _REGISTRY:
        raise KeyError(f"No connector registered for task_type '{task_type}'")
    return _REGISTRY[task_type]


def all_task_types() -> list[str]:
    _ensure_bootstrapped()
    return sorted(_REGISTRY.keys())
