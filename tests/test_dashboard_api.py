from datetime import date
from unittest.mock import patch

import mcp_server.dashboard_api as dashboard_api


def test_epoch_millis_uses_vietnam_midnight():
    assert dashboard_api._epoch_millis(date(2026, 7, 30)) == 1785344400000
    assert dashboard_api._epoch_millis(date(2026, 7, 30), end_of_day=True) == 1785430799999


def test_missing_token_does_not_make_a_network_call():
    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", ""):
        with patch.object(dashboard_api, "ROCKY_DASHBOARD_USERNAME", ""):
            with patch.object(dashboard_api, "ROCKY_DASHBOARD_PASSWORD", ""):
                with patch.object(dashboard_api.httpx, "post") as post:
                    result = dashboard_api.query_dashboard_order_overview("2026-07-30", "2026-07-30")
    assert result["ok"] is False
    assert result["http_status"] == 0
    assert "ROCKY_DASHBOARD_API_TOKEN" in result["error"]["required_env"]
    post.assert_not_called()


def test_local_login_uses_official_endpoint_without_returning_credentials():
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"data": {"accessToken": "access", "refreshToken": "refresh"}}

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", ""):
        with patch.object(dashboard_api, "ROCKY_DASHBOARD_USERNAME", "local-user"):
            with patch.object(dashboard_api, "ROCKY_DASHBOARD_PASSWORD", "local-password"):
                with patch.object(dashboard_api.httpx, "post", return_value=Response()) as post:
                    access, refresh, error = dashboard_api._login()
    assert (access, refresh, error) == ("access", "refresh", None)
    assert post.call_args.args[0] == "https://identity.rocky.endpoint.eggstech.io/Identity/Login/Password"
    assert post.call_args.kwargs["headers"]["appCode"] == "ROCKY"
    assert "local-password" not in repr((access, refresh, error))


def test_overview_preserves_dashboard_payload_and_request_contract():
    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"total": 98528882, "orders": 311}

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", return_value=Response()) as post:
            result = dashboard_api.query_dashboard_order_overview("2026-07-30", "2026-07-30")

    assert result["ok"] is True
    assert result["data"] == {"total": 98528882, "orders": 311}
    assert post.call_args.args[0].endswith("/Admin/Dashboard/Order/Overview")
    assert post.call_args.kwargs["json"] == {
        "periodType": 1,
        "startAt": 1785344400000,
        "endAt": 1785430799999,
        "siteIds": None,
        "staffIds": None,
    }
    assert "unit-test-token" not in repr(result)


def test_revenue_uses_the_revenue_endpoint_and_preserves_payload():
    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"data": {"summary": {"all": {"totalRevenue": 1505568035}}}}

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", return_value=Response()) as post:
            result = dashboard_api.query_dashboard_revenue("2026-07-27", "2026-08-02")

    assert result["ok"] is True
    assert result["data"]["data"]["summary"]["all"]["totalRevenue"] == 1505568035
    assert result["dashboard_summary"] == {
        "scope": "summary.all",
        "total_revenue": 1505568035,
        "hmk_revenue": None,
        "other_revenue": None,
        "sales_orders": None,
        "return_orders": None,
    }
    assert "source_snapshot_at" in result
    assert post.call_args.args[0].endswith("/Admin/Dashboard/Revenue")
    assert post.call_args.kwargs["json"] == {
        "periodType": 1,
        "startAt": 1785085200000,
        "endAt": 1785689999999,
        "siteIds": None,
    }


