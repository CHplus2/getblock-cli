"""User-level, non-secret CLI configuration. No repository config is loaded."""
import json
import math
import os
import re
from pathlib import Path

DEFAULTS = {"output": "table", "timeout": 10.0}


def profile_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise ValueError("Profile must be 1–64 letters, digits, dots, underscores or hyphens.")
    return value


def config_path():
    override = os.environ.get("GETBLOCK_CONFIG_DIR")
    if override:
        return Path(override) / "config.json"
    base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    return base / "getblock" / "config.json"


def validate(key, value):
    if key == "output" and value in ("table", "json", "tsv"):
        return value
    if key == "timeout" and not isinstance(value, bool):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0
        if math.isfinite(number) and number > 0:
            return number
    raise ValueError("Supported settings: output=table|json|tsv, timeout=positive seconds.")


def load():
    path = config_path()
    if not path.exists():
        return {"profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) - {"profiles"}:
            raise ValueError()
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError()
        for name, settings in profiles.items():
            profile_name(name)
            if not isinstance(settings, dict):
                raise ValueError()
            for key, value in settings.items():
                validate(key, value)
        return data
    except (ValueError, OSError) as error:
        raise ValueError(f"Cannot read configuration at {path}. Check its format and permissions.") from error


def resolve(profile, output=None, timeout=None):
    saved = load().get("profiles", {}).get(profile, {})
    result, origins = {}, {}
    for key, flag in (("output", output), ("timeout", timeout)):
        env = os.environ.get("GETBLOCK_" + key.upper())
        if flag is not None:
            value, origin = flag, "flag"
        elif env is not None:
            value, origin = env, "environment"
        elif key in saved:
            value, origin = saved[key], f"profile:{profile}"
        else:
            value, origin = DEFAULTS[key], "default"
        result[key], origins[key] = validate(key, value), origin
    return result, origins


def save(profile, key, value):
    value = validate(key, value)
    data = load()
    data.setdefault("profiles", {}).setdefault(profile_name(profile), {})[key] = value
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
