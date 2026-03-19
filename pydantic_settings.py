from __future__ import annotations

import os
from pathlib import Path


class SettingsConfigDict(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BaseSettings:
    model_config = SettingsConfigDict()

    def __init__(self, **overrides):
        config = getattr(self.__class__, "model_config", {}) or {}
        env_values = _load_env_file(config.get("env_file"))

        for name, value in self.__class__.__dict__.items():
            if name.startswith("_") or callable(value) or name == "model_config":
                continue

            resolved = overrides.get(name)
            if resolved is None and name in os.environ:
                resolved = os.environ[name]
            if resolved is None and name in env_values:
                resolved = env_values[name]
            if resolved is None:
                resolved = value

            annotation = getattr(self.__class__, "__annotations__", {}).get(name)
            setattr(self, name, _coerce_value(resolved, annotation))


def _load_env_file(env_file):
    if not env_file:
        return {}
    path = Path(env_file)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return {}

    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _coerce_value(value, annotation):
    if annotation is None:
        return value
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    target = annotation
    if origin is not None and args:
        non_none = [arg for arg in args if arg is not type(None)]
        if non_none:
            target = non_none[0]
    if target is bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}
    if target is int:
        return int(value)
    if target is float:
        return float(value)
    if target is str:
        return str(value)
    return value
