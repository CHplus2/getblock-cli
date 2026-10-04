"""Optional JSON filtering through the established jq executable; never a shell."""
import json
import shutil
import subprocess
from getblock.ux import CLIError


def prepare(expression):
    executable = shutil.which("jq")
    if not executable:
        raise CLIError("--jq requires jq on PATH. Install jq or omit --jq to export the full JSON response.", 2)
    # Compile without evaluating the user's expression against placeholder data.
    run(executable, "if false then (\n" + expression + "\n) else null end", "null")
    return executable


def run(executable, expression, data):
    try:
        result = subprocess.run([executable, "--monochrome-output", "--compact-output", "--", expression],
                                input=data, capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise CLIError("jq could not complete within 30 seconds; no query output was written.")
    if result.returncode:
        # jq errors can contain values from credential-bearing input.
        raise CLIError("jq could not evaluate the expression. Check its syntax and the response structure; no query output was written.", 2)
    return result.stdout


def apply(executable, expression, data):
    return run(executable, expression, json.dumps(data, ensure_ascii=False, allow_nan=False))
