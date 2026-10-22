"""Staging-only portal detail reads; backend object ACLs are not verified here."""
import os
from urllib.parse import urlsplit
from uuid import UUID
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import httpx

from . import config, portal_runtime
from .auth import get_current_user


_RESOURCES = {
    "order": ("pos", "/Admin/Order/"),
    "customer": ("pos", "/Admin/Customer/"),
    "outbound_delivery": ("wms", "/Admin/OutboundDelivery/"),
    "product_item_warehouse_inventory": ("wms", "/Admin/ProductItemWarehouseInventory/"),
    "warehouse": ("wms", "/Admin/Warehouse/"),
}
_WMS_DEFAULT = "https://api.wms.rocky.endpoint.eggstech.io"
_TIMEOUT_SECONDS = 20.0

READ_LISTS = {
    'orders': ('pos', 'Order', 'Danh sach don hang Rocky cho phep tai khoan hien tai xem.'),
    'customers': ('pos', 'Customer', 'Danh sach khach hang trong pham vi API cua nguoi dung.'),
    'products': ('pos', 'Product', 'Danh muc san pham.'),
    'product_items': ('pos', 'ProductItem', 'Bien the va ma hang chi tiet.'),
    'staff': ('pos', 'Staff', 'Danh sach nhan vien duoc phep xem.'),
    'payments': ('pos', 'PaymentOrder', 'Danh sach phieu thanh toan; khong tu suy ra doanh thu hoac cong no.'),
    'sale_zones': ('pos', 'SaleZone', 'Danh sach vung sale.'),
    'return_orders': ('pos', 'ReturnOrder', 'Danh sach don tra hang.'),
    'warranties': ('pos', 'Warranty', 'Danh sach bao hanh.'),
    'warehouses': ('wms', 'Warehouse', 'Danh sach kho.'),
    'outbound_deliveries': ('wms', 'OutboundDelivery', 'Danh sach phieu xuat kho.'),
    'purchase_orders': ('wms', 'PurchaseOrder', 'Danh sach don mua hang.'),
    'stock_takes': ('wms', 'StockTake', 'Danh sach phieu kiem ke.'),
    'stock_transfers': ('wms', 'StockTransferOrder', 'Danh sach phieu chuyen kho.'),
}

# Rocky's GetPage contract supports the same IssueAt range filter for these
# dated business documents. Keep this explicit so an unverified filter is
# never silently accepted for a different resource.
DATE_FILTER_RESOURCES = frozenset({'orders', 'payments'})


