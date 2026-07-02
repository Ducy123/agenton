from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult


async def execute_with_verification(connector: TaskConnector, ctx: TaskContext) -> TaskResult:
    """Run a connector, then give it a chance to independently verify.

    Mirrors the javis-os self-improvement loop's "assume it failed, prove
    otherwise" pattern: a connector's own success response is never the
    final word for anything billable — `verify()` gets a separate look
    before the caller (instances.service) records the task as done and
    charges for it.
    """
    result = await connector.run(ctx)
    return await connector.verify(ctx, result)
