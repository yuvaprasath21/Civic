def _register(client, email="ananya.sharma@example.com", password="SecurePass123"):
    return client.post(
        "/api/auth/register",
        json={"full_name": "Ananya Sharma", "email": email, "password": password},
    )


def test_register_creates_citizen_and_returns_tokens(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "CITIZEN"
    assert body["user"]["email"] == "ananya.sharma@example.com"
    assert "access_token" in body and "refresh_token" in body


def test_register_duplicate_email_rejected(client):
    _register(client)
    r = _register(client)
    assert r.status_code == 409
    assert r.json()["error_code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_weak_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Weak Pass", "email": "weak@example.com", "password": "abc"},
    )
    assert r.status_code == 422


def test_login_success(client):
    _register(client)
    r = client.post("/api/auth/login", json={"email": "ananya.sharma@example.com", "password": "SecurePass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_rejected(client):
    _register(client)
    r = client.post("/api/auth/login", json={"email": "ananya.sharma@example.com", "password": "wrongpass1"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user_same_error_as_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "INVALID_CREDENTIALS"


def test_me_requires_authentication(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json()["error_code"] == "MISSING_TOKEN"


def test_me_returns_current_user(client):
    tokens = _register(client).json()
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "ananya.sharma@example.com"


def test_refresh_issues_new_access_token(client):
    tokens = _register(client).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"] != tokens["access_token"]


def test_refresh_rejects_access_token(client):
    tokens = _register(client).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401
    assert r.json()["error_code"] == "INVALID_REFRESH_TOKEN"


def test_forgot_password_returns_dev_token_and_reset_works(client):
    _register(client)
    r = client.post("/api/auth/forgot-password", json={"email": "ananya.sharma@example.com"})
    assert r.status_code == 200
    token = r.json()["dev_reset_token"]
    assert token

    r = client.post("/api/auth/reset-password", json={"token": token, "new_password": "NewSecurePass456"})
    assert r.status_code == 200

    r = client.post("/api/auth/login", json={"email": "ananya.sharma@example.com", "password": "SecurePass123"})
    assert r.status_code == 401

    r = client.post("/api/auth/login", json={"email": "ananya.sharma@example.com", "password": "NewSecurePass456"})
    assert r.status_code == 200


def test_forgot_password_nonexistent_email_gives_generic_success(client):
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json().get("dev_reset_token") is None


def test_reset_token_cannot_be_reused(client):
    _register(client)
    token = client.post("/api/auth/forgot-password", json={"email": "ananya.sharma@example.com"}).json()[
        "dev_reset_token"
    ]
    client.post("/api/auth/reset-password", json={"token": token, "new_password": "FirstReset123"})

    r = client.post("/api/auth/reset-password", json={"token": token, "new_password": "SecondReset456"})
    assert r.status_code == 422
    assert r.json()["error_code"] == "INVALID_RESET_TOKEN"
