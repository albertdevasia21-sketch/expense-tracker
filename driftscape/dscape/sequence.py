"""Timeline planning: which clip plays when, for how long, and where every seam sits.

The 3-hour video = intro + (cycle x N) + outro, where the cycle is a few minutes
of unique, internally seamless footage whose end dissolves into its own start.
Only the cycle is ever encoded; repeats are stream-copied (zero CPU).
"""
from __future__ import annotations

import random

from .config import Project


def plan(proj: Project) -> dict:
    v = proj.video
    fps = float(v["fps"])
    loops = proj.load_json("work/loops.json")
    an = proj.load_json("work/analysis.json")
    rng = random.Random(int(v["seed"]))
    T = max(2, int(round(float(v["transition"]) * fps)))
    min_body = int(fps)
    D = int(round(proj.duration * fps))
    outro = int(round(float(v["fade_out"]) * fps))
    fade_in = int(round(float(v["fade_in"]) * fps))
    C_target = max(int(float(v["cycle_minutes"]) * 60 * fps), 1)
    N = max(1, round((D - outro) / C_target))
    C = (D - outro) // N
    outro = D - N * C          # absorb rounding so total is frame-exact

    clips = {}
    for cid, L in loops.items():
        if L["mode"] == "oneshot" and L["frames"] < 2 * T + min_body:
            print(f"  ! {cid}: too short ({L['frames']} frames) for {T}-frame dissolves as oneshot; skipped")
            continue
        clips[cid] = {**L, "weight": float(proj.clip_cfg(cid).get("weight", 1.0))}
    loopers = [c for c in clips if clips[c]["mode"] in ("loop", "pingpong")]
    if not loopers:
        raise SystemExit("Need at least one loopable clip (grade A-C) to build a cycle. "
                         "Check out/reports/analysis.md or force one with [clips.<id>] mode = \"loop\".")
    compat = an["compat"]
    max_c = max([x for row in compat.values() for x in row.values()] + [1e-6])

    def body_len(cid):
        c = clips[cid]
        if c["mode"] == "oneshot":
            return c["frames"] - 2 * T
        return max(min_body, int(rng.uniform(float(v["hold_min"]), float(v["hold_max"])) * fps) - T)

    # first unit: the most 'neutral' looper (best average compatibility) - it also hosts intro/outro
    first = min(loopers, key=lambda c: sum(compat.get(c, {}).values()) / max(1, len(compat.get(c, {}))))
    units = [{"clip": first, "body": max(body_len(first), fade_in, outro, min_body)}]
    last_used = {first: 0}
    total = units[0]["body"] + T
    while total < C:
        prev = units[-1]["clip"]
        cands = [c for c in clips if c != prev] or [prev]
        k = len(units)
        def score(c):
            s = compat.get(prev, {}).get(c, 0.0) / max_c
            age = k - last_used.get(c, -99)
            s += 0.8 / age if age > 0 else 0
            if clips[c]["mode"] == "oneshot" and age < max(3, len(clips)):
                s += 2.0
            s -= 0.15 * (clips[c]["weight"] - 1)
            return s + rng.random() * 0.35
        nxt = min(cands, key=score)
        units.append({"clip": nxt, "body": body_len(nxt)})
        last_used[nxt] = k
        total += units[-1]["body"] + T
    # cycle wraps last -> first: avoid same clip on both sides when possible
    if len(units) > 2 and units[-1]["clip"] == units[0]["clip"]:
        total -= units.pop()["body"] + T

    # make the cycle exactly C frames by stretching/shrinking looping bodies
    delta = C - sum(u["body"] + T for u in units)
    flex = [u for u in units if clips[u["clip"]]["mode"] != "oneshot"]
    for idx, u in enumerate(flex):
        share = delta // len(flex) + (1 if idx < delta % len(flex) else 0)
        u["body"] += share
    if any(u["body"] < min_body for u in flex) or units[0]["body"] < max(fade_in, 1):
        raise SystemExit("Cycle too short for these clips/transitions. Increase video.cycle_minutes or "
                         "project.duration, or reduce video.transition.")

    # positions & seam events
    pos, segs, events = 0, [], []
    for k, u in enumerate(units):
        c = clips[u["clip"]]
        n = c["frames"]
        u.update(mode=c["mode"], n=n, start=pos)
        segs.append({"type": "body", "clip": u["clip"], "s": T, "len": u["body"], "at": pos})
        if c["mode"] in ("loop", "pingpong"):
            # self-loop wrap points visible inside this unit (stream frames multiple of n)
            for p in range(n, T + u["body"] + T, n):
                if p > T:
                    events.append({"frame": pos + p - T, "kind": f"loop-wrap {u['clip']}"})
        pos += u["body"]
        nxt = units[(k + 1) % len(units)]["clip"]
        segs.append({"type": "trans", "a": u["clip"], "sa": T + u["body"], "b": nxt, "len": T, "at": pos})
        events.append({"frame": pos, "kind": f"dissolve {u['clip']} -> {nxt}", "len": T})
        pos += T
    assert pos == C, (pos, C)
    for s in segs[1:]:
        events.append({"frame": s["at"], "kind": "segment join"})
    events.append({"frame": 0, "kind": "cycle wrap (end -> start)"})
    events.sort(key=lambda e: e["frame"])

    timeline = {"fps": fps, "T": T, "C": C, "N": N, "D": D, "outro": outro, "fade_in": fade_in,
                "units": units, "segments": segs, "events": events}
    proj.save_json("work/timeline.json", timeline)
    print(f"  cycle {C / fps / 60:.2f} min x {N} + outro {outro / fps:.1f}s = {D / fps / 3600:.3f} h; "
          f"{len(units)} shots, {len(clips)} clips")
    return timeline
