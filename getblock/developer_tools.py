"""Task-oriented CLI commands using the existing management API contracts."""
import shlex
import math
import time
import httpx
import typer
from getblock import ux
from getblock.ux import CLIError, emit
from getblock.http_client import GetBlockAPIError


def watch_deliveries(webhook_id, limit, from_time, to_time, status, interval, timeout):
    from getblock import cli
    if not math.isfinite(interval) or not math.isfinite(timeout):
        raise CLIError("Watch interval and timeout must be finite.", 2)
    state = ux.current.get()
    client = cli.get_authenticated_client()
    deadline = time.monotonic() + timeout
    previous = None
    if state.output == "table":
        typer.echo("Watching first-page snapshots, not a complete event stream. Logs may be sampled and omit successful production deliveries.", err=True)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CLIError("Delivery watch deadline reached; no test-delivery outcome is inferred.", 5)
        client.client.timeout = httpx.Timeout(min(state.timeout, remaining))
        data = client.get_webhook_deliveries(webhook_id, limit, None, from_time, to_time, status)
        if data != previous:
            emit(data)
            previous = data
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CLIError("Delivery watch deadline reached; no test-delivery outcome is inferred.", 5)
        time.sleep(min(interval, remaining))


def register(app):
    app.command("doctor", rich_help_panel="CLI tools")(doctor)
    app.command("setup", rich_help_panel="CLI tools")(setup)


@ux.command()
def doctor(
    check_network: bool = typer.Option(False, help="Make read-only authentication checks; no billable POST requests."),
    api: str = typer.Option("public", help="Diagnose public, advanced, or both."),
):
    """Explain configuration and credential problems without exposing keys."""
    from getblock import cli, config
    state = ux.current.get()
    if api not in ("public", "advanced", "both"):
        raise CLIError("--api must be public, advanced or both.", 2)
    if state.dry_run:
        raise CLIError("Doctor is read-only. Omit --check-network for offline diagnosis; omit --dry-run.", 2)
    checks = [{"name": "configuration", "status": "failed" if getattr(state, "config_error", None) else "ok",
               "message": getattr(state, "config_error", "Configuration parsed successfully."), "path": str(config.config_path())}]
    if checks[0]["status"] == "failed":
        checks[0]["hint"] = "Correct the reported configuration or environment setting and run doctor again."
    for surface in (("public", "advanced") if api == "both" else (api,)):
        try:
            result = cli.credential_status(surface)
            configured = result["configured"]
            item = {"name": surface + " authentication", "status": "ok" if configured else "failed", **result}
            if not configured:
                item["hint"] = "Run getblock auth login --api " + surface
            elif result["source"] == "environment":
                item["hint"] = "The environment credential overrides this profile's stored key."
            if check_network and configured:
                state.advanced = surface == "advanced"
                if surface == "advanced":
                    cli.get_authenticated_advanced_client().get_tron_orders(limit=1)
                else:
                    cli.get_authenticated_client().get_me()
                item["verified"] = True
                item["verification_scope"] = "orders read" if surface == "advanced" else "account read"
            checks.append(item)
        except (CLIError, GetBlockAPIError) as error:
            checks.append({"name": surface + " authentication", "status": "failed", "message": ux.clean(str(error)),
                           "hint": "Check the credential for this API and retry auth status --api " + surface + " --check."})
    ok = all(item["status"] == "ok" for item in checks)
    emit({"ok": ok, "profile": state.profile, "network_checked": check_network, "checks": checks})
    if not ok:
        raise typer.Exit(1)


@ux.command()
def setup():
    """Sign in, verify Public access, select a configuration and create a token."""
    from getblock import cli
    from getblock.workflows import guide_token
    state = ux.current.get()
    if not ux.is_interactive() or state.output != "table" or state.dry_run or getattr(state, "jq_expression", None):
        raise CLIError("Setup requires a terminal and table output. Use auth login and tokens create with explicit flags in scripts.", 2)
    if not cli.credential_status("public")["configured"]:
        cli.auth_login.__wrapped__(with_key=False, api="public")
    client = cli.get_authenticated_client()
    client.get_me()
    values = guide_token("create_token", dict(protocol=None, network=None, mode=None, api=None, region=None, addon=""))
    command = ["getblock", "--profile", state.profile, "tokens", "create"]
    for name, value in values.items():
        command.extend(["--" + name, value])
    typer.echo("Equivalent command (running it again creates another token): " + shlex.join(command), err=True)
    emit(client.create_token(**values))
