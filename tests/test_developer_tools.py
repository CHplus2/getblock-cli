import json
import subprocess
import httpx
import pytest
from typer.testing import CliRunner
from getblock import cli, ux, auth


def run(args, **kwargs):
    return CliRunner().invoke(cli.app, args, **kwargs)


def test_advanced_environment_transport_and_cleanup(monkeypatch):
    original = httpx.Client
    clients = []
    monkeypatch.setenv("GETBLOCK_API_KEY", "public-secret")
    monkeypatch.setenv("GETBLOCK_ADVANCED_API_KEY", "advanced-secret")
    monkeypatch.setattr(cli, "get_api_key", lambda *args: pytest.fail("No Public key access"))
    monkeypatch.setattr(cli, "get_advanced_api_key", lambda *args: pytest.fail("Environment takes precedence"))
    def handler(request):
        assert str(request.url) == "https://services.getblock.io/v1/tron-energy/orders?limit=1&offset=0"
        assert request.headers["authorization"] == "Bearer advanced-secret"
        return httpx.Response(200, json={"data": []})
    def factory(**kwargs):
        assert kwargs["follow_redirects"] is False
        client = original(**kwargs, transport=httpx.MockTransport(handler))
        clients.append(client)
        return client
    monkeypatch.setattr(httpx, "Client", factory)
    result = run(["auth", "status", "--api", "advanced", "--check", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["verified"] is True
    assert "secret" not in result.output
    assert clients and all(client.is_closed for client in clients)


def test_advanced_no_public_fallback(monkeypatch):
    monkeypatch.setenv("GETBLOCK_API_KEY", "public-secret")
    result = run(["tron-energy", "orders", "list", "--json"])
    assert result.exit_code == 4
    assert "GETBLOCK_ADVANCED_API_KEY" in result.stderr
    assert "public-secret" not in result.output


def test_advanced_profile_keyring_is_separate(monkeypatch):
    calls = []
    monkeypatch.setattr(auth.keyring, "set_password", lambda *args: calls.append(args))
    result = run(["--profile", "production", "auth", "login", "--api", "advanced", "--with-key", "--json"], input="advanced-secret\n")
    assert result.exit_code == 0, result.output
    assert calls == [("getblock-cli", "getblock_advanced_api_key:production", "advanced-secret")]
    assert not json.loads(result.stdout)["verified"]
    assert "advanced-secret" not in result.output


def test_advanced_logout_only_advanced(monkeypatch):
    calls = []
    monkeypatch.setattr(auth.keyring, "delete_password", lambda *args: calls.append(args))
    monkeypatch.setenv("GETBLOCK_ADVANCED_API_KEY", "still-active")
    result = run(["auth", "logout", "--api", "advanced", "--json"])
    assert result.exit_code == 0
    assert calls == [("getblock-cli", "getblock_advanced_api_key")]
    assert json.loads(result.stdout)["environment_active"]


def test_advanced_preview_has_confirmed_host_without_credentials(monkeypatch):
    monkeypatch.setattr(cli, "get_advanced_api_key", lambda *args: pytest.fail("Offline"))
    result = run(["auth", "status", "--api", "advanced", "--check", "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["base_url"] == "https://services.getblock.io"
    assert data["path"] == "/v1/tron-energy/orders"


def test_doctor_offline_and_missing_advanced(monkeypatch):
    monkeypatch.setenv("GETBLOCK_API_KEY", "public-secret")
    result = run(["doctor", "--api", "both", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert not data["network_checked"]
    assert data["checks"][1]["source"] == "environment"
    assert "auth login --api advanced" in data["checks"][2]["hint"]
    assert "public-secret" not in result.output


def test_doctor_network_read_only(mock_client):
    paths = []
    def handler(request):
        paths.append((request.method, request.url.path))
        return httpx.Response(200, json={"user_id": "U"})
    mock_client(handler)
    result = run(["doctor", "--check-network", "--json"])
    assert result.exit_code == 0, result.output
    assert paths == [("GET", "/api/v1/me")]
    assert json.loads(result.stdout)["ok"]


def test_doctor_handles_broken_config(monkeypatch, artifact_dir):
    monkeypatch.setenv("GETBLOCK_CONFIG_DIR", str(artifact_dir))
    (artifact_dir / "config.json").write_text("broken", encoding="utf-8")
    monkeypatch.setenv("GETBLOCK_API_KEY", "secret")
    result = run(["doctor", "--json"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["checks"][0]["status"] == "failed"


@pytest.mark.parametrize("args", [
    ["webhooks", "create"], ["address-lists", "create"],
    ["tokens", "create"], ["aml", "tx-check"],
    ["address-lists", "entries", "replace", "list1"],
])
def test_generate_input_offline(args):
    result = run(args + ["--generate-input"])
    assert result.exit_code == 0, result.output
    assert isinstance(json.loads(result.stdout), dict)


@pytest.mark.parametrize("args,payload", [
    (["webhooks", "create"], {"chain": "eth", "trigger_type": "address_activity", "phases": ["confirmed"], "target_url": "https://example.invalid"}),
    (["aml", "tx-check"], {"network": "eth", "tx": "T"}),
    (["address-lists", "entries", "replace", "list1"], {"addresses": []}),
    (["endpoints", "request", "--token-id", "T"], {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}),
])
def test_validate_only_offline(args, payload):
    result = run(args + ["--input", "-", "--validate-only", "--json"], input=json.dumps(payload))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"valid": True, "scope": "local request structure only", "server_validated": False}


def test_validate_rejects_bad_input():
    result = run(["aml", "tx-check", "--input", "-", "--validate-only", "--json"], input='{"tx":4,"network":"eth"}')
    assert result.exit_code == 2
    assert result.stdout == ""


def test_jq_missing_fails_before_request(monkeypatch):
    monkeypatch.setattr("getblock.json_query.shutil.which", lambda _: None)
    result = run(["tokens", "delete", "T", "--yes", "--json", "--jq", "."])
    assert result.exit_code == 2
    assert "requires jq" in result.stderr


def test_jq_invokes_engine_without_shell(monkeypatch, mock_client):
    calls = []
    monkeypatch.setattr("getblock.json_query.shutil.which", lambda _: "/tools/jq")
    def execute(args, **kwargs):
        assert "shell" not in kwargs
        assert kwargs["timeout"] == 30
        calls.append((args, kwargs["input"]))
        return subprocess.CompletedProcess(args, 0, '"T"\n' if len(calls) == 2 else "null\n", "")
    monkeypatch.setattr("getblock.json_query.subprocess.run", execute)
    mock_client(lambda request: httpx.Response(200, json={"tokens": [{"id": "T"}]}))
    result = run(["tokens", "list", "--json", "--jq", ".tokens[].id"])
    assert result.exit_code == 0, result.output
    assert result.stdout == '"T"\n'
    assert calls[1][0][-1] == ".tokens[].id"
    assert json.loads(calls[1][1])["tokens"][0]["id"] == "T"


def test_endpoint_check_isolated_auth(mock_client):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.host == "public-api.getblock.io":
            return httpx.Response(200, json={"protocol": "eth", "endpoint": "https://go.getblock.io/rpc-secret/"})
        assert "authorization" not in request.headers
        assert json.loads(request.content)["method"] == "eth_blockNumber"
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "getblock-cli-check", "result": "0x10"})
    mock_client(handler)
    result = run(["endpoints", "check", "--token-id", "T", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["block_number"] == 16
    assert len(requests) == 2
    assert "rpc-secret" not in result.output


@pytest.mark.parametrize("endpoint", ["http://go.getblock.io/secret", "https://evil.test/secret", "https://go.getblock.io.evil.test/secret", "https://user:password@go.getblock.io/secret"])
def test_endpoint_rejects_untrusted_url(mock_client, endpoint):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"protocol": "eth", "endpoint": endpoint})
    mock_client(handler)
    result = run(["endpoints", "check", "--token-id", "T", "--json"])
    assert result.exit_code == 2
    assert len(calls) == 1
    assert endpoint not in result.output


def test_endpoint_request_requires_consent():
    result = run(["endpoints", "request", "--token-id", "T", "--input", "-", "--json"], input='{"jsonrpc":"2.0","id":1,"method":"eth_sendRawTransaction"}')
    assert result.exit_code == 3


def test_endpoint_redirect_not_followed(mock_client):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"protocol": "eth", "endpoint": "https://go.getblock.io/secret"})
        return httpx.Response(302, headers={"Location": "https://evil.test/"})
    mock_client(handler)
    result = run(["endpoints", "check", "--token-id", "T", "--json"])
    assert result.exit_code == 1
    assert len(calls) == 2


def test_rpc_application_failure_does_not_claim_success(mock_client):
    def handler(request):
        if request.url.host == "public-api.getblock.io":
            return httpx.Response(200, json={"endpoint": "https://go.getblock.io/secret/"})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601}})
    mock_client(handler)
    result = run(["endpoints", "request", "--token-id", "T", "--input", "-", "--yes", "--json"],
                 input='{"jsonrpc":"2.0","id":1,"method":"unknown"}')
    assert result.exit_code == 1
    assert "operation_succeeded" not in json.loads(result.stderr)["error"]


