"""Stock restricted to the products and warehouse of an assigned delivery."""
from uuid import UUID

from .tools import _get_pos_conn
from .wms_tools import _get_wms_conn, _rows


def query_shipping_inventory(staff_id, order_code):
    staff = str(UUID(str(staff_id)))
    if not str(order_code).strip():
        return {'code': 400, 'error': 'Order code required'}
    with _get_pos_conn() as conn:
        order = conn.execute('''SELECT "Id"::text,"WarehouseId"::text FROM "Order"
            WHERE "Code"=%s AND "ShipperId"=%s::uuid AND "DeleteAt" IS NULL
            AND "CancelAt" IS NULL LIMIT 2''', (order_code, staff)).fetchall()
        if len(order) != 1:
            return {'code': 403, 'error': 'Order unavailable in assigned delivery scope'}
        order_id, warehouse_id = order[0]
        items = conn.execute('''SELECT DISTINCT oi."ProductItemId"::text
            FROM "OrderItem" oi JOIN "OrderItemGroup" g ON g."Id"=oi."OrderItemGroupId"
            WHERE g."OrderId"=%s::uuid AND g."DeleteAt" IS NULL
            AND oi."DeleteAt" IS NULL AND oi."ProductItemId" IS NOT NULL LIMIT 201''', (order_id,)).fetchall()
    if len(items) > 200:
        return {'code': 400, 'error': 'Order exceeds the 200 SKU inventory limit'}
    ids = [r[0] for r in items]
    if not ids:
        return {'source': 'wms_live', 'order_code': order_code, 'rows': [], 'count': 0}
    with _get_wms_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT i."ProductItemId"::text AS product_item_id,
                p."Code" AS product_code,p."Name" AS product_name,w."Code" AS warehouse_code,
                SUM(i."StockQuantity") AS on_hand
                FROM "ProductItemWarehouseInventory" i
                JOIN "Product" p ON p."Id"=i."ProductId" AND p."DeleteAt" IS NULL
                JOIN "Warehouse" w ON w."Id"=i."WarehouseId" AND w."DeleteAt" IS NULL
                WHERE i."DeleteAt" IS NULL AND i."WarehouseId"=%s::uuid
                  AND i."ProductItemId"::text=ANY(%s)
                GROUP BY i."ProductItemId",p."Code",p."Name",w."Code" LIMIT 200''', (warehouse_id, ids))
            rows = _rows(cur)
    return {'source': 'wms_live', 'order_code': order_code, 'warehouse_id': warehouse_id,
            'scope': 'assigned order SKU and warehouse only', 'rows': rows, 'count': len(rows)}
