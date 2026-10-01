import httpx
from typer.testing import CliRunner

from getblock import cli


def test_get_addons_defaults(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'addons': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/addons'
        assert dict(request.url.params) == {'limit': '20', 'offset': '0'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_addons() == expected


def test_get_addons_filters(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'addons': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/addons'
        assert dict(request.url.params) == {'limit': '150', 'offset': '0', 'search': 'Ethereum', 'protocol': 'ETH'}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_addons(limit=150, offset=0, search='Ethereum', protocol='ETH') == expected


def test_get_addons_empty_filter_and_offset(mock_client):
    expected = {'total': 1, 'limit': 20, 'offset': 0, 'addons': [{'id': 'abc123'}]}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/addons'
        assert dict(request.url.params) == {'limit': '20', 'offset': '7', 'search': ''}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_addons(offset=7, search='') == expected


def test_cli_get_addons(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/addons'
        return httpx.Response(200, json={'total': 1, 'limit': 20, 'offset': 0, 'addons': [{'id': 'abc123'}]})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['addons', 'list'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert "{'total': 1, 'limit': 20, 'offset': 0, 'addons': [{'id': 'abc123'}]}" in result.output
