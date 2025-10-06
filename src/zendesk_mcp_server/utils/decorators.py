
import inspect
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .auth_context import get_user_zendesk_client

F = TypeVar("F", bound=Callable[..., Any])


def with_zendesk_client(func: F) -> F:
    """Decorator that injects a ZendeskClient while hiding it from the MCP schema."""

    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())

    stripped_signature = signature.replace(parameters=parameters[1:])

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = stripped_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        client = get_user_zendesk_client()
        return func(client, *bound.args, **bound.kwargs)

    wrapper.__signature__ = stripped_signature  # type: ignore[attr-defined]

    return cast(F, wrapper)