from advanced_payloads import AML_ADDRESS, AML_TRANSACTION
import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_check_aml_wallet(advanced_client, status_code):
    expected = AML_ADDRESS

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/aml/wallet-check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'address': 'test-address', 'network': 'ETH'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.check_aml_wallet(**{'address': 'test-address', 'network': 'ETH'}) == expected



def test_cli_check_aml_wallet(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/aml/wallet-check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'address': 'test-address', 'network': 'ETH'}
        return httpx.Response(200, json=AML_ADDRESS)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['aml', 'wallet-check', '--address', 'test-address', '--network', 'ETH', '--json', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == AML_ADDRESS



@pytest.mark.parametrize("status_code", [200])
def test_check_aml_transaction(advanced_client, status_code):
    expected = AML_TRANSACTION

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/aml/tx-check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'tx': 'test-transaction', 'network': 'ETH'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.check_aml_transaction(**{'tx': 'test-transaction', 'network': 'ETH'}) == expected



def test_cli_check_aml_transaction(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/aml/tx-check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'tx': 'test-transaction', 'network': 'ETH'}
        return httpx.Response(200, json=AML_TRANSACTION)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['aml', 'tx-check', '--tx', 'test-transaction', '--network', 'ETH', '--json', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == AML_TRANSACTION
