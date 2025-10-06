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
        return json.dumps(ticket, ensure_ascii=False, indent=2)

    @server.tool()
    @with_zendesk_client
    def get_ticket_comments(client: ZendeskClient, ticket_id: int) -> str:
        """Retrieve all comments for a Zendesk ticket by its ID"""
        comments = client.get_ticket_comments(ticket_id)
        return json.dumps(comments, ensure_ascii=False, indent=2)

    @server.tool()
    @with_zendesk_client
    def create_ticket_comment(client: ZendeskClient, ticket_id: int, comment: str, public: bool = True) -> str:
        """Create a new comment on an existing Zendesk ticket"""
        result = client.post_comment(ticket_id=ticket_id, comment=comment, public=public)
        return f"Comment created successfully: {result}"

    @server.tool()
    @with_zendesk_client
    def get_recent_tickets(client: ZendeskClient, limit: int = 25) -> str:
        """Get recent tickets sorted by creation date (newest first)"""
        tickets = client.get_recent_tickets(limit=limit)
        return json.dumps(tickets, ensure_ascii=False, indent=2)

    @server.tool()
    @with_zendesk_client
    def search_tickets(client: ZendeskClient, query: str, limit: int = 25) -> str:
        """Search tickets using Zendesk query syntax. Examples: 'status:open', 'status:pending assignee:me', 'priority:urgent'"""
        tickets = client.search_tickets(query=query, limit=limit)
        return json.dumps(tickets, ensure_ascii=False, indent=2)

    @server.tool()
    @with_zendesk_client
    def get_user(client: ZendeskClient, user_id: int) -> str:
        """Get user information by user ID (useful for looking up requesters and assignees)"""
        user = client.get_user(user_id=user_id)
        return json.dumps(user, ensure_ascii=False, indent=2)