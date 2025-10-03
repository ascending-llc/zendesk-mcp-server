import json
import logging
from typing import Literal

from cachetools.func import ttl_cache
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware

from .utils.user_token_middleware import UserTokenMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("zendesk-mcp-server")
logger.info("Zendesk MCP server started")


load_dotenv()


class AuthenticatedFastMCP(FastMCP):
    """FastMCP server with OAuth middleware"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def http_app(
        self,
        path: str | None = None,
        middleware: list[Middleware] | None = None,
        transport: Literal["streamable-http", "sse", "http"] = "streamable-http",
        stateless_http: bool = False,
    ):
        """Override to add user token middleware"""
        
        # Create user token middleware
        user_token_mw = Middleware(
            UserTokenMiddleware
        )

        # Combine with any additional middleware
        final_middleware_list = [user_token_mw]
        if middleware:
            final_middleware_list.extend(middleware)
        
        # Call parent method with combined middleware
        app = super().http_app(
            path=path,
            middleware=final_middleware_list,
            transport=transport,
            stateless_http=stateless_http,
        )
        return app

# Initialize server with authentication
server = AuthenticatedFastMCP(
    "Zendesk Server"
)

# Register tools after the server is instantiated
from .tools.tickets import register_tools
register_tools(server)


# -------------------------------
# Prompts
# -------------------------------
@server.prompt
def analyze_ticket(ticket_id: int):
    """Analyze a Zendesk ticket and provide insights"""
    
    return f"""
    You are a helpful Zendesk support analyst. You've been asked to analyze ticket #{ticket_id}.

    Please fetch the ticket info and comments to analyze it and provide:
    1. A summary of the issue
    2. The current status and timeline
    3. Key points of interaction

    Remember to be professional and focus on actionable insights.
"""


@server.prompt
def draft_ticket_response(ticket_id: int):
    """Draft a professional response to a Zendesk ticket"""

    return f"""
    You are a helpful Zendesk support agent. You need to draft a response to ticket #{ticket_id}.

    Please fetch the ticket info, comments and knowledge base to draft a professional and helpful response that:
    1. Acknowledges the customer's concern
    2. Addresses the specific issues raised
    3. Provides clear next steps or ask for specific details need to proceed
    4. Maintains a friendly and professional tone
    5. Ask for confirmation before commenting on the ticket

    The response should be formatted well and ready to be posted as a comment.
    """


# -------------------------------
# Resources
# -------------------------------
from .utils.auth_context import get_user_zendesk_client  # Add this import at the top or before usage

@ttl_cache(ttl=3600)
def get_cached_kb():
    zendesk_client = get_user_zendesk_client()
    return zendesk_client.get_all_articles()


@server.resource("zendesk://knowledge-base", name="Zendesk Knowledge Base")
def read_knowledge_base() -> str:
    """Access Zendesk Help Center articles and sections"""
    kb_data = get_cached_kb()
    return json.dumps(
        {
            "knowledge_base": kb_data,
            "metadata": {
                "sections": len(kb_data),
                "total_articles": sum(len(section["articles"]) for section in kb_data.values()),
            },
        },
        indent=2,
    )


if __name__ == "__main__":
    server.run(
        transport="streamable-http",  # Use streamable HTTP transport
        host="0.0.0.0",
        port=8000
    )
