# Driftscape production pipeline

A local, offline pipeline that turns a folder of short Veo clips (8–10 s) and licensed audio into a
finished 3-hour ambience video, with a thumbnail, YouTube metadata and QC reports. It runs on a
MacBook Air M3 (16 GB) using Python, FFmpeg and a few pip packages. It needs no AI service, no cloud
account and no subscription. The only network step is the optional YouTube upload, and that never
runs unless you confirm it.

```
inbox/*.mp4 ─► import ─► analyze ─► loops ─► plan ─► preview ─► render ─► qc
                 │          │          │                  │         │
            mezzanine   loop grades  seamless       360p preview  final.mp4 (stream-copied)
                        + artifacts  loop files     + seam reel   + loudness-normalised audio
audio/*  ───────────────────────────────────────► audio mix (2-pass EBU R128)
                                                   thumbs ─► meta ─► [upload: asks first]
```

## 1. One-time setup (macOS)

```bash
cd driftscape
./setup_mac.sh            # installs ffmpeg + Python 3.12 via Homebrew, creates .venv, runs doctor
./setup_mac.sh --with-upload   # same, plus the optional YouTube upload libraries
```

Manual alternative: `brew install ffmpeg python@3.12`, then `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
Check the install at any time with `./ds doctor`.

| Dependency | Version | Why |
|---|---|---|
| FFmpeg + ffprobe | 6.x or 7.x (Homebrew) | all decoding, encoding, filtering, loudness |
| Python | ≥ 3.11 | orchestration (uses built-in `tomllib`) |
| numpy, Pillow | see `requirements.txt` | analysis on tiny frames, thumbnails |
| google-api-python-client, google-auth-oauthlib | optional | `./ds upload` only |
| Blender | **not needed** | see "Why no Blender" below |

## 2. Make a video

```bash
./ds new ~/Driftscape/projects/misty-forest        # creates inbox/ audio/ project.toml
# copy Veo clips into .../misty-forest/inbox/, licensed audio into .../misty-forest/audio/
# edit project.toml: title, [[audio.layers]] with licence info, thumbnail text, tags
./ds all ~/Driftscape/projects/misty-forest        # import → analyse → loops → preview → thumbs → meta (+QC)
open ~/Driftscape/projects/misty-forest/out/preview.mp4
open ~/Driftscape/projects/misty-forest/out/seams_review.mp4
./ds render ~/Driftscape/projects/misty-forest     # final 3 h video + final QC
./ds upload ~/Driftscape/projects/misty-forest --dry-run   # shows exactly what would be sent
```

Tip: `P=~/Driftscape/projects/misty-forest` then `./ds all $P`.

### All commands

| Command | What it does |
|---|---|
| `./ds doctor` | check dependencies |
| `./ds new <project>` | create a project from `templates/project.toml` |
| `./ds samples <project> [--size 1920x1080]` | create a synthetic test project (clips with deliberate defects plus audio) |
| `./ds import <project> [--source DIR]` | normalise clips to a common resolution/fps/colour, strip clip audio |
| `./ds analyze <project>` | loop grades, best loop points, artifact detection → `out/reports/analysis.md` |
| `./ds loops <project>` | build seamless loop sources |
| `./ds plan <project>` | print the shot plan (cycle length, repeats) |
| `./ds audio <project>` | full-length audio mix only |
| `./ds preview <project>` | 360p preview (one full cycle plus the wrap-around), seam reel, QC |
| `./ds render <project>` | final video plus final QC |
| `./ds thumbs <project>` | 3 thumbnail candidates plus contact sheet |
| `./ds meta <project>` | title, description, tags → `out/metadata.json`, `out/description.txt` |
| `./ds qc <project> [--final]` | re-run QC |
| `./ds all <project> [--final]` | everything except upload |
| `./ds upload <project> --dry-run` / `--i-confirm` | YouTube upload (see §6) |
| `./ds -v <command> …` | also print every ffmpeg command |

Every step is **cached and resumable**. Re-running a command only redoes what changed. If the Mac
sleeps or you press Ctrl-C mid-render, run the same command again.

## 3. How it works

**Import.** Each clip is converted to a mezzanine file at the project resolution and fps, in BT.709,
with audio removed. The mezzanine is near-lossless H.264 (CRF 12, 12-frame GOP), or ProRes 422 if
you set `mezz_codec = "prores"`. Notes are recorded for fps conversion, upscaling and aspect crop.

**Analyze.** This step works on 160×90 greyscale frames, about 14 KB each, so a 4K clip costs only
a few MB of RAM. For every clip it records:
- best loop in/out points, chosen so that the frame after the loop's end matches its start
- *seam x-motion*: the mismatch at the seam, as a multiple of normal frame-to-frame motion (1.0 = invisible)
- *progressive* drift: does the shot keep moving away from itself (camera push, pan, evolving scene) or hover (water, rain, fog)?
- artifacts: sudden frame jumps (cuts, flashes, morph glitches), brightness flicker, exposure drift, near-black frames, frozen frames

| Grade | Meaning | Default use |
|---|---|---|
| A | seamless; loop points match naturally | self-loops |
| B | stationary texture; the crossfade is invisible | self-loops |
| C | some drift; crossfade works, mild ghosting possible | self-loops |
| D | camera move / evolving scene; a self-loop would visibly reset | **oneshot**: shown once per cycle, entered and left with dissolves |

Clips with flashes or jump cuts are **auto-excluded**. To use one anyway, set `[clips.<id>] exclude = false`.

**Loops.** A `loop` clip's tail is dissolved into its head (`loop_crossfade`, 1.5 s by default), so
the file repeats without a seam. A `oneshot` clip stays as it is. `pingpong` (forward, then reversed)
is available per clip, but reversed rain, snow or fire looks wrong, so review it.

**Plan.** The plan builds a **cycle** of unique footage (`cycle_minutes`, 10 by default). It is a
sequence of shots: each looping clip holds for 20–45 s, oneshots are spaced out, the next clip is
chosen for colour/brightness compatibility with some randomness (`seed`), and the cycle's end
dissolves into its own start. The 3 h video is intro + cycle × N + outro, and it is frame-exact.

**Render.** Only the cycle is encoded, one short segment at a time, each from a fresh decode, so
peak RAM stays low. The 3-hour file is then **stream-copied**: the cycle is repeated without
re-encoding. Rendering 3 h costs about the same as rendering 10 minutes, plus disk I/O.

**Audio.** Every layer is decoded to a 48 kHz FLAC mezzanine. This avoids the MP3/AAC priming
silence, a bug that turned up during testing. Each layer then becomes a seamless loop: an
equal-power crossfade by default, or `crossfade_curve = "tri"` for tonal/music material. Layers are
mixed at their `gain_db` and normalised in two passes: an EBU R128 (`ebur128`) measurement, then a
single linear gain to the target (default -18 LUFS integrated, -2 dBTP). The result is the same as
`loudnorm` in linear mode, about 3.5× faster. A transparent peak limiter is added only if the gain
would push true peak over the ceiling. Output is AAC 384 kbps. The final render **refuses to run** if
any layer is missing a `license`.

**QC.** QC scans the rendered cycle at 160×90 and measures the frame-to-frame change at every known
seam: dissolves, loop wraps, segment joins, and the cycle wrap. A seam is flagged as **VISIBLE** if
its jump is more than 3× the local motion. Any other jump is reported as an unexplained source
artifact and attributed to its clip. The final QC also checks duration, streams, A/V length match,
integrated loudness and audio loop seams. Reports go to `out/reports/qc_*.md`.

What QC **cannot** judge: AI morphing (warping objects, melting textures, wrong physics), visible
watermarks, and whether a dissolve between two very different scenes looks good. Watch
`out/seams_review.mp4`: it is 4 s around every seam, labelled, and takes a few minutes.

## 4. Settings you will actually touch (`project.toml`)

| Setting | Default | Notes |
|---|---|---|
| `project.duration` | `"3h"` | `"2h30m"`, `"45m"`, seconds |
| `video.width/height/fps` | 1920×1080, 24 | Veo's default is 24 fps; 4K = 3840×2160 |
| `video.codec` | `libx264` | `h264_videotoolbox` / `hevc_videotoolbox` use the M3 media engine (cooler, faster) — see §5 |
| `video.crf`, `maxrate` | 18, 16M | YouTube recommends ~8 Mbps for 1080p24 and 35–45 Mbps for 4K24; uploading above that is fine |
| `video.transition` / `loop_crossfade` | 3.0 / 1.5 s | longer = softer, more ghosting |
| `video.hold_min/max` | 20 / 45 s | how long a looping shot stays on screen |
| `video.cycle_minutes` | 10 | longer = less repetition, longer encode |
| `video.seed` | 7 | change it to reshuffle the shot order |
| `[clips.<id>]` | — | `mode`, `weight`, `exclude`, `loop_in`, `loop_out` (seconds) |
| `audio.target_lufs` | -18 | YouTube only turns *down* audio louder than about -14 LUFS (widely cited, not officially published); sleep content usually sits quieter |
| `[[audio.layers]]` | — | `file`, `gain_db`, `loop`, `loop_crossfade`, `crossfade_curve`, `start`, `license`, `source`, `credit`, `attribution_required` |
| `youtube.*` | private, AI disclosure on | title/description templates, tags, category |

## 5. MacBook Air M3 (16 GB) notes

- **RAM.** Analysis uses tiny frames. Segments are rendered one at a time from separate decodes,
  with no long filter graphs. The 3 h file is stream-copied. Measured peak RAM at 1080p: 680 MB
  (one ffmpeg process). `pingpong` mode is the exception: at 4K it buffers a clip (~3 GB).
- **Heat.** The Air has no fan, so long x264 encodes throttle. `system.threads = 6` and `nice = 10`
  keep the Mac usable. For 4K, try `codec = "h264_videotoolbox"` with `vt_bitrate = "40M"`, which
  uses the hardware media engine. **It is untested** (the test machine was Linux). Run
  `./ds qc <p> --final` after the first VideoToolbox render to confirm the stream-copy joins are clean.
- **Audio encoding** is the slowest single step for 3 h: FFmpeg's built-in AAC encoder is
  single-threaded (~11 min for 3 h on the 4-core test box). On macOS the pipeline automatically
  uses Apple's `aac_at` encoder when your FFmpeg has it (`./ds doctor` shows it); that is faster
  and higher quality. Set `audio.aac_encoder = "aac"` to force the built-in one.
- **Sleep.** Long renders run under `caffeinate -i` automatically (the screen can still sleep).
- **Disk** (the main constraint). The final file is about `bitrate × duration`: 3 h at 1080p ≈
  4–7 GB for typical ambience, and 4K at 40 Mbps ≈ 54 GB. `render` checks free space before
  assembling. You can delete `work/` once the video is uploaded; it only holds caches.
- Keep projects outside the git repo (e.g. `~/Driftscape/projects`).

## 6. YouTube upload (optional, always asks)

1. In Google Cloud Console, create a project, enable **YouTube Data API v3**, and create an OAuth
   client of type *Desktop app*. Download the JSON to `~/.driftscape/client_secret.json`.
2. Run `./setup_mac.sh --with-upload`.
3. Run `./ds upload <project> --dry-run`. It prints the exact request (title, description, tags,
   privacy, AI disclosure) and uploads nothing.
4. Run `./ds upload <project> --i-confirm`. You must also type the exact title at the prompt.
   Uploads go up as **private** by default. `public` needs a second typed confirmation.

Notes. Uploads from an *unverified* API project may be locked to private until Google audits the
project, which is fine because you publish from YouTube Studio. `contains_synthetic_media = true` is
the default. YouTube requires disclosure for realistic AI-generated scenes; review its current
policy and set the field to false only if your footage clearly doesn't qualify.

## 7. Tests

```bash
python3 -m unittest discover -s tests -v      # ~1–2 min: builds a tiny sample project end to end
./ds samples /tmp/ds-sample && ./ds all /tmp/ds-sample --final   # full-size demo (3 h, 1080p)
```

## 8. Why no Blender

FFmpeg does everything this workflow needs: trims, dissolves, loudness and encoding. It streams with
small memory, and its runs can be cached and repeated. Blender's Video Sequence Editor would add
a large dependency, GUI-driven state, more RAM, and slower renders on an Air, with no quality gain
for dissolves between clips. Blender would make sense for additions such as parallax/depth effects
on stills, particle overlays (snow, rain on glass), or 3D title cards. Render those to a clip, drop
it in `inbox/`, and the pipeline treats it like any Veo clip.

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `No usable clips after analysis` / `Need at least one loopable clip` | read `out/reports/analysis.md`; force one with `[clips.<id>] mode = "loop"` |
| A seam marked **VISIBLE** | lengthen `transition`/`loop_crossfade`, set manual `loop_in`/`loop_out`, or exclude the clip |
| Repetition is noticeable | add clips, raise `cycle_minutes`, change `seed`, raise `hold_max` |
| Audio loop audible | raise that layer's `loop_crossfade`; use `crossfade_curve = "tri"` for music/tones |
| Not enough disk | lower `maxrate`/`crf`, delete old projects' `work/` |
| Something odd | re-run with `./ds -v …` to see each ffmpeg command |

## Layout

```
driftscape/
  ds                 launcher (uses .venv if present)
  dscape/            pipeline package (one module per step)
  templates/project.toml
  tools/make_samples.py
  tests/test_pipeline.py
<project>/
  project.toml  inbox/  audio/
  work/   caches: mezz/ loops/ audio/ render_preview/ render_final/ *.json
  out/    preview.mp4  seams_review.mp4  <Title>.mp4  thumbnails/  metadata.json  description.txt  reports/
```
