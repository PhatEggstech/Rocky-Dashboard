import asyncio
from types import SimpleNamespace

from mcp_server import portal_tool_visibility
from mcp_server.portal_tool_visibility import PortalToolVisibilityMiddleware, SSO_VISIBLE_TOOLS


class Tool:
    def __init__(self, name):
        self.name = name


def test_non_admin_portal_session_only_sees_sso_safe_tools(monkeypatch):
    monkeypatch.setattr(
        portal_tool_visibility, "get_current_user",
        lambda: SimpleNamespace(portal_session="session", role="staff"),
    )

    async def next_tools(context):
        return [Tool("get_portal_list"), Tool("get_gpm"), Tool("query_raw_pos_sql_tool")]

    tools = asyncio.run(PortalToolVisibilityMiddleware().on_list_tools(None, next_tools))

    assert [tool.name for tool in tools] == ["get_portal_list"]


def test_admin_keeps_full_catalog(monkeypatch):
    monkeypatch.setattr(
        portal_tool_visibility, "get_current_user",
        lambda: SimpleNamespace(portal_session="session", role="admin"),
    )

    async def next_tools(context):
        return [Tool("get_portal_list"), Tool("get_gpm")]

    tools = asyncio.run(PortalToolVisibilityMiddleware().on_list_tools(None, next_tools))

    assert [tool.name for tool in tools] == ["get_portal_list", "get_gpm"]


def test_sso_catalog_keeps_only_api_adapters_or_safe_docs():
    assert {"get_portal_list", "get_dashboard_order_overview", "get_customer_sales"} <= SSO_VISIBLE_TOOLS
    assert "get_gpm" not in SSO_VISIBLE_TOOLS
    assert "query_raw_pos_sql_tool" not in SSO_VISIBLE_TOOLS
