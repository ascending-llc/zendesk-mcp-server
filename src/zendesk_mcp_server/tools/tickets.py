import json
import logging

from zendesk_mcp_server.utils.decorators import with_zendesk_client
from zendesk_mcp_server.zendesk_client import ZendeskClient

logger = logging.getLogger(__name__)


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
    def get_recent_tickets(client: ZendeskClient, page: int = 1, per_page: int = 100) -> str:
        """Get recent tickets sorted by creation date (newest first), one page at a time (max 100 per page).
        Response has has_more and next_page: while has_more is true, call again with page=next_page
        until you have as many tickets as the task needs."""
        result = client.get_recent_tickets(page=page, per_page=per_page)
        logger.info("get_recent_tickets page=%s per_page=%s returned=%s has_more=%s",
                    page, per_page, len(result["tickets"]), result["has_more"])
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))

    @server.tool()
    @with_zendesk_client
    def search_tickets(client: ZendeskClient, query: str, page: int = 1, per_page: int = 100) -> str:
        """Search tickets using Zendesk query syntax, one page at a time (max 100 per page, newest first).
        Examples: 'status:open', 'status:pending assignee:me', 'priority:urgent',
        'created>=2026-10-26 created<2026-11-02' (date range, end exclusive).
        Response includes count (total matches), has_more and next_page. While has_more is true, call again
        with page=next_page until you have everything the task needs; do not report partial coverage as complete.
        Zendesk search can only page through the first 1000 matches. If count exceeds 1000 the response has a
        'warning': then use search_tickets_export, or split the query into smaller date ranges.
        Call count_tickets first to size the job."""
        result = client.search_tickets(query=query, page=page, per_page=per_page)
        logger.info("search_tickets query=%r page=%s per_page=%s count=%s returned=%s has_more=%s",
                    query[:200], page, per_page, result["count"], len(result["tickets"]), result["has_more"])
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))

    @server.tool()
    @with_zendesk_client
    def search_tickets_export(client: ZendeskClient, query: str, cursor: str | None = None, page_size: int = 500) -> str:
        """Search tickets with NO 1000-result cap, using cursor pagination (max 500 per call; order is not guaranteed).
        Use for result sets larger than 1000, or to read a whole date range reliably. Same query syntax as
        search_tickets. Start with cursor omitted; while has_more is true, call again with cursor=after_cursor
        until has_more is false. Returns compact ticket rows; use get_ticket_comments for full threads."""
        result = client.search_tickets_export(query=query, cursor=cursor, page_size=page_size)
        logger.info("search_tickets_export query=%r cursor=%s page_size=%s returned=%s has_more=%s",
                    query[:200], bool(cursor), page_size, len(result["tickets"]), result["has_more"])
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))

    @server.tool()
    @with_zendesk_client
    def count_tickets(client: ZendeskClient, query: str) -> str:
        """Count tickets matching a Zendesk query without fetching them (same syntax as search_tickets).
        Use this first for 'how many' questions and to size a summary job before paging through results.
        Counts are refreshed periodically by Zendesk (see refreshed_at), so they can lag by a few minutes."""
        result = client.count_tickets(query=query)
        logger.info("count_tickets query=%r count=%s", query[:200], result.get("count"))
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))

    @server.tool()
    @with_zendesk_client
    def get_user(client: ZendeskClient, user_id: int) -> str:
        """Get user information by user ID (useful for looking up requesters and assignees)"""
        user = client.get_user(user_id=user_id)
        return json.dumps(user, ensure_ascii=False, indent=2)