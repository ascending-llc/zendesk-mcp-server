
import inspect
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .auth_context import get_user_zendesk_client

F = TypeVar("F", bound=Callable[..., Any])


def with_zendesk_client(func: F) -> F:
    """Decorator that injects a ZendeskClient while hiding it from the MCP schema."""

    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())

    if not parameters:
        raise TypeError("with_zendesk_client requires the wrapped function to accept a client parameter")

    client_param = parameters[0]
    if client_param.name != "client":
        raise TypeError("with_zendesk_client expects the first parameter to be named 'client'")

    allowed_kinds = {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    }
    if client_param.kind not in allowed_kinds:
        raise TypeError("client parameter must be positional")

    stripped_signature = signature.replace(parameters=parameters[1:])

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = stripped_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        client = get_user_zendesk_client()
        return func(client, *bound.args, **bound.kwargs)

    wrapper.__signature__ = stripped_signature  # type: ignore[attr-defined]

    return cast(F, wrapper)