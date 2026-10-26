#!/usr/bin/env python3
"""Build catalog.json from the vendored Krea OpenAPI specs.

Krea exposes 50+ generation models, each as its own POST endpoint under
/generate/{kind}/{provider}/{model}. Hand-maintaining a tool per model (or a
hand-copied parameter table) would drift from reality the moment Krea adds or
tweaks a model, so instead we parse the vendored OpenAPI YAML files that ship
in ./openapi (snapshotted from https://github.com/api-evangelist/krea-ai) into
one compact JSON catalog that the MCP server loads at startup.

Re-run this after refreshing the vendored specs:
    python3 scripts/build_catalog.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
OPENAPI_DIR = ROOT / "openapi"
OUTPUT_PATH = ROOT / "krea_mcp" / "catalog.json"

SPEC_FILES = {
    "image": "krea-ai-image-api-openapi.yml",
    "video": "krea-ai-video-api-openapi.yml",
    "enhance": "krea-ai-image-enhance-api-openapi.yml",
}

PATH_RE = re.compile(r"^/generate/(image|video|enhance)/([^/]+)/([^/]+)$")

# Only keep schema keys that matter for building a valid request; drop verbose
# OpenAPI-isms (x-krea-* extensions, nested "items"/"properties" beyond one
# level) to keep the catalog small enough to hand to a model as context.
KEPT_SCHEMA_KEYS = (
    "type",
    "description",
    "enum",
    "default",
    "minimum",
    "maximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "format",
    "pattern",
)


def _clean_description(text: str | None) -> str:
    if not text:
        return ""
    # Drop the deprecated-field-aliases blockquotes and compute-unit tables;
    # keep just the leading prose line(s) describing the model.
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") or stripped.startswith(">"):
            break
        lines.append(stripped)
    return " ".join(lines).strip()


def _simplify_property(schema: dict[str, Any]) -> dict[str, Any]:
    simplified: dict[str, Any] = {}
    for key in KEPT_SCHEMA_KEYS:
        if key in schema:
            simplified[key] = schema[key]
    if "items" in schema and isinstance(schema["items"], dict):
        item_schema = schema["items"]
        item_summary: dict[str, Any] = {"type": item_schema.get("type", "object")}
        if "properties" in item_schema:
            item_summary["properties"] = {
                name: _simplify_property(sub)
                for name, sub in item_schema["properties"].items()
            }
            if "required" in item_schema:
                item_summary["required"] = item_schema["required"]
        simplified["items"] = item_summary
    return simplified


def parse_spec(kind: str, path: Path) -> dict[str, Any]:
    spec = yaml.safe_load(path.read_text())
    models: dict[str, Any] = {}

    for route, methods in spec.get("paths", {}).items():
        match = PATH_RE.match(route)
        if not match or match.group(1) != kind:
            continue
        _, provider, model = match.groups()

        post = methods.get("post")
        if not post:
            continue

        request_schema = (
            post.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        properties = {
            name: _simplify_property(prop)
            for name, prop in request_schema.get("properties", {}).items()
        }

        supports_webhook = any(
            p.get("name") == "X-Webhook-URL" for p in post.get("parameters", [])
        )

        key = f"{provider}/{model}"
        models[key] = {
            "provider": provider,
            "model": model,
            "endpoint": route,
            "summary": post.get("summary", ""),
            "description": _clean_description(post.get("description")),
            "required": request_schema.get("required", []),
            "properties": properties,
            "supports_webhook": supports_webhook,
        }

    return models


def main() -> None:
    catalog: dict[str, Any] = {}
    for kind, filename in SPEC_FILES.items():
        spec_path = OPENAPI_DIR / filename
        if not spec_path.exists():
            raise SystemExit(f"Missing vendored spec: {spec_path}")
        catalog[kind] = parse_spec(kind, spec_path)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n")

    counts = {kind: len(models) for kind, models in catalog.items()}
    print(f"Wrote {OUTPUT_PATH} ({sum(counts.values())} models: {counts})")


if __name__ == "__main__":
    main()
