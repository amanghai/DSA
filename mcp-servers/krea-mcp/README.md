# Krea MCP Server

An MCP (Model Context Protocol) server for [Krea](https://www.krea.ai)'s
creative API — text-to-image, image-to-image, text/image-to-video, upscaling,
and custom style (LoRA) training — across Krea's 50+ underlying models
(Flux, Nano Banana, Imagen, Ideogram, GPT Image, Veo, Kling, Runway, Hailuo,
Wan, Seedance, Ray, Grok Imagine, and Topaz enhance).

Krea does not (yet) publish an official MCP server, so this wraps its public
REST API (`https://api.krea.ai`, documented at https://docs.krea.ai) directly.

## Why a generic `generate` tool instead of one tool per model?

Krea exposes each model as its own endpoint
(`POST /generate/{image|video|enhance}/{provider}/{model}`) and adds new
models fairly often. Rather than hand-writing (and maintaining) 50+ near-
identical tool schemas, this server ships a `catalog.json` generated from
Krea's own OpenAPI specs (see `scripts/build_catalog.py`), and exposes:

- `krea_list_models` / `krea_get_model_parameters` — discover models and their
  exact parameters from the catalog (no API key or network call needed).
- `krea_generate` — validates your `params` against the catalog (required
  fields present, no unknown fields) and then calls the right endpoint.

This keeps the tool count small while still covering the full model catalog,
and validation errors are caught locally instead of costing a round trip.

## Setup

1. Create a Krea API token at https://www.krea.ai/settings/api-tokens.
2. Install the server (from this directory):

   ```bash
   pip install -e .
   ```

3. Add it to your MCP client. For Claude Code:

   ```bash
   claude mcp add krea -e KREA_API_KEY=your-token-here -- krea-mcp
   ```

   Or, for a `claude_desktop_config.json` / manual `mcpServers` entry:

   ```json
   {
     "mcpServers": {
       "krea": {
         "command": "krea-mcp",
         "env": { "KREA_API_KEY": "your-token-here" }
       }
     }
   }
   ```

   If you didn't `pip install` it into your default environment, point
   `command` at the interpreter/venv instead, e.g.
   `"command": "python3", "args": ["-m", "krea_mcp.server"]` with `PYTHONPATH`
   set to this directory (or run `pip install -e .` inside a venv and point
   `command` at that venv's `krea-mcp` binary).

## Tools

| Tool | Description |
|---|---|
| `krea_list_models` | List/search available image, video, and enhance models |
| `krea_get_model_parameters` | Full parameter schema for one model |
| `krea_generate` | Start a generation job (image/video/enhance) |
| `krea_get_job` | Poll a job's status/result |
| `krea_list_jobs` | List your jobs, with filtering and pagination |
| `krea_cancel_job` | Cancel/delete a job |
| `krea_upload_asset` | Upload a local file, get back a URL to use in `krea_generate` |
| `krea_list_assets` | List uploaded assets |
| `krea_get_asset` | Get one asset's details |
| `krea_delete_asset` | Delete an asset |
| `krea_list_styles` | Search custom styles (trained LoRAs) |
| `krea_train_style` | Train a new custom style from reference images |

## Typical flow

1. `krea_list_models(search="flux")` to find a model.
2. `krea_get_model_parameters(kind="image", provider="bfl", model="flux-1.1-pro")`
   to see its exact fields.
3. `krea_generate(kind="image", provider="bfl", model="flux-1.1-pro", params={"prompt": "...", "width": 1024, "height": 1024})`
   — returns a `job_id` in a pending state.
4. `krea_get_job(job_id=...)` until `status` is `"completed"` (see
   `result.urls`) or pass `webhook_url` to `krea_generate` instead of polling.

## Regenerating the model catalog

Krea's model lineup changes over time. To refresh it:

```bash
pip install -e ".[dev]"
# Update the vendored specs in openapi/ (from Krea's published OpenAPI docs,
# e.g. https://docs.krea.ai/api-reference/openapi.json, split by tag), then:
python3 scripts/build_catalog.py
```

## Notes

- All generation and training endpoints are asynchronous — they return a job
  immediately, not the final result.
- `krea_generate` and `krea_train_style` accept an optional webhook URL
  (`X-Webhook-URL`) so you don't have to poll.
- This server does not implement Krea's node-apps (visual workflow) or style
  sharing endpoints; contributions welcome.
