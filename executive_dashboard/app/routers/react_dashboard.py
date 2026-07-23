"""React Dashboard API router — /api/react/*"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..auth import UserContext, require_page
from ..db import get_conn, put_conn
from ..react_logic import (
    b2b_payload,
    csat_by_store_payload,
    drill_down_payload,
    executive_summary_payload,
    inventory_by_category_payload,
    inventory_payload,
    order_list_payload,
    quality_payload,
    revenue_per_staff_payload,
    sales_marketing_payload,
    staff_revenue_payload,
    store_leaderboard_payload,
)

router = APIRouter(prefix="/api/react", tags=["react-dashboard"])


def _get_conn():
    """Dependency: get a PostgreSQL connection from pool, return after use."""
    conn = get_conn()
    try:
        yield conn
    finally:
        put_conn(conn)


def _parse_store_ids(store_id: str | None) -> list[str] | None:
    """Parse comma-separated store_id param into list."""
    if not store_id:
        return None
    return [s.strip() for s in store_id.split(",") if s.strip()]


@router.get("/executive-summary")
def get_executive_summary(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("executive-summary")),
    conn=Depends(_get_conn),
):
    """Executive summary scorecards, revenue trend, top products."""
    store_ids = _parse_store_ids(store_id)
    return executive_summary_payload(conn, start, end, store_ids)


@router.get("/sales-marketing")
def get_sales_marketing(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("sales-marketing")),
    conn=Depends(_get_conn),
):
    """Sales & marketing: daily trend, payment mix, customer segments."""
    store_ids = _parse_store_ids(store_id)
    return sales_marketing_payload(conn, start, end, store_ids)


@router.get("/quality-clv")
def get_quality_clv(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("quality-clv")),
    conn=Depends(_get_conn),
):
    """Quality & CLV: returns, RFM segments."""
    store_ids = _parse_store_ids(store_id)
    return quality_payload(conn, start, end, store_ids)


@router.get("/b2b-analytics")
def get_b2b_analytics(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("b2b-analytics")),
    conn=Depends(_get_conn),
):
    """B2B analytics: debt, top customers."""
    store_ids = _parse_store_ids(store_id)
    return b2b_payload(conn, start, end, store_ids)


@router.get("/store-leaderboard")
def get_store_leaderboard(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("store-leaderboard")),
    conn=Depends(_get_conn),
):
    """Store leaderboard: ranking by revenue, growth, efficiency."""
    store_ids = _parse_store_ids(store_id)
    return store_leaderboard_payload(conn, start, end, store_ids)


@router.get("/csat-by-store")
def get_csat_by_store(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("csat-by-store")),
    conn=Depends(_get_conn),
):
    """CSAT by store: customer satisfaction scores."""
    store_ids = _parse_store_ids(store_id)
    return csat_by_store_payload(conn, start, end, store_ids)


@router.get("/inventory")
def get_inventory(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("inventory")),
    conn=Depends(_get_conn),
):
    """Inventory analytics: category mix, top/bottom products, trends."""
    store_ids = _parse_store_ids(store_id)
    return inventory_payload(conn, start, end, store_ids)


@router.get("/revenue-per-staff")
def get_revenue_per_staff(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("revenue-per-staff")),
    conn=Depends(_get_conn),
):
    """Revenue per staff: productivity metrics by store."""
    store_ids = _parse_store_ids(store_id)
    return revenue_per_staff_payload(conn, start, end, store_ids)


@router.get("/drill-down/{metric_key}")
def get_drill_down(
    metric_key: str,
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    clicked_value: str | None = Query(None, description="Value clicked (date, name, segment)"),
    user: UserContext = Depends(require_page("executive-summary")),
    conn=Depends(_get_conn),
):
    """Generic drill-down: decompose any aggregated metric into detail rows."""
    store_ids = _parse_store_ids(store_id)
    return drill_down_payload(conn, metric_key, start, end, store_ids, clicked_value)


@router.get("/staff-revenue")
def get_staff_revenue(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("revenue-per-staff")),
    conn=Depends(_get_conn),
):
    """Staff revenue: breakdown by individual staff member."""
    store_ids = _parse_store_ids(store_id)
    return staff_revenue_payload(conn, start, end, store_ids)


@router.get("/order-list")
def get_order_list(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("executive-summary")),
    conn=Depends(_get_conn),
):
    """Order list: recent orders with staff, payment method, status."""
    store_ids = _parse_store_ids(store_id)
    return order_list_payload(conn, start, end, store_ids)


@router.get("/inventory-by-category")
def get_inventory_by_category(
    store_id: str | None = Query(None, description="Comma-separated store IDs"),
    user: UserContext = Depends(require_page("inventory")),
    conn=Depends(_get_conn),
):
    """Inventory grouped by product category."""
    store_ids = _parse_store_ids(store_id)
    return inventory_by_category_payload(conn, store_ids)


from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


@router.post("/chat")
def chat_with_ai(
    request: ChatRequest,
    user: UserContext = Depends(require_page("conversation")),
):
    """Chat with AI Assistant using MCP tools under the hood."""
    import sys
    from pathlib import Path
    root_dir = str(Path(__file__).resolve().parents[3])
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    from mcp_server.ai_chat import chat as ai_chat
    
    try:
        response = ai_chat(request.message, request.history)
        return {"ok": True, "response": response}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/chat/config")
def get_chat_config(
    user: UserContext = Depends(require_page("conversation")),
):
    """Return active AI config settings (provider & model)."""
    import sys
    from pathlib import Path
    root_dir = str(Path(__file__).resolve().parents[3])
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    from mcp_server.config import AI_PROVIDER, AI_MODEL
    return {
        "ok": True,
        "provider": AI_PROVIDER,
        "model": AI_MODEL,
    }

