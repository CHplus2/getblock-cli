"""Explicit node requests, isolated from management API authentication."""
import re
import time
from urllib.parse import urlsplit
import httpx
import typer
from getblock import ux
from getblock.ux import CLIError, emit
from getblock.paths import path_segment


app = typer.Typer(help="Check Ethereum JSON-RPC access or send an explicit JSON-RPC request. Requests may consume quota.")


def validate_payload(payload):
    if payload.get("jsonrpc") != "2.0" or not isinstance(payload.get("method"), str) or not payload["method"]:
        raise CLIError("Provide a JSON-RPC 2.0 object with a nonempty method.", 2)
    if "id" not in payload or isinstance(payload["id"], (bool, list, dict)):
        raise CLIError("Provide a JSON-RPC id (string, number or null); notifications are not supported.", 2)
    if "params" in payload and not isinstance(payload["params"], (list, dict)):
        raise CLIError("JSON-RPC params must be an array or object.", 2)


def perform(token_id, payload, check=False, yes=False):
    from getblock import cli
    state = ux.current.get()
    path_segment(token_id)
    validate_payload(payload)
    if state.dry_run:
        raise ux.PreviewReady({"dry_run": True, "action": "resolve token endpoint then POST JSON-RPC", "token_id": token_id,
              "endpoint": "[resolved at execution; redacted]", "body": {"jsonrpc": "2.0", "method": payload["method"], "params": "[redacted]"},
              "note": "No token lookup or RPC request. Endpoint and protocol are not verified."})
    if not check:
        ux.confirm("Send this JSON-RPC request? It may consume quota or change blockchain state. No automatic retry.", yes)
    token = cli.get_authenticated_client().get_token(token_id)
    if not isinstance(token, dict):
        raise CLIError("Token response is not an object; cannot resolve its endpoint.")
    if check and token.get("protocol") != "eth":
        raise CLIError("Automatic check currently supports protocol eth only. Use endpoints request with a documented method for other protocols.", 2)
    endpoint = token.get("endpoint")
    if not isinstance(endpoint, str):
        raise CLIError("Token response has no endpoint URL. No URL is inferred from the resource ID.")
    state.secrets.append(endpoint)
    try:
        parsed = urlsplit(endpoint)
        valid = parsed.scheme == "https" and parsed.hostname and parsed.hostname.endswith(".getblock.io") and not parsed.username and not parsed.password and parsed.port in (None, 443) and not parsed.fragment
    except ValueError:
        valid = False
    if not valid:
        raise CLIError("Endpoint must be an HTTPS GetBlock subdomain URL without user information, a custom port or fragment.", 2)
    state.secrets.extend(part for part in parsed.path.split("/") if part)
    started = time.monotonic()
    try:
        # Never attach a Public or Advanced management key, nor follow redirects.
        with httpx.Client(timeout=state.timeout, follow_redirects=False) as client:
            response = client.post(endpoint, json=payload)
    except httpx.TimeoutException:
        raise CLIError("RPC request timed out. Its outcome is unknown; inspect before retrying.")
    except httpx.RequestError:
        raise CLIError("Could not connect to the RPC endpoint. No automatic retry was made.")
    if not 200 <= response.status_code < 300:
        raise CLIError(f"RPC endpoint returned HTTP {response.status_code}. No automatic retry was made.")
    try:
        data = response.json()
    except ValueError:
        raise CLIError("RPC endpoint returned invalid JSON.")
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or data.get("id") != payload["id"]:
        raise CLIError("RPC response has an unexpected version or request ID.")
    if data.get("error") is not None:
        code = data["error"].get("code") if isinstance(data["error"], dict) else None
        raise CLIError("RPC returned an application error" + (f" (code {code})" if type(code) is int else "") + ". Check the method, parameters and endpoint configuration.")
    if "result" not in data:
        raise CLIError("RPC response contains no result.")
    if check:
        result = data["result"]
        if not isinstance(result, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", result):
            raise CLIError("eth_blockNumber returned an unexpected result.")
        emit({"token_id": token_id, "protocol": "eth", "connected": True, "block_number": int(result, 16),
              "latency_ms": round((time.monotonic() - started) * 1000, 2)})
    else:
        state.mutation_succeeded = True
        emit(data)


@app.command("check")
@ux.command()
def check_endpoint(token_id: str = typer.Option(..., help="Resource ID, not an endpoint access token.")):
    """Call eth_blockNumber once through a resolved Ethereum endpoint; may consume quota."""
    perform(token_id, {"jsonrpc": "2.0", "id": "getblock-cli-check", "method": "eth_blockNumber", "params": []}, check=True)


@app.command("request")
@ux.command(input_template={"jsonrpc": "2.0", "id": 1, "method": "REPLACE_METHOD", "params": []})
def request_endpoint(
    token_id: str = typer.Option(..., help="Token resource ID whose returned endpoint will be used."),
    request_file: str = typer.Option(..., "--input", help="One JSON-RPC object from a file or - for stdin."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Consent to sending the explicit RPC request."),
):
    """Send one JSON-RPC request. May consume quota or change blockchain state."""
    perform(token_id, ux.read_object(request_file), yes=yes)
