import json

import httpx
import pytest
from typer.testing import CliRunner

from getblock import cli, ux


WEBHOOK = {"chain": "eth", "trigger_type": "address_activity", "phases": ["confirmed"],
           "target_url": "https://hooks.example.io/getblock",
           "addresses": ["0x742d35cc6634c0532925a3b844bc454e4438f44e"]}
PATCH = {"confirm_depth": None, "addresses": [], "list_refs": [],
         "filters": {"any": [{"type": "address", "dir": "any", "in": WEBHOOK["addresses"]}]}}

# Contract cases transcribed from the supplied REST documentation: command,
# client method/arguments, HTTP method, path, query, request JSON and response.
CASES = [
    (["webhooks", "list"], "get_webhooks", (), "GET", "/webhooks", {"limit": "50"}, None, 200, {"items": []}),
    (["webhooks", "create", "--input", "-"], "create_webhook", (WEBHOOK,), "POST", "/webhooks", {}, WEBHOOK, 201, {"id": "wh_test", "secret": "whsec_private"}),
    (["webhooks", "limits"], "get_webhook_limits", (), "GET", "/webhooks/limits", {}, None, 200, {"plan_required": True, "caps": {}, "usage": {}}),
    (["webhooks", "get", "wh_test"], "get_webhook", ("wh_test",), "GET", "/webhooks/wh_test", {}, None, 200, {"id": "wh_test"}),
    (["webhooks", "update", "wh_test", "--input", "-"], "update_webhook", ("wh_test", PATCH), "PATCH", "/webhooks/wh_test", {}, PATCH, 200, {"id": "wh_test", "confirm_depth": None}),
    (["webhooks", "delete", "wh_test", "--yes"], "delete_webhook", ("wh_test",), "DELETE", "/webhooks/wh_test", {}, None, 204, None),
    (["webhooks", "pause", "wh_test"], "pause_webhook", ("wh_test",), "POST", "/webhooks/wh_test/pause", {}, None, 200, {"status": "paused"}),
    (["webhooks", "resume", "wh_test"], "resume_webhook", ("wh_test",), "POST", "/webhooks/wh_test/resume", {}, None, 200, {"status": "active"}),
    (["webhooks", "secret", "rotate", "wh_test", "--yes"], "rotate_webhook_secret", ("wh_test",), "POST", "/webhooks/wh_test/secret/rotate", {}, None, 200, {"secret": "whsec_private", "version": 4, "previous_expires_at": "2026-09-26T10:00:00Z"}),
    (["webhooks", "test", "wh_test"], "send_webhook_test", ("wh_test",), "POST", "/webhooks/wh_test/test", {}, None, 202, {"event_id": "evt_test", "status": "queued"}),
    (["webhooks", "deliveries", "wh_test"], "get_webhook_deliveries", ("wh_test",), "GET", "/webhooks/wh_test/deliveries", {"limit": "100"}, None, 200, {"items": []}),
    (["webhooks", "stats", "wh_test"], "get_webhook_stats", ("wh_test",), "GET", "/webhooks/wh_test/stats", {}, None, 200, {"webhook_id": "wh_test", "rates": None, "rates_available": False, "delivered_total": 0}),
    (["webhooks", "addresses", "wh_test"], "get_webhook_addresses", ("wh_test",), "GET", "/webhooks/wh_test/addresses", {"limit": "50"}, None, 200, {"list_id": None, "addresses": []}),
    (["address-lists", "list"], "get_address_lists", (), "GET", "/address-lists", {"limit": "50"}, None, 200, {"items": []}),
    (["address-lists", "create", "--input", "-"], "create_address_list", ({"name": "Treasury wallets"},), "POST", "/address-lists", {}, {"name": "Treasury wallets"}, 201, {"id": "al_test", "entry_count": 0}),
    (["address-lists", "get", "al_test"], "get_address_list", ("al_test",), "GET", "/address-lists/al_test", {}, None, 200, {"id": "al_test"}),
    (["address-lists", "rename", "al_test", "--name", "Cold wallets"], "rename_address_list", ("al_test", "Cold wallets"), "PATCH", "/address-lists/al_test", {}, {"name": "Cold wallets"}, 200, {"id": "al_test", "name": "Cold wallets"}),
    (["address-lists", "delete", "al_test", "--yes"], "delete_address_list", ("al_test",), "DELETE", "/address-lists/al_test", {}, None, 204, None),
    (["address-lists", "entries", "list", "al_test"], "get_address_list_entries", ("al_test",), "GET", "/address-lists/al_test/entries", {"limit": "50"}, None, 200, {"addresses": []}),
    (["address-lists", "entries", "add", "al_test", "--input", "-"], "add_address_list_entries", ("al_test", WEBHOOK["addresses"]), "POST", "/address-lists/al_test/entries", {}, {"addresses": WEBHOOK["addresses"]}, 200, {"entry_count": 1}),
    (["address-lists", "entries", "replace", "al_test", "--input", "-", "--yes"], "replace_address_list_entries", ("al_test", []), "PUT", "/address-lists/al_test/entries", {}, {"addresses": []}, 200, {"entry_count": 0}),
    (["address-lists", "entries", "remove", "al_test", "--input", "-", "--yes"], "remove_address_list_entries", ("al_test", WEBHOOK["addresses"]), "POST", "/address-lists/al_test/entries/remove", {}, {"addresses": WEBHOOK["addresses"]}, 200, {"entry_count": 0}),
]


