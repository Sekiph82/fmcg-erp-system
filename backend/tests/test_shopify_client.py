"""Shopify Admin API client against a mocked transport (no network, no real store)."""
import json

import httpx
import pytest

from app.services.shopify_service import ShopifyClient, ShopifyError

BASE = "https://synthetic-store.myshopify.com/admin/api/2024-10"


def make_order(n, **kw):
    return {"id": 1000 + n, "name": f"#{n}", "created_at": "2026-11-10T08:00:00Z", "currency": "KES",
            "financial_status": "paid", "cancelled_at": None,
            "line_items": [{"id": 1, "sku": "SKU-1", "quantity": 2, "price": "150.00", "total_discount": "0.00",
                            "tax_lines": [{"rate": 0.16}]}], **kw}


def transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_orders_follow_page_info_links_and_send_token():
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        assert request.headers["X-Shopify-Access-Token"] == "shpat_synthetic"
        if "page_info" not in str(request.url):
            assert request.url.params["status"] == "any" and request.url.params["limit"] == "250"
            return httpx.Response(200, json={"orders": [make_order(1)]},
                                  headers={"Link": f'<{BASE}/orders.json?page_info=abc&limit=250>; rel="next"'})
        return httpx.Response(200, json={"orders": [make_order(2)]})

    client = ShopifyClient("synthetic-store.myshopify.com", "shpat_synthetic", "2024-10", transport(handler))
    orders = await client.orders(None)
    await client.aclose()
    assert [o["name"] for o in orders] == ["#1", "#2"] and len(seen) == 2


@pytest.mark.asyncio
async def test_throttling_is_retried_and_errors_are_reported(monkeypatch):
    import app.services.shopify_service as svc

    async def no_sleep(_):
        return None

    monkeypatch.setattr(svc.asyncio, "sleep", no_sleep)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        if request.method == "POST":
            return httpx.Response(422, json={"errors": "inventory item not stocked at location"})
        return httpx.Response(200, json={"products": [{"id": 1, "variants": [{"id": 11, "sku": "SKU-1", "inventory_item_id": 99}]}]})

    client = ShopifyClient("synthetic-store.myshopify.com", "t", "2024-10", transport(handler))
    assert (await client.variants())[0]["inventory_item_id"] == 99 and calls["n"] == 2
    with pytest.raises(ShopifyError, match="422"):
        await client.set_available("123", 99, 5)
    await client.aclose()


@pytest.mark.parametrize("domain", ["evil.com", "store.myshopify.com.evil.com", "169.254.169.254", "", "a/b.myshopify.com"])
def test_only_myshopify_domains_are_accepted(domain):
    with pytest.raises(ShopifyError, match="myshopify.com"):
        ShopifyClient(domain, "t", "2024-10")


@pytest.mark.asyncio
async def test_pagination_link_to_another_host_is_refused():
    def handler(request):
        return httpx.Response(200, json={"orders": []}, headers={"Link": '<https://evil.example/x>; rel="next"'})

    client = ShopifyClient("synthetic-store.myshopify.com", "t", "2024-10", transport(handler))
    with pytest.raises(ShopifyError, match="pagination host"):
        await client.orders(None)
    await client.aclose()


@pytest.mark.asyncio
async def test_inventory_set_payload():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"inventory_level": {}})

    client = ShopifyClient("synthetic-store.myshopify.com", "t", "2024-10", transport(handler))
    await client.set_available("123", 99, 7)
    await client.aclose()
    assert bodies == [{"location_id": 123, "inventory_item_id": 99, "available": 7}]
