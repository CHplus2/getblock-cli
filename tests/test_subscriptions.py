import json
import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli
from getblock.client import GetBlockAPIError


def test_get_subscription_defaults(mock_client):
    expected = {'has_plan': False, 'plan': None}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscription'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_subscription() == expected


def test_cli_get_subscription(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscription'
        return httpx.Response(200, json={'has_plan': False, 'plan': None})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['subscription', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'has_plan': False, 'plan': None}


def test_get_subscriptions_defaults(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'subscriptions': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_subscriptions() == expected


def test_get_subscriptions_filters(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'subscriptions': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions'
        assert dict(request.url.params) == {'limit': '150', 'offset': '0', 'product_type': 'enterprise_plan', 'status': 'ACTIVE'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_subscriptions(limit=150, offset=0, product_type='enterprise_plan', status='ACTIVE') == expected


def test_get_subscriptions_empty_filter_and_offset(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'subscriptions': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions'
        assert dict(request.url.params) == {'limit': '20', 'offset': '7', 'product_type': ''}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_subscriptions(offset=7, product_type='') == expected


def test_cli_get_subscriptions(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions'
        return httpx.Response(200, json={'total': 1, 'limit': 20, 'offset': 0, 'subscriptions': [{'id': 'abc123'}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['subscriptions', 'list', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'total': 1, 'limit': 20, 'offset': 0, 'subscriptions': [{'id': 'abc123'}]}


def test_get_subscription_by_id_defaults(mock_client):
    expected = {'id': 'abc123'}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions/abc123'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_subscription_by_id('abc123') == expected


def test_cli_get_subscription_by_id(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/subscriptions/abc123'
        return httpx.Response(200, json={'id': 'abc123'})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['subscriptions', 'get', 'abc123', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'id': 'abc123'}


def test_get_subscription_by_id_not_found(mock_client):
    def handler(request):
        return httpx.Response(404, json={"error": "Resource was not found."})

    client = mock_client(handler)
    with pytest.raises(GetBlockAPIError) as error:
        client.get_subscription_by_id('abc123')
    assert error.value.status_code == 404


def test_get_subscription_with_plan(mock_client):
    expected = {
        "has_plan": True,
        "plan": {
            "id": "pro",
            "name": "Pro",
            "status": "active",
            "period": "1m",
            "type": "regular",
            "limits": {
                "rps": 800,
                "cu_amount": 1000000000,
                "max_tokens": 150,
                "cu_replenishment": "monthly",
            },
            "started_at": "2025-09-13T10:20:06Z",
            "paid_until": "2026-09-01T00:00:00Z",
            "current_period_end": "2026-09-01T00:00:00Z",
        },
    }

    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/subscription"
        assert not request.url.query
        return httpx.Response(200, json=expected)

    assert mock_client(handler).get_subscription() == expected
