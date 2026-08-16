from mcp_server import tools


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None
        self.closed = False

    def execute(self, query, params):
        self.query = query
        self.params = params
        return _FakeCursor(self.rows)

    def close(self):
        self.closed = True


def test_query_products_limits_in_database_and_preserves_rankings(monkeypatch):
    rows = [
        ("quantity", 1, "product-1", "sku-1", "Product one", "Frames", "SKU one", 200, 8, 1000),
        ("revenue", 1, "product-2", None, "Product two", "Lenses", "Product two", 600, 3, 1000),
        ("revenue", 2, "product-1", None, "Product one", "Frames", "Product one", 400, 7, 1000),
    ]
    connection = _FakeConnection(rows)
    monkeypatch.setattr(tools, "_get_pos_conn", lambda: connection)

    result = tools.query_products("2026-08-01", "2026-08-07", top_n=5)

    assert "GROUPING SETS" in connection.query
    assert "ROW_NUMBER()" in connection.query
    assert "WHERE ranked.rank <= %s" in connection.query
    assert connection.params == ["2026-08-01", "2026-08-07", 5]
    assert connection.closed is True
    assert result["top_by_revenue"] == [
        {
            "product_id": "product-2",
            "name": "Product two",
            "category": "Lenses",
            "revenue": 600.0,
            "units_sold": 3.0,
            "share_pct": 60.0,
        },
        {
            "product_id": "product-1",
            "name": "Product one",
            "category": "Frames",
            "revenue": 400.0,
            "units_sold": 7.0,
            "share_pct": 40.0,
        },
    ]
    assert result["top_by_quantity"] == [
        {
            "product_item_id": "sku-1",
            "name": "SKU one",
            "category": "Frames",
            "units_sold": 8.0,
            "revenue": 200.0,
        }
    ]
