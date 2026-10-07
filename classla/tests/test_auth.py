"""Tests for auth.py. Run with: uv run pytest

The provider is a fake. The client registers with fixed endpoints and a
symmetric test key in place of the discovery document, and the token endpoint
is a patched fetch_access_token. Authlib's own checks (state, PKCE, nonce and
the ID token signature) still run for real.
"""

import time
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey

from tlhelper import app as service
from tlhelper import auth
from tlhelper.flashcards import store

ISSUER = "https://id.example"
FLY = "https://boultonxyz-classla.fly.dev"
KEY = OctKey.import_key("0123456789abcdef0123456789abcdef", {"kid": "k1"})


@pytest.fixture(autouse=True)
def configuration(monkeypatch, tmp_path):
    # A login saves the name of the user.
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "flashcards.db")
    monkeypatch.setattr(auth, "OIDC_ISSUER", ISSUER)
    monkeypatch.setattr(auth, "OIDC_CLIENT_ID", "client-1")
    monkeypatch.setattr(auth, "SESSION_SECRET", "test-secret")
    auth.oauth._clients.pop("pocket_id", None)
    auth.oauth.register(
        "pocket_id",
        overwrite=True,
        client_id="client-1",
        authorize_url=f"{ISSUER}/authorize",
        access_token_url=f"{ISSUER}/api/oidc/token",
        issuer=ISSUER,
        jwks={"keys": [KEY.as_dict()]},
        id_token_signing_alg_values_supported=["HS256"],
        client_kwargs={
            "scope": "openid profile",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": "none",
        },
    )
    yield
    auth.oauth._clients.pop("pocket_id", None)


@pytest.fixture
def fly():
    # No `with`: the lifespan (and so the model warm-up) does not run.
    return TestClient(service.app, base_url=FLY, follow_redirects=False)


def start_login(client, next="/"):
    response = client.get("/auth/login", params={"next": next})
    assert response.status_code == 302, response.text
    location = response.headers["location"]
    assert location.startswith(f"{ISSUER}/authorize?")
    return parse_qs(urlparse(location).query)


def id_token(claims):
    return jose_jwt.encode({"alg": "HS256", "kid": "k1"}, claims, KEY)


def good_claims(nonce):
    now = int(time.time())
    return {
        "iss": ISSUER,
        "aud": "client-1",
        "sub": "user-1",
        "preferred_username": "michael",
        "name": "Michael B",
        "pocketid_user_group": "admin",
        "nonce": nonce,
        "iat": now,
        "exp": now + 60,
    }


def fake_token_endpoint(monkeypatch, claims):
    """Replace the network call to the token endpoint, and nothing else."""
    posted = {}

    async def fetch_access_token(**params):
        posted.update(params)
        return {
            "access_token": "at-1",
            "token_type": "bearer",
            "id_token": id_token(claims),
        }

    monkeypatch.setattr(auth.oauth.pocket_id, "fetch_access_token", fetch_access_token)
    return posted


def test_other_hosts_need_no_login(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DB_PATH", tmp_path / "lemmas.db")
    client = TestClient(service.app, follow_redirects=False)
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/lemmas").status_code == 200
    assert client.get("/auth/login").headers["location"] == "/"


def test_fly_host_redirects_the_page_and_refuses_the_api(fly):
    page = fly.get("/?x=1")
    assert page.status_code == 302
    assert page.headers["location"] == "/auth/login?next=%2F%3Fx%3D1"
    api = fly.post("/api/v1/classify", json={"text": "Bok"})
    assert api.status_code == 401
    assert "Load the page again" in api.json()["detail"]
    assert fly.get("/api/v1/lemmas").status_code == 401
    assert fly.get("/healthz").text == "ok"


def test_fly_host_serves_the_manifest_and_icons_with_no_login(fly):
    manifest = fly.get("/static/manifest.json")
    assert manifest.status_code == 200
    for icon in manifest.json()["icons"]:
        assert fly.get(icon["src"]).status_code == 200
    assert fly.get("/static/js/breakdown.js").status_code == 302


def test_fly_host_without_configuration_is_closed(fly, monkeypatch):
    monkeypatch.setattr(auth, "SESSION_SECRET", "")
    assert fly.get("/").status_code == 503
    assert fly.get("/api/v1/lemmas").status_code == 503
    assert fly.get("/healthz").status_code == 200


def test_login_sends_a_pkce_challenge(fly):
    query = start_login(fly)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["client-1"]
    assert query["redirect_uri"] == [f"{FLY}/auth/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"]
    assert query["nonce"]
    assert "openid" in query["scope"][0]


def test_full_login(fly, monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DB_PATH", tmp_path / "lemmas.db")
    query = start_login(fly, next="/?x=1")
    posted = fake_token_endpoint(monkeypatch, good_claims(query["nonce"][0]))

    response = fly.get(
        "/auth/callback", params={"code": "abc", "state": query["state"][0]}
    )
    assert response.status_code == 302, response.text
    assert response.headers["location"] == "/?x=1"
    assert posted["code"] == "abc"
    assert posted["code_verifier"]
    assert posted["redirect_uri"] == f"{FLY}/auth/callback"

    assert fly.get("/").status_code == 200
    assert fly.get("/api/v1/lemmas").status_code == 200
    # The group claim makes an admin, and the name claim is in the user list.
    users = fly.get("/api/v1/flashcards/users").json()
    assert (users["me"], users["admin"]) == ("user-1", True)
    assert store.users() == [{"id": "user-1", "name": "Michael B"}]

    assert fly.get("/auth/logout").status_code == 200
    assert fly.get("/").status_code == 302


def test_callback_refuses_a_wrong_state(fly, monkeypatch):
    query = start_login(fly)
    fake_token_endpoint(monkeypatch, good_claims(query["nonce"][0]))
    response = fly.get("/auth/callback", params={"code": "abc", "state": "other"})
    assert response.status_code == 400
    assert fly.get("/").status_code == 302


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "https://evil.example"},
        {"aud": "client-2"},
        {"nonce": "other"},
        {"iat": 1, "exp": 2},
    ],
)
def test_callback_refuses_a_bad_id_token(fly, monkeypatch, change):
    query = start_login(fly)
    claims = {**good_claims(query["nonce"][0]), **change}
    fake_token_endpoint(monkeypatch, claims)
    response = fly.get(
        "/auth/callback", params={"code": "abc", "state": query["state"][0]}
    )
    assert response.status_code == 502, response.text
    assert fly.get("/").status_code == 302


def test_callback_refuses_a_forged_signature(fly, monkeypatch):
    query = start_login(fly)
    claims = good_claims(query["nonce"][0])
    forged_key = OctKey.import_key("f" * 32, {"kid": "k1"})

    async def fetch_access_token(**params):
        return {
            "access_token": "at-1",
            "token_type": "bearer",
            "id_token": jose_jwt.encode(
                {"alg": "HS256", "kid": "k1"}, claims, forged_key
            ),
        }

    monkeypatch.setattr(auth.oauth.pocket_id, "fetch_access_token", fetch_access_token)
    response = fly.get(
        "/auth/callback", params={"code": "abc", "state": query["state"][0]}
    )
    assert response.status_code == 502
    assert fly.get("/").status_code == 302


def test_safe_next():
    assert auth.safe_next("/?x=1") == "/?x=1"
    assert auth.safe_next("//evil.example") == "/"
    assert auth.safe_next("https://evil.example") == "/"
    assert auth.safe_next(None) == "/"
