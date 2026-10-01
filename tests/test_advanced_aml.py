import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_check_aml_wallet(advanced_client, status_code):
    expected = {'data': {'schemaVersion': '1.0', 'overallRiskScore': 0, 'test_nested_detail': {'items': [0, {'test_flag': False}]}}}

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
        return httpx.Response(200, json={'data': {'schemaVersion': '1.0', 'overallRiskScore': 0, 'test_nested_detail': {'items': [0, {'test_flag': False}]}}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['aml', 'wallet-check', '--address', 'test-address', '--network', 'ETH'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {'schemaVersion': '1.0', 'overallRiskScore': 0, 'test_nested_detail': {'items': [0, {'test_flag': False}]}}}" in result.output



@pytest.mark.parametrize("status_code", [200])
def test_check_aml_transaction(advanced_client, status_code):
    expected = {'data': {'riskScore': 0}}

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
        return httpx.Response(200, json={'data': {'riskScore': 0}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['aml', 'tx-check', '--tx', 'test-transaction', '--network', 'ETH'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {'riskScore': 0}}" in result.output