def run(args, **kwargs):
    return CliRunner().invoke(cli.app, args, **kwargs)


@pytest.mark.parametrize("case", CASES, ids=[case[1] for case in CASES])
@pytest.mark.parametrize("surface", ["client", "cli"])
def test_notify_contract(mock_client, case, surface):
    argv, method, args, verb, path, query, body, code, response = case
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == verb
        assert request.url.path == "/api/v1" + path
        assert dict(request.url.params) == query
        assert request.headers["authorization"] == "Bearer fake-api-key"
        assert (json.loads(request.content) if request.content else None) == body
        return httpx.Response(code, json=response) if response is not None else httpx.Response(code)
    client = mock_client(handler)
    if surface == "client":
        assert getattr(client, method)(*args) == response
    else:
        result = run([*argv, "--json"], input=json.dumps(body) if body is not None else None)
        assert result.exit_code == 0, result.output
        expected = response if code != 204 else {"id": args[0], "deleted": True}
        assert json.loads(result.stdout) == expected
    assert len(calls) == 1


@pytest.mark.parametrize("body", [{"name": "Only name"}, {"confirm_depth": None}, {"confirm_depth": 2}, {"addresses": []}, {"list_refs": []}, {}])
def test_patch_exact_body(mock_client, body):
    def handler(request):
        assert json.loads(request.content) == body
        return httpx.Response(200, json={"id": "wh_test"})
    mock_client(handler)
    result = run(["webhooks", "update", "wh_test", "--input", "-", "--json"], input=json.dumps(body))
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("expire", [None, False, True])
def test_rotation_optional_body(mock_client, expire):
    def handler(request):
        if expire is None:
            assert request.content == b""
            assert "content-type" not in request.headers
        else:
            assert json.loads(request.content) == {"expire_previous": expire}
        return httpx.Response(200, json={"secret": "whsec_new", "previous_expires_at": None})
    assert mock_client(handler).rotate_webhook_secret("wh_test", expire)["secret"] == "whsec_new"


