import json

from zendesk_mcp_server.utils.decorators import with_zendesk_client
from zendesk_mcp_server.zendesk_client import ZendeskClient


def register_tools(server):
    """Register all ticket-related tools with the server."""
    
    @server.tool()
    @with_zendesk_client
    def get_ticket(client: ZendeskClient, ticket_id: int) -> str:
        """Retrieve a Zendesk ticket by its ID"""
        ticket = client.get_ticket(ticket_id)
        return json.dumps(ticket)

    @server.tool()
    @with_zendesk_client
    def get_ticket_comments(client: ZendeskClient, ticket_id: int) -> str:
        """Retrieve all comments for a Zendesk ticket by its ID"""
        comments = client.get_ticket_comments(ticket_id)
        return json.dumps(comments)

    @server.tool()
    @with_zendesk_client
    def create_ticket_comment(client: ZendeskClient, ticket_id: int, comment: str, public: bool = True) -> str:
        """Create a new comment on an existing Zendesk ticket"""
        result = client.post_comment(ticket_id=ticket_id, comment=comment, public=public)
        return f"Comment created successfully: {result}"