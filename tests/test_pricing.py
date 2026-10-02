import json
import httpx
from typer.testing import CliRunner

from getblock import cli


def test_get_pricing_defaults(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'plans': [{'id': 'pro', 'currency': 'USD', 'periods': [{'period': '12m', 'base': 5988, 'first_payment': 4790, 'renewal': 4790}]}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/pricing'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_pricing() == expected


def test_get_pricing_filters(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'plans': [{'id': 'pro', 'currency': 'USD', 'periods': [{'period': '12m', 'base': 5988, 'first_payment': 4790, 'renewal': 4790}]}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/pricing'
        assert dict(request.url.params) == {'limit': '150', 'offset': '0', 'search': 'Ethereum'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_pricing(limit=150, offset=0, search='Ethereum') == expected


def test_get_pricing_empty_filter_and_offset(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'plans': [{'id': 'pro', 'currency': 'USD', 'periods': [{'period': '12m', 'base': 5988, 'first_payment': 4790, 'renewal': 4790}]}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/pricing'
        assert dict(request.url.params) == {'limit': '20', 'offset': '7', 'search': ''}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_pricing(offset=7, search='') == expected


def test_cli_get_pricing(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/pricing'
        return httpx.Response(200, json={'total': 1, 'limit': 20, 'offset': 0, 'plans': [{'id': 'pro', 'currency': 'USD', 'periods': [{'period': '12m', 'base': 5988, 'first_payment': 4790, 'renewal': 4790}]}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['pricing', 'list', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'total': 1, 'limit': 20, 'offset': 0, 'plans': [{'id': 'pro', 'currency': 'USD', 'periods': [{'period': '12m', 'base': 5988, 'first_payment': 4790, 'renewal': 4790}]}]}