def test_delivery_watch_changed_snapshots_only(monkeypatch, mock_client):
    from getblock import developer_tools
    tick = [0]
    monkeypatch.setattr(developer_tools.time, "monotonic", lambda: tick[0])
    monkeypatch.setattr(developer_tools.time, "sleep", lambda seconds: tick.__setitem__(0, tick[0] + seconds))
    calls = []
    def handler(request):
        assert request.method == "GET"
        calls.append(request)
        return httpx.Response(200, json={"items": []})
    mock_client(handler)
    result = run(["webhooks", "deliveries", "W", "--watch", "--interval", "1", "--timeout", "2", "--json"])
    assert result.exit_code == 5, result.output
    assert len(calls) == 2
    assert result.stdout.count("\n") == 1
    assert json.loads(result.stdout) == {"items": []}


def test_setup_noninteractive_is_noop():
    result = run(["setup"])
    assert result.exit_code == 2


def test_setup_reuses_guided_creation(monkeypatch, mock_client):
    from getblock import workflows
    paths = []
    def handler(request):
        paths.append((request.method, request.url.path))
        return httpx.Response(200, json={"id": "T"})
    mock_client(handler)
    monkeypatch.setattr(ux, "is_interactive", lambda: True)
    monkeypatch.setattr(workflows, "guide_token", lambda *args: dict(protocol="eth", network="mainnet", api="json-rpc", mode="archive", region="eu", addon=""))
    result = run(["setup"])
    assert result.exit_code == 0, result.output
    assert paths == [("GET", "/api/v1/me"), ("POST", "/api/v1/tokens")]
    assert "Equivalent command" in result.stderr


