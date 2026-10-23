"""Per-request MCP tool visibility for Rocky Portal SSO sessions."""

from fastmcp.server.middleware import Middleware

from .auth import get_current_user
from .portal_policy import API_ONLY_TOOLS


# These names retain backward compatibility, but each is routed in
# portal_policy._api_alias to a verified per-user Rocky API adapter.
SSO_API_ALIASES = frozenset({'get_customer_sales', 'get_debt', 'get_customers'})
SSO_VISIBLE_TOOLS = API_ONLY_TOOLS | SSO_API_ALIASES


class PortalToolVisibilityMiddleware(Middleware):
    """Hide unsupported tools before an SSO client sees its MCP catalog."""

    async def on_list_tools(self, context, call_next):
        tools = await call_next(context)
        user = get_current_user()
        # Admin keeps the full catalog, including governed internal tools.
        # A non-admin Portal session receives only adapters that never fall
        # back to shared credentials or raw SQL.
        if user and user.portal_session and user.role != 'admin':
            return [tool for tool in tools if tool.name in SSO_VISIBLE_TOOLS]
        return tools
