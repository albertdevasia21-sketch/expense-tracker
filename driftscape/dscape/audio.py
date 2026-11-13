"""Step 4 - audio: seamless layer loops, mix, two-pass EBU R128 loudness normalisation.

Layers come from [[audio.layers]] in project.toml. Every layer must declare its
licence; the final render refuses to run without one.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from . import ff
from .config import Project, file_sig, is_fresh, mark_fresh


def _layer_path(proj: Project, layer: dict) -> Path:
    p = Path(layer["file"]).expanduser()
    return p if p.is_absolute() else proj.audio_dir / p


def require_licenses(proj: Project) -> None:
    layers = proj.cfg["audio"]["layers"]
    if not layers:
        raise SystemExit("No [[audio.layers]] in project.toml - add your licensed audio first.")
    missing = [l.get("file", "?") for l in layers if not str(l.get("license", "")).strip()]
    if missing:
        raise SystemExit("These audio layers have no 'license' entry (required before final render): "
                         + ", ".join(missing))


def _audio_mezz(proj: Project, src: Path, sr: int) -> Path:
    """Decode any input (mp3/aac/wav/...) once to 48 kHz stereo FLAC.

    Avoids compressed-codec priming/padding silence when cutting, and makes every
    later cut sample-exact.
    """
    out = proj.p("work", "audio", Path(src).stem + ".src.flac")
    spec = {"src": file_sig(src), "sr": sr}
    if not is_fresh(out, spec):
        ff.run(["-i", str(src), "-map", "0:a:0", "-ac", "2", "-ar", str(sr), "-c:a", "flac",
                "-sample_fmt", "s32", str(out)], desc="audio mezz")
        mark_fresh(out, spec)
    return out


def _samples(path: Path) -> int:
    info = ff.probe(path)
    st = ff.audio_stream(info) or {}
    ts = st.get("duration_ts")
    if ts and st.get("time_base") == f"1/{st.get('sample_rate')}":
        return int(ts)
    return int(round(float(info["format"]["duration"]) * int(st.get("sample_rate", 48000))))


def build_layer_loop(proj: Project, layer: dict) -> Path:
    """Crossfade the tail of the file into its head -> file that repeats without a seam."""
    src = _layer_path(proj, layer)
    if not src.exists():
        raise SystemExit(f"Audio file not found: {src}")
    sr = int(proj.cfg["audio"]["sample_rate"])
    mz = _audio_mezz(proj, src, sr)
    n = _samples(mz)
    X = int(min(float(layer.get("loop_crossfade", 3.0)), n / sr / 4) * sr)
    curve = layer.get("crossfade_curve", "qsin")   # qsin = equal power (noise/ambience); tri = music
    out = proj.p("work", "audio", Path(src).stem + ".loop.flac")
    spec = {"src": file_sig(mz), "X": X, "sr": sr, "curve": curve, "v": 2}
    if is_fresh(out, spec):
        return out
    print(f"  audio loop {src.name} ({n / sr:.1f}s, crossfade {X / sr:.1f}s)")
    d = f"{X / sr:.6f}"
    fc = (f"[0:a]atrim=start_sample={n - X}:end_sample={n},asetpts=PTS-STARTPTS,afade=t=out:d={d}:curve={curve}[t];"
          f"[1:a]atrim=end_sample={X},asetpts=PTS-STARTPTS,afade=t=in:d={d}:curve={curve}[h];"
          f"[t][h]amix=inputs=2:normalize=0:duration=longest[x];"
          f"[2:a]atrim=start_sample={X}:end_sample={n - X},asetpts=PTS-STARTPTS[b];"
          f"[x][b]concat=n=2:v=0:a=1[a]")
    ff.run(["-i", str(mz), "-i", str(mz), "-i", str(mz), "-filter_complex", fc, "-map", "[a]",
            "-c:a", "flac", "-sample_fmt", "s32", str(out)], desc="audio loop")
    got = _samples(out)
    if abs(got - (n - X)) > 1:
        raise SystemExit(f"audio loop {out.name}: {got} samples, expected {n - X}")
    mark_fresh(out, spec)
    return out


def seam_check(path: Path, sr: int = 48000) -> dict:
    """Measure click / level jump where the loop file wraps around."""
    dur = ff.duration_of(path)
    w = 0.5
    tail = ff.read_audio(path, max(0, dur - w), w, sr)
    head = ff.read_audio(path, 0, w, sr)
    joined = np.concatenate([tail, head]).mean(axis=1)
    j = len(tail)
    dif = np.abs(np.diff(joined))
    typical = float(np.percentile(dif, 99)) + 1e-9
    jump = float(dif[j - 1]) if 0 < j <= len(dif) else 0.0
    win = int(0.05 * sr)
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    step = abs(rms(joined[j - win:j]) - rms(joined[j:j + win]))
    ref = np.std([rms(joined[k:k + win]) for k in range(0, len(joined) - win, win)])
    return {"click_ratio": round(jump / typical, 2), "level_step_db": round(float(step), 2),
            "typical_level_var_db": round(float(ref), 2),
            "ok": bool(jump / typical < 1.5 and step < max(3.0, 3 * ref))}


def _build_graph(proj: Project, duration: float, loops: dict) -> tuple[list[str], str]:
    a = proj.cfg["audio"]
    sr = int(a["sample_rate"])
    fmt = f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo"
    inputs, chains, labels = [], [], []
    for k, layer in enumerate(a["layers"]):
        if layer.get("loop", True):
            inputs += ["-stream_loop", "-1", "-i", str(loops[k])]
        else:
            inputs += ["-i", str(_audio_mezz(proj, _layer_path(proj, layer), sr))]
        start = float(layer.get("start", 0.0))
        delay = f",adelay={int(start * 1000)}:all=1" if start > 0 else ""
        chains.append(f"[{k}:a]{fmt},volume={float(layer.get('gain_db', 0.0))}dB{delay},apad,"
                      f"atrim=end={duration:.6f}[l{k}]")
        labels.append(f"[l{k}]")
    fade_in = float(proj.video["fade_in"])
    fade_out = min(float(proj.video["fade_out"]), duration / 4)
    mix = (f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest" if len(labels) > 1
           else f"{labels[0]}anull")
    mix += (f",afade=t=in:d={fade_in:.3f}:curve=qsin,"
            f"afade=t=out:st={duration - fade_out:.3f}:d={fade_out:.3f}:curve=qsin")
    return inputs, ";".join(chains) + ";" + mix


def render_mix(proj: Project, duration: float, out: Path, preview: bool = False) -> Path:
    a = proj.cfg["audio"]
    if not a["layers"]:
        if not preview:
            require_licenses(proj)
        print("  ! no audio layers configured - preview will have silence")
        ff.run(["-f", "lavfi", "-i", f"anullsrc=r={a['sample_rate']}:cl=stereo", "-t", f"{duration:.3f}",
                "-c:a", "aac", "-b:a", "128k", str(out)])
        return out
    if not preview:
        require_licenses(proj)
    loops = {}
    for k, layer in enumerate(a["layers"]):
        if layer.get("loop", True):
            loops[k] = build_layer_loop(proj, layer)
    inputs, graph = _build_graph(proj, duration, loops)
    spec = {"inputs": inputs, "graph": graph, "lufs": a["target_lufs"], "tp": a["true_peak"],
            "sigs": [file_sig(Path(x)) for x in inputs if Path(x).exists()], "br": a["bitrate"]}
    if is_fresh(out, spec):
        print(f"  audio cached: {out.name}")
        return out
    I, TP = float(a["target_lufs"]), float(a["true_peak"])
    # Pass 1: EBU R128 measurement (ebur128 is ~3.5x faster than loudnorm's analysis pass).
    print(f"  audio pass 1/2: measuring loudness of {duration / 60:.1f} min mix")
    err = ff.run(inputs + ["-filter_complex", graph + ",ebur128=peak=true:framelog=quiet[o]",
                           "-map", "[o]", "-f", "null", "-"], desc="loudness pass 1", capture=True)
    m = _parse_ebur128(err)
    print(f"    measured {m['i']} LUFS, true peak {m['tp']} dBTP, LRA {m['lra']} LU")
    if m["i"] is None or m["i"] < -60:
        raise SystemExit("Audio mix is silent - check layer files and gain_db.")
    # Pass 2: linear normalisation = one constant gain (identical to loudnorm linear=true,
    # without its 192 kHz resampling cost). A transparent limiter catches peaks only if needed.
    gain = I - m["i"]
    limited = m["tp"] is not None and m["tp"] + gain > TP
    chain = f"volume={gain:.3f}dB"
    if limited:
        lim = 10 ** ((TP - 0.5) / 20)       # 0.5 dB margin: alimiter works on samples, not true peak
        chain += f",alimiter=limit={lim:.5f}:attack=5:release=80:level=false,aresample={a['sample_rate']}"
    print(f"  audio pass 2/2: gain {gain:+.2f} dB{' + peak limiter' if limited else ''} -> {out.name}")
    ff.run(inputs + ["-filter_complex", graph + f",{chain}[o]", "-map", "[o]"] + aac_args(a)
           + ["-ar", str(a["sample_rate"]), str(out)],
           desc="loudness pass 2", long_running=duration > 600)
    report = {"target_lufs": I, "target_tp": TP, "pass1": m, "gain_db": round(gain, 2),
              "output_i": round(m["i"] + gain, 2) if not limited else None,
              "output_tp": round(m["tp"] + gain, 2) if not limited else None,
              "normalization_type": "linear gain" + (" + limiter" if limited else ""), "layer_seams": {}}
    if limited or duration <= 600:     # verify by measuring (short previews, or when the limiter acted)
        mo = _parse_ebur128(ff.run(["-i", str(out), "-af", "ebur128=peak=true:framelog=quiet",
                                    "-f", "null", "-"], desc="verify loudness", capture=True))
        report["output_i"], report["output_tp"] = mo["i"], mo["tp"]
    for k, f in loops.items():
        report["layer_seams"][a["layers"][k]["file"]] = seam_check(f, int(a["sample_rate"]))
    proj.save_json(f"work/audio/{out.stem}.json", report)
    print(f"    output {report['output_i']} LUFS, true peak {report['output_tp']} dBTP")
    mark_fresh(out, spec)
    return out


def aac_args(a: dict) -> list[str]:
    """Apple's AudioToolbox AAC on macOS (faster, better quality); FFmpeg's native AAC elsewhere."""
    if a.get("aac_encoder", "auto") in ("auto", "aac_at") and ff.has_encoder("aac_at"):
        return ["-c:a", "aac_at", "-b:a", a["bitrate"]]
    return ["-c:a", "aac", "-aac_coder", "fast", "-b:a", a["bitrate"]]  # default twoloop coder is ~5x slower


def _parse_ebur128(err: str) -> dict:
    s = err[err.rfind("Summary:"):]
    num = lambda pat: (float(x.group(1)) if (x := re.search(pat, s)) and x.group(1) != "-inf" else None)
    return {"i": num(r"I:\s+(-?[\d.]+|-inf) LUFS"), "lra": num(r"LRA:\s+(-?[\d.]+) LU"),
            "tp": num(r"Peak:\s+(-?[\d.]+|-inf) dBFS")}