def test_rotation_expire_cli(mock_client):
    def handler(request):
        assert json.loads(request.content) == {"expire_previous": True}
        return httpx.Response(200, json={"secret": "whsec_new", "previous_expires_at": None})
    mock_client(handler)
    result = run(["webhooks", "secret", "rotate", "wh_test", "--expire-previous", "--yes", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["previous_expires_at"] is None


@pytest.mark.parametrize("argv", [case[0] for case in CASES if case[6] is None and case[5]])
def test_cursor_forwarding(mock_client, argv):
    def handler(request):
        assert request.url.params["limit"] == "1500"
        assert request.url.params["cursor"] == "opaque+/= value"
        assert "offset" not in request.url.params
        return httpx.Response(200, json={"items": []})
    mock_client(handler)
    result = run([*argv, "--limit", "1500", "--cursor", "opaque+/= value", "--json"])
    assert result.exit_code == 0, result.output


def test_delivery_filters_paginate(mock_client):
    calls = []
    def handler(request):
        calls.append(request)
        params = request.url.params
        assert params["from"] == "2026-09-25T00:00:00Z"
        assert params["to"] == "2026-09-26T00:00:00Z"
        assert params.get_list("status") == ["retrying", "failed_terminal,replayed"]
        assert params["limit"] == "9999"
        assert params.get("cursor") == (None if len(calls) == 1 else "next+/=")
        return httpx.Response(200, json={"items": [], **({"next_cursor": "next+/="} if len(calls) == 1 else {})})
    mock_client(handler)
    result = run(["webhooks", "deliveries", "wh_test", "--from", "2026-09-25T00:00:00Z", "--to", "2026-09-26T00:00:00Z", "--status", "retrying", "--status", "failed_terminal,replayed", "--limit", "9999", "--paginate", "--json"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)) == 2
    assert len(calls) == 2  # Even an empty page can carry a continuation.


@pytest.mark.parametrize("mode", ["repeat", "bound", "failure", "invalid", "missing"])
def test_cursor_failure_is_atomic(mock_client, mode):
    calls = []
    def handler(request):
        calls.append(request)
        if mode == "failure" and len(calls) == 2:
            return httpx.Response(503, json={"error": "delivery_log_not_configured"})
        if mode == "missing":
            return httpx.Response(200, json={"next_cursor": "next"})
        return httpx.Response(200, json={"items": [{"id": str(len(calls))}], "next_cursor": 42 if mode == "invalid" else "next"})
    mock_client(handler)
    result = run(["webhooks", "list", "--paginate", "--json", *(["--max-pages", "1"] if mode == "bound" else [])])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert len(calls) <= 2


@pytest.mark.parametrize("argv,code,error", [
    (["webhooks", "list"], 400, "invalid_cursor"),
    (["webhooks", "resume", "wh_test"], 403, "plan_required"),
    (["address-lists", "get", "al_test"], 404, "list_not_found"),
    (["address-lists", "delete", "al_test", "--yes"], 409, "list_in_use"),
    (["webhooks", "resume", "wh_test"], 409, "insufficient_balance"),
    (["webhooks", "resume", "wh_test"], 409, "cap_addresses_exceeded"),
    (["webhooks", "limits"], 503, "plan_caps_unavailable"),
    (["webhooks", "deliveries", "wh_test"], 503, "delivery_log_not_configured"),
    (["webhooks", "test", "wh_test"], 503, "test_event_unavailable"),
    (["webhooks", "test", "wh_test"], 409, "webhook_not_active"),
])
def test_documented_errors(mock_client, argv, code, error):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(code, json={"error": error, "request_id": "req-test"})
    mock_client(handler)
    result = run([*argv, "--json"])
    assert result.exit_code == 1
    detail = json.loads(result.stderr)["error"]
    assert detail["message"] == error
    assert detail["api_error_code"] == error
    assert detail["status_code"] == code
    assert detail["request_id"] == "req-test"
    assert result.stdout == ""
    assert len(calls) == 1


@pytest.mark.parametrize("code", [413, 502])
def test_non_json_gateway_error(mock_client, code):
    mock_client(lambda request: httpx.Response(code, text="private gateway page", headers={"x-request-id": "req-gateway"}))
    result = run(["webhooks", "create", "--input", "-", "--json"], input=json.dumps(WEBHOOK))
    assert result.exit_code == 1
    assert json.loads(result.stderr)["error"]["status_code"] == code
    assert "private gateway page" not in result.output


@pytest.mark.parametrize("argv", [case[0] for case in CASES if "--yes" in case[0]])
def test_mutation_requires_consent(mock_client, monkeypatch, argv):
    mock_client(lambda request: pytest.fail("No HTTP without consent"))
    monkeypatch.setattr(ux, "is_interactive", lambda: False)
    result = run([arg for arg in argv if arg != "--yes"] + ["--json"], input='{"addresses": []}')
    assert result.exit_code == 3, result.output
    assert result.stdout == ""


@pytest.mark.parametrize("argv", [["webhooks", "get"], ["webhooks", "update", "wh_test"], ["webhooks", "create"], ["address-lists", "rename", "al_test"], ["address-lists", "entries", "add", "al_test"]])
def test_required_arguments(argv):
    result = run([*argv, "--json"])
    assert result.exit_code == 2
    assert result.stdout == ""


@pytest.mark.parametrize("body", ['[]', '{', '{"chain":"eth"}', json.dumps({**WEBHOOK, "typo": 1})])
def test_invalid_create_input_before_auth(monkeypatch, body):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Invalid input must fail before auth"))
    result = run(["webhooks", "create", "--input", "-", "--json"], input=body)
    assert result.exit_code == 2, result.output


def test_nested_json_file_and_dry_run(monkeypatch):
    from pathlib import Path
    body = {**WEBHOOK, "batching": {"max_events": 10, "max_wait_ms": 500, "gzip": False},
            "filters": {"not": {"any": [{"type": "address", "dir": "out", "in": WEBHOOK["addresses"]}]}}, "confirm_depth": None}
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: json.dumps(body) if self.name == "webhook.json" else '{}')
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Preview reads no key"))
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: pytest.fail("Preview constructs no transport"))
    result = run(["webhooks", "create", "--input", "webhook.json", "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["body"] == body


def test_secret_human_redaction(mock_client):
    mock_client(lambda request: httpx.Response(200, json={"secret": "whsec_private", "version": 4}))
    result = run(["--verbose", "webhooks", "secret", "rotate", "wh_test", "--yes"])
    assert result.exit_code == 0, result.output
    assert "whsec_private" not in result.output
    assert "[redacted]" in result.stdout


@pytest.mark.parametrize("output", ["table", "tsv", "json"])
def test_addresses_output(mock_client, output):
    body = {"list_id": "al_private", "addresses": ["0xABC"], "next_cursor": "opaque"}
    mock_client(lambda request: httpx.Response(200, json=body))
    result = run(["webhooks", "addresses", "wh_test", "--output", output, *(["--fields", "address"] if output == "tsv" else [])])
    assert result.exit_code == 0, result.output
    if output == "json":
        assert json.loads(result.stdout) == body
    elif output == "tsv":
        assert result.stdout == "0xABC\n"
    else:
        assert "--cursor opaque" in result.stdout
        assert "al_private" in result.stdout
        assert "0xABC" in result.stdout


@pytest.mark.parametrize("argv", [case[0] for case in CASES])
def test_help_all_notify_commands_offline(monkeypatch, argv):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Help must be offline"))
    result = run([*argv, "--help"])
    assert result.exit_code == 0, result.output
    assert "Example:" in result.stdout
    if "--cursor" in result.stdout:
        assert "--offset" not in result.stdout


@pytest.mark.parametrize("case", CASES, ids=[case[1] for case in CASES])
def test_notify_requires_authentication(monkeypatch, case):
    monkeypatch.setattr(cli, "get_api_key", lambda: None)
    result = run([*case[0], "--json"], input=json.dumps(case[6]))
    assert result.exit_code == 4, result.output
    assert result.stdout == ""


@pytest.mark.parametrize("case", CASES, ids=[case[1] for case in CASES])
def test_notify_preview_is_offline(monkeypatch, case):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Preview reads no credentials"))
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: pytest.fail("Preview creates no transport"))
    result = run([*case[0], "--dry-run", "--json"], input=json.dumps(case[6]))
    assert result.exit_code == 0, result.output
    preview = json.loads(result.stdout)
    assert preview["method"] == case[3]
    assert preview["path"] == "/api/v1" + case[4]
    assert preview["body"] == case[6]


@pytest.mark.parametrize("reply,expected_calls", [("n", 0), ("y", 1)])
def test_interactive_delete_confirmation(mock_client, monkeypatch, reply, expected_calls):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(204)
    mock_client(handler)
    monkeypatch.setattr(ux, "is_interactive", lambda: True)
    result = run(["webhooks", "delete", "wh_test", "--json"], input=reply + "\n")
    assert len(calls) == expected_calls
    assert result.exit_code == (0 if expected_calls else 3), result.output
    assert "wh_test" in result.stderr
    if expected_calls:
        assert json.loads(result.stdout) == {"id": "wh_test", "deleted": True}
    else:
        assert result.stdout == ""


def test_cursor_address_pages_tsv(mock_client):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"addresses": ["0xABC"], "next_cursor": "opaque"})
        assert request.url.params["cursor"] == "opaque"
        return httpx.Response(200, json={"addresses": ["0xDEF"]})
    mock_client(handler)
    result = run(["address-lists", "entries", "list", "al_test", "--paginate", "--max-pages", "2", "--output", "tsv", "--fields", "address"])
    assert result.exit_code == 0, result.output
    assert result.stdout == "0xABC\n0xDEF\n"


@pytest.mark.parametrize("body", [{"chain": "eth"}, {"network": "mainnet"}, {"trigger_type": "log_event"}])
def test_immutable_patch_fields_rejected(monkeypatch, body):
    monkeypatch.setattr(cli, "get_api_key", lambda: pytest.fail("Reject immutable fields before auth"))
    result = run(["webhooks", "update", "wh_test", "--input", "-", "--json"], input=json.dumps(body))
    assert result.exit_code == 2


def test_rename_input_and_conflict(mock_client):
    def handler(request):
        assert json.loads(request.content) == {"name": "Cold wallets"}
        return httpx.Response(200, json={"name": "Cold wallets"})
    mock_client(handler)
    result = run(["address-lists", "rename", "al_test", "--input", "-", "--json"], input='{"name":"Cold wallets"}')
    assert result.exit_code == 0, result.output
    result = run(["address-lists", "rename", "al_test", "--input", "-", "--name", "Conflict", "--json"], input='{"name":"Cold wallets"}')
    assert result.exit_code == 2
