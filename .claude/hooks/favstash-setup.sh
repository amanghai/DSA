#!/bin/bash
# Idempotent setup for the FavStash video-editing skills (skills themselves live in .claude/skills).
# Restores the untracked pieces in a fresh cloud container: HyperFrames/GSAP runtime, yt-dlp, Python extras.
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
LOG="$ROOT/.favstash-studio/setup.log"
mkdir -p "$ROOT/.favstash-studio"
{
  command -v yt-dlp >/dev/null || pip install -q yt-dlp
  python3 - <<'PY' 2>/dev/null || pip install -q numpy opencv-python-headless pdqhash scipy
import numpy, cv2, pdqhash, scipy
PY
  [ -x "$ROOT/.favstash-studio/runtime/node_modules/.bin/hyperframes" ] || \
    node "$ROOT/.claude/skills/edit-video/scripts/init-workspace.mjs" --workspace "$ROOT" --install
} >>"$LOG" 2>&1
exit 0
