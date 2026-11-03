import logging
import time
from typing import Dict, Any, List, Optional

import requests
from zenpy import Zenpy
from zenpy.lib.api_objects import Comment

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100
MAX_EXPORT_PAGE_SIZE = 500
SEARCH_RESULT_CAP = 1000
MAX_RATE_LIMIT_RETRIES = 3


def _compact_ticket(ticket: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': ticket.get('id'),
        'subject': ticket.get('subject'),
        'status': ticket.get('status'),
        'priority': ticket.get('priority'),
        'created_at': ticket.get('created_at'),
        'updated_at': ticket.get('updated_at'),
        'requester_id': ticket.get('requester_id'),
        'assignee_id': ticket.get('assignee_id'),
        'tags': ticket.get('tags', []),
    }


def _ticket_query(query: str) -> str:
    query = query.strip()
    return query if 'type:ticket' in query else f"type:ticket {query}".strip()


class ZendeskClient:
    def __init__(self, subdomain: str, oauth_token: str):
        """
        Initialize the Zendesk client using zenpy lib.
        """
        self.subdomain = subdomain
        self.oauth_token = oauth_token
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

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"https://{self.subdomain}.zendesk.com{path}"
        headers = {"Authorization": f"Bearer {self.oauth_token}"}
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 429 and attempt < MAX_RATE_LIMIT_RETRIES:
                try:
                    delay = float(resp.headers.get("Retry-After", "2"))
                except ValueError:
                    delay = 2.0
                time.sleep(min(delay, 30))
                continue
            break
        if not resp.ok:
            raise Exception(f"Zendesk API {resp.status_code} for {path}: {resp.text[:300]}")
        return resp.json()

    def search_tickets(self, query: str, page: int = 1, per_page: int = MAX_PAGE_SIZE) -> Dict[str, Any]:
        """
        Search tickets using Zendesk query syntax, one page at a time (newest first).
        Zendesk only exposes the first 1000 matches of a search; use search_tickets_export beyond that.
        """
        page = max(1, page)
        per_page = max(1, min(per_page, MAX_PAGE_SIZE))
        if (page - 1) * per_page >= SEARCH_RESULT_CAP:
            raise Exception(
                f"Zendesk search cannot return results past the first {SEARCH_RESULT_CAP}. "
                "Use search_tickets_export to read larger result sets."
            )
        try:
            data = self._get("/api/v2/search.json", {
                "query": _ticket_query(query),
                "page": page,
                "per_page": per_page,
                "sort_by": "created_at",
                "sort_order": "desc",
            })
            count = data.get("count", 0)
            has_more = page * per_page < min(count, SEARCH_RESULT_CAP)
            result: Dict[str, Any] = {
                "tickets": [_compact_ticket(t) for t in data.get("results", [])],
                "count": count,
                "page": page,
                "per_page": per_page,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
            }
            if count > SEARCH_RESULT_CAP:
                result["warning"] = (
                    f"{count} tickets match but search can only page through the first {SEARCH_RESULT_CAP}. "
                    "To cover all of them, use search_tickets_export, or split the query into smaller "
                    "date ranges (e.g. created>=2026-10-26 created<2026-10-27)."
                )
            return result
        except Exception as e:
            raise Exception(f"Failed to search tickets: {str(e)}")

    def search_tickets_export(
        self, query: str, cursor: Optional[str] = None, page_size: int = MAX_EXPORT_PAGE_SIZE
    ) -> Dict[str, Any]:
        """
        Cursor-paginated ticket search with no 1000-result cap.
        """
        page_size = max(1, min(page_size, MAX_EXPORT_PAGE_SIZE))
        params: Dict[str, Any] = {
            "query": query.strip(),
            "filter[type]": "ticket",
            "page[size]": page_size,
        }
        if cursor:
            params["page[after]"] = cursor
        try:
            data = self._get("/api/v2/search/export.json", params)
            meta = data.get("meta", {})
            has_more = bool(meta.get("has_more"))
            return {
                "tickets": [_compact_ticket(t) for t in data.get("results", [])],
                "has_more": has_more,
                "after_cursor": meta.get("after_cursor") if has_more else None,
            }
        except Exception as e:
            raise Exception(f"Failed to export-search tickets: {str(e)}")

    def count_tickets(self, query: str) -> Dict[str, Any]:
        """
        Count tickets matching a query without fetching them.
        """
        try:
            data = self._get("/api/v2/search/count.json", {"query": _ticket_query(query)})
            count = data.get("count")
            if isinstance(count, dict):
                return {"count": count.get("value"), "refreshed_at": count.get("refreshed_at")}
            return {"count": count}
        except Exception as e:
            raise Exception(f"Failed to count tickets: {str(e)}")

    def get_recent_tickets(self, page: int = 1, per_page: int = MAX_PAGE_SIZE) -> Dict[str, Any]:
        """
        Get recent tickets sorted by created_at descending, one page at a time.
        """
        return self.search_tickets("", page=page, per_page=per_page)

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
