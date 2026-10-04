"""Per-invocation UX state and reusable command options."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import inspect
import json
import sys
import copy
from contextlib import redirect_stdout
from pathlib import Path

# Typer 0.27 vendors Click. Pin this dependency and exercise parse errors in CI.
from typer.core import _click as click
import typer
from typer.core import TyperGroup

from getblock import config
from getblock.output import render, safe_text
from getblock.http_client import GetBlockAPIError


@dataclass
class Runtime:
    color: str = "auto"
    profile: str = "default"
    output: str = "table"
    timeout: float = 10
    verbose: bool = False
    fields: str | None = None
    dry_run: bool = False
    paginate: bool = False
    max_pages: int | None = None
    mutation_succeeded: bool = False
    operation: str = "getblock"
    secrets: list = field(default_factory=list)
    clients: list = field(default_factory=list)


current = ContextVar("getblock_runtime", default=None)


class CLIError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


class PreviewReady(Exception):
    def __init__(self, data):
        self.data = data


def clean(message, state=None):
    text = safe_text(message)
    for secret in (state or current.get() or Runtime()).secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def report(error, state):
    if state.mutation_succeeded:
        error = CLIError("The server accepted the operation, but response processing or output failed. Inspect the resource before retrying. " + clean(str(error), state), 1)
    status = getattr(error, "status_code", None)
    code = getattr(error, "code", 4 if status == 401 else 1)
    hint = {
        401: "Run getblock auth status --check, then getblock auth login if needed.",
        402: "Review prepaid balance with getblock account balance.",
        429: "Wait before retrying. Billable operations are never retried automatically.",
    }.get(status)
    if status == 401 and getattr(state, "advanced", False):
        hint = "Run getblock auth status --api advanced and see getblock help advanced; Public credentials may not apply."
    detail = {"message": clean(str(error), state), "operation": state.operation, "exit_code": code}
    if state.mutation_succeeded:
        detail["operation_succeeded"] = True
    if status is not None:
        detail["status_code"] = status
    if getattr(error, "request_id", None):
        detail["request_id"] = clean(error.request_id, state)
    if getattr(error, "api_error_code", None):
        detail["api_error_code"] = clean(error.api_error_code, state)
    if getattr(error, "upstream_message", None) is not None:
        detail["upstream_message"] = clean(error.upstream_message, state)
    for field in ("have_cents", "need_cents"):
        value = getattr(error, field, None)
        if isinstance(value, int) and not isinstance(value, bool):
            detail[field] = value
    if hint:
        detail["hint"] = hint
    if state.output == "json":
        typer.echo(json.dumps({"error": detail}), err=True)
    else:
        from getblock.presentation import say
        say("Error: " + detail["message"], style="red", err=True)
        if "upstream_message" in detail:
            typer.echo("Upstream: " + detail["upstream_message"], err=True)
        if status:
            typer.echo(f"Operation: {state.operation}; HTTP {status}", err=True)
        if "request_id" in detail:
            typer.echo("Request ID: " + detail["request_id"], err=True)
        if hint:
            say(hint, style="yellow", err=True)
    return code


class UXGroup(TyperGroup):
    """Render parse/root errors consistently, including before callbacks run."""
    def main(self, args=None, **kwargs):
        args = list(sys.argv[1:] if args is None else args)
        state = Runtime()
        if "--json" in args or any(args[i:i+2] == ["--output", "json"] for i in range(len(args))) or "--output=json" in args:
            state.output = "json"
        state.explicit_json = state.output == "json"
        token = current.set(state)
        standalone = kwargs.pop("standalone_mode", True)
        try:
            result = super().main(args=args, standalone_mode=False, **kwargs)
            if result == 130:
                result = 3
            if standalone:
                raise SystemExit(result if isinstance(result, int) else 0)
            return result
        except click.ClickException as error:
            selected = current.get() or state
            if state.explicit_json:
                selected.output = "json"
            raise SystemExit(report(CLIError(error.format_message(), error.exit_code), selected))
        except (typer.Abort, KeyboardInterrupt):
            raise SystemExit(report(CLIError("Operation cancelled.", 3), current.get() or state))
        except BrokenPipeError:
            return 0
        except (CLIError, GetBlockAPIError, ValueError, OSError) as error:
            if isinstance(error, (ValueError, OSError)):
                error = CLIError(str(error), 2 if isinstance(error, ValueError) else 1)
            raise SystemExit(report(error, current.get() or state))
        finally:
            current.reset(token)


def emit(data):
    state = current.get() or Runtime()
    destination = getattr(state, "quote_destination", None)
    if destination:
        from getblock.workflows import save_quote
        save_quote(destination, state.quote_inputs, data)
        state.quote_destination = None
    if getattr(state, "jq_expression", None) is not None:
        from getblock.json_query import apply
        typer.echo(apply(state.jq_executable, state.jq_expression, data), nl=False)
    else:
        render(data, state.output, state.fields)


def is_interactive():
    return sys.stdin.isatty()


def confirm(message, yes):
    state = current.get() or Runtime()
    if yes:
        return
    if not is_interactive():
        raise CLIError("This operation requires consent. Use --yes for noninteractive execution.", 3)
    try:
        with redirect_stdout(sys.stderr):
            agreed = typer.confirm(f"Profile: {state.profile}. {message}", default=False, err=True)
    except (typer.Abort, EOFError):
        agreed = False
    if not agreed:
        raise CLIError("Operation cancelled.", 3)


def prompt(*args, **kwargs):
    kwargs["err"] = True
    with redirect_stdout(sys.stderr):
        return typer.prompt(*args, **kwargs)


def read_object(path):
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8-sig")
        data = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (OSError, ValueError):
        raise CLIError("Cannot read JSON input. Provide a UTF-8 JSON object with documented fields.", 2)
    if not isinstance(data, dict):
        raise CLIError("Input must be one JSON object, not an array or scalar.", 2)
    return data


def complete_from(values):
    def complete(incomplete: str):
        return [value for value in values if value.startswith(incomplete)]
    return complete


def command(*, collection=False, paid=False, mutation=None, advanced=False, input_fields=None, interactive=False, quote=False, estimate=False, input_template=None):
    """Add the same explicit options to existing Typer handlers without API logic."""
    def decorate(function):
        signature = inspect.signature(function)
        original = signature.parameters
        parameters = list(original.values())
        required = {p.name for p in parameters if getattr(p.default, "default", None) is Ellipsis}
        flexible = set(input_fields or {}) | (required if interactive else set()) | ({"quote_token"} if quote else set()) | ({"request_file"} if input_template else set())
        parameters = [p.replace(default=copy.copy(p.default)) for p in parameters]
        for p in parameters:
            if p.name in flexible and p.name in required and isinstance(p.default, typer.models.OptionInfo):
                p.default.default = None
                alternatives = []
                if input_fields:
                    alternatives.append("--input")
                if input_template:
                    alternatives.append("--generate-input")
                if interactive:
                    alternatives.append("--interactive")
                if quote and p.name == "quote_token":
                    alternatives.append("--quote-file")
                p.default.help = (p.default.help or "") + " Required unless supplied through " + " or ".join(alternatives) + "."
            static = None
            if p.name == "resource_type":
                static = ["energy", "bandwidth"]
            elif p.name == "status" and function.__name__ == "get_tron_orders":
                static = ["pending", "processing", "charged", "failed", "delivered_uncharged"]
            elif p.name == "product_type":
                static = ["plan", "enterprise_plan", "request_package"]
            elif p.name == "api" and function.__name__ == "auth_status":
                static = ["public", "advanced"]
            if static:
                p.default.autocompletion = complete_from(static)
        options = [
            ("output", str | None, typer.Option(None, "--output", help="Output: table, json, tsv.", autocompletion=complete_from(["table", "json", "tsv"]))),
            ("json_output", bool, typer.Option(False, "--json", help="Full JSON response; may contain endpoint credentials.")),
            ("fields", str | None, typer.Option(None, help="TSV scalar fields, for example id,protocol.")),
            ("dry_run", bool, typer.Option(False, "--dry-run", help="Preview a redacted request locally; no network or server validation.")),
            ("jq_expression", str | None, typer.Option(None, "--jq", help="Filter JSON with jq on PATH; requires JSON output. Explicit exports may contain secrets.")),
        ]
        if input_fields or input_template:
            options += [
                ("generate_input", bool, typer.Option(False, "--generate-input", help="Print a placeholder JSON body offline; sends no request.")),
                ("validate_only", bool, typer.Option(False, "--validate-only", help="Validate local request structure offline; does not check server rules.")),
            ]
        if collection:
            options += [("paginate", bool, typer.Option(False, help="Fetch all pages; JSON is an array of page responses.")), ("max_pages", int | None, typer.Option(None, min=1, help="Stop after this many pages; reaching the bound before exhaustion is an error."))]
        if input_fields:
            options += [("input_file", str | None, typer.Option(None, "--input", help="Documented JSON body from file, or - for stdin. Conflicts with body flags."))]
        if paid and "yes" not in original:
            options += [("yes", bool, typer.Option(False, "--yes", "-y", help="Consent to a potentially billable operation."))]
        if interactive:
            options += [("interactive", bool, typer.Option(False, help="Select a configuration from the live catalog (TTY only)."))]
        if quote:
            options += [("quote_file", str | None, typer.Option(None, help="Saved estimate with matching resource, volume and duration."))]
        if estimate:
            options += [("save_quote", str | None, typer.Option(None, help="Save inputs and estimate in a new private quote file; refuses overwrite."))]
        parameters.append(inspect.Parameter("_ctx", inspect.Parameter.KEYWORD_ONLY, annotation=typer.Context))
        for name, annotation, default in options:
            parameters.append(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation, default=default))

        @wraps(function)
        def wrapped(**kwargs):
            parent = current.get() or Runtime()
            state = copy.copy(parent)
            state.clients, state.secrets = [], list(parent.secrets)
            ctx = kwargs.pop("_ctx")
            state.operation = ctx.command_path
            state.advanced = advanced
            selected_output = kwargs.pop("output", None)
            state.output = selected_output or parent.output
            json_output = kwargs.pop("json_output", False)
            if json_output:
                state.output = "json"
            state.fields = kwargs.pop("fields", None)
            state.dry_run = kwargs.pop("dry_run", False)
            state.paginate = kwargs.pop("paginate", False)
            state.max_pages = kwargs.pop("max_pages", None)
            state.jq_expression = kwargs.pop("jq_expression", None)
            validate_only = kwargs.pop("validate_only", False)
            generate_input = kwargs.pop("generate_input", False)
            token = current.set(state)
            try:
                if json_output and selected_output not in (None, "json"):
                    raise CLIError("--json conflicts with --output.", 2)
                config.validate("output", state.output)
                if state.jq_expression is not None:
                    if state.output != "json":
                        raise CLIError("--jq requires --json or --output json.", 2)
                    from getblock.json_query import prepare
                    state.jq_executable = prepare(state.jq_expression)
                if generate_input:
                    if validate_only or state.dry_run or kwargs.get("input_file") or kwargs.get("request_file") or kwargs.get("interactive"):
                        raise CLIError("--generate-input cannot be combined with input, validation, previews or interactive creation.", 2)
                    for name in (input_fields or {}):
                        if getattr(ctx.get_parameter_source(name), "name", None) == "COMMANDLINE":
                            raise CLIError("--generate-input conflicts with explicit body flags.", 2)
                    template = input_template or {key: (1 if original[name].annotation is int else "REPLACE_" + key.upper()) for name, key in input_fields.items() if name in required}
                    typer.echo(json.dumps(template, indent=2))
                    return
                if validate_only:
                    if state.dry_run or kwargs.get("interactive") or kwargs.get("save_quote") or kwargs.get("save_secret"):
                        raise CLIError("--validate-only cannot be combined with dry-run, interactive creation or saved output.", 2)
                    state.dry_run = True
                if state.fields and state.output != "tsv":
                    raise CLIError("--fields requires --output tsv.", 2)
                if state.output == "tsv" and not state.fields:
                    raise CLIError("TSV requires --fields.", 2)
                if state.fields:
                    columns = [name.strip() for name in state.fields.split(",")]
                    if not all(columns) or len(columns) != len(set(columns)):
                        raise CLIError("--fields must be unique, nonempty scalar field names.", 2)
                if state.max_pages and not state.paginate:
                    raise CLIError("--max-pages requires --paginate.", 2)
                if state.dry_run and state.paginate:
                    raise CLIError("Preview one page at a time; omit --paginate with --dry-run.", 2)
                source = kwargs.pop("input_file", None)
                if source:
                    for name in input_fields:
                        if getattr(ctx.get_parameter_source(name), "name", None) == "COMMANDLINE":
                            raise CLIError("--input conflicts with explicit request fields.", 2)
                    data = read_object(source)
                    allowed = set(input_fields.values())
                    if set(data) - allowed:
                        raise CLIError("Input contains unsupported request fields.", 2)
                    for name, key in input_fields.items():
                        if key in data:
                            value = data[key]
                            expected = original[name].annotation
                            if expected is int and (not isinstance(value, int) or isinstance(value, bool)):
                                raise CLIError(f"Input field {key} must be an integer.", 2)
                            if expected in (str, str | None) and not isinstance(value, str):
                                raise CLIError(f"Input field {key} must be a string.", 2)
                            kwargs[name] = value
                guided = kwargs.pop("interactive", False)
                if guided:
                    if state.dry_run or source:
                        raise CLIError("--interactive cannot be combined with --dry-run or --input.", 2)
                    from getblock.workflows import guide_token
                    kwargs = guide_token(function.__name__, kwargs)
                quote_path = kwargs.pop("quote_file", None)
                if quote_path:
                    if kwargs.get("quote_token") is not None or source:
                        raise CLIError("--quote-file conflicts with --quote-token or --input.", 2)
                    from getblock.workflows import load_quote
                    kwargs["quote_token"] = load_quote(quote_path, function.__name__, kwargs)
                for name in required:
                    if kwargs.get(name) is None:
                        raise CLIError("Missing required value: " + name.replace("_", "-") + ". See --help.", 2)
                for name in ("quote_token",):
                    if kwargs.get(name):
                        state.secrets.append(kwargs[name])
                yes = kwargs.get("yes", False)
                if paid and "yes" not in original:
                    kwargs.pop("yes", None)
                save_quote = kwargs.pop("save_quote", None)
                if save_quote and state.dry_run:
                    raise CLIError("--save-quote requires a real estimate; omit --dry-run.", 2)
                if save_quote:
                    if Path(save_quote).exists():
                        raise CLIError("Quote file already exists; choose a new path.", 2)
                if (paid or mutation) and not state.dry_run:
                    from getblock import cli
                    # Check availability/credentials before asking permission.
                    (cli.get_authenticated_advanced_client if advanced else cli.get_authenticated_client)()
                    target = kwargs.get("webhook_id") or kwargs.get("list_id") or kwargs.get("target_address", kwargs.get("token_id", kwargs.get("address", kwargs.get("contract_address", kwargs.get("tx", "")))))
                    consequence = mutation or "This may consume prepaid balance or Credits."
                    summary = ", ".join(f"{name}={safe_text(kwargs[name])}" for name in ("network", "volume", "duration") if kwargs.get(name) is not None)
                    confirm(f"{function.__name__.replace('_', ' ')} {safe_text(target)}{(' (' + summary + ')') if summary else ''}? {consequence}", yes)
                if save_quote:
                    state.quote_destination = save_quote
                    state.quote_inputs = {"resourceType": kwargs["resource_type"], "volume": kwargs["volume"], "duration": kwargs["duration"]}
                return function(**kwargs)
            except BrokenPipeError:
                return
            except PreviewReady as preview:
                emit({"valid": True, "scope": "local request structure only", "server_validated": False} if validate_only else preview.data)
            except (CLIError, GetBlockAPIError, ValueError, OSError) as error:
                if isinstance(error, (ValueError, OSError)):
                    error = CLIError(str(error), 2 if isinstance(error, ValueError) else 1)
                code = report(error, state)
                raise typer.Exit(code)
            finally:
                for client in state.clients:
                    client.client.close()
                current.reset(token)
        wrapped.__signature__ = signature.replace(parameters=parameters)
        return wrapped
    return decorate
