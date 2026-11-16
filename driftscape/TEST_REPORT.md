# Test report — Driftscape pipeline v1.0.0

**Date:** 2026-11-13. **Result: PASS.** A 3-hour 1080p24 video was built end to end from sample
assets, and QC passed. Every defect deliberately planted in the samples was detected.

## Test environment (important)

| | Test box | Your Mac |
|---|---|---|
| OS / CPU | Linux, 4 vCPU (x86) | macOS, M3 (4P+4E cores), 16 GB |
| FFmpeg | 6.1.1 | Homebrew (7.x likely) |
| Hardware encoders | none | `h264_videotoolbox`, `hevc_videotoolbox`, `aac_at` |

What is **not verified** on real hardware:
- macOS-only paths: VideoToolbox encoding, `aac_at`, `caffeinate`.
- M3 timings.
- Real Veo clips. The clips here are procedural stand-ins, because Veo output can't be generated
  or downloaded in this environment.

The default path (`libx264` + native AAC) is the one that was tested.

## Sample assets (`./ds samples <dir>`)

| Clip | Spec | Planted property | Detected as |
|---|---|---|---|
| rain_window | 10 s, 24 fps | stationary texture | **A**, seam 1.02× normal motion → loop |
| lake_shimmer | 8 s, 24 fps, has audio | stationary water | **B** → loop; clip audio dropped (noted) |
| fog_valley | 9 s, 24 fps | drifting/evolving, exposure drift | **D**: exposure drift −30.7, progressive ×4.2 → oneshot |
| camera_push | 10 s, **30 fps, 1280×720** | steady zoom (camera move) | **D**: progressive ×4.7 → oneshot; fps conversion + upscale noted |
| aurora_glitch | 8 s, 24 fps | 2-frame flash @3.50 s, jump cut @5.50 s | all 3 frame jumps found (3.50, 3.58, 5.50 s), flicker → **auto-excluded** |
| rain_bed.wav | 40 s, 48 kHz | not loop-seamless | seamless loop built; seam click ×0.07, step 2.1 dB (within normal variation) |
| drone.mp3 | 25 s, 44.1 kHz MP3 | resampling + MP3 decoder delay | seamless loop built; seam click ×0.48, step 0.17 dB |

## Full-length run: 3 h, 1920×1080, 24 fps (`./ds all <p> --final`)

| Check | Result |
|---|---|
| Duration | 10800.00 s (target 10800) |
| Video frames | 259,200 / 259,200 (frame-exact) |
| Timestamps across stream-copy joins | 0 non-monotonic DTS; decodes cleanly at start, middle and end |
| Seams in cycle (dissolves, loop wraps, segment joins, cycle wrap) | **55/55 clean** (all ≤ 3× local motion) |
| Unexplained frame jumps | 0 |
| A/V length | video 10800.00 s, audio 10800.00 s |
| Loudness | −18.0 LUFS integrated (independent re-measure −18.1), true peak −6.0 dBTP, target −18 / −2 |
| Thumbnails | 3 × 1280×720 JPEG, ~200 KB each (< 2 MB limit), plus contact sheet |
| Metadata | title 48 chars, 0 validation errors, privacy `private`, AI disclosure `true`, attribution credit included |
| File size | 11.7 GB (synthetic film grain is unusually expensive to encode; clean Veo footage should be smaller) |

**Timings on the 4-vCPU test box** (expect different numbers on an M3):

| Stage | Time |
|---|---|
| Unique 3-min cycle, 1080p, libx264 medium | 296 s (~0.75× realtime) |
| Assemble 3 h video by stream copy | **23 s** |
| 3 h audio: measure + normalise + AAC (after the fixes below) | 783 s, almost all of it in FFmpeg's single-threaded AAC encoder |
| Peak RAM, any ffmpeg process | 680 MB |

The defaults use a 10-minute cycle, which means roughly 3.3× the cycle time above.

## Bugs found during testing (all fixed)

1. **MP3 audio loops had silent gaps.** Seeking (`-ss`) into compressed audio returns decoder-priming
   silence: 0.1 s of digital silence at the blend/body joint, which QC measured as a 37.7 dB level
   step. *Fix:* every layer is decoded once to a 48 kHz FLAC mezzanine and cut sample-exactly with
   `atrim`. Seam step after the fix: 0.17 dB.
2. **Jump-cut detection missed a 5× motion spike** because the absolute floor (+6 levels) was too
   high. *Fix:* the floor is now +2.5 levels, still with a 3.5× relative threshold.
3. **Grading was too strict on stationary textures.** Water was graded C because any two
   water frames differ. *Fix:* grades now use drift and exposure stability. Seam mismatch still
   decides grade A.
