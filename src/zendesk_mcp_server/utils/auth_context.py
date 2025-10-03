from contextvars import ContextVar
from typing import TypedDict

from ..zendesk_client import ZendeskClient

class ZendeskAuthContext(TypedDict):
    token: str
    subdomain: str

_current_ctx: ContextVar[ZendeskAuthContext] = ContextVar("zendesk_auth_ctx")

def set_auth_context(*, token: str, subdomain: str) -> None:
    _current_ctx.set({"token": token, "subdomain": subdomain})

def get_user_zendesk_client() -> ZendeskClient:
    try:
        ctx = _current_ctx.get()
    except LookupError as exc:
        raise ValueError("Zendesk auth context missing") from exc

    return ZendeskClient(subdomain=ctx["subdomain"], oauth_token=ctx["token"])