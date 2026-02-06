from contextvars import ContextVar
import os
from typing import TypedDict

from ..zendesk_client import ZendeskClient
from fastmcp.server.dependencies import get_http_headers

class ZendeskAuthContext(TypedDict):
    token: str
    subdomain: str

_current_ctx: ContextVar[ZendeskAuthContext] = ContextVar("zendesk_auth_ctx")

def _extract_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    if header_value.startswith("Bearer "):
        return header_value.split(" ", 1)[1].strip() or None
    if header_value.startswith("Token "):
        return header_value.split(" ", 1)[1].strip() or None
    return None

def set_auth_context(*, token: str, subdomain: str) -> None:
    _current_ctx.set({"token": token, "subdomain": subdomain})

def get_user_zendesk_client() -> ZendeskClient:
    try:
        ctx = _current_ctx.get()
    except LookupError as exc:
        # Fallback for cases where request context is available but the middleware
        # contextvar is not (e.g., streamable-http tool calls).
        headers = get_http_headers(include_all=True)
        auth_header = headers.get("authorization")
        token = _extract_token(auth_header)
        subdomain = os.getenv("ZENDESK_SUBDOMAIN")
        if token and subdomain:
            set_auth_context(token=token, subdomain=subdomain)
            ctx = _current_ctx.get()
        else:
            raise ValueError("Zendesk auth context missing") from exc

    return ZendeskClient(subdomain=ctx["subdomain"], oauth_token=ctx["token"])
