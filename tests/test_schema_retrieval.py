from mcp_server.tools import (
    describe_pos_table,
    get_schema_quick_context,
    get_spec_content,
    search_specs,
)


def test_quick_context_lists_payment_tables_and_rules():
    context = get_schema_quick_context()

    assert context["metric"] == "schema_quick_context"
    assert "PaymentOrder" in context["pos_core_tables"]
    assert any("Receive" in rule for rule in context["mandatory_rules"])


def test_schema_search_returns_context_for_payment_allocate():
    result = search_specs("PaymentOrder Allocate", max_results=5)

    assert result["tokens"] == ["paymentorder", "allocate"]
    assert result["total_files_matched"] >= 1
    assert any(item["matches"] for item in result["results"])


def test_schema_search_rejects_invalid_limit():
    assert "error" in search_specs("PaymentOrder", max_results=31)


def test_describe_pos_table_rejects_unsafe_name_without_connecting():
    assert "error" in describe_pos_table('Order; DROP TABLE "Order"')


def test_get_spec_content_reads_known_business_spec():
    result = get_spec_content("AGENTS.md", line_start=1, line_count=1)

    assert result["filename"] == "AGENTS.md"
    assert result["line_start"] == 1
    assert result["line_end"] == 1
    assert result["content"]
