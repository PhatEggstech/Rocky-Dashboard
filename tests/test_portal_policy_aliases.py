from types import SimpleNamespace

from mcp_server import auth, dashboard_api, portal_policy, portal_read_api


def _portal_user():
    return SimpleNamespace(portal_session="session", role="staff", username="staff")


def test_customer_sales_legacy_name_uses_dashboard_api(monkeypatch):
    monkeypatch.setattr(auth, "get_current_user", _portal_user)
    monkeypatch.setattr(
        dashboard_api,
        "query_dashboard_sales_by_customer",
        lambda start, end, top_n, page, page_size: {"ok": True, "data": {"data": []}},
    )

    def get_customer_sales(date_from=None, date_to=None, top_n=10, page=1, page_size=20,
                           order_type=None, store_id=None, relative_period=None,
                           exclude_hmk_customers=False):
        raise AssertionError("legacy SQL implementation must not run")

    result = portal_policy.dispatch(get_customer_sales, (), {"date_from": "2026-10-22", "date_to": "2026-10-22", "top_n": 150})

    assert result["ok"] is True
    assert result["query_context"]["adapter"] == "rocky_dashboard_sales_by_customer_api"
    assert result["authorization_source"] == "rocky_api_per_user_token"
    assert result["sql_fallback"] is False


def test_customers_legacy_name_uses_portal_api(monkeypatch):
    monkeypatch.setattr(auth, "get_current_user", _portal_user)
    monkeypatch.setattr(portal_read_api, "query_portal_list", lambda *args, **kwargs: {"data": [], "query_context": {}})

    def get_customers(segment=None, top_n=10, store_id=None, search=None, offset=0):
        raise AssertionError("legacy SQL implementation must not run")

    result = portal_policy.dispatch(get_customers, (), {"top_n": 20})

    assert result["query_context"]["adapter"] == "rocky_portal_customer_get_page_api"
    assert result["authorization_source"] == "rocky_api_per_user_token"


def test_unverified_customer_filter_is_not_ignored(monkeypatch):
    monkeypatch.setattr(auth, "get_current_user", _portal_user)

    def get_customer_sales(date_from=None, date_to=None, top_n=10, page=1, page_size=20,
                           order_type=None, store_id=None, relative_period=None,
                           exclude_hmk_customers=False):
        raise AssertionError("legacy SQL implementation must not run")

    result = portal_policy.dispatch(get_customer_sales, (), {"store_id": "K29"})

    assert result["code"] == 422
    assert result["sql_fallback"] is False


def test_local_business_docs_are_api_only_safe_tools():
    assert {"get_mcp_context", "list_business_specs", "search_business_specs"} <= portal_policy.API_ONLY_TOOLS
