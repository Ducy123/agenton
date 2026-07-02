import pytest

from app.engine.connectors.registry import all_task_types, get_connector, is_registered


def test_expected_task_types_are_registered():
    types = all_task_types()
    for expected in [
        "ai_content_generation",
        "twitter_follow",
        "twitter_like",
        "twitter_retweet",
        "twitter_post",
        "discord_join",
        "webvisit",
        "platform_register",
    ]:
        assert expected in types


def test_is_registered_false_for_unknown_type():
    assert is_registered("totally_made_up_task_type") is False


def test_get_connector_raises_for_unknown_type():
    with pytest.raises(KeyError):
        get_connector("totally_made_up_task_type")


def test_get_connector_returns_matching_task_type():
    connector = get_connector("webvisit")
    assert connector.task_type == "webvisit"


@pytest.mark.asyncio
async def test_webvisit_connector_missing_url_fails_cleanly():
    from app.engine.connectors.base import TaskContext
    from app.engine.connectors.webvisit import connector

    result = await connector.run(TaskContext(instance_id="i1", user_id="u1", params={}))
    assert result.success is False
    assert "url" in result.message
