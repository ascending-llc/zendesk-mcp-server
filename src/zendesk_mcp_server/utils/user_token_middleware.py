import json
import logging
import os
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from zendesk_mcp_server.utils.auth_context import set_auth_context

logger = logging.getLogger("zendesk_mcp_server.user_token_middleware")


class UserTokenMiddleware(BaseHTTPMiddleware):
    """Middleware to extract Zendesk user tokens/credentials from Authorization headers and verify JWT."""

    def __init__(
        self,
        app: Any,
        
    ) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> JSONResponse:
        logger.debug(
            f"UserTokenMiddleware.dispatch: ENTERED for request path='{request.url.path}', method='{request.method}'"
        )
        request_path = request.url.path
        logger.info(f"JWT Auth Middleware processing path: {request_path}")

        if request.url.path == "/health":
            return await call_next(request)

        if request.method == "POST" or request.method == "HEAD":
            auth_header = request.headers.get("authorization")
            # Log everything from the request
            logger.debug(
                f"UserTokenMiddleware: Full request - Method: {request.method}, URL: {request.url}"
            )
            logger.debug(
                f"UserTokenMiddleware: Request headers: {dict(request.headers)}"
            )
            try:
                body = await request.body()
                logger.debug(f"UserTokenMiddleware: Request body: {body!r}")
                request._body = body  # Reset body for downstream handlers

                # Check if this is an MCP protocol method that doesn't need auth
                if body:
                    try:
                        request_data = json.loads(body.decode())
                        method = request_data.get("method")
                        if method in [
                            "ping",
                            "tools/list",
                            "prompts/list",
                            "resources/list",
                        ]:
                            logger.debug(
                                f"UserTokenMiddleware: Allowing MCP protocol method '{method}' without auth"
                            )
                            response = await call_next(request)
                            logger.debug(
                                f"UserTokenMiddleware.dispatch: EXITED for MCP method '{method}'"
                            )
                            return response
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.debug(
                            f"UserTokenMiddleware: Could not parse request body as JSON: {e}"
                        )

            except Exception as e:
                logger.warning(f"UserTokenMiddleware: Failed to read request body: {e}")
            if not auth_header:
                logger.debug(
                    f"UserTokenMiddleware: Path='{request.url.path}', no auth header provided"
                )
                return JSONResponse(
                    content={
                        "error": "Unauthorized: Empty Authorization Header",
                        "code": 401,
                    },
                    status_code=401,
                )
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                if not token:
                    return JSONResponse(
                        {"error": "Unauthorized: Empty Bearer token"},
                        status_code=401,
                    )
    
                # JWT verification
                try:
                    
                    zendesk_subdomain = os.getenv("ZENDESK_SUBDOMAIN")
                    # Store in context var for this request
                    set_auth_context(token=token, subdomain=zendesk_subdomain)

                    # Also store in request.state for any non-async code that needs it
                    request.state.user_zendesk_token = token
                    request.state.user_zendesk_auth_type = "oauth"


                except Exception as e:
                    logger.warning(f"JWT verification failed: {e}")
                    return JSONResponse(
                        {"error": "Unauthorized: Invalid JWT token"},
                        status_code=401,
                    )
            elif auth_header:
                logger.warning(
                    f"Unsupported Authorization type for {request_path}: {auth_header.split(' ', 1)[0] if ' ' in auth_header else 'UnknownType'}"
                )
                return JSONResponse(
                    {
                        "error": "Unauthorized: Only 'Bearer <OAuthToken>' or 'Token <PAT>' types are supported."
                    },
                    status_code=401,
                )
            else:
                logger.debug(
                    f"No Authorization header provided for {request_path}. Will proceed with global/fallback server configuration if applicable."
                )
        response = await call_next(request)
        logger.debug(
            f"UserTokenMiddleware.dispatch: EXITED for request path='{request_path}'"
        )
        return response