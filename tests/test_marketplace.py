def _publish(client, headers, slug="agent-1", task_type="webvisit"):
    return client.post(
        "/marketplace/agents",
        headers=headers,
        json={
            "slug": slug,
            "name": "Test Agent",
            "category": "web3",
            "task_type": task_type,
            "short_description": "does a thing",
            "base_price_cents": 100,
            "pricing_unit": "token",
        },
    )


def test_publish_and_browse_agent(client, register_and_login):
    headers = register_and_login()
    resp = _publish(client, headers)
    assert resp.status_code == 201

    browse = client.get("/marketplace/agents")
    assert browse.status_code == 200
    body = browse.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "agent-1"


def test_publish_rejects_unknown_task_type(client, register_and_login):
    headers = register_and_login()
    resp = _publish(client, headers, task_type="not_a_real_connector")
    assert resp.status_code == 409


def test_publish_rejects_duplicate_slug(client, register_and_login):
    headers = register_and_login()
    _publish(client, headers, slug="dup-slug")
    resp = _publish(client, headers, slug="dup-slug")
    assert resp.status_code == 409


def test_get_agent_detail(client, register_and_login):
    headers = register_and_login()
    created = _publish(client, headers).json()
    resp = client.get(f"/marketplace/agents/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Agent"


def test_get_agent_detail_not_found(client):
    resp = client.get("/marketplace/agents/does-not-exist")
    assert resp.status_code == 404


def test_search_by_query(client, register_and_login):
    headers = register_and_login()
    _publish(client, headers, slug="findme")
    resp = client.get("/marketplace/agents", params={"q": "Test Agent"})
    assert resp.json()["total"] == 1

    resp_miss = client.get("/marketplace/agents", params={"q": "nonexistent-xyz"})
    assert resp_miss.json()["total"] == 0
