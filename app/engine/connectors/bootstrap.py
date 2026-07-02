from app.engine.connectors import ai_content, discord, platform_register, twitter, webvisit
from app.engine.connectors.registry import register


def register_all() -> None:
    """Single place that wires task_type strings to connector instances.

    Called lazily by `registry._ensure_bootstrapped()` on first lookup — add
    a new connector by writing its module and adding one `register(...)`
    line here.
    """
    register(ai_content.connector)
    register(twitter.follow_connector)
    register(twitter.like_connector)
    register(twitter.retweet_connector)
    register(twitter.post_connector)
    register(discord.connector)
    register(webvisit.connector)
    register(platform_register.connector)
