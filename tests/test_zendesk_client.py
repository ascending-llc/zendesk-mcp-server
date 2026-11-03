from unittest.mock import MagicMock, patch

import pytest

from zendesk_mcp_server.zendesk_client import ZendeskClient


def _resp(payload, status=200, headers=None):
    r = MagicMock()
    r.status_code = status
    r.ok = status < 400
    r.json.return_value = payload
    r.text = str(payload)
    r.headers = headers or {}
    return r


def _tickets(n, start=1):
    return [{"id": i, "subject": f"t{i}", "status": "open", "tags": ["a"]} for i in range(start, start + n)]


@pytest.fixture
def client():
    with patch("zendesk_mcp_server.zendesk_client.Zenpy"):
        yield ZendeskClient(subdomain="acme", oauth_token="tok")


def test_search_first_page_reports_more(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get",
               return_value=_resp({"results": _tickets(100), "count": 250})) as get:
        out = client.search_tickets("status:open", page=1, per_page=100)
    params = get.call_args.kwargs["params"]
    assert params["query"] == "type:ticket status:open"
    assert params["page"] == 1 and params["per_page"] == 100
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer tok"
    assert out["count"] == 250 and out["has_more"] is True and out["next_page"] == 2
    assert len(out["tickets"]) == 100 and "warning" not in out


def test_search_last_page_has_no_more(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get",
               return_value=_resp({"results": _tickets(50, 201), "count": 250})):
        out = client.search_tickets("status:open", page=3, per_page=100)
    assert out["has_more"] is False and out["next_page"] is None


def test_search_over_cap_warns_and_stops_at_cap(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get",
               return_value=_resp({"results": _tickets(100), "count": 3000})):
        out = client.search_tickets("x", page=10, per_page=100)
    assert out["has_more"] is False
    assert "search_tickets_export" in out["warning"]


def test_search_page_past_cap_raises_helpful_error(client):
    with pytest.raises(Exception, match="search_tickets_export"):
        client.search_tickets("x", page=11, per_page=100)


def test_per_page_is_clamped(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get",
               return_value=_resp({"results": [], "count": 0})) as get:
        client.search_tickets("x", per_page=5000)
    assert get.call_args.kwargs["params"]["per_page"] == 100


def test_export_follows_cursor(client):
    page1 = _resp({"results": _tickets(100), "meta": {"has_more": True, "after_cursor": "c1"}})
    page2 = _resp({"results": _tickets(7, 101), "meta": {"has_more": False, "after_cursor": "c2"}})
    with patch("zendesk_mcp_server.zendesk_client.requests.get", side_effect=[page1, page2]) as get:
        a = client.search_tickets_export("created>=2026-10-26")
        b = client.search_tickets_export("created>=2026-10-26", cursor=a["after_cursor"])
    assert a["has_more"] is True and a["after_cursor"] == "c1"
    assert get.call_args_list[1].kwargs["params"]["page[after]"] == "c1"
    assert get.call_args_list[0].kwargs["params"]["filter[type]"] == "ticket"
    assert b["has_more"] is False and b["after_cursor"] is None


def test_count_parses_value(client):
    payload = {"count": {"value": 412, "refreshed_at": "2026-11-03T00:00:00Z"}}
    with patch("zendesk_mcp_server.zendesk_client.requests.get", return_value=_resp(payload)):
        assert client.count_tickets("created>=2026-10-26") == {
            "count": 412, "refreshed_at": "2026-11-03T00:00:00Z"}


def test_rate_limit_is_retried(client):
    ok = _resp({"results": [], "count": 0})
    limited = _resp({}, status=429, headers={"Retry-After": "0"})
    with patch("zendesk_mcp_server.zendesk_client.requests.get", side_effect=[limited, ok]) as get, \
         patch("zendesk_mcp_server.zendesk_client.time.sleep"):
        client.search_tickets("x")
    assert get.call_count == 2


def test_http_error_surfaces_status(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get", return_value=_resp({"error": "bad"}, status=422)):
        with pytest.raises(Exception, match="422"):
            client.search_tickets("x")


def test_recent_tickets_pages_via_search(client):
    with patch("zendesk_mcp_server.zendesk_client.requests.get",
               return_value=_resp({"results": _tickets(25), "count": 25})) as get:
        out = client.get_recent_tickets(per_page=25)
    assert get.call_args.kwargs["params"]["query"] == "type:ticket"
    assert out["has_more"] is False