def query_portal_list(resource, page=1, size=20, date_from=None, date_to=None, code=None, ownership='visible'):
    """Fixed read-only POST list contracts; never accept a URL or arbitrary body."""
    user=get_current_user()
    if not user or not user.portal_session:
        return _error('Individual Rocky sign-in required',401,login_required=True)
    # `size=100` is Rocky's documented upstream page size.  There is no MCP
    # page ceiling: a signed-in user may request every page that Rocky exposes.
    if resource not in READ_LISTS or type(page) is not int or type(size) is not int or page < 1 or not 1 <= size <= 100:
        return _error('Invalid list resource or pagination',400)
    service,name,_=READ_LISTS[resource]
    payload={'page':page,'size':size}
    if ownership not in ('visible','mine_revenue'):
        return _error('Unsupported ownership meaning; choose visible or mine_revenue',400)
    filtered=bool(date_from or date_to or code or ownership!='visible')
    if (date_from or date_to) and resource not in DATE_FILTER_RESOURCES:
        return _error('Date filters are verified only for orders and payments; no filter was ignored',400)
    if (code or ownership != 'visible') and resource != 'orders':
        return _error('Code and ownership filters are verified only for orders; no filter was ignored',400)
    try:
        if date_from or date_to:
            if not date_from or not date_to:raise ValueError()
            first,last=date.fromisoformat(date_from),date.fromisoformat(date_to)
            if last<first:raise ValueError()
            tz=ZoneInfo('Asia/Ho_Chi_Minh')
            payload['issueAt']={'operator':10,
                'from':int(datetime.combine(first,time.min,tz).timestamp()*1000),
                'to':int(datetime.combine(last,time.max,tz).timestamp()*1000)}
        if code:
            if not isinstance(code,str) or not code.strip() or len(code)>100:raise ValueError()
            payload['code']={'operator':1,'value':code.strip()}
    except (ValueError,TypeError):
        return _error('Invalid date range or order code',400)
    try:
        token,error=portal_runtime.portal_access_token(user)
        if error:return error
        if not isinstance(token,str) or not token:
            return _error('Individual Rocky sign-in required',401,login_required=True)
        staff_id=None
        if ownership=='mine_revenue':
            profile=httpx.get(_base_url('pos')+'/Admin/Account/CurrentProfile',
                headers={'Authorization':token,'Accept':'application/json'},timeout=_TIMEOUT_SECONDS,follow_redirects=False)
            if profile.status_code!=200:return _error('Rocky profile rejected request',profile.status_code,profile.status_code)
            staff=(profile.json().get('data') or {}).get('staff') or {}
            staff_id=staff.get('id')
            if not staff_id:return _error('No staff mapping for current Rocky identity; own-order scope was not broadened',403)
            staff_id=str(UUID(staff_id))
            payload['revenueStaffId']={'operator':1,'values':[staff_id]}
        response=httpx.post(_base_url(service)+'/Admin/'+name+'/GetPage',
            headers={'Authorization':token,'Accept':'application/json'},json=payload,
            timeout=_TIMEOUT_SECONDS,follow_redirects=False)
        if not 200<=response.status_code<300:
            return _error('Rocky list API rejected request',response.status_code,response.status_code,
                          login_required=response.status_code==401)
        body=response.json()
        if not isinstance(body,dict):return _error('Invalid Rocky list response',502)
        rows=body.get('data')
        if isinstance(rows,list):
            for row in rows:
                if not isinstance(row,dict):return _error('Invalid Rocky list row',502)
                if staff_id and str(row.get('revenueStaffId','')).lower()!=staff_id:
                    return _error('Rocky did not enforce requested ownership filter; data withheld',502)
                if 'issueAt' in payload:
                    timestamp=row.get('issueAt')
                    if not isinstance(timestamp,(int,float)) or not payload['issueAt']['from']<=timestamp<=payload['issueAt']['to']:
                        return _error('Rocky did not enforce requested date filter; data withheld',502)
                if code and row.get('code')!=code.strip():
                    return _error('Rocky did not enforce requested code filter; data withheld',502)
        body['query_context']={'resource':resource,'ownership':ownership,'date_from':date_from,'date_to':date_to,
            'date_field':'issueAt' if 'issueAt' in payload else None,'timezone':'Asia/Ho_Chi_Minh',
            'staff_id':staff_id,'page_is_complete_dataset':False,
            'total_meaning':'Rocky API total for requested filters within token-visible scope; not proven system-wide total'}
        return body
    except Exception:
        return _error('Rocky list service unavailable',503)


_LENS_CATEGORY_CODES = frozenset({
    'HAI TRONG', 'DRIVESHIELD', 'CHONG TIA UV', 'DOI MAU', 'CHONG VA DAP',
    'BLUECUT', 'BLUECONTROL', 'MYOPIA', 'DA TRONG',
})


def _category_code(value):
    """Normalise Rocky category codes/names without guessing from product names."""
    import unicodedata
    text = unicodedata.normalize('NFD', str(value or ''))
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    return ' '.join(text.upper().split())


