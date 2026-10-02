"""Output rendering; JSON is the unchanged API response, human output is redacted."""
import csv
import io
import json
import re
import typer

COLLECTIONS = ("tokens", "nodes", "subscriptions", "protocols", "addons", "plans", "data", "items", "addresses")
COLUMNS = ("id", "name", "status", "protocol", "network", "region", "product_type", "currency", "chain", "trigger_type", "entry_count", "event_id", "attempt", "http_status", "latency_ms", "delivered_at", "address")
SENSITIVE = {"authorization", "api_key", "apikey", "quote_token", "endpoint", "access_token", "token", "password", "secret", "signing_secret"}


def safe_text(value):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", str(value))


def redact(data):
    if isinstance(data, dict):
        return {k: "[redacted]" if k.lower() in SENSITIVE else redact(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact(v) for v in data]
    if isinstance(data, str):
        return safe_text(data)
    return data


def rows_of(data):
    if isinstance(data, dict):
        for key in COLLECTIONS:
            if isinstance(data.get(key), list):
                return [{"address": item} if key == "addresses" and isinstance(item, str) else item for item in data[key]]
        return [data]
    if isinstance(data, list):
        rows = []
        for page in data:
            rows.extend(rows_of(page))
        return rows
    return [{"value": data}]


def scalar(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return safe_text(value)


def render(data, output="table", fields=None):
    if output == "json":
        typer.echo(json.dumps(data, ensure_ascii=False, allow_nan=False))
        return
    if output == "tsv":
        if not fields:
            raise ValueError("TSV requires --fields, for example --fields id,protocol.")
        columns = [field.strip() for field in fields.split(",")]
        if not all(columns) or len(set(columns)) != len(columns):
            raise ValueError("--fields must be unique, comma-separated field names.")
        lines = []
        for row in rows_of(data):
            if not isinstance(row, dict) or any(key not in row for key in columns):
                raise ValueError("A selected TSV field is missing from a result.")
            values = [row[key] for key in columns]
            if any(isinstance(value, (list, dict)) for value in values):
                raise ValueError("TSV fields must be scalar values; use --json for nested data.")
            lines.append(["" if value is None else safe_text(value) for value in values])
        buffer = io.StringIO()
        csv.writer(buffer, delimiter="\t", lineterminator="\n").writerows(lines)
        typer.echo(buffer.getvalue(), nl=False)
        return
    data = redact(data)
    if isinstance(data, dict) and data.get("has_plan") is False:
        typer.echo("No active plan")
        return
    rows = rows_of(data)
    is_list = isinstance(data, list) or (isinstance(data, dict) and any(isinstance(data.get(k), list) for k in COLLECTIONS))
    if is_list and all(isinstance(row, dict) for row in rows):
        columns = [key for key in COLUMNS if any(key in row for row in rows)]
        if not rows:
            typer.echo("No matching results.")
        elif columns:
            values = [[scalar(row.get(key)) for key in columns] for row in rows]
            widths = [max(len(key), *(len(row[i]) for row in values)) for i, key in enumerate(columns)]
            typer.echo("  ".join(key.upper().ljust(widths[i]) for i, key in enumerate(columns)))
            for row in values:
                typer.echo("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
        else:
            detail(rows)
        if isinstance(data, dict) and "total" in data:
            typer.echo(f"Returned {len(rows)} of {data['total']} reported results.")
            if isinstance(data.get("total"), int) and data.get("offset", 0) + len(rows) < data["total"]:
                typer.echo("More results: use --paginate, or continue with --offset " + str(data.get("offset", 0) + len(rows)))
        if isinstance(data, dict) and data.get("next_cursor"):
            typer.echo("More results: use --paginate, or --cursor " + safe_text(data["next_cursor"]))
        if isinstance(data, dict) and "list_id" in data:
            typer.echo("List ID: " + scalar(data["list_id"]))
        return
    detail(data)


def detail(data, indent=0):
    prefix = " " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            label = safe_text(key).replace("_", " ").capitalize()
            if key == "balance_cents":
                label = "Credit balance (cents)"
            if key == "cu":
                label = "Compute units (CU)"
            if isinstance(value, (dict, list)):
                typer.echo(prefix + label + ":")
                detail(value, indent + 2)
            else:
                typer.echo(prefix + label + ": " + scalar(value))
    elif isinstance(data, list):
        if not data:
            typer.echo(prefix + "(none)")
        for item in data:
            if isinstance(item, (dict, list)):
                detail(item, indent + 2)
            else:
                typer.echo(prefix + "- " + scalar(item))
    else:
        typer.echo(prefix + scalar(data))
