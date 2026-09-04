#!/usr/bin/env python3
"""MCP server for the Krea AI creative API (https://api.krea.ai).

Exposes Krea's async job-based generation API (image, video, and Topaz
upscale/enhance models), plus job, asset, and custom-style (LoRA) management,
as MCP tools.

Authentication: set the KREA_API_KEY environment variable to a token created
at https://www.krea.ai/settings/api-tokens (Bearer auth).

The 50+ generation models are not hand-coded here: they are loaded from
catalog.json, which is generated from Krea's own OpenAPI specs by
scripts/build_catalog.py. Use `krea_list_models` / `krea_get_model_parameters`
to discover what is available and what each model accepts before calling
`krea_generate`.
"""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

mcp = FastMCP("krea_mcp")

KREA_API_BASE = os.environ.get("KREA_API_BASE", "https://api.krea.ai")
REQUEST_TIMEOUT = 60.0
UPLOAD_TIMEOUT = 180.0

CATALOG_PATH = Path(__file__).parent / "catalog.json"
CATALOG: dict[str, dict[str, Any]] = json.loads(CATALOG_PATH.read_text())

GenerationKind = Literal["image", "video", "enhance"]
JobStatus = Literal[
    "backlogged",
    "queued",
    "scheduled",
    "processing",
    "sampling",
    "intermediate-complete",
    "completed",
    "failed",
    "cancelled",
]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _api_key() -> str:
    key = os.environ.get("KREA_API_KEY")
    if not key:
        raise RuntimeError(
            "KREA_API_KEY is not set. Create a token at "
            "https://www.krea.ai/settings/api-tokens and set it as the "
            "KREA_API_KEY environment variable for this MCP server."
        )
    return key


def _auth_headers(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_api_key()}"}
    if extra:
        headers.update(extra)
    return headers


def _format_http_error(e: httpx.HTTPStatusError) -> str:
    status = e.response.status_code
    try:
        detail = e.response.json().get("error", e.response.text)
    except Exception:
        detail = e.response.text

    hints = {
        400: "The request body is invalid.",
        401: "Not authenticated - check that KREA_API_KEY is set to a valid token.",
        402: "Out of Krea compute credits.",
        404: "Resource not found (or you don't have access to it).",
        429: "Too many concurrent jobs - wait for one to finish or cancel one.",
    }
    hint = hints.get(status, f"Request failed with HTTP {status}.")
    return f"Error: {hint} Details: {detail}"


async def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    files: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    timeout: float = REQUEST_TIMEOUT,
) -> Any:
    """Shared request helper for every Krea API call."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                f"{KREA_API_BASE}{path}",
                json=json_body,
                params=params,
                headers=_auth_headers(headers),
                files=files,
                data=data,
            )
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"__error__": _format_http_error(e)}
    except httpx.TimeoutException:
        return {"__error__": "Error: Request to Krea timed out. Please try again."}
    except RuntimeError as e:
        return {"__error__": f"Error: {e}"}


def _is_error(result: Any) -> Optional[str]:
    if isinstance(result, dict) and "__error__" in result:
        return result["__error__"]
    return None


def _to_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _catalog_entry(kind: GenerationKind, provider: str, model: str) -> Optional[dict[str, Any]]:
    return CATALOG.get(kind, {}).get(f"{provider}/{model}")


def _closest_model_hint(kind: GenerationKind, provider: str, model: str) -> str:
    key = f"{provider}/{model}".lower()
    candidates = [k for k in CATALOG.get(kind, {}) if key in k.lower() or provider.lower() in k.lower()]
    if not candidates:
        candidates = sorted(CATALOG.get(kind, {}).keys())[:10]
    return ", ".join(candidates[:10])


# ---------------------------------------------------------------------------
# Model discovery tools
# ---------------------------------------------------------------------------


class ListModelsInput(BaseModel):
    """Input model for listing available Krea generation models."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    kind: Optional[GenerationKind] = Field(
        default=None,
        description="Restrict results to 'image', 'video', or 'enhance' models. Omit to list all kinds.",
    )
    search: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring to filter by provider, model id, or summary (e.g. 'flux', 'veo', 'upscale').",
        max_length=100,
    )


