from advanced_payloads import ORDER
import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_get_tron_orders(advanced_client, status_code):
    expected = {'data': [], 'total': 0}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/orders'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0', 'status': 'pending', 'resource_type': 'energy'}
        assert request.content == b""
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.get_tron_orders(**{'limit': 20, 'offset': 0, 'status': 'pending', 'resource_type': 'energy'}) == expected



def test_cli_get_tron_orders(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/orders'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0', 'status': 'pending', 'resource_type': 'energy'}
        return httpx.Response(200, json={'data': [], 'total': 0})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'orders', 'list', '--limit', '20', '--offset', '0', '--status', 'pending', '--resource-type', 'energy', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == {'data': [], 'total': 0}



@pytest.mark.parametrize("status_code", [200])
def test_get_tron_order(advanced_client, status_code):
    expected = ORDER

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/orders/44a33415-21f6-45a9-b529-91e6503f6c1b'
        assert dict(request.url.params) == {}
        assert request.content == b""
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.get_tron_order(**{'order_id': '44a33415-21f6-45a9-b529-91e6503f6c1b'}) == expected



def test_cli_get_tron_order(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/orders/44a33415-21f6-45a9-b529-91e6503f6c1b'
        assert dict(request.url.params) == {}
        return httpx.Response(200, json=ORDER)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'orders', 'get', '44a33415-21f6-45a9-b529-91e6503f6c1b', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == ORDER


def test_orders_defaults_preserve_zero_offset(advanced_client):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/v1/tron-energy/orders"
        assert dict(request.url.params) == {"limit": "20", "offset": "0"}
        return httpx.Response(200, json={"data": [], "total": 0})

    assert advanced_client(handler).get_tron_orders() == {"data": [], "total": 0}


def test_orders_nonzero_offset_and_empty_filter(advanced_client):
    def handler(request):
        assert dict(request.url.params) == {"limit": "100", "offset": "7", "status": "", "resource_type": "bandwidth"}
        return httpx.Response(200, json={"data": [], "total": 0})

    advanced_client(handler).get_tron_orders(limit=100, offset=7, status="", resource_type="bandwidth")
