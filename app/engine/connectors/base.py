from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class TaskContext(BaseModel):
    instance_id: str
    user_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class TaskConnector(ABC):
    """Executes one kind of rentable task.

    Subclasses are plain instances registered by task_type string in
    `registry.py` — there is no dynamic discovery magic, so adding a new
    task type is: write the connector, register it in `bootstrap.py`, done.
    """

    task_type: str

    @abstractmethod
    async def run(self, ctx: TaskContext) -> TaskResult: ...

    async def verify(self, ctx: TaskContext, result: TaskResult) -> TaskResult:
        """Independent check that the task actually completed.

        Default trusts the connector's own result. Override this for task
        types where completion can be checked from a separate source of
        truth (e.g. re-querying the Twitter API for the follow relationship)
        following the javis-os self-improvement "assume it failed, prove
        otherwise" verification pattern.
        """
        return result
