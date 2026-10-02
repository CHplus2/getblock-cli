"""Focused CLI contracts; every HTTP request is MockTransport-backed."""
import json
import sys
import httpx
import pytest
from typer.testing import CliRunner
from getblock import cli, ux, config
from getblock.output import render


@pytest.fixture
def tmp_path():
    # Python 3.14's Windows mode-0700 temp directories exclude the sandbox identity.
    # Use an isolated, normally inherited-ACL directory and only remove that directory.
    import os
    import uuid
    import shutil
    from pathlib import Path
    root = Path(os.environ.get("TEMP", "/tmp")).resolve()
    path = root / ("getblock-test-" + uuid.uuid4().hex)
    path.mkdir(mode=0o777)
    try:
        yield path
    finally:
        assert path.resolve().parent == root
        shutil.rmtree(path)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    for key in ("GETBLOCK_API_KEY", "GETBLOCK_PROFILE", "GETBLOCK_OUTPUT", "GETBLOCK_TIMEOUT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GETBLOCK_CONFIG_DIR", str(tmp_path / "config"))


def run(args, **kwargs):
    return CliRunner().invoke(cli.app, args, **kwargs)


def test_json_and_aliases(mock_client):
    expected = {"cu": {"total_balance": 0}, "credits": {"balance_cents": 10000}, "nested": [None, False]}
    for args in (["balance", "--json"], ["account", "balance", "--output", "json"]):
        mock_client(lambda request: httpx.Response(200, json=expected))
        result = run(args)
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == expected
        assert result.stderr == ""


def test_human_output_redacts_and_labels(mock_client):
    mock_client(lambda request: httpx.Response(200, json={"cu": {"total_balance": 0}, "credits": {"balance_cents": 0}, "endpoint": "https://secret", "missing": None}))
    result = run(["balance"])
    assert "Compute units (CU)" in result.stdout
    assert "Credit balance (cents): 0" in result.stdout
    assert "https://secret" not in result.stdout
    assert "Missing: —" in result.stdout


def test_no_plan(mock_client):
    mock_client(lambda request: httpx.Response(200, json={"has_plan": False, "plan": None}))
    assert run(["account", "plan"]).stdout.strip() == "No active plan"


def test_tsv_full_id(mock_client):
    identifier = "id-that-must-never-be-truncated-1234567890"
    mock_client(lambda request: httpx.Response(200, json={"tokens": [{"id": identifier, "protocol": "eth"}]}))
    result = run(["tokens", "list", "--output", "tsv", "--fields", "id,protocol"])
    assert result.exit_code == 0, result.output
    assert result.stdout == identifier + "\teth\n"


def test_tsv_missing_field_is_atomic(mock_client):
    mock_client(lambda request: httpx.Response(200, json={"tokens": [{"id": "one"}, {"name": "two"}]}))
    result = run(["tokens", "list", "--output", "tsv", "--fields", "id"])
    assert result.exit_code == 2
    assert result.stdout == ""


@pytest.mark.parametrize("args", [
    ["tokens", "list", "--limit", "bad", "--json"],
    ["tokens", "list", "--unknown", "--json"],
    ["tokens", "create", "--json"],
    ["tokens", "list", "--output", "tsv", "--json"],
])
def test_json_argument_errors(args):
    result = run(args)
    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]["exit_code"] == 2


def test_pagination_retains_filters_and_clamped_page_size(mock_client):
    seen = []
    def handler(request):
        params = dict(request.url.params)
        seen.append(params)
        offset = int(params["offset"])
        return httpx.Response(200, json={"total": 3, "limit": 1, "offset": offset, "nodes": [{"id": str(offset)}]})
    mock_client(handler)
    result = run(["dedicated", "list", "--protocol", "ETH", "--limit", "150", "--paginate", "--json"])
    assert result.exit_code == 0, result.output
    pages = json.loads(result.stdout)
    assert len(pages) == 3
    assert seen == [{"limit": "150", "offset": str(i), "protocol": "ETH"} for i in range(3)]


@pytest.mark.parametrize("mode", ["failure", "bound", "repeat"])
def test_pagination_never_emits_partial_export(mock_client, mode):
    def handler(request):
        offset = int(request.url.params["offset"])
        if mode == "failure" and offset:
            return httpx.Response(502, json={"error": "unavailable"})
        return httpx.Response(200, json={"total": 10, "tokens": [{"id": "same" if mode == "repeat" else str(offset)}]})
    mock_client(handler)
    result = run(["tokens", "list", "--paginate", "--json"] + (["--max-pages", "1"] if mode == "bound" else []))
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert "error" in json.loads(result.stderr)


