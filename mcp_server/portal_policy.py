"""API-only boundary for non-admin identities in the portal-session rollout."""
import inspect
import os


def enabled():
    return os.environ.get('MCP_PORTAL_SESSIONS_ENABLED','false').lower() in {'true','1','yes'}


def require_sql_admin():
    if not enabled():
        return
    from .auth import get_current_user
    user=get_current_user()
    if user is not None and user.role!='admin':
        raise PermissionError('Direct business SQL is disabled for non-admin portal sessions')


API_ONLY_TOOLS=frozenset({
    'get_my_api_capabilities',
    'get_portal_list',
    'get_orders_created_summary',
    'get_effective_date_payment_summary',
    'get_assigned_orders',
    'get_portal_record',
    'get_dashboard_order_overview','get_tinh_hinh_kinh_doanh','get_dashboard_order_by_site',
    'get_dashboard_revenue','get_revenue_by_source','get_dashboard_sales_by_customer','get_dashboard_debt_overview',
    'get_dashboard_debt_customers','get_dashboard_metric',
    'get_product_industry_sales',
    # Local read-only MCP documentation does not access Rocky business data.
    'get_mcp_context', 'explain', 'list_business_specs',
    'get_business_spec_content', 'search_business_specs',
})


_API_ADAPTER_ALTERNATIVES = {
    'get_customer_sales': ['get_dashboard_sales_by_customer', 'get_portal_list'],
    'get_customer_debt_profile': ['get_dashboard_debt_overview', 'get_dashboard_debt_customers', 'get_portal_list'],
    'get_debt': ['get_dashboard_debt_overview', 'get_dashboard_debt_customers'],
    'get_inventory': ['get_portal_list'],
    'get_inventory_live': ['get_portal_list'],
    'get_staff_revenue': ['get_dashboard_metric', 'get_portal_list'],
    'get_products': ['get_dashboard_metric', 'get_portal_list'],
    'get_stores': ['get_dashboard_order_by_site', 'get_portal_list'],
}


def _bound_arguments(func, args, kwargs):
    """Bind a tool call without invoking its legacy implementation."""
    return inspect.signature(inspect.unwrap(func)).bind_partial(*args, **kwargs).arguments


