#!/usr/bin/env python3
"""Verify a delivered kinetic-multicam prompt against the frozen template.

Usage: python verify_prompt.py <delivered_prompt.txt>

PASS iff:
  - head (everything through "Follow this timeline:") and tail ("Important
    requirements:" onward) match the canonical template in ../SKILL.md
    byte-for-byte;
  - every timeline block is exactly 4 lines:
        From [<n>s] to [<n>s]
        Display the kinetic super:
        "<SUPER TEXT>"
        <a position line from the template or the presets table>
  - the safe-zone sentence (all text inside the central band of the frame) is present;
  - the LAST block uses the back-to-original position line;
  - timestamps ascend and adjacent blocks share their boundary.

Soft reports (never fail): block count, opening-hold length, first snap time.
Exit 0 on PASS, 1 on FAIL.
"""
import re
import sys
from pathlib import Path

BLOCK_RE = re.compile(
    r'From \[(\d+(?:\.\d+)?)s\] to \[(\d+(?:\.\d+)?)s\]\n'
    r'Display the kinetic super:\n'
    r'"([^"\n]{2,80})"\n'
    r'((?:Instantly snap|Whip|Keep) the camera [^\n]+)'
)
# camera-only block: range + whip, no super lines. Only moving lines allowed
# ("Keep the camera" blocks exist solely to show text — without one they are dead air).
CAM_ONLY_RE = re.compile(
    r'From \[(\d+(?:\.\d+)?)s\] to \[(\d+(?:\.\d+)?)s\]\n'
    r'((?:Instantly snap|Whip) the camera [^\n]+)'
)
POS_PREFIX = r"(?:Instantly snap|Whip|Keep) the camera "
HOOK_LINE = "Keep the camera in the original position and framing, completely still."
STATIC_LINE = "Keep the camera locked in the same position, completely still."
# the safe-zone sentence added to the typography paragraph on 2026-10-02 (text stays in the central band)
SAFE_ZONE_MARK = "central band of the frame"


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python verify_prompt.py <delivered_prompt.txt>")

    skill_md_path = Path(__file__).resolve().parent.parent / "SKILL.md"
    skill_md = skill_md_path.read_text(encoding="utf-8")
    m = re.search(r"## The canonical template \(FROZEN\).*?\n```\n(.*?)\n```", skill_md, re.S)
    if not m:
        sys.exit("could not extract canonical template from SKILL.md")
    template = m.group(1).replace("\r\n", "\n").strip()

    delivered = Path(sys.argv[1]).read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()

    marker_head = "Follow this timeline:\n\n"
    marker_tail = "\n\nImportant requirements:"
    t_head = template.split(marker_head)[0] + marker_head
    t_tail = marker_tail + template.split(marker_tail)[1]

    # allowed position lines: the ones inside the template + every backticked
    # preset in SKILL.md ("Instantly snap the camera ...")
    allowed = set(re.findall(rf"^({POS_PREFIX}[^\n]+)$", template, re.M))
    allowed |= set(re.findall(rf"`({POS_PREFIX}[^`]+)`", skill_md))
    allowed.add(HOOK_LINE)
    allowed.add(STATIC_LINE)
    final_line = next((l for l in allowed if "back to the original camera position" in l), None)
    if not final_line:
        sys.exit("could not find the back-to-original position line in SKILL.md")

    safe_zone = SAFE_ZONE_MARK in template
    if safe_zone and SAFE_ZONE_MARK not in delivered:
        fail("the safe-zone sentence is missing from the typography paragraph (keep all on-screen text inside the "
             f"{SAFE_ZONE_MARK}, clear of the top, bottom and right edges): the supers can land under the app interface")

    if not delivered.startswith(t_head):
        for i, (a, b) in enumerate(zip(t_head.split("\n"), delivered.split("\n")), 1):
            if a != b:
                fail(f"head diverges from template at line {i}:\n  template : {a!r}\n  delivered: {b!r}")
        fail("head is truncated")
    if not delivered.endswith(t_tail):
        fail("tail (Important requirements list) diverges from the template")

    middle = delivered[len(t_head):len(delivered) - len(t_tail)].strip()
    chunks = [c for c in re.split(r"\n\n+", middle) if c.strip()]
    if not chunks:
        fail("no timeline blocks found")

    blocks = []
    for i, chunk in enumerate(chunks, 1):
        b = BLOCK_RE.fullmatch(chunk.strip())
        if b:
            start, end, super_text, pos = float(b.group(1)), float(b.group(2)), b.group(3), b.group(4)
        else:
            c = CAM_ONLY_RE.fullmatch(chunk.strip())
            if not c:
                fail(f"block {i} is malformed (brackets stripped? quotes missing? extra lines?):\n{chunk}")
            start, end, super_text, pos = float(c.group(1)), float(c.group(2)), None, c.group(3)
        if pos not in allowed:
            fail(f"block {i} position line is not in the canonical menu:\n  {pos}")
        blocks.append((start, end, super_text, pos))

    for i, (start, end, _, _) in enumerate(blocks, 1):
        if not start < end:
            fail(f"block {i} range is not ascending: [{start}s] to [{end}s]")
    for i in range(len(blocks) - 1):
        if blocks[i][1] != blocks[i + 1][0]:
            fail(f"blocks {i + 1} and {i + 2} do not share their boundary "
                 f"({blocks[i][1]} vs {blocks[i + 1][0]})")
    if blocks[-1][3] != final_line:
        fail("last block does not snap back to the original camera")
    if any(b[3] == final_line for b in blocks[:-1]):
        fail("back-to-original appears before the last block")

    hook = blocks[0][3] == HOOK_LINE
    if hook and blocks[0][0] != 0:
        fail(f"hook block must start at [0s], not [{blocks[0][0]}s]")
    if any(b[3] == HOOK_LINE for b in blocks[1:]):
        fail("hook block (camera still) is only allowed as the first block")

    statics = [i for i, b in enumerate(blocks) if b[3] == STATIC_LINE]
    if statics:
        if len(statics) > 1:
            fail("only ONE static-super block is allowed per timeline")
        i = statics[0]
        if i == 0:
            fail("static-super block cannot be the first block (nothing to hold from; the [0s] hook has its own line)")
        if blocks[i - 1][3] in (HOOK_LINE, STATIC_LINE):
            fail("static-super block cannot follow another still block (two stills in a row kills the format)")

    first_move = blocks[1][0] if hook and len(blocks) > 1 else blocks[0][0]
    whips = len(blocks) - (1 if hook else 0) - len(statics)
    texts = sum(1 for b in blocks if b[2] is not None)
    print("PASS: template intact outside mutable zones")
    print("safe zone: sentence present in the typography paragraph" if safe_zone
          else "WARNING: the template in SKILL.md carries no safe-zone sentence")
    print(f"blocks: {len(blocks)}{' (incl. opening hook super)' if hook else ''}"
          f"{f' ({len(statics)} static-super)' if statics else ''} "
          f"-> {whips} camera moves / {texts} text beats (each layer has its own density rule)")
    print(f"opening hold before first camera move: 0 -> {first_move}s"
          + ("  (WARNING: <0.8s)" if first_move < 0.8 else ""))
    for i, (start, end, super_text, pos) in enumerate(blocks, 1):
        label = re.sub(rf"^{POS_PREFIX}", "", pos).rstrip(".")
        stxt = f'"{super_text}"' if super_text is not None else "(camera-only)"
        print(f'  {i}. [{start}s -> {end}s]  {stxt}  ({label[:60]})')
    sys.exit(0)


if __name__ == "__main__":
    main()