@mcp.tool(
    name="krea_list_models",
    annotations={
        "title": "List Krea Generation Models",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def krea_list_models(params: ListModelsInput) -> str:
    """List the image, video, and enhance (upscale) models Krea's API supports.

    This reads a bundled catalog (generated from Krea's own OpenAPI specs), so
    it works without an API key and without a network call. Use this first to
    find a model's exact `provider`/`model` identifiers, then call
    `krea_get_model_parameters` for its full parameter schema before calling
    `krea_generate`.

    Args:
        params (ListModelsInput): Validated input containing:
            - kind (Optional[str]): 'image', 'video', or 'enhance' to filter by kind
            - search (Optional[str]): substring filter over provider/model/summary

    Returns:
        str: JSON list of objects, each with:
        {
            "kind": str,             # "image" | "video" | "enhance"
            "provider": str,         # e.g. "bfl", "google", "kling"
            "model": str,            # e.g. "flux-1.1-pro", "veo-3"
            "summary": str,          # short human name, e.g. "Flux 1.1 Pro"
            "description": str,      # one-line description
            "required": [str],       # required request body fields
            "supports_webhook": bool # whether X-Webhook-URL is accepted
        }
    """
    kinds = [params.kind] if params.kind else ["image", "video", "enhance"]
    needle = params.search.lower() if params.search else None

    results = []
    for kind in kinds:
        for key, entry in CATALOG.get(kind, {}).items():
            if needle and needle not in key.lower() and needle not in entry.get("summary", "").lower():
                continue
            results.append(
                {
                    "kind": kind,
                    "provider": entry["provider"],
                    "model": entry["model"],
                    "summary": entry["summary"],
                    "description": entry["description"],
                    "required": entry["required"],
                    "supports_webhook": entry["supports_webhook"],
                }
            )

    if not results:
        return f"No models found matching search={params.search!r} kind={params.kind!r}."
    return _to_json({"count": len(results), "models": results})


class GetModelParametersInput(BaseModel):
    """Input model for fetching one model's full parameter schema."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    kind: GenerationKind = Field(..., description="'image', 'video', or 'enhance'.")
    provider: str = Field(..., description="Provider id from krea_list_models, e.g. 'bfl', 'google', 'kling'.", min_length=1)
    model: str = Field(..., description="Model id from krea_list_models, e.g. 'flux-1.1-pro', 'veo-3'.", min_length=1)


@mcp.tool(
    name="krea_get_model_parameters",
    annotations={
        "title": "Get Krea Model Parameter Schema",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def krea_get_model_parameters(params: GetModelParametersInput) -> str:
    """Get the full request-body parameter schema for one Krea generation model.

    Call this before `krea_generate` to see exactly which fields a model
    accepts (types, defaults, enums, min/max), so the `params` dict you build
    for `krea_generate` is valid on the first try.

    Args:
        params (GetModelParametersInput): Validated input containing:
            - kind (str): 'image', 'video', or 'enhance'
            - provider (str): provider id, e.g. 'bfl'
            - model (str): model id, e.g. 'flux-1.1-pro'

    Returns:
        str: JSON object with the model's endpoint, summary, description,
        required fields, supports_webhook flag, and a `properties` map of
        JSON-Schema-like field definitions (type/description/enum/default/
        minimum/maximum/etc), or an error message if the model is unknown.
    """
    entry = _catalog_entry(params.kind, params.provider, params.model)
    if entry is None:
        hint = _closest_model_hint(params.kind, params.provider, params.model)
        return (
            f"Error: No {params.kind} model '{params.provider}/{params.model}'. "
            f"Did you mean one of: {hint}? Call krea_list_models for the full list."
        )
    return _to_json(entry)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class GenerateInput(BaseModel):
    """Input model for starting a Krea generation job."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", populate_by_name=True)

    kind: GenerationKind = Field(..., description="'image', 'video', or 'enhance'.")
    provider: str = Field(..., description="Provider id from krea_list_models, e.g. 'bfl', 'google', 'kling', 'topaz'.", min_length=1)
    model: str = Field(..., description="Model id from krea_list_models, e.g. 'flux-1.1-pro', 'veo-3', 'standard-enhance'.", min_length=1)
    request_params: dict[str, Any] = Field(
        default_factory=dict,
        alias="params",
        description=(
            "Request body for the model, e.g. {\"prompt\": \"a red fox in snow\", "
            "\"width\": 1024, \"height\": 1024}. Field names and constraints come "
            "from krea_get_model_parameters; unknown fields are rejected."
        ),
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Optional URL Krea will POST to when the job finishes, instead of (or in addition to) polling krea_get_job.",
    )


@mcp.tool(
    name="krea_generate",
    annotations={
        "title": "Generate Image, Video, or Enhancement with Krea",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def krea_generate(params: GenerateInput) -> str:
    """Start an async Krea generation job (image, video, or Topaz enhance/upscale).

    Krea's generate endpoints are asynchronous: this returns immediately with a
    job in a pending state (e.g. "queued"). Poll `krea_get_job` with the
    returned `job_id` (or pass `webhook_url` to be notified) until `status` is
    "completed" (result.urls has the output) or "failed"/"cancelled".

    Args:
        params (GenerateInput): Validated input containing:
            - kind (str): 'image', 'video', or 'enhance'
            - provider (str): provider id, e.g. 'bfl'
            - model (str): model id, e.g. 'flux-1.1-pro'
            - params (Dict[str, Any]): the model's request body, e.g. {"prompt": "..."}
            - webhook_url (Optional[str]): URL to notify on completion

    Returns:
        str: JSON job object on success:
        {
            "job_id": str,        # UUID, pass to krea_get_job / krea_cancel_job
            "status": str,        # e.g. "queued"
            "created_at": str,    # ISO 8601 timestamp
            "completed_at": null,
            "result": null
        }

        Or "Error: ..." describing what to fix, such as missing required
        fields, unknown fields, an unknown model, or an API error (invalid
        request, unauthenticated, out of credits, or too many concurrent jobs).

    Examples:
        - Use when: "Generate an image of a cyberpunk city with Flux" ->
          kind="image", provider="bfl", model="flux-1.1-pro",
          params={"prompt": "a cyberpunk city at night", "width": 1024, "height": 1024}
        - Don't use when: you haven't checked krea_get_model_parameters yet and
          are guessing at field names - check first to avoid a wasted job.
    """
    entry = _catalog_entry(params.kind, params.provider, params.model)
    if entry is None:
        hint = _closest_model_hint(params.kind, params.provider, params.model)
        return (
            f"Error: No {params.kind} model '{params.provider}/{params.model}'. "
            f"Did you mean one of: {hint}? Call krea_list_models for the full list."
        )

    body = params.request_params
    missing = [f for f in entry["required"] if f not in body]
    if missing:
        return (
            f"Error: Missing required field(s) {missing} for {params.provider}/{params.model}. "
            f"Call krea_get_model_parameters(kind={params.kind!r}, provider={params.provider!r}, "
            f"model={params.model!r}) to see the full schema."
        )

    unknown = sorted(set(body) - set(entry["properties"]))
    if unknown:
        return (
            f"Error: Unknown field(s) {unknown} for {params.provider}/{params.model}. "
            f"Valid fields are: {sorted(entry['properties'])}."
        )

    headers = {"X-Webhook-URL": params.webhook_url} if params.webhook_url else None
    result = await _request("POST", entry["endpoint"], json_body=body, headers=headers)
    if error := _is_error(result):
        return error
    return _to_json(result)


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------


class GetJobInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    job_id: str = Field(..., description="Job UUID returned by krea_generate or krea_list_jobs.", min_length=1)


@mcp.tool(
    name="krea_get_job",
    annotations={
        "title": "Get Krea Job Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_get_job(params: GetJobInput) -> str:
    """Get the current status and result of a Krea generation/training job.

    Args:
        params (GetJobInput): Validated input containing:
            - job_id (str): the job's UUID

    Returns:
        str: JSON job object:
        {
            "job_id": str,
            "status": str,          # one of: backlogged, queued, scheduled,
                                     # processing, sampling, intermediate-complete,
                                     # completed, failed, cancelled
            "created_at": str,
            "completed_at": Optional[str],
            "result": {
                "urls": [str],      # output URLs, once completed
                "style_id": str     # present for completed style-training jobs
            } | null
        }
        Or "Error: ..." if the job does not exist or isn't yours.
    """
    result = await _request("GET", f"/jobs/{params.job_id}")
    if error := _is_error(result):
        return error
    return _to_json(result)


class ListJobsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Optional[JobStatus] = Field(default=None, description="Filter to jobs in this status.")
    types: Optional[str] = Field(
        default=None,
        description="Comma-separated job type filter, e.g. 'flux,k1,externalImage'.",
    )
    cursor: Optional[str] = Field(default=None, description="ISO 8601 timestamp cursor; returns jobs created before this time.")
    limit: int = Field(default=100, description="Max jobs to return.", ge=1, le=1000)


@mcp.tool(
    name="krea_list_jobs",
    annotations={
        "title": "List Krea Jobs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_list_jobs(params: ListJobsInput) -> str:
    """List your Krea jobs (generation and style-training), most recent first.

    Args:
        params (ListJobsInput): Validated input containing:
            - status (Optional[str]): filter by job status
            - types (Optional[str]): comma-separated job type filter
            - cursor (Optional[str]): pagination cursor from a previous call's next_cursor
            - limit (int): max results, 1-1000 (default 100)

    Returns:
        str: JSON object: {"items": [job, ...], "next_cursor": str | null}.
        Pass next_cursor as `cursor` to fetch the next page.
    """
    query = {
        "status": params.status,
        "types": params.types,
        "cursor": params.cursor,
        "limit": params.limit,
    }
    result = await _request("GET", "/jobs", params={k: v for k, v in query.items() if v is not None})
    if error := _is_error(result):
        return error
    return _to_json(result)


@mcp.tool(
    name="krea_cancel_job",
    annotations={
        "title": "Cancel/Delete a Krea Job",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_cancel_job(params: GetJobInput) -> str:
    """Cancel (delete) a Krea job by ID. Cancelled jobs are not billed.

    Args:
        params (GetJobInput): Validated input containing:
            - job_id (str): the job's UUID

    Returns:
        str: "Job <id> cancelled." on success, or "Error: ..." if the job
        does not exist or you don't have access to it.
    """
    result = await _request("DELETE", f"/jobs/{params.job_id}")
    if error := _is_error(result):
        return error
    return f"Job {params.job_id} cancelled."


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


class UploadAssetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    file_path: str = Field(
        ...,
        description="Absolute path to a local file to upload (JPEG, PNG, WebP, HEIC, MP4, MOV, WebM, GLB, WAV, or MP3; max 75MB).",
        min_length=1,
    )
    description: Optional[str] = Field(default=None, description="Optional description to store with the asset.")


@mcp.tool(
    name="krea_upload_asset",
    annotations={
        "title": "Upload Asset to Krea",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def krea_upload_asset(params: UploadAssetInput) -> str:
    """Upload a local image, video, audio, or 3D model file to Krea's asset store.

    Use this to get a stable https URL for a local file (e.g. a reference
    image) that you can then pass into `krea_generate` params such as
    `image_url` / `style_images` / `reference_images`.

    Args:
        params (UploadAssetInput): Validated input containing:
            - file_path (str): absolute path to the local file (max 75MB)
            - description (Optional[str]): optional description

    Returns:
        str: JSON asset object: {"id": str, "image_url": str, "uploaded_at": str,
        "width": Optional[int], "height": Optional[int], "size_bytes": Optional[int],
        "mime_type": Optional[str]}, or "Error: ..." if the file is missing,
        too large, or an unsupported type.
    """
    path = Path(params.file_path).expanduser()
    if not path.is_file():
        return f"Error: File not found: {path}"

    size = path.stat().st_size
    if size > 75 * 1024 * 1024:
        return f"Error: File is {size / (1024 * 1024):.1f}MB, which exceeds Krea's 75MB upload limit."

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = {"description": params.description} if params.description else None

    with path.open("rb") as f:
        result = await _request(
            "POST",
            "/assets",
            files={"file": (path.name, f, mime_type)},
            data=data,
            timeout=UPLOAD_TIMEOUT,
        )
    if error := _is_error(result):
        return error
    return _to_json(result)


class ListAssetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cursor: Optional[str] = Field(default=None, description="Pagination cursor from a previous call's next_cursor.")
    limit: int = Field(default=100, description="Max assets to return.", ge=1, le=1000)


@mcp.tool(
    name="krea_list_assets",
    annotations={
        "title": "List Krea Assets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_list_assets(params: ListAssetsInput) -> str:
    """List assets you've uploaded to Krea, most recent first.

    Args:
        params (ListAssetsInput): Validated input containing:
            - cursor (Optional[str]): pagination cursor
            - limit (int): max results, 1-1000 (default 100)

    Returns:
        str: JSON object: {"items": [asset, ...], "next_cursor": str | null}.
    """
    query = {"cursor": params.cursor, "limit": params.limit}
    result = await _request("GET", "/assets", params={k: v for k, v in query.items() if v is not None})
    if error := _is_error(result):
        return error
    return _to_json(result)


class AssetIdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    asset_id: str = Field(..., description="Asset UUID from krea_upload_asset or krea_list_assets.", min_length=1)


@mcp.tool(
    name="krea_get_asset",
    annotations={
        "title": "Get Krea Asset",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_get_asset(params: AssetIdInput) -> str:
    """Get details for one uploaded Krea asset by ID.

    Args:
        params (AssetIdInput): Validated input containing:
            - asset_id (str): the asset's UUID

    Returns:
        str: JSON asset object, or "Error: ..." if not found.
    """
    result = await _request("GET", f"/assets/{params.asset_id}")
    if error := _is_error(result):
        return error
    return _to_json(result)


@mcp.tool(
    name="krea_delete_asset",
    annotations={
        "title": "Delete Krea Asset",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_delete_asset(params: AssetIdInput) -> str:
    """Permanently delete an uploaded Krea asset by ID.

    Args:
        params (AssetIdInput): Validated input containing:
            - asset_id (str): the asset's UUID

    Returns:
        str: "Asset <id> deleted." on success, or "Error: ..." if not found.
    """
    result = await _request("DELETE", f"/assets/{params.asset_id}")
    if error := _is_error(result):
        return error
    return f"Asset {params.asset_id} deleted."


# ---------------------------------------------------------------------------
# Styles (custom LoRAs)
# ---------------------------------------------------------------------------


class ListStylesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", populate_by_name=True)

    query_filter: Optional[
        Literal["all", "user", "community", "krea", "shared", "unapproved", "editor", "gallery", "public"]
    ] = Field(default=None, alias="filter", description="Which styles to include (default 'all').")
    liked: Optional[bool] = Field(default=None, description="Only styles you've liked.")
    model_name: Optional[str] = Field(default=None, alias="model", description="Filter by compatible base model, e.g. 'flux_dev'.")
    cursor: Optional[str] = Field(default=None, description="Pagination cursor.")
    limit: int = Field(default=100, description="Max styles to return.", ge=1, le=1000)


@mcp.tool(
    name="krea_list_styles",
    annotations={
        "title": "List/Search Krea Styles",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def krea_list_styles(params: ListStylesInput) -> str:
    """Search custom styles (trained LoRAs) available on Krea.

    Returns Krea-official, community, and/or your own trained styles. Use a
    style's `id` as an entry in a generation model's `styles` parameter
    (e.g. {"id": "<style_id>", "strength": 1}).

    Args:
        params (ListStylesInput): Validated input containing:
            - filter (Optional[str]): 'all' (default), 'user', 'community', 'krea', 'shared', 'unapproved', 'editor', 'gallery', or 'public'
            - liked (Optional[bool]): only styles you've liked
            - model (Optional[str]): filter by compatible base model, e.g. 'flux_dev'
            - cursor (Optional[str]): pagination cursor
            - limit (int): max results, 1-1000 (default 100)

    Returns:
        str: JSON object: {"items": [style, ...], "next_cursor": str | null},
        where each style has id, title, urls (preview images), public, prompt,
        models (compatible base models), owner, like_count, created_at.
    """
    query = {
        "filter": params.query_filter,
        "liked": params.liked,
        "model": params.model_name,
        "cursor": params.cursor,
        "limit": params.limit,
    }
    result = await _request("GET", "/styles", params={k: v for k, v in query.items() if v is not None})
    if error := _is_error(result):
        return error
    return _to_json(result)


class TrainStyleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", populate_by_name=True)

    name: str = Field(..., description="Name for the trained style.", min_length=1)
    urls: list[str] = Field(
        ...,
        description="URLs of training images (upload local files with krea_upload_asset first to get URLs). 5-20 images recommended.",
        min_length=1,
    )
    base_model: Literal["flux_dev", "flux_schnell", "wan", "wan22", "qwen", "z-image"] = Field(
        default="flux_dev",
        alias="model",
        description="Base model to train the LoRA on. qwen/z-image use a separate, simpler training path.",
    )
    training_type: Literal["Style", "Object", "Character", "Default"] = Field(
        default="Default",
        alias="type",
        description="What the style should capture. qwen/z-image do not support 'Default' (use 'Style' there).",
    )
    trigger_word: Optional[str] = Field(default=None, description="Word to trigger the style in prompts.")
    learning_rate: Optional[float] = Field(default=None, description="Training learning rate (flux/wan models only).")
    max_train_steps: Optional[int] = Field(default=None, description="Number of training steps.", ge=1, le=2000)
    batch_size: Optional[int] = Field(default=None, description="Training batch size (flux/wan models only).", ge=1)


@mcp.tool(
    name="krea_train_style",
    annotations={
        "title": "Train a Custom Krea Style (LoRA)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def krea_train_style(params: TrainStyleInput) -> str:
    """Start training a custom style (LoRA) from a set of reference images.

    This is an async job like `krea_generate` - poll `krea_get_job` with the
    returned `job_id`; once `status` is "completed", `result.style_id`
    identifies the new style for use in generation calls. Trained styles are
    private until shared with your workspace (via the Krea app).

    Args:
        params (TrainStyleInput): Validated input containing:
            - name (str): name for the style
            - urls (List[str]): training image URLs (5-20 recommended)
            - model (str): 'flux_dev' (default), 'flux_schnell', 'wan', 'wan22', 'qwen', or 'z-image'
            - type (str): 'Default' (default), 'Style', 'Object', or 'Character' - qwen/z-image require 'Style'/'Object'/'Character'
            - trigger_word (Optional[str]): word to trigger the style
            - learning_rate (Optional[float]): flux/wan models only
            - max_train_steps (Optional[int]): 1-2000
            - batch_size (Optional[int]): flux/wan models only

    Returns:
        str: JSON job object (job_id, status, created_at), or "Error: ..." on
        an invalid combination of model/type/fields or an API error.
    """
    body: dict[str, Any] = {
        "name": params.name,
        "urls": params.urls,
        "model": params.base_model,
        "type": params.training_type,
    }
    if params.trigger_word is not None:
        body["trigger_word"] = params.trigger_word
    if params.max_train_steps is not None:
        body["max_train_steps"] = params.max_train_steps
    if params.base_model in ("qwen", "z-image"):
        if params.training_type == "Default":
            return "Error: model 'qwen'/'z-image' require type to be 'Style', 'Object', or 'Character' (not 'Default')."
        if params.learning_rate is not None or params.batch_size is not None:
            return "Error: learning_rate/batch_size are only supported for flux_dev, flux_schnell, wan, and wan22 models."
    else:
        if params.learning_rate is not None:
            body["learning_rate"] = params.learning_rate
        if params.batch_size is not None:
            body["batch_size"] = params.batch_size

    result = await _request("POST", "/styles/train", json_body=body)
    if error := _is_error(result):
        return error
    return _to_json(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
