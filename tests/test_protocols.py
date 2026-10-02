import json
import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli
from getblock.client import GetBlockAPIError


def test_get_protocols_defaults(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'protocols': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_protocols() == expected


def test_get_protocols_filters(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'protocols': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols'
        assert dict(request.url.params) == {'limit': '150', 'offset': '0', 'search': 'Ethereum'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_protocols(limit=150, offset=0, search='Ethereum') == expected


def test_get_protocols_empty_filter_and_offset(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'protocols': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols'
        assert dict(request.url.params) == {'limit': '20', 'offset': '7', 'search': ''}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_protocols(offset=7, search='') == expected


def test_cli_get_protocols(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols'
        return httpx.Response(200, json={'total': 1, 'limit': 20, 'offset': 0, 'protocols': [{'id': 'abc123'}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['protocols', 'list', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'total': 1, 'limit': 20, 'offset': 0, 'protocols': [{'id': 'abc123'}]}


def test_get_protocol_defaults(mock_client):
    expected = {'id': 'eth', 'name': 'Ethereum', 'based_on': '', 'networks': [{'id': 'mainnet', 'paid_regions': [], 'modes': [{'id': 'full', 'apis': [{'id': 'json-rpc', 'regions': ['eu-central-1']}], 'addons': []}]}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols/abc123'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_protocol('abc123') == expected


def test_cli_get_protocol(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/protocols/abc123'
        return httpx.Response(200, json={'id': 'eth', 'name': 'Ethereum', 'based_on': '', 'networks': [{'id': 'mainnet', 'paid_regions': [], 'modes': [{'id': 'full', 'apis': [{'id': 'json-rpc', 'regions': ['eu-central-1']}], 'addons': []}]}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['protocols', 'get', 'abc123', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'id': 'eth', 'name': 'Ethereum', 'based_on': '', 'networks': [{'id': 'mainnet', 'paid_regions': [], 'modes': [{'id': 'full', 'apis': [{'id': 'json-rpc', 'regions': ['eu-central-1']}], 'addons': []}]}]}


def test_get_protocol_not_found(mock_client):
    def handler(request):
        return httpx.Response(404, json={"error": "Resource was not found."})

    client = mock_client(handler)
    with pytest.raises(GetBlockAPIError) as error:
        client.get_protocol('abc123')
    assert error.value.status_code == 404