def query_product_industry_sales_api(date_from: str, date_to: str) -> dict:
    """Classify Dashboard product revenue using the caller-visible Product category.

    Dashboard's Product/ByRevenue response has product IDs and amounts but no
    category. Product/GetPage provides the authoritative category per product.
    Joining those two read-only, per-user API responses avoids the former SQL
    fallback and never treats a product name as its industry.
    """
    product_pages = []
    first = query_portal_list('products', page=1, size=100)
    if first.get('error'):
        return first
    product_pages.extend(first.get('data') or [])
    meta = first.get('meta') or {}
    page_count = meta.get('pageCount')
    if not isinstance(page_count, int) or page_count < 1:
        return _error('Invalid Rocky product pagination metadata', 502)
    for page in range(2, page_count + 1):
        response = query_portal_list('products', page=page, size=100)
        if response.get('error'):
            return response
        product_pages.extend(response.get('data') or [])

    product_categories = {}
    for product in product_pages:
        if not isinstance(product, dict) or not product.get('id'):
            continue
        category = product.get('productCategory') or {}
        category_code = _category_code(category.get('code') or category.get('name'))
        product_categories[str(product['id'])] = {
            'code': category_code,
            'name': category.get('displayName') or category.get('name'),
        }

    from .dashboard_api import query_dashboard_metric
    dashboard = query_dashboard_metric('product_by_revenue', date_from, date_to, size=100)
    if not dashboard.get('ok'):
        return dashboard
    body = dashboard.get('data') or {}
    items = ((body.get('data') or {}).get('items') or []) if isinstance(body, dict) else []
    if not isinstance(items, list):
        return _error('Invalid Rocky dashboard product revenue response', 502)

    buckets = {
        'frames_dd': {'revenue': 0.0, 'products': 0},
        'lenses_dt': {'revenue': 0.0, 'products': 0},
        'other_categorized': {'revenue': 0.0, 'products': 0},
        'unclassified': {'revenue': 0.0, 'products': 0},
    }
    category_breakdown = {}
    dashboard_total = 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            amount = float(item.get('totalAmount') or 0)
        except (TypeError, ValueError):
            return _error('Invalid product revenue amount from Rocky dashboard', 502)
        dashboard_total += amount
        category = product_categories.get(str(item.get('productId'))) or {}
        code = category.get('code') or ''
        name = category.get('name') or 'Chưa phân loại'
        if code == 'GONG':
            bucket = 'frames_dd'
        elif code in _LENS_CATEGORY_CODES:
            bucket = 'lenses_dt'
        elif code:
            bucket = 'other_categorized'
        else:
            bucket = 'unclassified'
        buckets[bucket]['revenue'] += amount
        buckets[bucket]['products'] += 1
        entry = category_breakdown.setdefault(name, {'category': name, 'revenue': 0.0, 'products': 0})
        entry['revenue'] += amount
        entry['products'] += 1

    for bucket in buckets.values():
        bucket['revenue'] = round(bucket['revenue'])
    for entry in category_breakdown.values():
        entry['revenue'] = round(entry['revenue'])

    return {
        'metric': 'product_industry_sales',
        'source': 'rocky_dashboard_api + rocky_pos_product_api',
        'authorization_source': 'rocky_api_per_user_token',
        'sql_fallback': False,
        'period': {'date_from': date_from, 'date_to': date_to},
        'frames_dd': buckets['frames_dd'],
        'lenses_dt': buckets['lenses_dt'],
        'other_categorized': buckets['other_categorized'],
        'unclassified': buckets['unclassified'],
        'dashboard_total_revenue': round(dashboard_total),
        'category_breakdown': sorted(category_breakdown.values(), key=lambda entry: entry['revenue'], reverse=True),
        'coverage': {
            'dashboard_products': len(items),
            'visible_product_catalog': len(product_pages),
            'classified_by_authoritative_category': len(items) - buckets['unclassified']['products'],
            'unclassified_products': buckets['unclassified']['products'],
        },
        'disclaimer': (
            'DD chi gom ProductCategory.Code=GONG. DT chi gom cac ProductCategory lens da khai bao. '
            'San pham khong co danh muc API duoc bao rieng va khong duoc cong vao DD hay DT.'
        ),
    }


