# Local 4K edit: iPhone 18 customer-review reel

Run this on the owner's Windows laptop, not in the cloud. Talk to the owner (Amanjot, Nazakat Telecom) in simple Hinglish; they are not technical.

## Goal
Edit the ORIGINAL 4K video on the laptop. Never upload it, and never use a WhatsApp-compressed copy.
- Video: `C:\Users\DELL\Desktop\claude video test\20261008_185220.mp4`
  (4K landscape, about 1:12, HEVC 60 fps, about 1.09 GB, filmed on a Galaxy Z Fold7)
- Outputs: `C:\Users\DELL\Desktop\claude video test\output\`

Make two versions, both at most 55 seconds:
1. **Vertical 9:16, 2160x3840.** Use `examples/iphone18_testimonial.json`; only fix timings if needed.
2. **Horizontal 16:9, 3840x2160, GenZ vibe.** This is new: add a 16:9 mode to the toolkit.

## 1. Install only what is missing (check first)
- ffmpeg + ffprobe: `winget install Gyan.FFmpeg`, then open a new shell and run `ffmpeg -version`.
- Python 3.10+: `winget install Python.Python.3.12` if `python --version` fails.
- `python -m pip install pillow numpy scipy faster-whisper`
- Tell the owner in one line what you installed.

## 2. Check the source
- Run ffprobe on the video: resolution, rotation, fps, duration. `make_reel.py` already handles rotation metadata.
- The plan's times were measured on a WhatsApp copy; they match the original to about 0.5 s. Verify them.

What the video shows (source seconds):
- 0–40: two customers unbox an iPhone 18 Pro and a Pro Max at the counter. Navy shirt on the left, white tee with glasses on the right.
- ~6: a finger covers the lens. Avoid it.
- ~22: the white-tee customer holds the phone up, smiling.
- ~38–72: the white-tee customer talks to camera. Per the owner, he says he has bought every phone from Nazakat Telecom since his first one, and praises the service.
- Earlier speech pauses were at about 43.0–43.5, 44.7–45.6, 50.3, 53.7, 65.0 and 68.3. Re-measure on the original audio (RMS in 0.1 s windows) and cut speech only at real pauses.

## 3. Vertical 4K
- Copy the example plan. Set `source` to the absolute video path and `output` to the output folder.
- Run `python make_reel.py <plan> --res 4k`.
- Crops are `[left fraction of width, top fraction of height, size fraction of height]`: `two` frames both customers, `cu` is the speaker close-up. Check them on 4K frames.
- Transcribe the speech with faster-whisper (`small` or `medium`, language `hi`, word timestamps). Add `captions` as `[from, to, text]` in reel seconds, in Roman Hinglish.
  - Only add words you are confident were said. Never invent or polish the customer's words.
  - If the transcript is unreliable, leave captions out and tell the owner.

## 4. Horizontal 16:9 GenZ (new mode in the toolkit)
**Framing**
- Full-frame footage, no square crop. Close-ups are 16:9 punch-ins of the 4K frame.

**Story order**
1. Hook (≤1.5 s)
2. Sealed boxes
3. Fast unboxing with speed ramps
4. "Wait for it" build
5. Beat drop on the first look
6. Customer review with real audio
7. End card

**GenZ style**
- Hook text like "POV: Pathankot mein 2 iPhone 18 Pro ek saath 😳".
- Word-by-word pop captions: bold Montserrat, white with black outline, the current word in yellow #FFD54F.
- Zoom punches, and flash or RGB-split glitch transitions on beats.
- Meme lines such as "unboxing ASMR", "vibe check ✅", "Pathankot ka iPhone plug 🔌", "main character energy", "customer ne bola, hum nahi 😌".
- Keep it factual: no prices, no "cheapest" or comparisons, no competitor names.
- Emoji: drawtext cannot draw colour emoji. Render sticker PNGs with Pillow using `C:\Windows\Fonts\seguiemj.ttf`, or drop the emoji. Never ship empty boxes.

**Brand**
- Logo: `assets/logo.jpg`, masked to a circle.
- Colours: red #D32F2F, yellow #FFD54F. Fonts in `assets/fonts`.
- Call/WhatsApp 81968 48484 and 99889 69696; Defence Road, Mamun Cantt, Pathankot; Since 1992.
- Keep text inside a 5% title-safe margin.

**Sound**
- Original music from `tools/music.py`; a faster variant is fine. Duck it under the customer's speech.
- SFX from `assets/sfx`, only on visible events.

**Paths**
- Keep the toolkit rule: ffmpeg runs with cwd = this folder and every filter path is relative, so `C:` never appears inside a filter.
- Pass the video path as a list argument; the path contains spaces.

## 5. Review before showing
For each export:
- Full decode with `ffmpeg -v error -i out.mp4 -f null -`.
- Loudness about -14 to -16 LUFS, true peak ≤ -1 dBTP. Use `alimiter` with `level=disabled`.
- Look at frame 0, the first 3 s, every text beat, the close-ups and the end card. Fix clipped text, overlapping beats, a logo over a face, and wrong crops.
- Test a short segment before the full 4K render.

## 6. Deliver
- Open the output folder for the owner. Tell them what each file is, its length, and what you could not verify (for example, exact captions).
- Remind them to get both customers' permission before posting.
- Do NOT post or schedule anything.
- Commit toolkit code changes (not videos; `input/`, `output/` and `work/` are ignored) to branch `claude/quirky-hawking-ks344g` and push.
