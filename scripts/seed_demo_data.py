"""Seeds the marketplace with one sample agent per connector type so a
fresh install has something to browse and rent immediately, covering every
task category the PDF spec calls out. Idempotent — re-running it skips any
slug that already exists, so it's safe after a database reset.

Usage:
    cd agenton && source .venv/bin/activate && python scripts/seed_demo_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.common.enums import PricingUnit
from app.db import engine, init_db
from app.marketplace.models import AgentTemplate

SAMPLE_AGENTS = [
    {
        "slug": "web-visitor-bot",
        "name": "Web Visitor Bot",
        "category": "growth",
        "task_type": "webvisit",
        "short_description": "Visits a URL for quest/referral tracking links.",
        "long_description": (
            "Give it any URL and it fetches it with a real HTTP request, following "
            "redirects — useful for referral link warm-up, quest platforms, and "
            "traffic-based promotions. No account connection needed."
        ),
        "capabilities": ["Visit any URL", "Follows redirects", "Works instantly, no setup"],
        "base_price_cents": 20,
        "pricing_unit": PricingUnit.TOKEN,
    },
    {
        "slug": "ai-content-writer",
        "name": "AI Content Writer",
        "category": "content",
        "task_type": "ai_content_generation",
        "short_description": "Generates text content (captions, posts, articles) on demand.",
        "long_description": (
            "Give it a brief and it writes the content for you — great for social "
            "captions, product descriptions, or blog drafts. Requires the operator to "
            "have the Claude CLI installed and signed in on the server (see the "
            "README FAQ)."
        ),
        "capabilities": ["Text generation from any brief", "Powered by Claude"],
        "base_price_cents": 200,
        "pricing_unit": PricingUnit.TOKEN,
    },
    {
        "slug": "x-auto-follow",
        "name": "X Auto-Follow",
        "category": "social",
        "task_type": "twitter_follow",
        "short_description": "Follows a target X (Twitter) account on your behalf.",
        "long_description": (
            "Connect your X account once under Connected Accounts, then rent this "
            "agent to follow target accounts for growth campaigns. Every follow is "
            "independently re-verified against X's own following list before it's "
            "marked done."
        ),
        "capabilities": ["Follow any public account", "Independently verified", "Uses your own X login"],
        "base_price_cents": 500,
        "pricing_unit": PricingUnit.PACKAGE,
    },
    {
        "slug": "x-auto-like",
        "name": "X Auto-Like",
        "category": "social",
        "task_type": "twitter_like",
        "short_description": "Likes a target post on X (Twitter) on your behalf.",
        "long_description": "Connect your X account once, then rent this agent to like specific posts for engagement campaigns.",
        "capabilities": ["Like any public post", "Uses your own X login"],
        "base_price_cents": 10,
        "pricing_unit": PricingUnit.TOKEN,
    },
    {
        "slug": "x-auto-retweet",
        "name": "X Auto-Retweet",
        "category": "social",
        "task_type": "twitter_retweet",
        "short_description": "Retweets a target post on X (Twitter) on your behalf.",
        "long_description": "Connect your X account once, then rent this agent to retweet specific posts to amplify reach.",
        "capabilities": ["Retweet any public post", "Uses your own X login"],
        "base_price_cents": 10,
        "pricing_unit": PricingUnit.TOKEN,
    },
    {
        "slug": "x-auto-post",
        "name": "X Auto-Post",
        "category": "social",
        "task_type": "twitter_post",
        "short_description": "Publishes a tweet on X (Twitter) on your behalf.",
        "long_description": "Connect your X account once, then rent this agent by the hour to publish content directly to your timeline.",
        "capabilities": ["Post text tweets", "Uses your own X login"],
        "base_price_cents": 300,
        "pricing_unit": PricingUnit.HOUR,
    },
    {
        "slug": "discord-community-joiner",
        "name": "Discord Community Joiner",
        "category": "web3",
        "task_type": "discord_join",
        "short_description": "Joins a Discord server on your behalf.",
        "long_description": (
            "Connect your Discord account once, then rent this agent to auto-join "
            "target community servers — common for Web3 quest and whitelist campaigns."
        ),
        "capabilities": ["Join any invite-based server", "Uses your own Discord login"],
        "base_price_cents": 15,
        "pricing_unit": PricingUnit.TOKEN,
    },
    {
        "slug": "platform-signup-bot",
        "name": "Platform Signup Bot",
        "category": "web3",
        "task_type": "platform_register",
        "short_description": "Registers your info on a target platform's signup endpoint.",
        "long_description": (
            "Give it a signup endpoint and payload and it submits it for you — "
            "useful for waitlists, referral programs, and quest platforms that "
            "expose a plain HTTP signup API."
        ),
        "capabilities": ["Submit any JSON signup form", "Works instantly, no setup"],
        "base_price_cents": 15,
        "pricing_unit": PricingUnit.TOKEN,
    },
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        for data in SAMPLE_AGENTS:
            existing = session.exec(select(AgentTemplate).where(AgentTemplate.slug == data["slug"])).first()
            if existing:
                print(f"skip (already exists): {data['slug']}")
                continue
            session.add(AgentTemplate(**data))
            print(f"created: {data['slug']}")
        session.commit()


if __name__ == "__main__":
    seed()
