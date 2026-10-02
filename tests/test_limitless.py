import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli
from getblock.client import GetBlockAPIError


def test_get_limitless_nodes_defaults(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'nodes': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_limitless_nodes() == expected


def test_get_limitless_nodes_filters(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'nodes': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless'
        assert dict(request.url.params) == {'limit': '150', 'offset': '0', 'protocol': 'ETH', 'network': 'mainnet', 'region': 'eu-central-1', 'status': 'ACTIVE'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_limitless_nodes(limit=150, offset=0, protocol='ETH', network='mainnet', region='eu-central-1', status='ACTIVE') == expected


def test_get_limitless_nodes_empty_filter_and_offset(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'nodes': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless'
        assert dict(request.url.params) == {'limit': '20', 'offset': '7', 'protocol': ''}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_limitless_nodes(offset=7, protocol='') == expected


def test_cli_get_limitless_nodes(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless'
        return httpx.Response(200, json={'total': 1, 'limit': 20, 'offset': 0, 'nodes': [{'id': 'abc123'}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['limitless', 'list', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'total': 1, 'limit': 20, 'offset': 0, 'nodes': [{'id': 'abc123'}]}


def test_get_limitless_node_defaults(mock_client):
    expected = {'id': 'abc123'}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless/abc123'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_limitless_node('abc123') == expected


def test_cli_get_limitless_node(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/limitless/abc123'
        return httpx.Response(200, json={'id': 'abc123'})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['limitless', 'get', 'abc123', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'id': 'abc123'}


def test_get_limitless_node_not_found(mock_client):
    def handler(request):
        return httpx.Response(404, json={"error": "Resource was not found."})

    client = mock_client(handler)
    with pytest.raises(GetBlockAPIError) as error:
        client.get_limitless_node('abc123')
    assert error.value.status_code == 404


def test_create_limitless_token_without_addon(mock_client):
    expected = {'id': 'abc123'}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/api/v1/limitless/abc123/tokens'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert json.loads(request.content) == {'api': 'json-rpc', 'addon': ''}
        return httpx.Response(201, json=expected)

    client = mock_client(handler)
    assert client.create_limitless_token('abc123', api='json-rpc') == expected


def test_create_limitless_token_with_addon(mock_client):
    expected = {'id': 'abc123'}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/api/v1/limitless/abc123/tokens'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert json.loads(request.content) == {'api': 'json-rpc', 'addon': 'debug'}
        return httpx.Response(201, json=expected)

    client = mock_client(handler)
    assert client.create_limitless_token('abc123', api='json-rpc', addon='debug') == expected


def test_cli_create_limitless_token(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/api/v1/limitless/abc123/tokens'
        return httpx.Response(201, json={'id': 'abc123'})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['limitless', 'tokens', 'create', 'abc123', '--api', 'json-rpc', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'id': 'abc123'}


def test_cli_create_limitless_token_requires_api(monkeypatch):
    def unexpected_client():
        pytest.fail("Invalid arguments must not create a client")

    monkeypatch.setattr(cli, "get_authenticated_client", unexpected_client)
    result = CliRunner().invoke(cli.app, ['limitless', 'tokens', 'create', 'abc123', '--json'])
    assert result.exit_code == 2


def test_create_limitless_token_not_found(mock_client):
    def handler(request):
        return httpx.Response(404, json={"error": "Resource was not found."})

    client = mock_client(handler)
    with pytest.raises(GetBlockAPIError) as error:
        client.create_limitless_token('abc123', api="json-rpc")
    assert error.value.status_code == 404
