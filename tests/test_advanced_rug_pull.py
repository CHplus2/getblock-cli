from advanced_payloads import RUG_PULL
import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200])
def test_check_rug_pull(advanced_client, status_code):
    expected = RUG_PULL

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/rug-pull/check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'contract_address': '0xtest-contract'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.check_rug_pull(**{'network': 'ETH', 'contract_address': '0xtest-contract'}) == expected



def test_cli_check_rug_pull(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/rug-pull/check'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'network': 'ETH', 'contract_address': '0xtest-contract'}
        return httpx.Response(200, json=RUG_PULL)

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['rug-pull', 'check', '--network', 'ETH', '--contract-address', '0xtest-contract', '--json', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert json.loads(result.stdout) == RUG_PULL
