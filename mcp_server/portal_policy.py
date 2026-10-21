"""API-only boundary for non-admin identities in the portal-session rollout."""
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
})


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
    if func.__name__ not in API_ONLY_TOOLS:
        return {'error':'This tool has no verified per-user Rocky API adapter; SQL fallback is disabled',
                'code':403,'api_only':True,'alternatives':sorted(API_ONLY_TOOLS)}
    import inspect
    result=inspect.unwrap(func)(*args,**kwargs)
    if isinstance(result,dict):
        result['authorization_source']='rocky_api_per_user_token'
        result['sql_fallback']=False
    return result