def test_dry_run_never_reads_key_or_constructs_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline preview must not read credentials or create a transport")
    monkeypatch.setattr(cli, "get_api_key", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    result = run(["tron-energy", "delegate-energy", "--target-address", "T", "--volume", "1", "--duration", "test", "--quote-token", "secret", "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["path"] == "/v1/tron-energy/delegate-energy"
    assert data["body"]["quote_token"] == "[redacted]"
    assert "secret" not in result.output


def test_file_and_stdin_input(advanced_client, tmp_path):
    received = []
    def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(200, json={"data": {"riskScore": 0}})
    advanced_client(handler)
    path = tmp_path / "request.json"
    body = {"tx": "test", "network": "eth"}
    path.write_text(json.dumps(body))
    for source, stdin in ((str(path), None), ("-", json.dumps(body))):
        result = run(["aml", "tx-check", "--input", source, "--yes", "--json"], input=stdin)
        assert result.exit_code == 0, result.output
    assert received == [body, body]


@pytest.mark.parametrize("body,extra", [({"tx": "test", "network": "eth", "unsupported_field": "ETH"}, []), ({"tx": 1, "network": "eth"}, []), ({"tx": "test", "network": "eth"}, ["--tx", "other"])])
def test_invalid_input_before_request(body, extra):
    result = run(["aml", "tx-check", "--input", "-", "--dry-run", "--json", *extra], input=json.dumps(body))
    assert result.exit_code == 2
    assert result.stdout == ""


def test_config_profile_precedence_and_origins(monkeypatch):
    config.save("production", "timeout", "15")
    monkeypatch.setenv("GETBLOCK_TIMEOUT", "20")
    result = run(["--profile", "production", "--timeout", "30", "config", "list", "--show-origin", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["settings"]["timeout"] == 30
    assert data["origins"]["timeout"] == "flag"
    assert "production" in config.load()["profiles"]
    result = run(["config", "set", "yes", "true", "--json"])
    assert result.exit_code == 2


def test_profile_credentials_and_environment_override(monkeypatch):
    keys = []
    clients = []
    from getblock.client import GetBlockClient
    original = httpx.Client
    def transport(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "user"}))
        return original(*args, **kwargs)
    monkeypatch.setattr(httpx, "Client", transport)
    monkeypatch.setattr(cli, "get_api_key", lambda profile="default": keys.append(profile) or "stored")
    monkeypatch.setenv("GETBLOCK_API_KEY", "environment-key")
    def make(key):
        clients.append(key)
        return GetBlockClient(key)
    monkeypatch.setattr(cli, "GetBlockClient", make)
    assert run(["--profile", "production", "me", "--json"]).exit_code == 0
    assert not keys
    assert clients == ["environment-key"]
    monkeypatch.delenv("GETBLOCK_API_KEY")
    assert run(["--profile", "production", "me", "--json"]).exit_code == 0
    assert keys == ["production"]


def test_login_with_stdin_never_echoes_key(monkeypatch):
    stored = []
    monkeypatch.setattr(cli, "save_api_key", lambda key, profile: stored.append((key, profile)))
    result = run(["--profile", "production", "auth", "login", "--with-key", "--json"], input="secret-key\n")
    assert result.exit_code == 0, result.output
    assert stored == [("secret-key", "production")]
    assert "secret-key" not in result.output
    assert json.loads(result.stdout)["verified"] is False


def test_auth_check_makes_only_me_request(mock_client):
    paths = []
    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={"id": "user"})
    mock_client(handler)
    assert run(["auth", "status", "--json"]).exit_code == 0
    assert not paths
    result = run(["auth", "status", "--check", "--json"])
    assert json.loads(result.stdout)["verified"]
    assert paths == ["/api/v1/me"]


def test_advanced_preflight_before_confirmation(monkeypatch):
    monkeypatch.setattr(ux, "confirm", lambda *args: pytest.fail("Unavailable Advanced auth must fail before consent"))
    result = run(["wallet-audit", "audit", "--network", "ETH", "--address", "A", "--json"])
    assert result.exit_code == 1
    assert "authentication" in json.loads(result.stderr)["error"]["message"]


def test_paid_noninteractive_requires_yes(advanced_client):
    advanced_client(lambda request: pytest.fail("No request without consent"))
    result = run(["aml", "tx-check", "--tx", "T", "--network", "eth", "--json"])
    assert result.exit_code == 3
    assert "--yes" in result.stderr


def test_request_id_and_credential_redaction(mock_client):
    mock_client(lambda request: httpx.Response(401, json={"error": "rejected fake-api-key", "request_id": "req-123"}))
    result = run(["me", "--json"])
    assert result.exit_code == 4
    error = json.loads(result.stderr)["error"]
    assert error["request_id"] == "req-123"
    assert "fake-api-key" not in result.output


def test_interactive_token_uses_only_returned_configuration(mock_client, monkeypatch):
    from getblock import workflows
    monkeypatch.setattr(workflows, "is_interactive", lambda: True)
    monkeypatch.setattr(ux, "is_interactive", lambda: True)
    sent = []
    def handler(request):
        if request.url.path == "/api/v1/protocols":
            return httpx.Response(200, json={"total": 1, "protocols": [{"id": "eth"}]})
        if request.url.path == "/api/v1/protocols/eth":
            return httpx.Response(200, json={"id": "eth", "networks": [{"id": "mainnet", "modes": [{"id": "full", "apis": [{"id": "json-rpc", "regions": ["eu-central-1"]}], "addons": []}]}]})
        assert request.url.path == "/api/v1/tokens"
        sent.append(json.loads(request.content))
        return httpx.Response(201, json={"id": "new"})
    mock_client(handler)
    result = run(["tokens", "create", "--interactive", "--json"], input="1\n1\n1\n1\n1\n1\ny\n")
    assert result.exit_code == 0, result.output
    assert sent == [{"protocol": "eth", "network": "mainnet", "mode": "full", "api": "json-rpc", "region": "eu-central-1", "addon": ""}]
    assert json.loads(result.stdout) == {"id": "new"}


def test_guided_node_cancel_does_not_create(mock_client, monkeypatch):
    from getblock import workflows
    monkeypatch.setattr(workflows, "is_interactive", lambda: True)
    monkeypatch.setattr(ux, "is_interactive", lambda: True)
    methods = []
    def handler(request):
        methods.append(request.method)
        return httpx.Response(200, json={"id": "N", "apis": ["jsonrpc"], "addons": ["debug"]})
    mock_client(handler)
    result = run(["dedicated", "tokens", "create", "N", "--interactive", "--json"], input="1\n1\nn\n")
    assert result.exit_code == 3, result.output
    assert methods == ["GET"]
    assert result.stdout == ""


def test_quote_file_roundtrip_and_no_overwrite(advanced_client, tmp_path):
    path = tmp_path / "quote.json"
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"data": {"quote_token": "secret-quote", "price_usd": "1"}})
    advanced_client(handler)
    args = ["tron-energy", "price-estimate", "--resource-type", "energy", "--volume", "1", "--duration", "test-duration", "--save-quote", str(path)]
    result = run(args)
    assert result.exit_code == 0, result.output
    assert "secret-quote" not in result.output
    assert json.loads(path.read_text())["inputs"] == {"resourceType": "energy", "volume": 1, "duration": "test-duration"}
    result = run(args)
    assert result.exit_code == 2
    assert len(calls) == 1
    from getblock.workflows import load_quote
    assert load_quote(str(path), "delegate_tron_energy", {"volume": 1, "duration": "test-duration"}) == "secret-quote"
    with pytest.raises(ux.CLIError):
        load_quote(str(path), "delegate_tron_bandwidth", {"volume": 1, "duration": "test-duration"})


