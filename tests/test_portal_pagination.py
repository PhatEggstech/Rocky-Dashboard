from types import SimpleNamespace

from mcp_server import portal_read_api


def test_portal_list_accepts_every_positive_page_number(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"meta": {"total": 1}, "data": [{"id": "customer-1"}]}

    monkeypatch.setattr(
        portal_read_api, "get_current_user", lambda: SimpleNamespace(portal_session="session")
    )
    monkeypatch.setattr(portal_read_api.portal_runtime, "portal_access_token", lambda user: ("token", None))
    monkeypatch.setattr(portal_read_api.httpx, "post", lambda *args, **kwargs: Response())

    result = portal_read_api.query_portal_list("customers", page=10_001, size=100)

    assert result["data"] == [{"id": "customer-1"}]
    assert result["query_context"]["page_is_complete_dataset"] is False


def test_orders_summary_crawls_beyond_the_previous_100_page_ceiling(monkeypatch):
    total = 10_001

    def page(resource, page, size, **kwargs):
        assert resource == "orders"
        return {
            "meta": {"total": total},
            "data": [{
                "productAmount": 1,
                "shippingFee": 0,
                "totalDiscountAmount": 0,
                "refundAmount": 0,
                "needPayAmount": 1,
                "paidAmount": 1,
                "leftAmount": 0,
            }],
        }

    monkeypatch.setattr(portal_read_api, "query_portal_list", page)

    result = portal_read_api.query_orders_created_summary("2026-10-01", "2026-10-01")

    assert result["complete"] is True
    assert result["page_count"] == 101
    assert result["crawl_policy"].startswith("All Rocky API pages")
