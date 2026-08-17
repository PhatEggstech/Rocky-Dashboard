from mcp_server.server import _result_disclaimer


def test_dashboard_disclaimer_explains_total_scope():
    disclaimer = _result_disclaimer("get_dashboard_revenue")

    assert disclaimer["type"] == "dashboard_snapshot"
    assert "bao gồm cả hai nguồn" in disclaimer["message"]


def test_wms_disclaimer_marks_live_snapshot():
    disclaimer = _result_disclaimer("get_inventory_live")

    assert disclaimer["type"] == "wms_live_snapshot"
    assert "WMS live" in disclaimer["message"]


def test_legacy_and_raw_disclaimers_are_not_dashboard_kpis():
    legacy = _result_disclaimer("get_revenue_legacy")
    raw = _result_disclaimer("query_raw_pos_sql_tool")

    assert legacy["type"] == "legacy_pos_reconciliation"
    assert raw["type"] == "technical_read_only_result"