def test_advanced_profile_lookup_and_redaction(monkeypatch):
    original = httpx.Client
    profiles = []
    def key(profile):
        profiles.append(profile)
        return "advanced-private"
    monkeypatch.setattr(cli, "get_advanced_api_key", key)
    def handler(request):
        assert request.headers["authorization"] == "Bearer advanced-private"
        return httpx.Response(401, json={"error": "invalid advanced-private"})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)))
    result = run(["--profile", "production", "tron-energy", "orders", "list", "--json"])
    assert result.exit_code == 4
    assert profiles == ["production"]
    assert "advanced-private" not in result.output
    assert json.loads(result.stderr)["error"]["status_code"] == 401


def test_jq_bad_syntax_fails_before_mutation(monkeypatch):
    monkeypatch.setattr("getblock.json_query.shutil.which", lambda _: "/tools/jq")
    monkeypatch.setattr("getblock.json_query.subprocess.run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 3, "", "syntax error"))
    result = run(["tokens", "delete", "T", "--yes", "--json", "--jq", "["])
    assert result.exit_code == 2
    assert not result.stdout


def test_jq_runtime_failure_after_success_warns(monkeypatch, mock_client):
    monkeypatch.setattr("getblock.json_query.shutil.which", lambda _: "/tools/jq")
    calls = []
    def execute(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0 if len(calls) == 1 else 5, "", "private-response")
    monkeypatch.setattr("getblock.json_query.subprocess.run", execute)
    mock_client(lambda request: httpx.Response(200, json={"deleted": True}))
    result = run(["tokens", "delete", "T", "--yes", "--json", "--jq", ".missing[]"])
    assert result.exit_code == 1
    assert json.loads(result.stderr)["error"]["operation_succeeded"] is True
    assert not result.stdout
    assert "private-response" not in result.output


def test_jq_cannot_discard_webhook_secret(monkeypatch):
    monkeypatch.setattr("getblock.json_query.prepare", lambda _: "/tools/jq")
    result = run(["webhooks", "create", "--input", "-", "--json", "--jq", ".id"],
                 input='{"chain":"eth","trigger_type":"address_activity","phases":[],"target_url":"https://example.invalid"}')
    assert result.exit_code == 2
    assert "--save-secret" in result.stderr


@pytest.mark.parametrize("rpc_response", [
    {"jsonrpc": "2.0", "id": "getblock-cli-check", "error": {"code": -32601, "message": "secret"}},
    {"jsonrpc": "2.0", "id": "wrong", "result": "0x10"},
    {"jsonrpc": "2.0", "id": "getblock-cli-check", "result": "invalid"},
])
def test_endpoint_rpc_failures_are_nonzero(mock_client, rpc_response):
    def handler(request):
        if request.url.host == "public-api.getblock.io":
            return httpx.Response(200, json={"protocol": "eth", "endpoint": "https://go.getblock.io/secret/"})
        return httpx.Response(200, json=rpc_response)
    mock_client(handler)
    result = run(["endpoints", "check", "--token-id", "T", "--json"])
    assert result.exit_code == 1
    assert not result.stdout
    assert "secret" not in result.output


@pytest.mark.parametrize("args", [["--cursor", "C"], ["--paginate"], ["--dry-run"]])
def test_watch_conflicts_fail_before_request(args):
    result = run(["webhooks", "deliveries", "W", "--watch", *args, "--json"])
    assert result.exit_code == 2
