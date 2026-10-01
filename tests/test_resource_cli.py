import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli


LIST_FILTERS = [
    ("dedicated", {"protocol": "ETH", "network": "mainnet", "region": "eu-central-1", "status": "ACTIVE"}),
    ("limitless", {"protocol": "ETH", "network": "mainnet", "region": "ap-southeast-1", "status": "ACTIVE"}),
    ("subscriptions", {"product_type": "request_package", "status": "active"}),
    ("protocols", {"search": "Ethereum"}),
    ("addons", {"search": "MEV", "protocol": "eth"}),
    ("pricing", {"search": "Pro"}),
]


@pytest.mark.parametrize("resource,filters", LIST_FILTERS)
def test_list_cli_forwards_options(mock_client, resource, filters):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/{resource}"
        assert dict(request.url.params) == {"limit": "11", "offset": "3", **filters}
        return httpx.Response(200, json={})

    mock_client(handler)
    args = [resource, "list", "--limit", "11", "--offset", "3"]
    for key, value in filters.items():
        args.extend(["--" + key.replace("_", "-"), value])
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    assert len(calls) == 1


@pytest.mark.parametrize("resource,api", [("dedicated", "jsonrpc"), ("limitless", "json-rpc")])
def test_node_token_cli_forwards_only_api_addon(mock_client, resource, api):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/{resource}/abc123/tokens"
        assert not request.url.query
        assert json.loads(request.content) == {"api": api, "addon": "debug"}
        return httpx.Response(201, json={"id": "test-token"})

    mock_client(handler)
    result = CliRunner().invoke(
        cli.app, [resource, "tokens", "create", "abc123", "--api", api, "--addon", "debug"]
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1


@pytest.mark.parametrize("args", [
    ["dedicated", "list"],
    ["dedicated", "get", "abc123"],
    ["dedicated", "tokens", "create", "abc123", "--api", "jsonrpc"],
    ["limitless", "list"],
    ["limitless", "get", "abc123"],
    ["limitless", "tokens", "create", "abc123", "--api", "json-rpc"],
    ["subscription"],
    ["subscriptions", "list"],
    ["subscriptions", "get", "s-plan"],
    ["protocols", "list"],
    ["protocols", "get", "eth"],
    ["addons", "list"],
    ["pricing", "list"],
    ["balance"],
])
def test_new_commands_require_authentication(monkeypatch, args):
    monkeypatch.setattr(cli, "get_api_key", lambda: None)

    def unexpected_client(*args, **kwargs):
        pytest.fail("Unauthenticated commands must not create a client")

    monkeypatch.setattr(cli, "GetBlockClient", unexpected_client)
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 1
    assert "getblock auth login" in result.output
