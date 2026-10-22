from mcp_server import portal_read_api


def test_product_industry_joins_dashboard_amounts_to_authoritative_categories(monkeypatch):
    pages = {
        1: {
            'meta': {'pageCount': 2},
            'data': [
                {'id': 'frame', 'productCategory': {'code': 'GONG', 'name': 'Gọng kính'}},
                {'id': 'lens', 'productCategory': {'code': 'BLUECUT', 'name': 'BLUECUT'}},
            ],
        },
        2: {
            'meta': {'pageCount': 2},
            'data': [{'id': 'accessory', 'productCategory': {'code': 'PK', 'name': 'Phụ kiện'}}],
        },
    }
    monkeypatch.setattr(portal_read_api, 'query_portal_list', lambda resource, page, size: pages[page])
    monkeypatch.setattr(
        'mcp_server.dashboard_api.query_dashboard_metric',
        lambda *args, **kwargs: {
            'ok': True,
            'data': {'data': {'items': [
                {'productId': 'frame', 'totalAmount': 100},
                {'productId': 'lens', 'totalAmount': 80},
                {'productId': 'accessory', 'totalAmount': 10},
                {'productId': 'missing-category', 'totalAmount': 5},
            ]}},
        },
    )

    result = portal_read_api.query_product_industry_sales_api('2026-10-01', '2026-10-21')

    assert result['frames_dd'] == {'revenue': 100, 'products': 1}
    assert result['lenses_dt'] == {'revenue': 80, 'products': 1}
    assert result['other_categorized'] == {'revenue': 10, 'products': 1}
    assert result['unclassified'] == {'revenue': 5, 'products': 1}
    assert result['dashboard_total_revenue'] == 195
    assert result['sql_fallback'] is False


def test_product_industry_does_not_guess_category_from_product_name(monkeypatch):
    monkeypatch.setattr(
        portal_read_api,
        'query_portal_list',
        lambda resource, page, size: {'meta': {'pageCount': 1}, 'data': [{'id': 'frame', 'productCategory': None}]},
    )
    monkeypatch.setattr(
        'mcp_server.dashboard_api.query_dashboard_metric',
        lambda *args, **kwargs: {
            'ok': True,
            'data': {'data': {'items': [{'productId': 'frame', 'productName': 'GỌNG KÍNH', 'totalAmount': 100}]}},
        },
    )

    result = portal_read_api.query_product_industry_sales_api('2026-10-01', '2026-10-21')

    assert result['frames_dd']['revenue'] == 0
    assert result['unclassified'] == {'revenue': 100, 'products': 1}
