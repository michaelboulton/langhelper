"""Login through an OIDC provider (Pocket ID), only on a fly.dev hostname.

Authlib runs the authorization code flow with PKCE (RFC 7636). The client in
the provider is a public client, so there is no client secret: the PKCE code
verifier proves that the token request comes from the app that started the
login. Authlib checks the state, the nonce and the ID token signature.

GET /auth/login     start the flow, redirect to the provider
GET /auth/callback  the provider comes back here, store the user in the session
GET /auth/logout    drop the session

The session is the signed cookie of Starlette's SessionMiddleware (app.py).

A request whose Host does not end in AUTH_HOST_SUFFIX (localhost, a compose
run) never sees a login. On a fly.dev hostname a missing OIDC_CLIENT_ID or
SESSION_SECRET closes the app with a 503: it never falls back to public.
"""

import os
from urllib.parse import quote

import httpx2
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from joserfc.errors import JoseError

from .flashcards import store

OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "").rstrip("/")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
# Signs the session cookie. `openssl rand -base64 32`, as a Fly secret.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", str(7 * 24 * 3600)))
AUTH_HOST_SUFFIX = os.environ.get("AUTH_HOST_SUFFIX", ".fly.dev")

# /healthz stays open for the Fly check, which has no session. Chrome fetches
# the manifest and its icons with no cookie (README.md, "Install on Android").
OPEN_PATHS = {
    "/healthz",
    "/auth/login",
    "/auth/callback",
    "/auth/logout",
    "/static/manifest.json",
    "/static/icon.svg",
    "/static/icon-maskable.svg",
    "/static/icon-192.png",
    "/static/icon-512.png",
    "/static/icon-maskable-512.png",
}

router = APIRouter(prefix="/auth", include_in_schema=False)

oauth = OAuth()
oauth.register(
    "pocket_id",
    client_id=OIDC_CLIENT_ID,
    server_metadata_url=f"{OIDC_ISSUER}/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid profile",
        "code_challenge_method": "S256",
        # A public client sends no secret with the token request.
        "token_endpoint_auth_method": "none",
        # Pocket ID stops when idle too, so a call can wait for its cold start.
        "timeout": 15,
    },
)


def needs_auth(request: Request) -> bool:
    host = (request.url.hostname or "").lower()
    return bool(AUTH_HOST_SUFFIX) and host.endswith(AUTH_HOST_SUFFIX)


def configured() -> bool:
    return bool(OIDC_ISSUER and OIDC_CLIENT_ID and SESSION_SECRET)


def safe_next(target: str | None) -> str:
    """Only a path on this site, so the login cannot redirect to another one."""
    if not target or not target.startswith("/") or target.startswith(("//", "/\\")):
        return "/"
    return target


def gate(request: Request):
    """The response that stops this request, or None to let it through.

    Sets request.state.user for the access log.
    """
    request.state.user = "-"
    if not needs_auth(request) or request.url.path in OPEN_PATHS:
        return None
    if not configured():
        return PlainTextResponse(
            "The login is not configured: set OIDC_ISSUER, OIDC_CLIENT_ID and"
            " SESSION_SECRET.",
            status_code=503,
        )
    user = request.session.get("user")
    if user:
        request.state.user = user.get("name") or user.get("sub") or "?"
        return None
    if request.method == "GET" and not request.url.path.startswith("/api/"):
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        return RedirectResponse(f"/auth/login?next={quote(target, safe='')}", 302)
    # The page shows `detail` next to the status code.
    return JSONResponse(
        {"detail": "The login expired. Load the page again."}, status_code=401
    )


@router.get("/login")
async def login(request: Request, next: str = "/"):
    if not needs_auth(request):
        return RedirectResponse("/", 302)
    if not configured():
        return PlainTextResponse("The login is not configured.", status_code=503)
    request.session["next"] = safe_next(next)
    # Only fly.dev hostnames get here, and the Fly proxy forces https. Behind
    # the proxy the app sees plain http, so request.url_for would say http://.
    redirect_uri = f"https://{request.url.netloc}/auth/callback"
    try:
        return await oauth.pocket_id.authorize_redirect(request, redirect_uri)
    except (OAuthError, httpx2.HTTPError) as exc:
        return PlainTextResponse(f"The provider is not reachable: {exc!r}", 502)


@router.get("/callback")
async def callback(request: Request):
    if not needs_auth(request):
        return RedirectResponse("/", 302)
    try:
        token = await oauth.pocket_id.authorize_access_token(request)
    except OAuthError as exc:
        return PlainTextResponse(
            f"The login failed: {exc.error} {exc.description or ''}".strip(),
            status_code=400,
        )
    except (JoseError, httpx2.HTTPError) as exc:
        return PlainTextResponse(f"The login failed: {exc!r}", status_code=502)
    claims = token.get("userinfo")
    if not claims or not claims.get("sub"):
        return PlainTextResponse(
            "The login failed: the provider sent no ID token.", status_code=502
        )
    request.session["user"] = {
        "sub": claims["sub"],
        "name": claims.get("preferred_username") or claims.get("name"),
        # A custom claim of Pocket ID. "admin" can see the cards of each user.
        "group": claims.get("pocketid_user_group"),
    }
    # The flashcard tables hold only the sub. An admin sees this name instead.
    store.save_user(
        claims["sub"], claims.get("name") or claims.get("preferred_username")
    )
    return RedirectResponse(safe_next(request.session.pop("next", "/")), 302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return PlainTextResponse("Logged out.")