def query_orders_created_summary(date_from: str, date_to: str) -> dict:
    """Aggregate the Order page footer using only the caller's API-visible rows.

    The Rocky order screen calls this date concept ``Ngay tao``. In the API it
    is ``Order.IssueAt``. This is intentionally separate from cash collected
    or Dashboard revenue, whose date basis is PaymentOrder.IssueAt.
    """
    first = query_portal_list(
        'orders', page=1, size=100, date_from=date_from, date_to=date_to,
        ownership='visible',
    )
    if not isinstance(first, dict) or first.get('error'):
        return first
    meta = first.get('meta') or {}
    total = meta.get('total')
    if not isinstance(total, int) or total < 0:
        return _error('Rocky order list did not provide a valid total', 502)
    page_count = (total + 99) // 100
    pages = [first]
    for page in range(2, page_count + 1):
        response = query_portal_list(
            'orders', page=page, size=100, date_from=date_from, date_to=date_to,
            ownership='visible',
        )
        if not isinstance(response, dict) or response.get('error'):
            return response if isinstance(response, dict) else _error('Invalid Rocky order list response', 502)
        pages.append(response)

    fields = {
        'product_amount': 'productAmount',
        'shipping_fee': 'shippingFee',
        'order_discount': 'totalDiscountAmount',
        'return_value': 'refundAmount',
        'amount_due': 'needPayAmount',
        'paid_amount': 'paidAmount',
        'remaining_amount': 'leftAmount',
    }
    totals = {'order_count': total}
    for output_name, field_name in fields.items():
        totals[output_name] = sum(
            float(row.get(field_name) or 0)
            for response in pages
            for row in response.get('data', [])
            if isinstance(row, dict)
        )
    due_paid_remaining_difference = (
        totals['amount_due'] - totals['paid_amount'] - totals['remaining_amount']
    )
    return {
        'metric': 'orders_created_summary',
        'source': 'rocky_portal_api',
        'period': {'date_from': date_from, 'date_to': date_to},
        'date_basis': 'Order.IssueAt (Ngay tao tren man hinh Don hang)',
        'scope': 'records visible to the signed-in Rocky token',
        'totals': totals,
        'field_mapping': {
            'product_amount': 'SUM(Order.productAmount)',
            'shipping_fee': 'SUM(Order.shippingFee)',
            'order_discount': 'SUM(Order.totalDiscountAmount)',
            'return_value': 'SUM(Order.refundAmount)',
            'amount_due': 'SUM(Order.needPayAmount)',
            'paid_amount': 'SUM(Order.paidAmount)',
            'remaining_amount': 'SUM(Order.leftAmount)',
        },
        'presentation_rules': {
            'headline_for_orders_created_revenue_question': 'Da thanh toan cua don tao trong ky',
            'primary_amount': 'paid_amount',
            'amount_due_is_secondary': True,
            'paid_amount_meaning': (
                'SUM(Order.paidAmount) for every order created in the period. '
                'Use this as the answer when the user asks for doanh thu of orders created.'
            ),
            'not_cash_collection_by_payment_effective_date': True,
            'footer_values_are_independent': True,
            'do_not_infer_formula': (
                'Do not infer product + shipping - discount - return = amount_due, '
                'or paid + remaining = amount_due, unless reconciliation is balanced.'
            ),
        },
        'reconciliation': {
            'due_paid_remaining_difference': due_paid_remaining_difference,
            'is_balanced': abs(due_paid_remaining_difference) < 0.005,
            'meaning': (
                'Difference between SUM(needPayAmount) and '
                'SUM(paidAmount) + SUM(leftAmount). A non-zero value means these '
                'API footer fields must be presented as independent snapshots, not a '
                'single accounting equation.'
            ),
        },
        'page_count': page_count,
        'crawl_policy': 'All Rocky API pages in the requested period were read; MCP does not impose a page cap.',
        'complete': True,
    }


