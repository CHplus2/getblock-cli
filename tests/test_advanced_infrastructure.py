import httpx
import pytest

from getblock.advanced_client import AdvancedGetBlockClient
from getblock.client import GetBlockAPIError


@pytest.mark.parametrize("status", [400, 401, 402, 404, 429, 500, 502, 503])
def test_advanced_errors(status):
    with httpx.Client(
        base_url="https://advanced.example.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"error": "test error"})),
    ) as transport:
        with pytest.raises(GetBlockAPIError) as error:
            AdvancedGetBlockClient(transport)._request("GET", "/v1/tron-energy/orders")
    assert error.value.status_code == status
    assert str(error.value) == "test error"


@pytest.mark.parametrize("payload,expected", [
    ({"error": "insufficient_balance", "have_cents": 0, "need_cents": 125},
     "insufficient_balance (have_cents=0, need_cents=125)"),
    ({"error": "insufficient_balance"}, "insufficient_balance"),
    ({}, "Insufficient prepaid balance."),
])
def test_insufficient_balance_details(payload, expected):
    with httpx.Client(
        base_url="https://advanced.example.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(402, json=payload)),
    ) as transport:
        with pytest.raises(GetBlockAPIError) as error:
            AdvancedGetBlockClient(transport)._request("POST", "/v1/tron-energy/delegate-energy")
    assert error.value.status_code == 402
    assert str(error.value) == expected


@pytest.mark.parametrize("status", [402, 500, 503])
def test_non_json_error_fallback(status):
    with httpx.Client(
        base_url="https://advanced.example.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="upstream unavailable")),
    ) as transport:
        with pytest.raises(GetBlockAPIError) as error:
            AdvancedGetBlockClient(transport)._request("GET", "/v1/tron-energy/orders")
    assert error.value.status_code == status
    assert "GetBlock" in str(error.value) or "balance" in str(error.value)


@pytest.mark.parametrize("exception,message", [
    (httpx.ReadTimeout, "Request to GetBlock timed out."),
    (httpx.ConnectError, "Unable to connect to GetBlock."),
])
def test_transport_errors_do_not_leak_details(exception, message):
    def handler(request):
        raise exception("secret-test-credential", request=request)

    with httpx.Client(
        base_url="https://advanced.example.test",
        transport=httpx.MockTransport(handler),
    ) as transport:
        with pytest.raises(GetBlockAPIError) as error:
            AdvancedGetBlockClient(transport).get_tron_orders()
    assert str(error.value) == message
    assert "secret-test-credential" not in str(error.value)


def test_public_client_keeps_host_and_bearer_auth(monkeypatch):
    from getblock.client import GetBlockClient

    original_client = httpx.Client

    def handler(request):
        assert str(request.url) == "https://public-api.getblock.io/api/v1/me"
        assert request.headers["Authorization"] == "Bearer fake-api-key"
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(200, json={"user_id": "test-user"})

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)
    client = GetBlockClient("fake-api-key")
    try:
        assert client.get_me() == {"user_id": "test-user"}
    finally:
        client.client.close()


def test_advanced_auth_does_not_guess_or_read_public_credentials(monkeypatch, capsys):
    import sys
    from getblock import cli

    def unexpected(*args, **kwargs):
        pytest.fail("Unconfirmed Advanced auth must not read credentials or create a transport")

    monkeypatch.setattr(cli, "get_api_key", unexpected)
    monkeypatch.setattr(httpx, "Client", unexpected)
    monkeypatch.setattr(sys, "argv", ["getblock", "tron-energy", "address-activation-estimate"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    assert "Advanced API authentication is not configured" in capsys.readouterr().err
