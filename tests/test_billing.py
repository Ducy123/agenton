def _publish_template(client, headers, slug="billed-agent"):
    resp = client.post(
        "/marketplace/agents",
        headers=headers,
        json={
            "slug": slug,
            "name": "Billed Agent",
            "category": "growth",
            "task_type": "webvisit",
            "base_price_cents": 500,
            "pricing_unit": "hour",
        },
    )
    return resp.json()["id"]


def test_wallet_starts_at_zero(client, register_and_login):
    headers = register_and_login()
    resp = client.get("/billing/wallet", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["balance_cents"] == 0
    assert resp.json()["is_low_balance"] is True


def test_toggle_auto_renew(client, register_and_login):
    headers = register_and_login()
    resp = client.patch("/billing/wallet/settings", headers=headers, json={"auto_renew_enabled": True})
    assert resp.status_code == 200
    assert resp.json()["auto_renew_enabled"] is True

    resp = client.patch("/billing/wallet/settings", headers=headers, json={"auto_renew_enabled": False})
    assert resp.json()["auto_renew_enabled"] is False


def test_recharge_increases_balance(client, register_and_login):
    headers = register_and_login()
    resp = client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 1000})
    assert resp.status_code == 200
    assert resp.json()["kind"] == "recharge"

    wallet = client.get("/billing/wallet", headers=headers).json()
    assert wallet["balance_cents"] == 1000


def test_recharge_rejects_non_positive_amount(client, register_and_login):
    headers = register_and_login()
    resp = client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 0})
    assert resp.status_code == 409


def test_create_and_pay_order_debits_wallet(client, register_and_login):
    headers = register_and_login()
    template_id = _publish_template(client, headers)
    client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 5000})

    order = client.post("/billing/orders", headers=headers, json={"template_id": template_id, "quantity": 2}).json()
    assert order["amount_cents"] == 1000  # 500 cents/hour * 2

    paid = client.post(f"/billing/orders/{order['id']}/pay", headers=headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    wallet = client.get("/billing/wallet", headers=headers).json()
    assert wallet["balance_cents"] == 4000


def test_pay_order_with_insufficient_balance_fails(client, register_and_login):
    headers = register_and_login()
    template_id = _publish_template(client, headers)
    order = client.post("/billing/orders", headers=headers, json={"template_id": template_id, "quantity": 1}).json()

    resp = client.post(f"/billing/orders/{order['id']}/pay", headers=headers)
    assert resp.status_code == 402


def test_paying_twice_conflicts(client, register_and_login):
    headers = register_and_login()
    template_id = _publish_template(client, headers)
    client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 5000})
    order = client.post("/billing/orders", headers=headers, json={"template_id": template_id, "quantity": 1}).json()

    client.post(f"/billing/orders/{order['id']}/pay", headers=headers)
    second = client.post(f"/billing/orders/{order['id']}/pay", headers=headers)
    assert second.status_code == 409


def test_transactions_are_listed_newest_first(client, register_and_login):
    headers = register_and_login()
    client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 100})
    client.post("/billing/wallet/recharge", headers=headers, json={"amount_cents": 200})

    resp = client.get("/billing/transactions", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["amount_cents"] == 200