def _api_alias(tool_name, func, args, kwargs, user):
    """Route verified legacy report names to the caller's Rocky API token.

    These aliases exist only where the request/response contract has been
    verified against Rocky.  Never broaden an SSO session to SQL as fallback.
    """
    values = _bound_arguments(func, args, kwargs)
    from .auth import is_bod_assistant

    # The dedicated BOD assistant must not receive customer-level rows that
    # could include HMK customers through a token-scoped Dashboard list.
    if is_bod_assistant(user) and tool_name in {'get_customer_sales', 'get_customers'}:
        return {
            'error': 'Customer-level rows are restricted for the BOD assistant role.',
            'code': 403,
            'api_only': True,
            'alternatives': ['get_dashboard_order_overview', 'get_dashboard_revenue'],
        }

    if tool_name == 'get_customer_sales':
        unsupported = [name for name in ('order_type', 'store_id', 'exclude_hmk_customers') if values.get(name)]
        if unsupported:
            return {
                'error': 'Those filters do not have a verified per-user Rocky Dashboard API contract.',
                'code': 422,
                'api_only': True,
                'unsupported_filters': unsupported,
                'alternatives': ['get_dashboard_sales_by_customer'],
            }
        from .dashboard_api import query_dashboard_sales_by_customer
        from .server import _resolve_reporting_range
        start, end, label = _resolve_reporting_range(
            values.get('date_from'), values.get('date_to'), values.get('relative_period')
        )
        result = query_dashboard_sales_by_customer(
            start, end, values.get('top_n', 10), values.get('page', 1), values.get('page_size', 20)
        )
        result['query_context'] = {
            'date_from': start, 'date_to': end, 'period_label': label,
            'adapter': 'rocky_dashboard_sales_by_customer_api',
        }
        return result

    if tool_name == 'get_debt':
        if values.get('customer_name'):
            return {
                'error': 'Customer-name debt lookup has no verified per-user Rocky API contract.',
                'code': 422,
                'api_only': True,
                'alternatives': ['get_dashboard_debt_overview', 'get_dashboard_debt_customers'],
            }
        from .dashboard_api import query_dashboard_debt_overview
        from .server import _resolve_reporting_range
        start, end, label = _resolve_reporting_range(values.get('date_from'), values.get('date_to'), None)
        result = query_dashboard_debt_overview(start, end)
        result['query_context'] = {
            'date_from': start, 'date_to': end, 'period_label': label,
            'adapter': 'rocky_dashboard_debt_overview_api',
        }
        return result

    if tool_name == 'get_customers':
        if values.get('segment') or values.get('search') or values.get('store_id'):
            return {
                'error': 'RFM, search, and store filters have no verified per-user Rocky Customer API contract.',
                'code': 422,
                'api_only': True,
                'alternatives': ['get_portal_list'],
            }
        from .portal_read_api import query_portal_list
        top_n = values.get('top_n', 10)
        offset = values.get('offset', 0)
        if type(top_n) is not int or type(offset) is not int or top_n < 1 or offset < 0:
            return {'error': 'top_n and offset must be non-negative integers.', 'code': 400, 'api_only': True}
        size = min(top_n, 100)
        result = query_portal_list('customers', page=(offset // size) + 1, size=size)
        result['query_context'] = {
            **result.get('query_context', {}),
            'adapter': 'rocky_portal_customer_get_page_api',
            'requested_customer_rows': top_n,
        }
        return result

    return None


def allowed_read_post(path):
    if os.environ.get('MCP_PORTAL_ALLOW_READ_POST','false').lower() not in {'true','1','yes'}:
        return False
    from .dashboard_api import DASHBOARD_READ_METRICS
    paths={value[0] for value in DASHBOARD_READ_METRICS.values()}
    paths.update({'/Admin/Dashboard/Order/Overview','/Admin/Dashboard/Order/BySite',
        '/Admin/Dashboard/Revenue','/Admin/Dashboard/Revenue/SalesByCustomer',
        '/Admin/DebtDashboard/RecoveryRate/Statistic','/Admin/DebtDashboard/Revenue/Statistic',
        '/Admin/DebtDashboard/CustomerDebt/GetPage'})
    return path in paths


def dispatch(func,args,kwargs):
    """Never execute the legacy SQL-backed implementation for a non-admin."""
    from .auth import get_current_user
    user=get_current_user()
    if not user or not getattr(user,'portal_session',''):
        return {'error':'Sign in with your own Rocky Dashboard account','code':401,'login_required':True}
    alias = _api_alias(func.__name__, func, args, kwargs, user)
    if alias is not None:
        if isinstance(alias, dict):
            alias['authorization_source'] = 'rocky_api_per_user_token'
            alias['sql_fallback'] = False
        return alias
    if func.__name__ not in API_ONLY_TOOLS:
        alternatives = _API_ADAPTER_ALTERNATIVES.get(
            func.__name__,
            ['get_my_api_capabilities', 'get_portal_list', 'get_dashboard_metric'],
        )
        return {
            'error': 'This operation has no verified per-user Rocky API adapter. '
                     'MCP does not use raw SQL or legacy direct queries for Portal sessions.',
            'code': 403,
            'api_only': True,
            'scope': 'The signed-in account can still use the listed read-only Portal and Dashboard API tools, subject to its Rocky permissions.',
            'alternatives': alternatives,
            'research_status': (
                'No verified read-only per-user Rocky API contract exists for this operation.'
                if func.__name__ in {'get_customer_debt_profile', 'get_gpm', 'check_wms_health'} else None
            ),
        }
    result=inspect.unwrap(func)(*args,**kwargs)
    if isinstance(result,dict):
        result['authorization_source']='rocky_api_per_user_token'
        result['sql_fallback']=False
    return result
