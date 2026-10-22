"""Describe fixed per-user read adapters without granting access from JWT claims."""

import os

from .auth import get_current_user
from .portal_read_api import _base_url, READ_LISTS
from .dashboard_api import DASHBOARD_READ_METRICS
from . import portal_runtime
import httpx


READ_ADAPTERS = (
    ('order', 'pos', '/Admin/Order/{id}', 'Read one order by its UUID; not an order list.'),
    ('customer', 'pos', '/Admin/Customer/{id}', 'Read one customer by its UUID.'),
    ('warehouse', 'wms', '/Admin/Warehouse/{id}', 'Read one warehouse by its UUID.'),
    ('outbound_delivery', 'wms', '/Admin/OutboundDelivery/{id}', 'Read one outbound delivery by its UUID.'),
    ('product_item_warehouse_inventory', 'wms', '/Admin/ProductItemWarehouseInventory/{id}',
     'Read one warehouse inventory record by its UUID, not aggregate stock.'),
)


def query_my_api_capabilities():
    user = get_current_user()
    if not user or not user.portal_session:
        return {'error': 'Individual Rocky sign-in required', 'code': 401}
    token, error = portal_runtime.portal_access_token(user)
    if error:
        return error
    try:
        response = httpx.get(_base_url('pos')+'/Admin/Account/CurrentProfile',
                            headers={'Authorization': token, 'Accept': 'application/json'},
                            timeout=20, follow_redirects=False)
        if response.status_code != 200:
            return {'error': 'Rocky identity check rejected', 'code': response.status_code}
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get('data'), dict):
            return {'error': 'Invalid Rocky profile response', 'code': 502}
    except Exception:
        return {'error': 'Rocky identity service unavailable', 'code': 503}
    dashboard_post_enabled = os.environ.get('MCP_PORTAL_ALLOW_READ_POST', 'false').lower() in {'true', '1', 'yes'}
    dashboard_summary_tools = [
        dict(tool='get_dashboard_revenue', method='POST', endpoint='/Admin/Dashboard/Revenue',
             description='Doanh so theo Dashboard, gom Tong/HMK/Khac/so don ban/don tra.'),
        dict(tool='get_dashboard_order_overview', method='POST', endpoint='/Admin/Dashboard/Order/Overview',
             description='Bon KPI Tong quan: so don, gia tri, thuc thu va con phai thu.'),
        dict(tool='get_dashboard_order_by_site', method='POST', endpoint='/Admin/Dashboard/Order/BySite',
             description='Tong quan theo chi nhanh.'),
        dict(tool='get_dashboard_sales_by_customer', method='POST', endpoint='/Admin/Dashboard/Revenue/SalesByCustomer',
             description='Doanh so theo khach hang theo giao dien Dashboard, co page/page_size (toi da 100 dong/trang).'),
    ]
    dashboard_debt_tools = [
        dict(tool='get_dashboard_debt_overview', method='POST',
             endpoint='/Admin/DebtDashboard/RecoveryRate/Statistic + /Admin/DebtDashboard/Revenue/Statistic',
             description='KPI thu hoi no va doanh thu cong no trong khoang ngay.'),
        dict(tool='get_dashboard_debt_customers', method='POST',
             endpoint='/Admin/DebtDashboard/CustomerDebt/GetPage',
             description='Danh sach cong no khach hang co phan trang.'),
    ]
    dashboard_metric_tools = [
        dict(tool='get_dashboard_metric', metric=metric, method='POST', endpoint=path,
             payload_contract=payload_kind,
             description='Dashboard metric da dang ky chi-doc; Rocky kiem tra quyen cua token o moi request.')
        for metric, (path, payload_kind) in DASHBOARD_READ_METRICS.items()
    ]
    result = {
        'current_identity': {
            'rk_user_id':getattr(user,'rk_user_id',None),
            'rk_role_code':(body['data'].get('account') or {}).get('roleCode'),
            'staff_id':(body['data'].get('staff') or {}).get('id'),
            'staff_code':(body['data'].get('staff') or {}).get('code'),
        },
        'identity_api_verified': True,
        'verification_scope': 'Profile API only; resource access is checked by Rocky on each request.',
        'read_tools': [dict(tool='get_portal_record', resource=resource, service=service,
                            method='GET', endpoint=path, description=description,
                            arguments={'resource': resource, 'object_id': 'UUID'},
                            permission_status='not_probed_for_requested_object')
                       for resource, service, path, description in READ_ADAPTERS],
        'unavailable': ([] if dashboard_post_enabled else [
            {'tools': 'get_dashboard_* / get_tinh_hinh_kinh_doanh',
             'reason': 'Dashboard read reports require POST; the MCP read-only POST allow-list is disabled.'}]),
        'llm_rules': [
            'Use current_identity to identify the employee; do not ask for their code if already mapped.',
            'Orders visible to a token are not automatically personal orders or all system orders.',
            'For my revenue orders use ownership=mine_revenue. Creator/processor/shipper ownership meanings are not implemented; clarify rather than substitute.',
            'For monthly orders or payments pass date_from/date_to; the date field is issueAt in Vietnam time. Do not scan thousands of pages to filter locally.',
            'get_portal_list supports every positive page number and up to 100 rows per request. Continue with Rocky API pages when a complete list is requested; never call the first page a complete list.',
            'For SSO receipt questions, call get_portal_list(resource="payments") with date_from/date_to. Do not call legacy SQL receipt tools.',
            'Never treat this catalog or a role name as authorization to an object.',
            'Use only registered tools and documented arguments; do not invent an endpoint.',
            'Do not use detail endpoints to claim a complete list, count, or aggregate.',
            'On 401 request sign-in; on 403 report the actual API or MCP restriction.',
            'Never substitute shared/admin credentials or SQL for a denied API.',
            'Do not execute create/update/delete/approve/export actions from this catalog.'],
        'sql_fallback': False,
        'order_list_alias': {'tool':'get_assigned_orders','adapter':'get_portal_list(resource=orders)',
            'description':'Returns API-visible orders, not a locally inferred employee assignment.',
            'supported_filters':['date_from','date_to','code'],
            'default_ownership':'mine_revenue'},
        'order_created_summary': {
            'tool': 'get_orders_created_summary',
            'description': 'Tong cac cot footer cua man hinh Don hang theo Ngay tao. Cau hoi doanh thu cua don tao dung paid_amount (Da thanh toan) lam so chinh.',
            'arguments': {'date_from': 'YYYY-MM-DD', 'date_to': 'YYYY-MM-DD',
                          'relative_period': 'today|yesterday|this_week|last_week|this_month'},
            'date_basis': 'Order.IssueAt; khong phai PaymentOrder.IssueAt',
            'returns': ['order_count', 'product_amount', 'shipping_fee', 'order_discount',
                        'return_value', 'amount_due', 'paid_amount', 'remaining_amount',
                        'reconciliation'],
            'permission_status': 'checked_by-upstream-on-each-request',
        },
        'effective_date_payment_summary': {
            'tool': 'get_effective_date_payment_summary',
            'description': 'Tong thu cua man hinh Phieu thu chi theo Ngay hieu luc.',
            'arguments': {'date_from': 'YYYY-MM-DD', 'date_to': 'YYYY-MM-DD',
                          'relative_period': 'today|yesterday|this_week|last_week|this_month'},
            'date_basis': 'PaymentOrder.IssueAt; chi DocumentType=1 la Tong thu',
            'aggregation_rule': 'Khong tinh Thu + Can tru - Hoan. Can tru/Allocate va Hoan chi bao cao rieng.',
            'returns': ['total_receipt_amount', 'total_receipt_count', 'by_document_type'],
            'permission_status': 'checked-by-upstream-on-each-request',
        },
        'read_list_tools': [dict(tool='get_portal_list',resource=resource,service=service,
            method='POST',endpoint='/Admin/'+name+'/GetPage',description=description,
            arguments={'resource':resource,'page':1,'size':20,
                       **({'date_from':'YYYY-MM-DD','date_to':'YYYY-MM-DD'} if resource in {'orders','payments'} else {})},
            permission_status='checked_by_upstream_on_each_request')
            for resource,(service,name,description) in READ_LISTS.items()],
    }
    if dashboard_post_enabled:
        result['read_dashboard_tools'] = [
            dict(item, permission_status='checked_by-upstream-on-each-request')
            for item in dashboard_summary_tools + dashboard_debt_tools
        ]
        result['read_dashboard_metric_tools'] = [
            dict(item, permission_status='checked-by-upstream-on-each-request')
            for item in dashboard_metric_tools
        ]
    return result
