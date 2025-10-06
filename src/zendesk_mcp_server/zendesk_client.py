from typing import Dict, Any, List

from zenpy import Zenpy
from zenpy.lib.api_objects import Comment


class ZendeskClient:
    def __init__(self, subdomain: str, oauth_token: str):
        """
        Initialize the Zendesk client using zenpy lib.
        """
        self.client = Zenpy(
            subdomain=subdomain,
            oauth_token=oauth_token,
        )

    def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """
        Query a ticket by its ID
        """
        try:
            ticket = self.client.tickets(id=ticket_id)
            return {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status,
                'priority': ticket.priority,
                'created_at': str(ticket.created_at),
                'updated_at': str(ticket.updated_at),
                'requester_id': ticket.requester_id,
                'assignee_id': ticket.assignee_id,
                'organization_id': ticket.organization_id
            }
        except Exception as e:
            raise Exception(f"Failed to get ticket {ticket_id}: {str(e)}")

    def get_ticket_comments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """
        Get all comments for a specific ticket.
        """
        try:
            comments = self.client.tickets.comments(ticket=ticket_id)
            return [{
                'id': comment.id,
                'author_id': comment.author_id,
                'body': comment.body,
                'html_body': comment.html_body,
                'public': comment.public,
                'created_at': str(comment.created_at)
            } for comment in comments]
        except Exception as e:
            raise Exception(f"Failed to get comments for ticket {ticket_id}: {str(e)}")

    def post_comment(self, ticket_id: int, comment: str, public: bool = True) -> str:
        """
        Post a comment to an existing ticket.
        """
        try:
            ticket = self.client.tickets(id=ticket_id)
            ticket.comment = Comment(
                html_body=comment,
                public=public
            )
            self.client.tickets.update(ticket)
            return comment
        except Exception as e:
            raise Exception(f"Failed to post comment on ticket {ticket_id}: {str(e)}")

    def get_recent_tickets(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Get recent tickets, sorted by created_at descending.
        """
        try:
            tickets = list(self.client.tickets(sort_by='created_at', sort_order='desc'))
            # Limit results
            tickets = tickets[:limit]
            
            return [{
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status,
                'priority': ticket.priority,
                'created_at': str(ticket.created_at),
                'updated_at': str(ticket.updated_at),
                'requester_id': ticket.requester_id,
                'assignee_id': ticket.assignee_id
            } for ticket in tickets]
        except Exception as e:
            raise Exception(f"Failed to get recent tickets: {str(e)}")

    def search_tickets(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Search tickets using Zendesk search API.
        Query can include status, assignee, tags, etc.
        Example: "status:open assignee:me" or "type:ticket urgent"
        """
        try:
            # Ensure we're searching tickets
            if 'type:ticket' not in query:
                query = f"type:ticket {query}"
            
            results = self.client.search(query)
            tickets = list(results)[:limit]
            
            return [{
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status,
                'priority': ticket.priority,
                'created_at': str(ticket.created_at),
                'updated_at': str(ticket.updated_at),
                'requester_id': ticket.requester_id,
                'assignee_id': ticket.assignee_id
            } for ticket in tickets]
        except Exception as e:
            raise Exception(f"Failed to search tickets: {str(e)}")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information by user ID.
        """
        try:
            user = self.client.users(id=user_id)
            return {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role,
                'created_at': str(user.created_at),
                'updated_at': str(user.updated_at),
                'organization_id': user.organization_id,
                'phone': user.phone,
                'time_zone': user.time_zone
            }
        except Exception as e:
            raise Exception(f"Failed to get user {user_id}: {str(e)}")

    def get_all_articles(self) -> Dict[str, Any]:
        """
        Fetch help center articles as knowledge base.
        Returns a Dict of section -> [article].
        """
        try:
            # Get all sections
            sections = self.client.help_center.sections()

            # Get articles for each section
            kb = {}
            for section in sections:
                articles = self.client.help_center.sections.articles(section.id)
                kb[section.name] = {
                    'section_id': section.id,
                    'description': section.description,
                    'articles': [{
                        'id': article.id,
                        'title': article.title,
                        'body': article.body,
                        'updated_at': str(article.updated_at),
                        'url': article.html_url
                    } for article in articles]
                }

            return kb
        except Exception as e:
            raise Exception(f"Failed to fetch knowledge base: {str(e)}")
