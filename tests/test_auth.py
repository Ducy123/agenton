def test_register_creates_user(client):
    resp = client.post("/auth/register", json={"email": "a@test.dev", "password": "password123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@test.dev"
    assert "hashed_password" not in body


def test_register_duplicate_email_conflicts(client):
    client.post("/auth/register", json={"email": "dup@test.dev", "password": "password123"})
    resp = client.post("/auth/register", json={"email": "dup@test.dev", "password": "password123"})
    assert resp.status_code == 409


def test_login_wrong_password_unauthorized(client):
    client.post("/auth/register", json={"email": "b@test.dev", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "b@test.dev", "password": "wrong-password"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, register_and_login):
    headers = register_and_login("c@test.dev")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "c@test.dev"
