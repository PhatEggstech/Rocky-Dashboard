from types import SimpleNamespace
from unittest.mock import patch

import mcp_server.server as server
from mcp_server.tools import validate_read_only_sql


def test_read_only_sql_accepts_select_and_cte_queries():
    assert validate_read_only_sql('SELECT "Id" FROM "Order" LIMIT 1') is None
    assert validate_read_only_sql("WITH orders AS (SELECT 1 AS id) SELECT id FROM orders") is None
    assert validate_read_only_sql("SELECT ';' AS literal_value") is None


def test_read_only_sql_blocks_write_and_multiple_statements():
    assert validate_read_only_sql("DELETE FROM orders")
    assert validate_read_only_sql("WITH changed AS (UPDATE orders SET state = 1 RETURNING id) SELECT * FROM changed")
    assert validate_read_only_sql("SELECT 1; SELECT 2")


def test_tracker_marks_structured_error_as_failure_not_success():
    @server.track_tool
    def broken_tool():
        return {"error": "upstream unavailable"}

    with patch.object(server, "get_current_user", return_value=None):
        with patch.object(server.tracker_logger, "error") as error_log:
            with patch.object(server.tracker_logger, "info") as info_log:
                result = broken_tool()

    assert result == {"error": "upstream unavailable"}
    assert any("[FAILURE]" in call.args[0] for call in error_log.call_args_list)
    assert not any("[SUCCESS]" in call.args[0] for call in info_log.call_args_list)


def test_bod_is_given_dashboard_alternative_for_disallowed_debt_detail():
    @server.track_tool
    def get_debt():
        raise AssertionError("BOD must be blocked before tool execution")

    bod = SimpleNamespace(name="BOD Assistant", role="bod")
    with patch.object(server, "get_current_user", return_value=bod):
        result = get_debt()

    assert result["code"] == 403
    assert result["alternatives"] == ["get_dashboard_debt_overview"]
    assert "get_dashboard_sales_by_customer" in server.BOD_ALLOWED_TOOLS
    assert "get_dashboard_debt_overview" in server.BOD_ALLOWED_TOOLS