def query_effective_date_payment_summary(date_from: str, date_to: str) -> dict:
    """Aggregate the payment screen's receipt total from caller-visible rows.

    The Rocky ``Phiếu thu chi`` screen labels PaymentOrder.IssueAt as ``Ngày
    hiệu lực``. Its ``Tổng thu`` is the sum of ``needPayAmount`` for document
    type 1 (Thu). Allocate/cấn trừ and refund documents are returned separately
    rather than silently mixed into the receipt total.
    """
    first = query_portal_list(
        'payments', page=1, size=100, date_from=date_from, date_to=date_to,
        ownership='visible',
    )
    if not isinstance(first, dict) or first.get('error'):
        return first
    meta = first.get('meta') or {}
    total = meta.get('total')
    if not isinstance(total, int) or total < 0:
        return _error('Rocky payment list did not provide a valid total', 502)
    page_count = (total + 99) // 100
    pages = [first]
    for page in range(2, page_count + 1):
        response = query_portal_list(
            'payments', page=page, size=100, date_from=date_from, date_to=date_to,
            ownership='visible',
        )
        if not isinstance(response, dict) or response.get('error'):
            return response if isinstance(response, dict) else _error('Invalid Rocky payment list response', 502)
        pages.append(response)

    labels = {1: 'receipt', 3: 'allocation', 4: 'refund'}
    by_document_type: dict[str, dict[str, float | int]] = {}
    for response in pages:
        for row in response.get('data', []):
            if not isinstance(row, dict):
                continue
            document_type = row.get('documentType')
            bucket = labels.get(document_type, f'other_{document_type}')
            totals = by_document_type.setdefault(bucket, {
                'document_type': document_type, 'count': 0,
                'amount': 0.0, 'paid_amount': 0.0, 'allocate_amount': 0.0,
            })
            totals['count'] += 1
            totals['amount'] += float(row.get('needPayAmount') or 0)
            totals['paid_amount'] += float(row.get('paidAmount') or 0)
            totals['allocate_amount'] += float(row.get('allocateAmount') or 0)

    receipt = by_document_type.get('receipt', {})
    return {
        'metric': 'effective_date_payment_summary',
        'source': 'rocky_portal_api',
        'period': {'date_from': date_from, 'date_to': date_to},
        'date_basis': 'PaymentOrder.IssueAt (Ngay hieu luc tren man hinh Phieu thu chi)',
        'scope': 'records visible to the signed-in Rocky token',
        'payment_document_count': total,
        'total_receipt_amount': receipt.get('amount', 0.0),
        'total_receipt_count': receipt.get('count', 0),
        'total_receipt_formula': 'SUM(PaymentOrder.needPayAmount) WHERE DocumentType = 1 (Thu)',
        'by_document_type': by_document_type,
        'document_type_meaning': {
            'receipt': 'DocumentType=1 (Thu): dong tien thu; day la gia tri Tong thu tren man hinh.',
            'allocation': 'DocumentType=3 (Can tru/Allocate): but toan phan bo, doi tru cong no; khong phai dong tien thu moi.',
            'refund': 'DocumentType=4 (Hoan): chung tu hoan/chi; bao cao rieng, khong tru vao Tong thu.',
        },
        'aggregation_rule': (
            'Do not calculate Thu + Can tru - Hoan. Tong thu is only '
            'DocumentType=1. Can tru may be linked to an original receipt and '
            'adding it can double count cash collection.'
        ),
        'page_count': page_count,
        'crawl_policy': 'All Rocky API pages in the requested period were read; MCP does not impose a page cap.',
        'complete': True,
    }


def _error(message, code, http_status=None, login_required=False):
    result = {"error": message, "code": code, "http_status": http_status}
    if login_required:
        result["login_required"] = True
    return result


def _base_url(service):
    base = (config.ROCKY_DASHBOARD_API_BASE_URL if service == "pos" else
            os.environ.get("ROCKY_WMS_API_BASE_URL", _WMS_DEFAULT))
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.path not in ("", "/") or parsed.query or parsed.fragment or
            any(char.isspace() or ord(char) < 32 for char in base) or
            "\\" in base):
        raise ValueError("Invalid API base")
    # Force validation of malformed ports before any credentials are sent.
    parsed.port
    return base.rstrip("/")


def query_portal_detail(resource: str, object_id: str):
    """GET one fixed resource using the current user's RK session.

    Return upstream JSON unchanged on success, or a sanitized error dictionary.
    No URL, method, body, shared credential, SQL, or retry interface is exposed.
    """
    user = get_current_user()
    if user is None or not getattr(user, "portal_session", ""):
        return _error("Individual Rocky sign-in required", 401, login_required=True)
    if not isinstance(resource, str) or resource not in _RESOURCES:
        return _error("Unsupported portal resource", 400)
    try:
        if not isinstance(object_id, str) or str(UUID(object_id)) != object_id.lower():
            raise ValueError("Invalid UUID")
        service, path = _RESOURCES[resource]
        url = _base_url(service) + path + str(UUID(object_id))
    except (ValueError, TypeError, AttributeError):
        return _error("Invalid identifier or API configuration", 400)
    try:
        token, error = portal_runtime.portal_access_token(user)
        if error or not isinstance(token, str) or not token:
            if error and error.get("code") == 503:
                return _error("Portal credentials unavailable", 503)
            return _error("Individual Rocky sign-in required", 401, login_required=True)
        response = httpx.get(
            url, headers={"Authorization": token, "Accept": "application/json"},
            timeout=_TIMEOUT_SECONDS, follow_redirects=False,
        )
    except Exception:
        # Transport and credential exceptions may contain tokens or raw headers.
        return _error("Portal service unavailable", 503)
    status = response.status_code
    if status == 401:
        return _error("Rocky sign-in required", 401, status, login_required=True)
    if not 200 <= status < 300:
        return _error("Portal request rejected", status, status)
    try:
        return response.json()
    except (ValueError, TypeError):
        return _error("Invalid portal response", 502, status)