4. **Audio step was slow** (est. 35+ min for 3 h). *Fix:* the measurement uses `ebur128` (3.5× faster
   than `loudnorm` analysis, same result), the gain is applied linearly, the AAC `fast` coder is
   used, and Apple `aac_at` is used automatically on macOS.
5. Minor: numpy values broke the JSON reports, and sub-hour titles read "0.0 Hours". Both fixed.

## Artifacts and discontinuities reported

- **Planted defects.** With `aurora_glitch` force-included (dev test), QC flagged its flash (jump
  62.9, 51× local motion) and jump cut (6.0, 4.9×), and attributed every occurrence to that clip.
  With defaults, the clip is auto-excluded and QC passes.
- **Preview-only keyframe "pulsing".** The 360p/CRF 30 preview showed small brightness pulses every
  2 s, exactly at keyframes. At final quality, the same frames measured 1.0–1.3× local motion
  (clean). Preview QC now labels these instead of failing them.
- **Upscale and frame-rate conversion.** `camera_push` (720p30 → 1080p24) is noted as softer and
  possibly juddery. Prefer 1080p/24 fps Veo exports.

## Limits of automated QC

QC does not detect AI morphing (warping, melting objects, wrong physics), visible watermarks, or
dissolves between scenes that look bad together. Watch `out/seams_review.mp4`: it shows every seam,
4 s each, labelled.

## Reproduce

```bash
python3 -m unittest discover -s tests -v                    # 9 tests, ~1 min
./ds samples ~/ds-sample && ./ds all ~/ds-sample --final     # full 3 h run
```

---

# Audit — 2026-11-16

A full re-read of the code plus tests of paths the first test run never exercised.
**Result: no defect that corrupts output; six issues fixed; 19/19 tests pass.**

## Newly tested

| Area | Method | Result |
|---|---|---|
| Real footage | 3 Gemini clips (720p, 24 fps, 10 s), 3-minute render | 41/41 seams clean, QC pass |
| Looped audio continuity | FLAC loop repeated ×3 by FFmpeg vs the same samples tiled in numpy | identical: max sample difference 0, exact length |
| `pingpong` mode | 1-minute render with one ping-pong clip | 16/16 seams clean, frame-exact |
| ProRes intermediates (`mezz_codec = "prores"`) | 1-minute render | 18/18 seams clean; working files 2.6× larger (428 MB vs 163 MB) |
| Clip queue, verification, duplicates, hand-off | 5 unit tests | pass |
| Browser assistant | 5 tests against a local mock site (generate, download, usage-limit stop, duplicate, truncated file) | pass |

## Issues found and fixed

1. **Loop grading failed on real clips.** Two of three real clips were marked "not loopable"
   because drifting fog looked like a camera move. *Fix:* a static-scene check that compares the
   fixed scenery at the start and end of the clip.
2. **Loops were shorter than they needed to be** (6.0 s from a 10 s clip). When no frames match
   naturally, trimming gains nothing. *Fix:* such clips now keep their full length (8.5 s loops).
3. **Peak level overshot the ceiling** (−1.6 dBTP against a −2.0 target) when the limiter was
   active, and QC did not check it. *Fix:* wider limiter margin (now −2.4 dBTP), a new QC true-peak
   check, and a warning when a quiet source needs heavy limiting.
4. **Unused segment files accumulated in `work/`** after every settings change. *Fix:* they are
   removed automatically, as are intermediates of clips taken out of a project.
5. **A short `-d` sample could be uploaded as the real video.** *Fix:* `upload` refuses when the
   last render's length does not match the project duration.
6. **Usage-limit detection could be confused by old page text.** *Fix:* page text is compared line
   by line against what was there before the prompt was sent.

## Still unverified (cannot be tested in the build environment)

- Everything macOS-specific: VideoToolbox encoding, `aac_at`, `caffeinate`, clipboard copy, M3 timings.
- The browser assistant against Google's real Gemini and Flow pages, including whether Google
  accepts a sign-in in the assistant's Chrome window.
- The YouTube upload against the real API (only the refusal paths and `--dry-run` were exercised).
- 4K output.
- A render longer than 3 minutes from real clips (the 3-hour test used synthetic clips).

## Known limits (by design, not fixed)

- `clips watch` takes the next new video that appears in `~/Downloads`; an unrelated video
  downloaded at that moment would be picked up (it is still verified and hash-checked).
- Duplicate detection is by exact file content; two different renders of a similar scene are
  not flagged.
- Quality checks cannot see AI artefacts in the picture (the tripod in one real clip was found
  by eye, not by the tool).
