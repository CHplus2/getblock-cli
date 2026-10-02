import json
import httpx
from typer.testing import CliRunner

from getblock import cli


def test_get_balance_defaults(mock_client):
    expected = {'cu': {'total_balance': 0, 'main_balance': 0, 'extra_balance': 0}, 'credits': {'balance_cents': 10000}}

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/balance'
        assert dict(request.url.params) == {}
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.content == b""
        return httpx.Response(200, json=expected)

    client = mock_client(handler)
    assert client.get_balance() == expected


def test_cli_get_balance(mock_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/api/v1/balance'
        return httpx.Response(200, json={'cu': {'total_balance': 0, 'main_balance': 0, 'extra_balance': 0}, 'credits': {'balance_cents': 10000}})

    mock_client(handler)
    result = CliRunner().invoke(cli.app, ['balance', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "fake-api-key" not in result.output
    assert json.loads(result.stdout) == {'cu': {'total_balance': 0, 'main_balance': 0, 'extra_balance': 0}, 'credits': {'balance_cents': 10000}}