def test_quote_file_delegation_sends_matching_body(advanced_client, tmp_path):
    path = tmp_path / "quote.json"
    path.write_text(json.dumps({"inputs": {"resourceType": "energy", "volume": 1, "duration": "test"}, "estimate": {"data": {"quote_token": "secret"}}}))
    received = []
    def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(202, json={"data": {"orderId": "O"}})
    advanced_client(handler)
    result = run(["tron-energy", "delegate-energy", "--target-address", "A", "--volume", "1", "--duration", "test", "--quote-file", str(path), "--yes", "--json"])
    assert result.exit_code == 0, result.output
    assert received == [{"target_address": "A", "volume": 1, "duration": "test", "quote_token": "secret"}]
    assert json.loads(result.stdout)["data"]["orderId"] == "O"


def test_watch_explicit_condition_and_no_post(advanced_client, monkeypatch):
    import time
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda value: clock.__setitem__(0, clock[0] + value))
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={"data": {"status": "pending" if len(calls) == 1 else "charged"}})
    advanced_client(handler)
    result = run(["tron-energy", "orders", "watch", "O", "--interval", "1", "--timeout", "3", "--status-field", "data.status", "--until-status", "charged", "--json"])
    assert result.exit_code == 0, result.output
    assert calls == ["GET", "GET"]
    assert json.loads(result.stdout) == {"data": {"status": "charged"}}