def test_customer_sales_uses_top_n_and_matches_dashboard_card_rule():
    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "meta": {"total": 169},
                "data": [
                    {"totalRevenue": 30, "numOrder": 4, "numReturnOrder": 1},
                    {"totalRevenue": 12, "numOrder": 2, "numReturnOrder": 0},
                ],
            }

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", return_value=Response()) as post:
            result = dashboard_api.query_dashboard_sales_by_customer(
                "2026-07-31", "2026-07-31", top_n=10, page=1, page_size=10
            )

    assert result["dashboard_summary"] == {
        "start_page": 1,
        "page_size": 10,
        "pages_read": [1],
        "returned_customer_rows": 2,
        "requested_customer_rows": 10,
        "returned_revenue": 42,
        "customer_count": 169,
        "returned_num_order": 6,
        "returned_num_return_order": 1,
        "complete_for_token_scope": False,
        "scope": "rows_read_from_rocky_pages",
    }
    assert post.call_args.args[0].endswith("/Admin/Dashboard/Revenue/SalesByCustomer")
    assert post.call_args.kwargs["json"] == {
        "fromDate": 1785430800000,
        "toDate": 1785517199999,
        "page": 1,
        "size": 10,
    }


def test_customer_sales_reads_multiple_rocky_pages_when_top_n_exceeds_100():
    class Response:
        status_code = 200
        text = ""

        def __init__(self, page):
            self.page = page

        def json(self):
            row_count = 100 if self.page < 3 else 50
            return {
                "meta": {"total": 250},
                "data": [
                    {"totalRevenue": 1, "numOrder": 1, "numReturnOrder": 0}
                    for _ in range(row_count)
                ],
            }

    def post(*args, **kwargs):
        return Response(kwargs["json"]["page"])

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", side_effect=post) as mocked_post:
            result = dashboard_api.query_dashboard_sales_by_customer(
                "2026-07-31", "2026-07-31", top_n=250
            )

    assert result["dashboard_summary"]["pages_read"] == [1, 2, 3]
    assert result["dashboard_summary"]["returned_customer_rows"] == 250
    assert result["dashboard_summary"]["complete_for_token_scope"] is True
    assert mocked_post.call_count == 3


def test_allow_listed_metric_uses_common_dashboard_contract():
    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"meta": {"success": True}, "data": {"items": []}}

    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", return_value=Response()) as post:
            result = dashboard_api.query_dashboard_metric(
                "customer_overview", "2026-07-31", "2026-07-31", days=7
            )

    assert result["ok"] is True
    assert post.call_args.args[0].endswith("/Admin/Dashboard/Customer/Overview")
    assert post.call_args.kwargs["json"]["days"] == 7


def test_metric_rejects_unknown_or_invalid_paging():
    try:
        dashboard_api.query_dashboard_metric("not_a_metric", "2026-07-31", "2026-07-31")
    except ValueError as exc:
        assert "Unsupported dashboard metric" in str(exc)
    else:
        raise AssertionError("unknown metric should fail")

    try:
        dashboard_api.query_dashboard_metric("customer_overview", "2026-07-31", "2026-07-31", size=101)
    except ValueError as exc:
        assert "size must be" in str(exc)
    else:
        raise AssertionError("oversized page should fail")


def test_debt_overview_combines_only_official_dashboard_payloads():
    class Response:
        status_code = 200
        text = ""

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    responses = [
        Response({"data": {"totalPreviousBalance": -10, "totalDebtAmount": 20, "totalPaidAmount": 5, "recoverDebtRate": 25}}),
        Response({"data": {"totalAmount": 5}}),
    ]
    with patch.object(dashboard_api, "ROCKY_DASHBOARD_API_TOKEN", "unit-test-token"):
        with patch.object(dashboard_api.httpx, "post", side_effect=responses) as post:
            result = dashboard_api.query_dashboard_debt_overview("2026-07-30", "2026-07-30")

    assert result["ok"] is True
    assert result["dashboard_summary"] == {
        "total_previous_balance": -10,
        "total_debt_amount": 20,
        "total_paid_amount": 5,
        "recovery_debt_rate": 25,
        "revenue_total_amount": 5,
    }
    assert post.call_args_list[0].args[0].endswith("/Admin/DebtDashboard/RecoveryRate/Statistic")
    assert post.call_args_list[1].args[0].endswith("/Admin/DebtDashboard/Revenue/Statistic")
