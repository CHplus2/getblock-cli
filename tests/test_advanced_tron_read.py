from advanced_payloads import ADDRESS_STATUS, ACTIVATION_ESTIMATE
import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_estimate_tron_price(advanced_client, status_code):
    expected = {'data': {'price_sun': '1000000', 'trx': '1', 'price_usd': '0.1', 'reserve_usd': '0.2', 'quote_token': 'test-quote'}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/price-estimate'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'resourceType': 'energy', 'volume': 1, 'duration': 'test-duration'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.estimate_tron_price(**{'resource_type': 'energy', 'volume': 1, 'duration': 'test-duration'}) == expected



def test_cli_estimate_tron_price(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/price-estimate'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'resourceType': 'energy', 'volume': 1, 'duration': 'test-duration'}
        return httpx.Response(200, json={'data': {'price_sun': '1000000', 'trx': '1', 'price_usd': '0.1', 'reserve_usd': '0.2', 'quote_token': 'test-quote'}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'price-estimate', '--resource-type', 'energy', '--volume', '1', '--duration', 'test-duration', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == {'data': {'price_sun': '1000000', 'trx': '1', 'price_usd': '0.1', 'reserve_usd': '0.2', 'quote_token': 'test-quote'}}



@pytest.mark.parametrize("status_code", [200])
def test_get_tron_address_status(advanced_client, status_code):
    expected = ADDRESS_STATUS

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/address-status'
        assert dict(request.url.params) == {'address': 'test-address'}
        assert request.content == b""
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.get_tron_address_status(**{'address': 'test-address'}) == expected



def test_cli_get_tron_address_status(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/address-status'
        assert dict(request.url.params) == {'address': 'test-address'}
        return httpx.Response(200, json=ADDRESS_STATUS)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'address-status', 'test-address', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == ADDRESS_STATUS



@pytest.mark.parametrize("status_code", [200])
def test_estimate_tron_address_activation(advanced_client, status_code):
    expected = ACTIVATION_ESTIMATE

    def handler(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/address-activation-estimate'
        assert dict(request.url.params) == {}
        assert request.content == b""
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.estimate_tron_address_activation(**{}) == expected



def test_cli_estimate_tron_address_activation(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'GET'
        assert request.url.path == '/v1/tron-energy/address-activation-estimate'
        assert dict(request.url.params) == {}
        return httpx.Response(200, json=ACTIVATION_ESTIMATE)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'address-activation-estimate', '--json'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == ACTIVATION_ESTIMATE