def test_watch_without_condition_times_out_not_success(advanced_client, monkeypatch):
    import time
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda value: clock.__setitem__(0, clock[0] + value))
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={"data": {"status": "delivered_uncharged"}})
    advanced_client(handler)
    result = run(["tron-energy", "orders", "watch", "O", "--interval", "1", "--timeout", "2", "--json"])
    assert result.exit_code == 5, result.output
    assert calls == ["GET", "GET"]
    assert result.stdout == ""
    # Progress is separate from final machine-readable diagnostics.
    assert json.loads(result.stderr.splitlines()[-1])["error"]["exit_code"] == 5


@pytest.mark.parametrize("topic", ["workflows", "shell", "advanced", "exit-codes", "configuration"])
def test_help_topics_offline(topic, monkeypatch):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Help reads no credentials"))
    result = run(["help", topic])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_legacy_default_keyring_name(monkeypatch):
    from getblock import auth
    seen = []
    monkeypatch.setattr(auth.keyring, "get_password", lambda service, key: seen.append((service, key)))
    auth.get_api_key()
    auth.get_api_key("production")
    assert seen == [("getblock-cli", "getblock_api_key"), ("getblock-cli", "getblock_api_key:production")]


def test_keyring_failure_has_actionable_error(monkeypatch):
    import keyring
    def fail():
        raise keyring.errors.NoKeyringError("secret internal data")
    monkeypatch.setattr(cli, "get_api_key", fail)
    result = run(["auth", "status", "--json"])
    assert result.exit_code == 4
    assert "secret internal data" not in result.output
    assert "keyring" in result.stderr


def test_timeout_no_post_retry(advanced_client):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret", request=request)
    advanced_client(handler)
    result = run(["aml", "tx-check", "--network", "eth", "--tx", "T", "--yes", "--json"])
    assert result.exit_code == 1
    assert len(calls) == 1
    assert "secret" not in result.output


def test_node_token_optional_addon_remains_empty_string(mock_client):
    bodies = []
    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={"id": "new"})
    mock_client(handler)
    result = run(["dedicated", "tokens", "create", "N", "--api", "jsonrpc", "--json"])
    assert result.exit_code == 0, result.output
    assert bodies == [{"api": "jsonrpc", "addon": ""}]


def test_interactive_still_requires_node_id():
    result = run(["dedicated", "tokens", "create", "--interactive", "--json"])
    assert result.exit_code == 2
    assert result.stdout == ""


def test_invalid_api_json_is_operational_error(mock_client):
    mock_client(lambda request: httpx.Response(200, text="private upstream response"))
    result = run(["me", "--json"])
    assert result.exit_code == 1
    assert "invalid JSON" in result.stderr
    assert "private upstream response" not in result.output


def test_broken_pipe_does_not_traceback(mock_client, monkeypatch):
    mock_client(lambda request: httpx.Response(200, json={"id": "user"}))
    def broken(*args, **kwargs):
        raise BrokenPipeError()
    monkeypatch.setattr(ux, "render", broken)
    result = run(["me", "--json"])
    assert result.exit_code == 0
    assert result.output == ""


def test_verbose_never_prints_auth_or_bodies(mock_client):
    mock_client(lambda request: httpx.Response(200, json={"id": "user"}))
    result = run(["--verbose", "me"])
    assert result.exit_code == 0
    assert "GET /api/v1/me" in result.stderr
    assert "fake-api-key" not in result.output


def test_completion_values_are_offline():
    assert ux.complete_from(["energy", "bandwidth"])("en") == ["energy"]


def test_logout_only_selected_profile(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "delete_api_key", lambda profile: seen.append(profile))
    result = run(["--profile", "production", "auth", "logout", "--json"])
    assert result.exit_code == 0
    assert seen == ["production"]


def test_conflicting_output_flags_before_mutation(advanced_client):
    advanced_client(lambda request: pytest.fail("Cannot mutate with conflicting output settings"))
    result = run(["aml", "tx-check", "--tx", "T", "--network", "eth", "--yes", "--json", "--output", "table"])
    assert result.exit_code == 2


def test_version_offline(monkeypatch):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Version must be offline"))
    result = run(["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("getblock ")


def test_invalid_tsv_columns_rejected_before_paid_request(advanced_client):
    advanced_client(lambda request: pytest.fail("Invalid output syntax must not spend credits"))
    result = run(["aml", "tx-check", "--tx", "T", "--network", "eth", "--yes", "--output", "tsv", "--fields", "id,,id"])
    assert result.exit_code == 2
    assert result.stdout == ""
