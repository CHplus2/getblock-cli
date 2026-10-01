import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_audit_wallet(advanced_client, status_code):
    expected = {'data': {}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/wallet-audit/audit'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'address': 'test-address'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.audit_wallet(**{'network': 'ETH', 'address': 'test-address'}) == expected



def test_cli_audit_wallet(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/wallet-audit/audit'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'address': 'test-address'}
        return httpx.Response(200, json={'data': {}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['wallet-audit', 'audit', '--network', 'ETH', '--address', 'test-address'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {}}" in result.output



@pytest.mark.parametrize("status_code", [200])
def test_check_wallet(advanced_client, status_code):
    expected = {'data': {}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/wallet-audit/check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'address': 'test-address'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.check_wallet(**{'network': 'ETH', 'address': 'test-address'}) == expected



def test_cli_check_wallet(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/wallet-audit/check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'address': 'test-address'}
        return httpx.Response(200, json={'data': {}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['wallet-audit', 'check', '--network', 'ETH', '--address', 'test-address'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {}}" in result.output
