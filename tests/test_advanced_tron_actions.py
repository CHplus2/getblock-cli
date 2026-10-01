import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli



@pytest.mark.parametrize("status_code", [200, 202])
def test_delegate_tron_energy(advanced_client, status_code):
    expected = {'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/delegate-energy'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.delegate_tron_energy(**{'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}) == expected



def test_cli_delegate_tron_energy(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/delegate-energy'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}
        return httpx.Response(200, json={'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'delegate-energy', '--target-address', 'test-address', '--volume', '1', '--duration', 'test-duration', '--quote-token', 'test-quote', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}}" in result.output



@pytest.mark.parametrize("status_code", [200, 202])
def test_delegate_tron_bandwidth(advanced_client, status_code):
    expected = {'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/delegate-bandwidth'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.delegate_tron_bandwidth(**{'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}) == expected



def test_cli_delegate_tron_bandwidth(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/delegate-bandwidth'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address', 'volume': 1, 'duration': 'test-duration', 'quote_token': 'test-quote'}
        return httpx.Response(200, json={'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'delegate-bandwidth', '--target-address', 'test-address', '--volume', '1', '--duration', 'test-duration', '--quote-token', 'test-quote', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {'orderId': '44a33415-21f6-45a9-b529-91e6503f6c1b'}}" in result.output



@pytest.mark.parametrize("status_code", [200])
def test_activate_tron_address(advanced_client, status_code):
    expected = {'data': {'status': 'activated', 'target_address': 'test-address', 'price_trx': '1', 'price_usd': '0.1'}}

    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/address-activate'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address'}
        return httpx.Response(status_code, json=expected)

    client = advanced_client(handler)
    assert client.activate_tron_address(**{'target_address': 'test-address'}) == expected



def test_cli_activate_tron_address(advanced_client):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/tron-energy/address-activate'
        assert dict(request.url.params) == {}
        assert json.loads(request.content) == {'target_address': 'test-address'}
        return httpx.Response(200, json={'data': {'status': 'activated', 'target_address': 'test-address', 'price_trx': '1', 'price_usd': '0.1'}})

    advanced_client(handler)
    result = CliRunner().invoke(cli.app, ['tron-energy', 'address-activate', 'test-address', '--yes'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "{'data': {'status': 'activated', 'target_address': 'test-address', 'price_trx': '1', 'price_usd': '0.1'}}" in result.output


ACTION_ARGS = [
    ["tron-energy", "delegate-energy", "--target-address", "test-address", "--volume", "1", "--duration", "test-duration", "--quote-token", "test-quote"],
    ["tron-energy", "delegate-bandwidth", "--target-address", "test-address", "--volume", "1", "--duration", "test-duration", "--quote-token", "test-quote"],
    ["tron-energy", "address-activate", "test-address"],
]


@pytest.mark.parametrize("args", ACTION_ARGS)
@pytest.mark.parametrize("answer", ["n\n", "\n", ""])
def test_declined_or_unavailable_confirmation_makes_no_request(monkeypatch, args, answer):
    def unexpected_client():
        pytest.fail("Cancelled actions must not obtain a client")

    monkeypatch.setattr(cli, "get_authenticated_advanced_client", unexpected_client)
    result = CliRunner().invoke(cli.app, args, input=answer)
    assert result.exit_code == (1 if answer == "" else 0)
    assert "may consume prepaid balance" in result.output
    assert "test-quote" not in result.output


@pytest.mark.parametrize("args", ACTION_ARGS)
@pytest.mark.parametrize("confirmation", ["interactive", "--yes", "-y"])
def test_confirmed_action_sends_one_request(advanced_client, args, confirmation):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": {}})

    advanced_client(handler)
    result = CliRunner().invoke(
        cli.app,
        args + ([] if confirmation == "interactive" else [confirmation]),
        input="y\n" if confirmation == "interactive" else "",
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert ("may consume prepaid balance" in result.output) == (confirmation == "interactive")
    assert "test-quote" not in result.output


def test_cli_reports_insufficient_balance(advanced_client, monkeypatch, capsys):
    import sys

    def handler(request):
        return httpx.Response(402, json={
            "error": "insufficient_balance", "have_cents": 0, "need_cents": 125,
        })

    advanced_client(handler)
    monkeypatch.setattr(sys, "argv", ["getblock", *ACTION_ARGS[0], "--yes"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    output = capsys.readouterr().err
    assert "insufficient_balance" in output
    assert "have_cents=0" in output
    assert "need_cents=125" in output
    assert "test-quote" not in output
